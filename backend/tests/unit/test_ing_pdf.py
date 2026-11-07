"""Testy parsera wyciągów ING na sztucznym wyciągu o tym samym układzie co prawdziwy."""

import datetime as dt
import io
from decimal import Decimal

import pdfplumber
import pytest
from reportlab.pdfgen import canvas

from app.models.enums import TransactionKind
from app.parsers.ing_pdf import (
    ParsedStatement,
    StatementParseError,
    detect_kind,
    parse_amount,
    parse_ing_pdf,
    validate_statement,
)
from tests.fixtures.ing_statement import make_ing_statement, sample_transactions


@pytest.fixture(scope="module")
def wyciag() -> ParsedStatement:
    return parse_ing_pdf(make_ing_statement())


def po_opisie(wyciag: ParsedStatement, fragment: str):
    return next(t for t in wyciag.transactions if fragment in t.description)


def test_odczytuje_wszystkie_transakcje_zgodnie_z_sumami(
    wyciag: ParsedStatement,
) -> None:
    assert len(wyciag.transactions) == len(sample_transactions())
    assert validate_statement(wyciag) == []


def test_naglowek_wyciagu(wyciag: ParsedStatement) -> None:
    s = wyciag.summary
    assert (s.period_start, s.period_end) == (
        dt.date(2026, 10, 1),
        dt.date(2026, 10, 31),
    )
    assert s.opening_balance == Decimal("1000.00")
    assert (s.credits_count, s.debits_count) == (3, 22)


def test_wyciag_ma_kilka_stron_i_transakcje_dzielona() -> None:
    dane = make_ing_statement()
    with pdfplumber.open(io.BytesIO(dane)) as pdf:
        assert len(pdf.pages) >= 2


def test_transakcja_dzielona_miedzy_strony_jest_scalona(
    wyciag: ParsedStatement,
) -> None:
    """Wpłata gotówki zaczyna się na stronie 1, a adres płatnika jest na stronie 2."""
    wplata = po_opisie(wyciag, "Wpłata gotówki")

    assert wplata.amount == Decimal("2000.00")
    assert wplata.counterparty == "ul. Testowa 9"


def test_kwoty_z_separatorem_tysiecy_i_znakiem(wyciag: ParsedStatement) -> None:
    assert po_opisie(wyciag, "Płatność BLIK 02.10").amount == Decimal("-1403.86")
    assert po_opisie(wyciag, "Wynagrodzenie").amount == Decimal("5120.00")


def test_data_operacji_z_tytulu_i_data_ksiegowania(wyciag: ParsedStatement) -> None:
    karta = wyciag.transactions[0]

    assert karta.date == dt.date(2026, 9, 29)
    assert karta.booking_date == dt.date(2026, 10, 1)


def test_numer_karty_nie_trafia_do_opisu(wyciag: ParsedStatement) -> None:
    assert all("Nr karty" not in t.description for t in wyciag.transactions)
    assert all("1234xx5678" not in t.description for t in wyciag.transactions)


def test_kontrahent_z_etykiety_odbiorcy_i_platnika(wyciag: ParsedStatement) -> None:
    assert wyciag.transactions[0].counterparty == "SKLEP TESTOWY WARSZAWA"
    assert po_opisie(wyciag, "Wynagrodzenie").counterparty.startswith("FIRMA TESTOWA")


def test_waluta_obca_jest_w_opisie_a_kwota_w_pln(wyciag: ParsedStatement) -> None:
    platnosc = po_opisie(wyciag, "25,00 EUR")

    assert (platnosc.amount, platnosc.currency) == (Decimal("-106.41"), "PLN")


