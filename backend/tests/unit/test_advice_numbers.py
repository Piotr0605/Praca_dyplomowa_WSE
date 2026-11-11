"""Zgodność liczb porady z pakietem (research/advice_numbers.py) na sztucznych przykładach."""

from decimal import Decimal

from research.advice_numbers import check, numbers_in_text, payload_numbers

PAKIET = {
    "podsumowanie": {
        "przychody": "4000.00",
        "wydatki": "1150.00",
        "stopa_oszczednosci": 0.713,
        "liczba_transakcji": 4,
    },
    "wydatki_wedlug_kategorii": [
        {"kategoria": "Zakupy spożywcze", "kwota": "900.00", "udzial": 0.783},
    ],
}


def test_wyciaganie_liczb() -> None:
    liczby = numbers_in_text(
        "Wydajesz 1 150,00 zł, czyli 78,3% na zakupy; 4 transakcje po 12 zł."
    )
    assert [(n.value, n.kind) for n in liczby] == [
        (Decimal("1150.00"), "amount"),
        (Decimal(12), "amount"),
        (Decimal("78.3"), "percent"),
        (Decimal(4), "count"),
    ]


def test_liczby_pakietu() -> None:
    kwoty, procenty, liczby = payload_numbers(PAKIET)
    assert Decimal("900.00") in kwoty
    assert Decimal("71.30") in procenty
    assert Decimal(4) in liczby


def test_wartosci_wprost_pokryte() -> None:
    raport = check("Wydatki to 1150,00 zł przy 4 transakcjach (71,3%).", PAKIET)
    assert raport.uncovered == []


def test_roznica_suma_udzial_i_procent_kwoty() -> None:
    tekst = (
        "Zostaje Ci 2850,00 zł (różnica). Zakupy to 78,3% wydatków. "
        "Ograniczenie zakupów o 10% da 90,00 zł oszczędności."
    )
    raport = check(tekst, PAKIET)
    assert raport.uncovered == []


def test_liczba_bez_pokrycia() -> None:
    raport = check("Przeciętny Polak wydaje 2345,67 zł i oszczędza 33%.", PAKIET)
    assert [n.value for n in raport.uncovered] == [Decimal("2345.67"), Decimal(33)]
    assert raport.covered == 0


def test_tolerancja_zaokraglen() -> None:
    # 78,26% w pakiecie jako udział 900/1150 = 78,3: w granicach 0,5 punktu procentowego.
    raport = check("To 78% wydatków.", PAKIET)
    assert raport.uncovered == []
