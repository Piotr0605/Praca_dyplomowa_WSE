"""Testy silnika kategoryzacji (czysta funkcja) i słownika reguł systemowych."""

import json
from decimal import Decimal

import pytest

from app.categorization.engine import (
    Rule,
    TransactionText,
    categorize,
    rule_from_correction,
    rule_matches,
    same_rule,
)
from app.models.enums import CategorizedBy, RuleMatchType, RuleSource, TransactionKind
from app.services.categorization_service import SYSTEM_RULES_FILE

SPOZYWCZE, PALIWO, TRANSPORT, RESTAURACJE, WLASNE, PENSJA, MOJA = range(1, 8)


def tx(
    opis: str = "Płatność kartą",
    kontrahent: str | None = None,
    kwota: str = "-10.00",
    rodzaj: TransactionKind = TransactionKind.CARD,
) -> TransactionText:
    return TransactionText(opis, kontrahent, Decimal(kwota), rodzaj)


def systemowa(wzorzec: str, kategoria: int, **pola) -> Rule:
    return Rule(wzorzec, RuleMatchType.CONTAINS, kategoria, RuleSource.SYSTEM, **pola)


def uzytkownika(
    wzorzec: str, kategoria: int, typ=RuleMatchType.EXACT_COUNTERPARTY, **pola
):
    return Rule(wzorzec, typ, kategoria, RuleSource.USER, id=99, **pola)


SLOWNIK = [
    systemowa("żabka", SPOZYWCZE),
    systemowa("orlen", PALIWO),
    systemowa("bp", PALIWO),
    systemowa("uber", TRANSPORT),
    systemowa("uber eats", RESTAURACJE),
    systemowa("wynagrodzenie", PENSJA, sign=1),
]


def kategoria(t: TransactionText, uzytkownik=(), slownik=SLOWNIK) -> int | None:
    wynik = categorize(t, uzytkownik, slownik, WLASNE)
    return wynik.category_id if wynik else None


@pytest.mark.parametrize(
    "kontrahent",
    ["ZABKA Z4244 K.2 BIALYSTOK", "Żabka Polska", "żabka", "SKLEP ŻABKA"],
)
def test_wielkosc_liter_i_polskie_znaki(kontrahent: str) -> None:
    assert kategoria(tx(kontrahent=kontrahent)) == SPOZYWCZE


def test_dopasowanie_calych_slow() -> None:
    assert kategoria(tx(kontrahent="BP STACJA 12")) == PALIWO
    assert kategoria(tx(kontrahent="ABPX SP. Z O.O.")) is None
    assert kategoria(tx(kontrahent="UBERTRANS")) is None


def test_wzorzec_w_opisie() -> None:
    assert kategoria(tx(opis="Płatność BLIK orlen.pl", kontrahent="PayU")) == PALIWO


def test_dluzszy_wzorzec_jest_bardziej_konkretny() -> None:
    assert kategoria(tx(kontrahent="UBER EATS WARSZAWA")) == RESTAURACJE
    assert kategoria(tx(kontrahent="UBER BV")) == TRANSPORT


def test_znak_kwoty() -> None:
    wplyw = tx(
        opis="Wynagrodzenie za wrzesień",
        kwota="5200.00",
        rodzaj=TransactionKind.TRANSFER,
    )
    zwrot = tx(
        opis="Zwrot wynagrodzenie", kwota="-100.00", rodzaj=TransactionKind.TRANSFER
    )
    assert kategoria(wplyw) == PENSJA
    assert kategoria(zwrot) is None


def test_przelew_wlasny_ma_pierwszenstwo() -> None:
    t = tx(opis="przelew Smart Saver orlen", rodzaj=TransactionKind.OWN_TRANSFER)
    wynik = categorize(t, [], SLOWNIK, WLASNE)
    assert wynik is not None
    assert (wynik.category_id, wynik.categorized_by, wynik.rule) == (
        WLASNE,
        CategorizedBy.SYSTEM_RULE,
        None,
    )


def test_regula_uzytkownika_wygrywa_ze_slownikiem() -> None:
    t = tx(kontrahent="ORLEN STACJA 185")
    wynik = categorize(t, [uzytkownika("orlen stacja 185", MOJA)], SLOWNIK, WLASNE)
    assert wynik is not None
    assert (wynik.category_id, wynik.categorized_by) == (MOJA, CategorizedBy.USER_RULE)
    assert wynik.rule is not None and wynik.rule.id == 99