@pytest.mark.parametrize(
    ("fragment", "rodzaj"),
    [
        ("Płatność kartą 29.09", TransactionKind.CARD),
        ("przelew Smart Saver", TransactionKind.OWN_TRANSFER),
        ("Przelew własny", TransactionKind.OWN_TRANSFER),
        ("Płatność BLIK", TransactionKind.BLIK),
        ("Przelew na telefon", TransactionKind.BLIK),
        ("Wynagrodzenie", TransactionKind.TRANSFER),
        ("Prowizja", TransactionKind.FEE),
        ("Zwrot płatności", TransactionKind.REFUND),
        ("Wpłata gotówki", TransactionKind.CASH),
    ],
)
def test_rodzaje_operacji(
    wyciag: ParsedStatement, fragment: str, rodzaj: TransactionKind
) -> None:
    assert po_opisie(wyciag, fragment).kind == rodzaj


def test_numery_operacji_sa_unikalne_i_daja_staly_hash(wyciag: ParsedStatement) -> None:
    hashe = [t.dedup_hash for t in wyciag.transactions]

    assert len(set(hashe)) == len(hashe)
    assert parse_ing_pdf(make_ing_statement()).transactions[0].dedup_hash == hashe[0]


@pytest.mark.parametrize(
    ("zmiana", "fragment"),
    [
        ({"credits_count": 4}, "liczba uznań"),
        ({"credits_sum": Decimal("1.00")}, "suma uznań"),
        ({"debits_count": 21}, "liczba obciążeń"),
        ({"debits_sum": Decimal("1.00")}, "suma obciążeń"),
        ({"closing": Decimal("1.00")}, "saldo"),
    ],
)
def test_niezgodnosc_z_sumami_jest_wykrywana(zmiana: dict, fragment: str) -> None:
    problemy = validate_statement(
        parse_ing_pdf(make_ing_statement(summary_override=zmiana))
    )

    assert any(fragment in p for p in problemy)


def test_brakujaca_transakcja_jest_wykrywana() -> None:
    """Gdyby parser zgubił wiersz, sumy kontrolne nie będą się zgadzać."""
    wszystkie = sample_transactions()
    pelny = parse_ing_pdf(make_ing_statement(wszystkie))
    bez_jednej = ParsedStatement(pelny.summary, pelny.transactions[1:])

    assert validate_statement(bez_jednej)


@pytest.mark.parametrize("dane", [b"", b"to nie jest PDF", b"%PDF-1.4 uszkodzony"])
def test_plik_niebedacy_pdf_jest_odrzucany(dane: bytes) -> None:
    with pytest.raises(StatementParseError):
        parse_ing_pdf(dane)


def test_pdf_bez_wyciagu_jest_odrzucany() -> None:
    bufor = io.BytesIO()
    plotno = canvas.Canvas(bufor)
    plotno.drawString(100, 700, "Faktura nr 1")
    plotno.save()

    with pytest.raises(StatementParseError):
        parse_ing_pdf(bufor.getvalue())


@pytest.mark.parametrize(
    ("tekst", "kwota"),
    [
        ("-3,00", "-3.00"),
        ("1 403,86", "1403.86"),
        ("-11 000,00", "-11000.00"),
        ("0,30", "0.30"),
    ],
)
def test_odczyt_kwoty(tekst: str, kwota: str) -> None:
    assert parse_amount(tekst) == Decimal(kwota)


@pytest.mark.parametrize(
    ("tytul", "kod", "rodzaj"),
    [
        ("Opł.Przel.Expr.ELIXIR", "PRZELEW", TransactionKind.FEE),
        ("Wypłata gotówki BLIK 04.05.2026", "TR.BLIK", TransactionKind.CASH),
        ("Wpłata na cel Wesele", "PRZELEW", TransactionKind.OWN_TRANSFER),
        ("Rata", "ST.ZLEC", TransactionKind.TRANSFER),
        ("Coś nowego", None, TransactionKind.OTHER),
    ],
)
def test_rodzaj_z_tytulu_i_kodu(
    tytul: str, kod: str | None, rodzaj: TransactionKind
) -> None:
    assert detect_kind(tytul, kod) == rodzaj
