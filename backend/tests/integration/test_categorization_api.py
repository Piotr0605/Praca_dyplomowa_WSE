"""Testy kategoryzacji w API: import, poprawki jako reguły, przeliczanie wstecz, statystyka, izolacja."""

import pytest
from fastapi.testclient import TestClient

from tests.fixtures.csv_samples import make_ing_csv
from tests.integration.helpers import konto


@pytest.fixture
def jan(client: TestClient) -> dict[str, str]:
    return konto(client, "jan@example.com")


@pytest.fixture
def anna(client: TestClient) -> dict[str, str]:
    return konto(client, "anna@example.com")


def kategorie(client: TestClient, naglowek: dict) -> dict[str, int]:
    return {
        k["name"]: k["id"]
        for k in client.get("/api/categories", headers=naglowek).json()
    }


def transakcje(client: TestClient, naglowek: dict, **filtry) -> list[dict]:
    return client.get(
        "/api/transactions", headers=naglowek, params={"page_size": 100, **filtry}
    ).json()["items"]


def po_kontrahencie(client: TestClient, naglowek: dict) -> dict[str, dict]:
    return {t["counterparty"]: t for t in transakcje(client, naglowek)}


def importuj(client: TestClient, naglowek: dict, dane: bytes | None = None) -> None:
    odpowiedz = client.post(
        "/api/imports/confirm",
        headers=naglowek,
        files={"file": ("h.csv", dane or make_ing_csv(), "text/csv")},
    )
    assert odpowiedz.status_code == 201


def dodaj(client: TestClient, naglowek: dict, **pola) -> dict:
    dane = {"date": "2026-10-10", "amount": "-20.00", "description": "Zakupy"} | pola
    odpowiedz = client.post("/api/transactions", headers=naglowek, json=dane)
    assert odpowiedz.status_code == 201
    return odpowiedz.json()


def zmien_kategorie(
    client: TestClient, naglowek: dict, id_: int, kategoria: int | None
):
    odpowiedz = client.patch(
        f"/api/transactions/{id_}", headers=naglowek, json={"category_id": kategoria}
    )
    assert odpowiedz.status_code == 200
    return odpowiedz.json()


def statystyka(client: TestClient, naglowek: dict) -> dict:
    return client.get("/api/categorization/stats", headers=naglowek).json()


def test_import_przypisuje_kategorie(client: TestClient, jan: dict) -> None:
    importuj(client, jan)
    k = kategorie(client, jan)
    t = po_kontrahencie(client, jan)

    assert t["JAN TESTOWY"]["category_id"] == k["Przelewy własne"]
    assert t["FIRMA PRZYKŁADOWA SP. Z O.O."]["category_id"] == k["Wynagrodzenie"]
    assert t["JAN TESTOWY"]["categorized_by"] == "system_rule"
    # Kontrahent spoza słownika czeka na przypisanie.
    assert t["SKLEP TESTOWY WARSZAWA"]["category_id"] is None
    assert t["SKLEP TESTOWY WARSZAWA"]["categorized_by"] is None


def test_reczna_transakcja_bez_kategorii_dostaje_ja_ze_slownika(
    client: TestClient, jan: dict
) -> None:
    k = kategorie(client, jan)
    auto = dodaj(client, jan, counterparty="ORLEN STACJA 7")
    wybrana = dodaj(client, jan, counterparty="ORLEN STACJA 7", category_id=k["Inne"])

    assert (auto["category_id"], auto["categorized_by"]) == (k["Paliwo"], "system_rule")
    assert (wybrana["category_id"], wybrana["categorized_by"]) == (k["Inne"], "manual")


def test_poprawka_tworzy_regule_i_dziala_przy_kolejnym_imporcie(
    client: TestClient, jan: dict
) -> None:
    importuj(client, jan)
    k = kategorie(client, jan)
    sklep = po_kontrahencie(client, jan)["SKLEP TESTOWY WARSZAWA"]

    po = zmien_kategorie(client, jan, sklep["id"], k["Zakupy spożywcze"])
    assert po["categorized_by"] == "manual"
    assert po["category_rule_id"] is not None

    reguly = client.get("/api/rules", headers=jan).json()
    assert [(r["pattern"], r["match_type"], r["category_name"]) for r in reguly] == [
        ("SKLEP TESTOWY WARSZAWA", "exact_counterparty", "Zakupy spożywcze")
    ]

    # Następny wyciąg z tym samym sklepem: kategoria z zapamiętanej reguły.
    wiersz = ("2026-11-02", "2026-11-03", "SKLEP TESTOWY WARSZAWA", "Płatność kartą 02.11.2026",
              "TR.KART", "'202611030000000099'", "-10,00", "")  # fmt: skip
    importuj(client, jan, make_ing_csv([wiersz]))
    nowa = next(t for t in transakcje(client, jan) if t["date"] == "2026-11-02")
    assert (nowa["category_id"], nowa["categorized_by"]) == (
        k["Zakupy spożywcze"],
        "user_rule",
    )
    assert nowa["category_rule_id"] == po["category_rule_id"]


def test_kolejna_poprawka_zmienia_istniejaca_regule(
    client: TestClient, jan: dict
) -> None:
    k = kategorie(client, jan)
    t = dodaj(client, jan, counterparty="Sklep Testowy")
    zmien_kategorie(client, jan, t["id"], k["Zakupy spożywcze"])
    zmien_kategorie(client, jan, t["id"], k["Odzież"])

    reguly = client.get("/api/rules", headers=jan).json()
    assert len(reguly) == 1
    assert reguly[0]["category_name"] == "Odzież"


