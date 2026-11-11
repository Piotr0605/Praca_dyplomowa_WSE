"""Porady AI z dostawcą mock: pakiet bez danych osobowych, cache, limit dzienny, historia, błędy."""

import json

import pytest
from fastapi.testclient import TestClient

from app.ai.prompt_builder import PROMPT_VERSION
from app.ai.providers.base import AdviceProviderError
from app.core.config import get_settings
from app.services import advice_service
from research.advice_numbers import check
from tests.fixtures.ing_statement import make_ing_statement
from tests.integration.helpers import konto

OKRES = {"date_from": "2026-10-01", "date_to": "2026-10-31"}


@pytest.fixture
def jan(client: TestClient) -> dict[str, str]:
    naglowek = konto(client, "jan@example.com")
    odpowiedz = client.post(
        "/api/imports/confirm",
        headers=naglowek,
        files={"file": ("wyciag.pdf", make_ing_statement(), "application/pdf")},
    )
    assert odpowiedz.status_code == 201
    return naglowek


def poradz(client: TestClient, naglowek: dict, okres: dict = OKRES):
    return client.post("/api/advice", headers=naglowek, json=okres)


def test_wymaga_logowania(client: TestClient) -> None:
    assert client.post("/api/advice", json=OKRES).status_code == 401
    assert client.get("/api/advice").status_code == 401
    assert client.get("/api/advice/preview-payload", params=OKRES).status_code == 401


def test_pakiet_zawiera_tylko_agregaty(client: TestClient, jan: dict) -> None:
    pakiet = client.get("/api/advice/preview-payload", headers=jan, params=OKRES).json()

    assert set(pakiet) == {
        "wersja",
        "okres",
        "podsumowanie",
        "wydatki_wedlug_kategorii",
        "wplywy_wedlug_kategorii",
        "zmiany_w_kategoriach_wydatkow",
        "trend_miesieczny",
    }
    tekst = json.dumps(pakiet, ensure_ascii=False)
    # Z wyciągu: kontrahenci, numery kont i kart, tytuły przelewów nie mogą opuścić komputera.
    for fragment in (
        "SKLEP",
        "PayU",
        "FIRMA TESTOWA",
        "JAN",
        "Anna",
        "1234",
        "2222",
        "@",
        "Płatność",
        "telefon",
    ):
        assert fragment not in tekst, fragment
    assert pakiet["podsumowanie"]["liczba_transakcji"] > 0


def test_nazwa_kategorii_uzytkownika_jest_anonimizowana(
    client: TestClient, jan: dict
) -> None:
    kategoria = client.post(
        "/api/categories", headers=jan, json={"name": "Pożyczka dla Ani"}
    ).json()
    transakcja = client.get(
        "/api/transactions", headers=jan, params={"q": "BLIK", "page_size": 1}
    ).json()["items"][0]
    client.patch(
        f"/api/transactions/{transakcja['id']}",
        headers=jan,
        json={"category_id": kategoria["id"]},
    )

    tekst = json.dumps(
        client.get("/api/advice/preview-payload", headers=jan, params=OKRES).json(),
        ensure_ascii=False,
    )
    assert "Ani" not in tekst
    assert "Pożyczka dla [OSOBA]" in tekst


def test_porada_mock_z_zapisem_warunkow_badania(client: TestClient, jan: dict) -> None:
    odpowiedz = poradz(client, jan)
    assert odpowiedz.status_code == 200
    dane = odpowiedz.json()
    porada = dane["advice"]

    assert dane["cached"] is False
    assert porada["provider"] == "mock"
    assert "## Rekomendacje" in porada["response_text"]
    assert porada["prompt_version"] == PROMPT_VERSION
    assert porada["tokens_in"] > 0
    assert porada["response_time_ms"] >= 0
    assert porada["prompt_payload"]["okres"]["od"] == "2026-10-01"

    historia = client.get("/api/advice", headers=jan).json()
    assert [p["id"] for p in historia] == [porada["id"]]


def test_liczby_porady_pokryte_pakietem(client: TestClient, jan: dict) -> None:
    """Narzędzie badania H4a na poradzie mock: wszystkie liczby wynikają z pakietu."""
    porada = poradz(client, jan).json()["advice"]
    raport = check(porada["response_text"], porada["prompt_payload"])
    assert len(raport.numbers) >= 6
    assert raport.uncovered == []


def test_cache_dla_niezmienionych_danych(client: TestClient, jan: dict) -> None:
    pierwsza = poradz(client, jan).json()
    druga = poradz(client, jan).json()
    assert druga["cached"] is True
    assert druga["advice"]["id"] == pierwsza["advice"]["id"]
    assert len(client.get("/api/advice", headers=jan).json()) == 1


def test_zmiana_danych_uniewaznia_cache(client: TestClient, jan: dict) -> None:
    pierwsza = poradz(client, jan).json()
    client.post(
        "/api/transactions",
        headers=jan,
        json={"date": "2026-10-15", "amount": "-99.00", "description": "Nowy wydatek"},
    )
    druga = poradz(client, jan).json()
    assert druga["cached"] is False
    assert druga["advice"]["id"] != pierwsza["advice"]["id"]


def test_dzienny_limit(client: TestClient, jan: dict, monkeypatch) -> None:
    monkeypatch.setattr(get_settings(), "ADVICE_DAILY_LIMIT", 1)
    assert poradz(client, jan).status_code == 200
    # Cache nie zużywa limitu...
    assert poradz(client, jan).status_code == 200
    # ...ale nowy okres wymaga nowej porady, a limit jest wyczerpany.
    odpowiedz = poradz(
        client, jan, {"date_from": "2026-10-01", "date_to": "2026-10-15"}
    )
    assert odpowiedz.status_code == 429
    assert "limit" in odpowiedz.json()["detail"].lower()


def test_okres_bez_transakcji(client: TestClient, jan: dict) -> None:
    odpowiedz = poradz(
        client, jan, {"date_from": "2020-01-01", "date_to": "2020-01-31"}
    )
    assert odpowiedz.status_code == 422


def test_zly_okres(client: TestClient, jan: dict) -> None:
    odpowiedz = poradz(
        client, jan, {"date_from": "2026-10-31", "date_to": "2026-10-01"}
    )
    assert odpowiedz.status_code == 422


def test_blad_dostawcy_to_502(client: TestClient, jan: dict, monkeypatch) -> None:
    class Zepsuty:
        def generate_advice(self, payload: dict):
            raise AdviceProviderError("OpenAI: klucz API został odrzucony")

    monkeypatch.setattr(
        advice_service, "current_provider", lambda: ("openai", Zepsuty())
    )
    odpowiedz = poradz(client, jan)
    assert odpowiedz.status_code == 502
    assert "klucz API" in odpowiedz.json()["detail"]
    assert client.get("/api/advice", headers=jan).json() == []


def test_izolacja_uzytkownikow(client: TestClient, jan: dict) -> None:
    poradz(client, jan)
    anna = konto(client, "anna@example.com")
    assert client.get("/api/advice", headers=anna).json() == []
