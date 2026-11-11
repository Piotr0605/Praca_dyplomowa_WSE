"""Anonimizacja (app/ai/anonymizer.py) na sztucznych przykładach o strukturze tytułów z wyciągów ING."""

import pytest

from app.ai.anonymizer import anonymize, luhn_valid, pesel_valid


def maska(tekst: str) -> str:
    return anonymize(tekst).text


# --- dane o stałym formacie -------------------------------------------------------------------


@pytest.mark.parametrize(
    "numer",
    [
        "11 2222 3333 4444 5555 6666 7777",
        "11222233334444555566667777",
        "PL11222233334444555566667777",
        "PL 11 2222 3333 4444 5555 6666 7777",
    ],
)
def test_iban(numer: str) -> None:
    assert maska(f"Przelew | {numer} Firma") == "Przelew | [IBAN] Firma"


def test_krotszy_numer_nie_jest_ibanem() -> None:
    assert maska("Faktura 1234 5678 9012") == "Faktura 1234 5678 9012"


@pytest.mark.parametrize("numer", ["1234xx5678", "4111XX1111", "5555**4444"])
def test_karta_zamaskowana_jak_w_wyciagu(numer: str) -> None:
    assert maska(f"Płatność kartą 29.09.2026 Nr karty {numer}") == (
        "Płatność kartą 29.09.2026 Nr karty [KARTA]"
    )


def test_pelny_numer_karty_z_suma_luhna() -> None:
    assert luhn_valid("4111111111111111")
    assert maska("karta 4111 1111 1111 1111") == "karta [KARTA]"
    # 16 cyfr bez poprawnej sumy kontrolnej to nie numer karty.
    assert not luhn_valid("4111111111111112")
    assert "[KARTA]" not in maska("nr 4111 1111 1111 1112")


@pytest.mark.parametrize(
    "telefon",
    ["+48xxxxxx123", "+48 601 234 567", "601234567", "601-234-567", "+48601234567"],
)
def test_telefon(telefon: str) -> None:
    assert maska(f"Przelew na telefon {telefon}") == "Przelew na telefon [TELEFON]"


@pytest.mark.parametrize(
    "tekst",
    [
        "Płatność kartą 29.09.2026",
        "Kwota: 1 234,56 PLN",
        "Kwota: 45,99 PLN",
        "Faktura FV/123/2026",
        "Wynagrodzenie 10/2026",
    ],
)
def test_daty_i_kwoty_bez_zmian(tekst: str) -> None:
    assert maska(tekst) == tekst


@pytest.mark.parametrize(
    "email", ["jan.kowalski@gmail.com", "a.nowak+bank@poczta.onet.pl", "anna_99@wp.pl"]
)
def test_email(email: str) -> None:
    assert maska(f"kontakt {email}, dziękuję") == "kontakt [EMAIL], dziękuję"


def test_pesel_z_suma_kontrolna_i_data() -> None:
    assert pesel_valid("44051401359")
    assert maska("Składka 44051401359") == "Składka [PESEL]"
    # 11 cyfr z błędną sumą (np. numer transakcji BLIK) zostaje.
    assert not pesel_valid("12345678901")
    assert maska("Nr transakcji 12345678901") == "Nr transakcji 12345678901"


def test_po_slowie_pesel_zawsze() -> None:
    assert maska("PESEL: 12345678901") == "PESEL: [PESEL]"


@pytest.mark.parametrize(
    ("tekst", "wynik"),
    [
        ("ul. Przykładowa 1", "[ADRES]"),
        ("UL. Lipowa 12/4", "[ADRES]"),
        ("al. Jana Pawła II 33/4", "[ADRES]"),
        ("ul. 3 Maja 65", "[ADRES]"),
        ("os. Słoneczne 7a", "[ADRES]"),
        ("00-001 Warszawa", "[ADRES]"),
        ("ul. Długa 5 15-001 Białystok", "[ADRES] [ADRES]"),
    ],
)
def test_adres(tekst: str, wynik: str) -> None:
    assert maska(tekst) == wynik


# --- osoby ------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "osoba",
    [
        "JAN KOWALSKI",
        "Anna Nowak",
        "anna nowak",
        "KOWALSKA ANNA",
        "Katarzyna Nowak-Wiśniewska",
        "OLENA SHEVCHENKO",
    ],
)
def test_imie_ze_slownika_z_nazwiskiem(osoba: str) -> None:
    assert maska(f"Za obiad | {osoba}") == "Za obiad | [OSOBA]"


@pytest.mark.parametrize(
    ("tekst", "wynik"),
    [
        (
            "Przelew na telefon Dla Anna Od JAN TESTOWY",
            "Przelew na telefon Dla [OSOBA] Od [OSOBA]",
        ),
        ("Prezent dla Ola", "Prezent dla [OSOBA]"),
        ("Za obiad kasia", "Za obiad [OSOBA]"),
    ],
)
def test_imie_samo_i_zdrobnienia(tekst: str, wynik: str) -> None:
    assert maska(tekst) == wynik


