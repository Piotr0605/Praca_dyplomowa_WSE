"""Izolacja danych: użytkownik B nie może zobaczyć, zmienić ani wykorzystać danych użytkownika A.

Cudzy zasób zachowuje się dokładnie jak nieistniejący (404, a przy polach formularza 422),
więc odpowiedź nie zdradza nawet, że zasób o takim numerze istnieje.
"""

import pytest
from fastapi.testclient import TestClient

from tests.integration.helpers import konto


@pytest.fixture
def dane_a(client: TestClient) -> dict:
    """Użytkownik A z własną kategorią i transakcją przypisaną do niej."""
    a = konto(client, "a@example.com")
    kategoria = client.post(
        "/api/categories", headers=a, json={"name": "Sekretna A"}
    ).json()
    transakcja = client.post(
        "/api/transactions",
        headers=a,
        json={
            "date": "2026-11-01",
            "amount": "-321.00",
            "description": "Prywatny zakup A",
            "counterparty": "Sklep A",
            "category_id": kategoria["id"],
        },
    ).json()
    return {"naglowek": a, "kategoria": kategoria, "transakcja": transakcja}


@pytest.fixture
def b(client: TestClient) -> dict[str, str]:
    return konto(client, "b@example.com")


def test_b_nie_widzi_transakcji_a_na_liscie(
    client: TestClient, dane_a: dict, b: dict
) -> None:
    strona = client.get("/api/transactions", headers=b).json()

    assert strona["total"] == 0
    assert strona["items"] == []


@pytest.mark.parametrize(
    "parametry",
    [
        {"q": "Prywatny"},
        {"q": "Sklep A"},
        {"date_from": "2026-01-01"},
        {"kind": "other"},
    ],
    ids=["opis", "kontrahent", "daty", "rodzaj"],
)
def test_b_nie_znajduje_danych_a_filtrami(
    client: TestClient, dane_a: dict, b: dict, parametry: dict
) -> None:
    assert (
        client.get("/api/transactions", headers=b, params=parametry).json()["total"]
        == 0
    )


def test_filtr_po_cudzej_kategorii_nic_nie_zwraca(
    client: TestClient, dane_a: dict, b: dict
) -> None:
    parametry = {"category_id": dane_a["kategoria"]["id"]}

    assert (
        client.get("/api/transactions", headers=b, params=parametry).json()["total"]
        == 0
    )


def test_b_nie_odczyta_transakcji_a(client: TestClient, dane_a: dict, b: dict) -> None:
    adres = f"/api/transactions/{dane_a['transakcja']['id']}"

    assert client.get(adres, headers=b).status_code == 404


def test_b_nie_zmieni_ani_nie_usunie_transakcji_a(
    client: TestClient, dane_a: dict, b: dict
) -> None:
    adres = f"/api/transactions/{dane_a['transakcja']['id']}"

    assert client.patch(adres, headers=b, json={"amount": "-1.00"}).status_code == 404
    assert client.delete(adres, headers=b).status_code == 404
    assert client.get(adres, headers=dane_a["naglowek"]).json() == dane_a["transakcja"]


def test_cudza_i_nieistniejaca_transakcja_daja_te_sama_odpowiedz(
    client: TestClient, dane_a: dict, b: dict
) -> None:
    cudza = client.get(f"/api/transactions/{dane_a['transakcja']['id']}", headers=b)
    nieistniejaca = client.get("/api/transactions/999999", headers=b)

    assert (cudza.status_code, cudza.json()) == (
        nieistniejaca.status_code,
        nieistniejaca.json(),
    )


def test_b_nie_widzi_kategorii_a(client: TestClient, dane_a: dict, b: dict) -> None:
    nazwy = {k["name"] for k in client.get("/api/categories", headers=b).json()}

    assert "Sekretna A" not in nazwy
    assert len(nazwy) == 16


def test_b_moze_miec_kategorie_o_tej_samej_nazwie(
    client: TestClient, dane_a: dict, b: dict
) -> None:
    assert (
        client.post(
            "/api/categories", headers=b, json={"name": "Sekretna A"}
        ).status_code
        == 201
    )


def test_b_nie_zmieni_ani_nie_usunie_kategorii_a(
    client: TestClient, dane_a: dict, b: dict
) -> None:
    adres = f"/api/categories/{dane_a['kategoria']['id']}"

    assert client.patch(adres, headers=b, json={"name": "Przejeta"}).status_code == 404
    assert client.delete(adres, headers=b).status_code == 404
    nazwy = {
        k["name"]
        for k in client.get("/api/categories", headers=dane_a["naglowek"]).json()
    }
    assert "Sekretna A" in nazwy


def test_b_nie_przypisze_kategorii_a_nowej_transakcji(
    client: TestClient, dane_a: dict, b: dict
) -> None:
    dane = {
        "date": "2026-11-01",
        "amount": "-1",
        "description": "x",
        "category_id": dane_a["kategoria"]["id"],
    }

    assert client.post("/api/transactions", headers=b, json=dane).status_code == 422


def test_b_nie_przypisze_kategorii_a_swojej_transakcji(
    client: TestClient, dane_a: dict, b: dict
) -> None:
    wlasna = client.post(
        "/api/transactions",
        headers=b,
        json={"date": "2026-11-01", "amount": "-1", "description": "x"},
    ).json()

    odpowiedz = client.patch(
        f"/api/transactions/{wlasna['id']}",
        headers=b,
        json={"category_id": dane_a["kategoria"]["id"]},
    )

    assert odpowiedz.status_code == 422


def test_cudza_kategoria_i_nieistniejaca_daja_ten_sam_blad(
    client: TestClient, dane_a: dict, b: dict
) -> None:
    def blad(kategoria_id: int) -> tuple[int, dict]:
        dane = {
            "date": "2026-11-01",
            "amount": "-1",
            "description": "x",
            "category_id": kategoria_id,
        }
        odpowiedz = client.post("/api/transactions", headers=b, json=dane)
        return odpowiedz.status_code, odpowiedz.json()

    assert blad(dane_a["kategoria"]["id"]) == blad(999999)


def test_dane_b_nie_trafiaja_do_a(client: TestClient, dane_a: dict, b: dict) -> None:
    client.post(
        "/api/transactions",
        headers=b,
        json={"date": "2026-11-02", "amount": "-5", "description": "B"},
    )

    assert (
        client.get("/api/transactions", headers=dane_a["naglowek"]).json()["total"] == 1
    )