def test_zapis_bez_zmiany_kategorii_nie_jest_poprawka(
    client: TestClient, jan: dict
) -> None:
    k = kategorie(client, jan)
    t = dodaj(client, jan, counterparty="ORLEN STACJA 7")
    assert t["category_id"] == k["Paliwo"]

    po = zmien_kategorie(client, jan, t["id"], k["Paliwo"])

    assert po["categorized_by"] == "system_rule"
    assert client.get("/api/rules", headers=jan).json() == []


def test_bez_kontrahenta_regula_nie_powstaje(client: TestClient, jan: dict) -> None:
    t = dodaj(client, jan)
    po = zmien_kategorie(client, jan, t["id"], kategorie(client, jan)["Inne"])

    assert po["category_rule_id"] is None
    assert client.get("/api/rules", headers=jan).json() == []


def test_zastosuj_do_podobnych(client: TestClient, jan: dict) -> None:
    k = kategorie(client, jan)
    pierwsza = dodaj(client, jan, counterparty="Kawiarnia Pod Lipą")
    druga = dodaj(client, jan, counterparty="kawiarnia pod lipą")
    reczna = dodaj(
        client, jan, counterparty="Kawiarnia Pod Lipą", category_id=k["Inne"]
    )
    assert druga["category_id"] == k["Restauracje"]  # słownik: „kawiarnia”

    zmien_kategorie(client, jan, pierwsza["id"], k["Jedzenie"])
    wynik = client.post(
        "/api/categorization/apply", headers=jan, params={"recategorize": True}
    ).json()

    assert wynik == {"categorized": 1}
    stan = {t["id"]: t for t in transakcje(client, jan)}
    assert stan[druga["id"]]["category_id"] == k["Jedzenie"]
    assert stan[druga["id"]]["categorized_by"] == "user_rule"
    # Decyzja użytkownika zostaje.
    assert stan[reczna["id"]]["category_id"] == k["Inne"]


def test_przypisanie_wstecz_tylko_bez_kategorii(client: TestClient, jan: dict) -> None:
    k = kategorie(client, jan)
    t = dodaj(client, jan, counterparty="Sklep Testowy")
    usunieta = dodaj(client, jan, counterparty="ORLEN STACJA 7")
    zmien_kategorie(
        client, jan, usunieta["id"], None
    )  # użytkownik świadomie usuwa kategorię
    zmien_kategorie(client, jan, t["id"], k["Odzież"])
    druga = dodaj(client, jan, counterparty="Sklep Testowy", category_id=None)
    assert druga["category_id"] == k["Odzież"]

    assert client.post("/api/categorization/apply", headers=jan).json() == {
        "categorized": 0
    }
    stan = {x["id"]: x for x in transakcje(client, jan)}
    assert stan[usunieta["id"]]["category_id"] is None


def test_statystyka(client: TestClient, jan: dict) -> None:
    importuj(client, jan)
    k = kategorie(client, jan)
    sklep = po_kontrahencie(client, jan)["SKLEP TESTOWY WARSZAWA"]
    zmien_kategorie(client, jan, sklep["id"], k["Zakupy spożywcze"])

    s = statystyka(client, jan)
    assert s["total"] == 7
    assert s["manual"] == 1
    assert s["system_rule"] + s["user_rule"] + s["manual"] + s["uncategorized"] == 7
    assert s["rules_version"]


def test_usuniecie_reguly(client: TestClient, jan: dict) -> None:
    k = kategorie(client, jan)
    t = dodaj(client, jan, counterparty="Sklep Testowy")
    zmien_kategorie(client, jan, t["id"], k["Odzież"])
    regula = client.get("/api/rules", headers=jan).json()[0]

    assert client.delete(f"/api/rules/{regula['id']}", headers=jan).status_code == 204
    assert client.get("/api/rules", headers=jan).json() == []
    assert client.delete(f"/api/rules/{regula['id']}", headers=jan).status_code == 404
    # Transakcja zachowuje kategorię.
    assert transakcje(client, jan)[0]["category_id"] == k["Odzież"]


def test_reguly_innego_uzytkownika(client: TestClient, jan: dict, anna: dict) -> None:
    k = kategorie(client, jan)
    t = dodaj(client, jan, counterparty="Sklep Testowy")
    zmien_kategorie(client, jan, t["id"], k["Odzież"])
    regula = client.get("/api/rules", headers=jan).json()[0]

    assert client.get("/api/rules", headers=anna).json() == []
    assert client.delete(f"/api/rules/{regula['id']}", headers=anna).status_code == 404
    # Reguła Jana nie działa u Anny.
    assert dodaj(client, anna, counterparty="Sklep Testowy")["category_id"] is None
    assert client.post(
        "/api/categorization/apply", headers=anna, params={"recategorize": True}
    ).json() == {"categorized": 0}
    assert statystyka(client, anna)["total"] == 1


def test_wymaga_logowania(client: TestClient) -> None:
    assert client.get("/api/rules").status_code == 401
    assert client.get("/api/categorization/stats").status_code == 401
    assert client.post("/api/categorization/apply").status_code == 401
