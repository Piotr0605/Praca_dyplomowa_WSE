"""Testy narzędzi badania (research/): statystyka, symulacja H2 i etykietowanie, na sztucznych danych."""

from decimal import Decimal

import pytest

from app.categorization.engine import TransactionText
from app.models.enums import TransactionKind
from research.data import Item, group_key, load_labels, save_labels
from research.label import groups_to_label, run
from research.simulate import evaluate, mcnemar_exact, month_metrics, simulate, wilson

SLOWNIK = {
    "version": "test",
    "rules": [{"category": "Paliwo", "contains": ["orlen"]}],
}


def item(miesiac: int, klucz: str, kontrahent: str | None, rodzaj=TransactionKind.CARD):
    return Item(
        miesiac,
        klucz,
        TransactionText("Płatność kartą", kontrahent, Decimal(-10), rodzaj),
    )


def test_mcnemar() -> None:
    assert mcnemar_exact(0, 0) == 1.0
    assert mcnemar_exact(5, 5) == 1.0
    assert mcnemar_exact(0, 10) == pytest.approx(2 / 1024)
    assert mcnemar_exact(10, 0) == mcnemar_exact(0, 10)
    assert mcnemar_exact(2, 8) == pytest.approx(0.109375)


def test_wilson() -> None:
    dol, gora = wilson(8, 10)
    assert dol == pytest.approx(0.4902, abs=1e-4)
    assert gora == pytest.approx(0.9433, abs=1e-4)
    assert wilson(0, 0) == (0.0, 1.0)


def test_symulacja_uczy_sie_od_kolejnego_miesiaca() -> None:
    items = [item(m, f"s{m}", "Sklep X") for m in (1, 2, 3)]
    items += [item(m, f"o{m}", "ORLEN 7") for m in (1, 2, 3)]
    etykiety = {f"s{m}": "Zakupy spożywcze" for m in (1, 2, 3)} | {
        f"o{m}": "Paliwo" for m in (1, 2, 3)
    }

    wyniki = simulate(items, etykiety, SLOWNIK)

    a = {o.key: o.correct for o in wyniki["A"]}
    b = {o.key: o.correct for o in wyniki["B"]}
    assert a == {
        "s1": False,
        "s2": False,
        "s3": False,
        "o1": True,
        "o2": True,
        "o3": True,
    }
    # Poprawka z miesiąca 1 działa od miesiąca 2, a nie w tym samym miesiącu.
    assert b == {
        "s1": False,
        "s2": True,
        "s3": True,
        "o1": True,
        "o2": True,
        "o3": True,
    }


def test_nowa_poprawka_zastepuje_regule() -> None:
    items = [item(m, f"s{m}", "Sklep X") for m in (1, 2, 3)]
    etykiety = {"s1": "Odzież", "s2": "Zakupy spożywcze", "s3": "Zakupy spożywcze"}

    b = {o.key: o.correct for o in simulate(items, etykiety, SLOWNIK)["B"]}

    assert b == {"s1": False, "s2": False, "s3": True}


def test_przelewy_wlasne_i_bez_etykiety_poza_ocena() -> None:
    items = [
        item(1, "w", "Smart Saver", TransactionKind.OWN_TRANSFER),
        item(1, "x", "Sklep X"),
        item(1, "brak", "Sklep Y"),
    ]
    wyniki = simulate(items, {"w": "Przelewy własne", "x": "Inne"}, SLOWNIK)
    assert [o.key for o in wyniki["A"]] == ["x"]


def test_miary_miesieczne() -> None:
    items = [item(1, "o", "ORLEN"), item(1, "s", "Sklep"), item(1, "t", "Bez reguły")]
    etykiety = {"o": "Paliwo", "s": "Paliwo", "t": "Inne"}
    (m,) = month_metrics("A", simulate(items, etykiety, SLOWNIK)["A"])
    assert (m.n, m.accuracy, m.coverage, m.precision) == (3, 1 / 3, 1 / 3, 1.0)
    assert m.corrections_per_100 == pytest.approx(200 / 3)


def test_ocena_hipotez() -> None:
    items = [item(m, f"s{m}{i}", f"Sklep {i}") for m in range(1, 7) for i in range(4)]
    etykiety = {i.key: "Inne" for i in items}

    wynik = evaluate(simulate(items, etykiety, SLOWNIK))

    assert wynik["n_test"] == 12
    assert wynik["accuracy_test"] == {"A": 0.0, "B": 1.0}
    assert wynik["discordant"] == {"A_dobrze_B_zle": 0, "A_zle_B_dobrze": 12}
    assert wynik["H2a"] and wynik["H2b"] and wynik["H2c"]


def test_grupy_do_etykietowania() -> None:
    items = [
        item(1, "a", "ZABKA 1"),
        item(2, "b", "Żabka 1"),
        item(1, "c", "Kino"),
        item(1, "d", "Smart Saver", TransactionKind.OWN_TRANSFER),
        item(1, "e", None),
    ]
    grupy = groups_to_label(items)
    assert [[i.key for i in g] for g in grupy] == [["a", "b"], ["c"], ["e"]]
    assert group_key(items[4]).startswith("opis: ")


def test_etykietowanie_z_zaprogramowanymi_odpowiedziami() -> None:
    items = [item(1, "a", "Sklep"), item(1, "b", "Sklep"), item(1, "c", "Kino")]
    odpowiedzi = iter(["2", "p", "s"])
    zapisy: list[dict] = []

    etykiety = run(
        items,
        {},
        ask=lambda _: next(odpowiedzi),
        save=lambda e: zapisy.append(dict(e)),
    )

    assert etykiety == {"a": "Zakupy spożywcze", "b": "Zakupy spożywcze"}
    assert zapisy, "postęp zapisuje się po każdej grupie"


def test_etykietowanie_wznawia_prace() -> None:
    items = [item(1, "a", "Sklep"), item(1, "c", "Kino")]
    odpowiedzi = iter(["n", "Kino i teatr", "q"])
    etykiety = run(
        items, {"a": "Inne"}, ask=lambda _: next(odpowiedzi), save=lambda e: None
    )
    assert etykiety == {"a": "Inne", "c": "Kino i teatr"}


def test_zapis_i_odczyt_etykiet(tmp_path) -> None:
    plik = tmp_path / "etykiety.csv"
    save_labels({"k1": "Zakupy spożywcze", "k2": "Kino; teatr"}, plik)
    assert load_labels(plik) == {"k1": "Zakupy spożywcze", "k2": "Kino; teatr"}
    assert oct(plik.stat().st_mode & 0o777) == "0o600"
