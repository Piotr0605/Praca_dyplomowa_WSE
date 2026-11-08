"""Testy importera CSV: profil, odczyt według profilu i rozpoznawanie formatu nieznanego pliku."""

import hashlib
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.models.enums import TransactionKind
from app.parsers.csv_detect import (
    detect,
    fold,
    guess_decimal_separator,
    guess_delimiter,
    guess_encoding,
    profile_matches,
)
from app.parsers.csv_generic import (
    CsvFormatError,
    guess_kind,
    parse_amount_text,
    parse_csv,
    unique_headers,
)
from app.parsers.csv_profile import CsvProfile, builtin_profiles
from tests.fixtures.csv_samples import (
    ING_ROWS,
    make_ing_csv,
    make_other_bank_csv,
)

ING = builtin_profiles()["ing"]


def inny_bank(**zmiany) -> CsvProfile:
    ustawienia = {
        "bank_name": "Inny bank",
        "encoding": "utf-8-sig",
        "delimiter": ",",
        "date_format": "%d/%m/%Y",
        "decimal_separator": ".",
        "columns": {
            "date": "Data operacji",
            "credit": "Uznania",
            "debit": "Obciążenia",
            "currency": "Waluta",
            "description": ["Opis"],
            "counterparty": "Odbiorca/Nadawca",
        },
    }
    return CsvProfile.model_validate({**ustawienia, **zmiany})


# --- kwoty i nazwy kolumn ---


@pytest.mark.parametrize(
    ("tekst", "separator", "kwota"),
    [
        ("-1 403,86", ",", Decimal("-1403.86")),
        ("1.403,86 PLN", ",", Decimal("1403.86")),
        ("-1\xa0403,86", ",", Decimal("-1403.86")),
        ("+12,5", ",", Decimal("12.5")),
        ("1,250.00", ".", Decimal("1250.00")),
        ("-7", ".", Decimal(-7)),
        ("", ",", None),
        ("  ", ",", None),
    ],
)
def test_kwoty(tekst: str, separator: str, kwota: Decimal | None) -> None:
    assert parse_amount_text(tekst, separator) == kwota


@pytest.mark.parametrize("tekst", ["abc", "PLN", "12,345", "1-2", "11 2222 3333,1,2"])
def test_niepoprawne_kwoty(tekst: str) -> None:
    with pytest.raises(ValueError):
        parse_amount_text(tekst, ",")


def test_powtorzone_i_puste_nazwy_kolumn() -> None:
    assert unique_headers(["Waluta", "Kwota", "Waluta", "", "Waluta"]) == [
        "Waluta",
        "Kwota",
        "Waluta (2)",
        "Kolumna 4",
        "Waluta (3)",
    ]


# --- profil ---


def test_profil_wymaga_kwoty_albo_uznan_i_obciazen() -> None:
    kolumny = {"date": "Data", "description": ["Opis"]}
    with pytest.raises(ValidationError, match="kolumnę kwoty"):
        inny_bank(columns=kolumny)
    with pytest.raises(ValidationError, match="kolumnę kwoty"):
        inny_bank(columns={**kolumny, "credit": "Uznania"})
    with pytest.raises(ValidationError, match="nie oba naraz"):
        inny_bank(columns={**kolumny, "amount": "Kwota", "debit": "Obciążenia"})


@pytest.mark.parametrize(
    "zmiana",
    [
        {"encoding": "utf-16"},
        {"delimiter": ":"},
        {"date_format": "%A"},
        {"default_currency": "zł"},
        {"bank_name": ""},
        {"reference_namespace": "a:b"},
        {"nieznane_pole": 1},
    ],
)
def test_profil_odrzuca_nieobslugiwane_ustawienia(zmiana: dict) -> None:
    with pytest.raises(ValidationError):
        inny_bank(**zmiana)


def test_profil_ing_jest_wbudowany() -> None:
    assert ING.bank_name == "ING"
    assert ING.reference_namespace == "ING"


# --- odczyt według profilu ING ---