def test_osoba_spoza_slownika_po_dla_i_od() -> None:
    assert maska("Przelew na telefon Dla Bożydar Od GNIEWOMIR TESTOWY") == (
        "Przelew na telefon Dla [OSOBA] Od [OSOBA]"
    )


def test_osoba_spoza_slownika_po_numerze_rachunku() -> None:
    assert (
        maska("Zwrot | 11222233334444555566667777 Pierre Baran")
        == "Zwrot | [IBAN] [OSOBA]"
    )


def test_osoba_spoza_slownika_z_koncowka_nazwiska() -> None:
    assert maska("Zwrot za bilety | KEVIN MALINOWSKI") == "Zwrot za bilety | [OSOBA]"
    assert maska("Czynsz | Mehmet Dudek") == "Czynsz | [OSOBA]"


def test_osoba_spoza_slownika_przed_adresem() -> None:
    assert maska("Czynsz | Pierre Baran ul. Wiejska 1") == "Czynsz | [OSOBA] [ADRES]"


def test_kontakt_przy_przelewie_na_telefon() -> None:
    assert maska("Przelew na telefon +48xxxxxx123 | Hans") == (
        "Przelew na telefon [TELEFON] | [OSOBA]"
    )


# --- nazwy firm i teksty bez danych osobowych ---------------------------------------------------


@pytest.mark.parametrize(
    "firma",
    [
        "SALON ANNA",
        "KWIACIARNIA ROZA",
        "PIEKARNIA JAN",
        "APTEKA DR.MAX",
        "HOTEL MARIA",
        "KAWIARNIA ZOFIA",
        "ZAKLAD FRYZJERSKI KAMIL",
        "BIEDRONKA GDAŃSK",
        "ORANGE POLSKA S.A.",
        "URZĄD SKARBOWY",
        "KANCELARIA NOWAK I WSPÓLNICY",
        "FIRMA TESTOWA SPÓŁKA Z O.O.",
        "Spotify",
    ],
)
def test_firma_nie_jest_maskowana(firma: str) -> None:
    assert (
        maska(f"Płatność kartą 01.10.2026 | {firma}")
        == f"Płatność kartą 01.10.2026 | {firma}"
    )


def test_sklep_przed_adresem_przy_platnosci() -> None:
    assert maska("Płatność BLIK 02.10.2026 | PayU ul. Testowa 2 60-001 Poznań") == (
        "Płatność BLIK 02.10.2026 | PayU [ADRES] [ADRES]"
    )


def test_sklep_przed_adresem_przy_platnosci_bez_slowa_firmowego() -> None:
    """„Stokrotka” nie ma słowa firmowego ani wielkiej litery w środku: chroni ją reguła płatności."""
    assert maska("Płatność kartą 01.10.2026 | Stokrotka ul. Polna 1") == (
        "Płatność kartą 01.10.2026 | Stokrotka [ADRES]"
    )


def test_firma_przed_adresem_w_przelewie() -> None:
    assert maska("Faktura | TECHSOFT SP. Z O.O. ul. Fabryczna 3") == (
        "Faktura | TECHSOFT SP. Z O.O. [ADRES]"
    )


@pytest.mark.parametrize(
    "tekst",
    [
        "Opłata za prowadzenie rachunku",
        "przelew Smart Saver",
        "Wynagrodzenie wrzesień",
        "Zakupy spożywcze",
        "",
    ],
)
def test_tekst_bez_danych_bez_zmian(tekst: str) -> None:
    assert maska(tekst) == tekst


# --- wynik funkcji ----------------------------------------------------------------------------


def test_fragmenty_z_typem_i_polozeniem() -> None:
    tekst = "Za obiad | 11222233334444555566667777 JAN KOWALSKI ul. Lipowa 1"
    wynik = anonymize(tekst)
    assert [(tekst[s.start : s.end], s.type) for s in wynik.spans] == [
        ("11222233334444555566667777", "IBAN"),
        ("JAN KOWALSKI", "OSOBA"),
        ("ul. Lipowa 1", "ADRES"),
    ]
    assert wynik.text == "Za obiad | [IBAN] [OSOBA] [ADRES]"


def test_powtorna_anonimizacja_nic_nie_zmienia() -> None:
    raz = maska("Przelew na telefon +48xxxxxx123 Dla Anna Od JAN KOWALSKI")
    assert maska(raz) == raz


def test_w_wyniku_nie_ma_oryginalnych_danych() -> None:
    tekst = "Za obiad | PL11222233334444555566667777 Anna Nowak, anna.nowak@wp.pl, 601234567"
    wynik = maska(tekst)
    for fragment in ("1122223333", "Anna", "Nowak", "anna.nowak", "601234567"):
        assert fragment not in wynik