def test_dokladny_kontrahent_przed_fragmentem() -> None:
    reguly = [
        uzytkownika("sklep", SPOZYWCZE, RuleMatchType.CONTAINS, priority=5),
        uzytkownika("Sklep Testowy", MOJA),
    ]
    assert kategoria(tx(kontrahent="SKLEP TESTOWY"), reguly) == MOJA
    assert kategoria(tx(kontrahent="SKLEP INNY"), reguly) == SPOZYWCZE


def test_dokladny_kontrahent_wymaga_calej_nazwy() -> None:
    regula = uzytkownika("Sklep Testowy", MOJA)
    assert rule_matches(regula, tx(kontrahent="  sklep   testowy "))
    assert not rule_matches(regula, tx(kontrahent="Sklep Testowy Bis"))
    assert not rule_matches(regula, tx(opis="Sklep Testowy"))


def test_wyzszy_priorytet() -> None:
    reguly = [
        uzytkownika("kino", MOJA, RuleMatchType.CONTAINS),
        uzytkownika("kino", SPOZYWCZE, RuleMatchType.CONTAINS, priority=1),
    ]
    assert kategoria(tx(kontrahent="KINO"), reguly) == SPOZYWCZE


def test_regex() -> None:
    regula = Rule(r"stacja \d+", RuleMatchType.REGEX, PALIWO, RuleSource.SYSTEM)
    assert rule_matches(regula, tx(kontrahent="STACJA 185"))
    assert not rule_matches(regula, tx(kontrahent="STACJA"))


def test_brak_dopasowania() -> None:
    assert categorize(tx(kontrahent="Jan Kowalski"), [], SLOWNIK, WLASNE) is None


def test_regula_z_poprawki() -> None:
    regula = rule_from_correction(tx(kontrahent=" Pyszne.pl Wroclaw "), MOJA)
    assert regula is not None
    assert (regula.pattern, regula.match_type, regula.source) == (
        "Pyszne.pl Wroclaw",
        RuleMatchType.EXACT_COUNTERPARTY,
        RuleSource.USER,
    )
    # Sam opis jest za ogólny: reguła nie powstaje.
    assert rule_from_correction(tx(opis="Płatność kartą 01.10.2026"), MOJA) is None


def test_ta_sama_regula() -> None:
    a = uzytkownika("Sklep Testowy", MOJA)
    assert same_rule(a, uzytkownika("SKLEP TESTOWY", SPOZYWCZE))
    assert not same_rule(a, uzytkownika("Sklep Testowy", MOJA, RuleMatchType.CONTAINS))


# --- słownik systemowy ---

SLOWNIK_PLIK = json.loads(SYSTEM_RULES_FILE.read_text(encoding="utf-8"))
WZORCE = [w for grupa in SLOWNIK_PLIK["rules"] for w in grupa["contains"]]


def test_slownik_ma_wersje() -> None:
    assert SLOWNIK_PLIK["version"]


def test_wzorce_sie_nie_powtarzaja() -> None:
    from app.core.text import fold

    zlozone = [fold(w) for w in WZORCE]
    assert len(zlozone) == len(set(zlozone))


@pytest.mark.parametrize(
    ("kontrahent", "kategoria_nazwa"),
    [
        ("ZABKA Z4244 K.2 BIALYSTOK", "Zakupy spożywcze"),
        ("ORLEN STACJA NR 185", "Paliwo"),
        ("Pyszne.pl Wroclaw POL", "Restauracje"),
        ("BOLT.EU/O/2610", "Transport"),
        ("NETFLIX.COM", "Subskrypcje"),
        ("Google Play", "Subskrypcje"),
        ("APTEKA DOZ", "Zdrowie"),
        ("CINEMA CITY BONARKA", "Rozrywka"),
        ("H&M HENNES", "Odzież"),
        ("PLAYSTATION NETWORK", "Rozrywka"),
    ],
)
def test_przyklady_ze_slownika(kontrahent: str, kategoria_nazwa: str) -> None:
    nazwy = {i: g["category"] for i, g in enumerate(SLOWNIK_PLIK["rules"])}
    reguly = [
        systemowa(w, i, sign=g.get("sign"))
        for i, g in enumerate(SLOWNIK_PLIK["rules"])
        for w in g["contains"]
    ]
    wynik = kategoria(tx(kontrahent=kontrahent), slownik=reguly)
    assert wynik is not None and nazwy[wynik] == kategoria_nazwa