def test_odczyt_pliku_ing() -> None:
    wynik = parse_csv(make_ing_csv(), ING)

    # 8 wierszy, z czego jedna blokada kartowa bez kwoty transakcji.
    assert len(wynik.transactions) == len(ING_ROWS) - 1
    assert wynik.skipped == 1
    pierwsza = wynik.transactions[0]
    assert str(pierwsza.date) == "2026-10-01"
    assert str(pierwsza.booking_date) == "2026-10-02"
    assert pierwsza.amount == Decimal("-45.99")
    assert pierwsza.currency == "PLN"
    assert pierwsza.counterparty == "SKLEP TESTOWY WARSZAWA"
    assert sum(t.amount for t in wynik.transactions) == Decimal("3565.17")


def test_ing_rodzaje_operacji() -> None:
    rodzaje = [t.kind for t in parse_csv(make_ing_csv(), ING).transactions]
    assert rodzaje == [
        TransactionKind.CARD,
        TransactionKind.OWN_TRANSFER,
        TransactionKind.BLIK,
        TransactionKind.TRANSFER,
        TransactionKind.REFUND,
        TransactionKind.CASH,
        TransactionKind.FEE,
    ]


def test_numer_karty_nie_trafia_do_opisu() -> None:
    opis = parse_csv(make_ing_csv(), ING).transactions[0].description
    assert "1234xx5678" not in opis
    assert opis == "Płatność kartą 01.10.2026"


def test_klucz_duplikatow_ing_jak_w_wyciagu_pdf() -> None:
    """Ten sam numer operacji z PDF i z CSV daje ten sam klucz: import obu nie dubluje danych."""
    pierwsza = parse_csv(make_ing_csv(), ING).transactions[0]
    oczekiwany = hashlib.sha256(b"ING:202610020000000001").hexdigest()
    assert pierwsza.dedup_hash == oczekiwany


def test_metadane_i_stopka_sa_pomijane() -> None:
    """Nad tabelą ING są dane właściciela, pod nią stopka; żadne nie są transakcją."""
    opisy = {t.description for t in parse_csv(make_ing_csv(), ING).transactions}
    assert not any("Saldo" in o or "Dokument" in o for o in opisy)


def test_plik_innego_banku_nie_pasuje_do_profilu_ing() -> None:
    assert profile_matches(make_ing_csv(), ING)
    assert not profile_matches(make_other_bank_csv(), ING)
    with pytest.raises(CsvFormatError, match="nie pasuje do profilu „ING”"):
        parse_csv(make_other_bank_csv(), ING)


def test_bledne_kodowanie() -> None:
    utf8 = make_ing_csv().decode("cp1250").encode("utf-8")
    # W UTF-8 nazwy kolumn z polskimi literami odczytane jako cp1250 nie pasują do profilu.
    assert not profile_matches(utf8, ING)
    with pytest.raises(CsvFormatError, match="kodowaniu"):
        parse_csv(make_ing_csv(), inny_bank(encoding="utf-8-sig"))


def test_bledny_wiersz_zatrzymuje_import() -> None:
    zly = list(ING_ROWS)
    zly[2] = ("02.10.2026", *zly[2][1:])
    with pytest.raises(CsvFormatError, match="wiersz 21: data „02.10.2026”"):
        parse_csv(make_ing_csv(zly), ING)

    zla_kwota = list(ING_ROWS)
    zla_kwota[0] = (*zla_kwota[0][:6], "dużo", "")
    with pytest.raises(CsvFormatError, match="nie rozpoznano kwoty"):
        parse_csv(make_ing_csv(zla_kwota), ING)


def test_plik_bez_transakcji() -> None:
    with pytest.raises(CsvFormatError, match="nie zawiera żadnej transakcji"):
        parse_csv(make_ing_csv([]), ING)


# --- odczyt pliku innego banku ---


def test_osobne_kolumny_uznan_i_obciazen() -> None:
    wynik = parse_csv(make_other_bank_csv(), inny_bank())

    assert [t.amount for t in wynik.transactions] == [
        Decimal("-123.45"),
        Decimal("-123.45"),
        Decimal("1250.00"),
        Decimal("-7.00"),
    ]
    assert wynik.transactions[3].currency == "EUR"
    assert wynik.transactions[3].kind is TransactionKind.FEE
    assert wynik.transactions[2].description == "Zwrot za bilety, część 1"


def test_identyczne_zakupy_tego_samego_dnia_nie_sa_duplikatem() -> None:
    """Bez numeru operacji klucz to data, kwota i opis z numerem kolejnym w pliku."""
    pierwszy, drugi = parse_csv(make_other_bank_csv(), inny_bank()).transactions[:2]
    assert pierwszy.dedup_hash != drugi.dedup_hash


def test_ponowny_odczyt_daje_te_same_klucze() -> None:
    raz = parse_csv(make_other_bank_csv(), inny_bank()).transactions
    dwa = parse_csv(make_other_bank_csv(), inny_bank()).transactions
    assert [t.dedup_hash for t in raz] == [t.dedup_hash for t in dwa]


def test_kwota_w_obu_kolumnach_jest_bledem() -> None:
    wiersze = [("03/10/2026", "Coś", "", "1.00", "2.00", "PLN")]
    with pytest.raises(CsvFormatError, match="jednocześnie w uznaniach i obciążeniach"):
        parse_csv(make_other_bank_csv(wiersze), inny_bank())


def test_waluta_musi_byc_kodem() -> None:
    wiersze = [("03/10/2026", "Coś", "", "", "2.00", "zł")]
    with pytest.raises(CsvFormatError, match="nie jest kodem ISO"):
        parse_csv(make_other_bank_csv(wiersze), inny_bank())


def test_za_duza_kwota() -> None:
    wiersze = [("03/10/2026", "Coś", "", "", "10000000000.00", "PLN")]
    with pytest.raises(CsvFormatError, match="za duża"):
        parse_csv(make_other_bank_csv(wiersze), inny_bank())


@pytest.mark.parametrize(
    ("opis", "rodzaj", "wynik"),
    [
        ("Zakup", "Płatność kartą", TransactionKind.CARD),
        ("Przelew na telefon BLIK", None, TransactionKind.BLIK),
        ("Opłata za kartę", None, TransactionKind.FEE),
        ("Wypłata z bankomatu", None, TransactionKind.CASH),
        ("Czynsz", "Przelew wychodzący", TransactionKind.TRANSFER),
        ("Przelew własny", "Przelew", TransactionKind.OWN_TRANSFER),
        ("Coś", None, TransactionKind.OTHER),
    ],
)
def test_rodzaj_operacji_innych_bankow(
    opis: str, rodzaj: str | None, wynik: TransactionKind
) -> None:
    assert guess_kind(opis, rodzaj) is wynik


# --- rozpoznawanie formatu ---


def test_fold() -> None:
    assert fold("  Tytuł  OPERACJI ") == "tytul operacji"
    assert fold("Obciążenia") == "obciazenia"


def test_kodowanie() -> None:
    tekst = "Data;Opis\n2026-10-01;Zażółć gęślą jaźń\n"
    assert guess_encoding(tekst.encode("utf-8-sig")) == "utf-8-sig"
    assert guess_encoding(tekst.encode("utf-8")) == "utf-8-sig"
    assert guess_encoding(tekst.encode("cp1250")) == "cp1250"
    assert guess_encoding(tekst.encode("iso-8859-2")) == "iso-8859-2"


def test_separator() -> None:
    assert guess_delimiter("a;b;c\n1;2;3\n") == ";"
    assert guess_delimiter('a,b,c\n1,"2,5",3\n') == ","
    assert guess_delimiter("a\tb\n1\t2\n") == "\t"
    with pytest.raises(CsvFormatError):
        guess_delimiter("jedna kolumna\nbez separatora\n")


def test_separator_dziesietny() -> None:
    assert guess_decimal_separator(["-12,50", "1 403,86"]) == ","
    assert guess_decimal_separator(["1,250.00", "-7.5"]) == "."
    assert guess_decimal_separator(["1.403,86 PLN"]) == ","


def test_rozpoznanie_pliku_ing() -> None:
    wynik = detect(make_ing_csv())

    assert (wynik.encoding, wynik.delimiter, wynik.header_row) == ("cp1250", ";", 17)
    assert wynik.date_format == "%Y-%m-%d"
    assert wynik.decimal_separator == ","
    assert wynik.missing == []
    kolumny = ING.columns.model_dump()
    for rola in ("date", "booking_date", "amount", "currency", "counterparty"):
        assert wynik.columns[rola] == kolumny[rola], rola
    assert wynik.columns["description"] == ["Tytuł"]
    assert wynik.columns["reference"] == "Nr transakcji"
    assert len(wynik.sample_rows) == 5


def test_rozpoznanie_pliku_innego_banku() -> None:
    wynik = detect(make_other_bank_csv())

    assert (wynik.encoding, wynik.delimiter, wynik.header_row) == ("utf-8-sig", ",", 0)
    assert wynik.date_format == "%d/%m/%Y"
    assert wynik.decimal_separator == "."
    assert wynik.columns["amount"] is None
    assert (wynik.columns["credit"], wynik.columns["debit"]) == (
        "Uznania",
        "Obciążenia",
    )
    assert wynik.columns["description"] == ["Opis"]
    assert wynik.missing == []


def test_rozpoznanie_po_zawartosci_gdy_nazwy_sa_nieznane() -> None:
    plik = b"Dzien;Tekst;Suma\n2026-10-01;Zakupy w sklepie;-12,50\n2026-10-02;Kino;-30,00\n"
    wynik = detect(plik)

    assert wynik.header_row == 0
    assert wynik.columns["date"] == "Dzien"
    assert wynik.columns["amount"] == "Suma"
    assert wynik.columns["description"] == ["Tekst"]
    assert wynik.date_format == "%Y-%m-%d"


def test_numer_konta_nie_jest_kwota() -> None:
    plik = b"Dzien;Konto;Opis\n2026-10-01;11 2222 3333;Zakupy\n2026-10-02;11 2222 3333;Kino\n"
    wynik = detect(plik)

    assert wynik.columns["amount"] is None
    assert "amount" in wynik.missing


def test_wymuszone_kodowanie_i_separator() -> None:
    wynik = detect(make_ing_csv(), encoding="cp1250", delimiter=",")
    assert (wynik.encoding, wynik.delimiter) == ("cp1250", ",")


def test_propozycja_tworzy_dzialajacy_profil() -> None:
    """Profil z samej propozycji detektora odczytuje plik tak samo jak profil wbudowany."""
    wynik = detect(make_ing_csv())
    profil = CsvProfile(
        bank_name="ING z kreatora",
        encoding=wynik.encoding,
        delimiter=wynik.delimiter,
        date_format=wynik.date_format,
        decimal_separator=wynik.decimal_separator,
        columns={k: v for k, v in wynik.columns.items() if v},
    )
    z_kreatora = parse_csv(make_ing_csv(), profil).transactions
    wbudowany = parse_csv(make_ing_csv(), ING).transactions
    assert [(t.date, t.amount, t.description) for t in z_kreatora] == [
        (t.date, t.amount, t.description) for t in wbudowany
    ]


def test_kwota_blokady_i_saldo_nie_sa_kwota_operacji() -> None:
    """„Kwota blokady” i „Saldo” wyglądają jak kwota, ale nią nie są."""
    plik = (
        b"Data;Opis;Kwota blokady;Saldo po operacji;Kwota (PLN)\n"
        b"2026-10-01;Zakupy;-12,50;100,00;-12,50\n"
        b"2026-10-02;Kino;0,00;70,00;-30,00\n"
    )
    assert detect(plik).columns["amount"] == "Kwota (PLN)"
