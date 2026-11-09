"""Testy transakcji: dodawanie ręczne, lista z filtrami, edycja i usuwanie."""

import datetime as dt
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Transaction, User
from app.models.enums import TransactionKind, TransactionSource
from tests.integration.helpers import konto

URL = "/api/transactions"


@pytest.fixture
def jan(client: TestClient) -> dict[str, str]:
    return konto(client, "jan@example.com")


def dodaj(client: TestClient, naglowek: dict[str, str], **pola: object) -> dict:
    dane = {"date": "2026-11-01", "amount": "-12.50", "description": "Kawa"} | pola
    odpowiedz = client.post(URL, headers=naglowek, json=dane)
    assert odpowiedz.status_code == 201, odpowiedz.text
    return odpowiedz.json()


def kategoria(client: TestClient, naglowek: dict[str, str], nazwa: str) -> int:
    return next(
        k["id"]
        for k in client.get("/api/categories", headers=naglowek).json()
        if k["name"] == nazwa
    )


def lista(client: TestClient, naglowek: dict[str, str], **parametry: object) -> dict:
    odpowiedz = client.get(URL, headers=naglowek, params=parametry)
    assert odpowiedz.status_code == 200, odpowiedz.text
    return odpowiedz.json()


def test_wymaga_logowania(client: TestClient) -> None:
    assert client.get(URL).status_code == 401
    assert client.post(URL, json={}).status_code == 401


def test_dodanie_transakcji_recznej(client: TestClient, jan: dict[str, str]) -> None:
    transakcja = dodaj(client, jan, currency="eur", counterparty="  Pan Kowalski ")

    assert transakcja["amount"] == "-12.50"
    assert transakcja["currency"] == "EUR"
    assert transakcja["counterparty"] == "Pan Kowalski"
    assert transakcja["source"] == "manual"
    assert transakcja["kind"] == "other"
    # Żadna reguła nie pasuje, więc transakcja czeka na przypisanie kategorii.
    assert transakcja["category_id"] is None
    assert transakcja["categorized_by"] is None


def test_kwota_jest_dokladna(client: TestClient, jan: dict[str, str]) -> None:
    dodaj(client, jan, amount="0.10")
    dodaj(client, jan, amount="0.20")

    suma = sum(Decimal(t["amount"]) for t in lista(client, jan)["items"])

    assert suma == Decimal("0.30")


def test_dwie_identyczne_transakcje_reczne_sa_dozwolone(
    client: TestClient, jan: dict[str, str]
) -> None:
    dodaj(client, jan)
    dodaj(client, jan)

    assert lista(client, jan)["total"] == 2


@pytest.mark.parametrize(
    "pola",
    [
        {"amount": "0"},
        {"amount": "1.005"},
        {"amount": "12345678901"},
        {"amount": "abc"},
        {"description": "  "},
        {"description": "x" * 501},
        {"currency": "PL"},
        {"currency": "P1N"},
        {"date": "2026-02-30"},
        {"kind": "zakupy"},
        {"counterparty": "x" * 256},
    ],
    ids=[
        "zero",
        "trzy-miejsca",
        "za-duza",
        "tekst",
        "pusty-opis",
        "dlugi-opis",
        "waluta-2",
        "waluta-cyfra",
        "zla-data",
        "zly-rodzaj",
        "dlugi-kontrahent",
    ],
)
def test_bledne_dane_daja_422(
    client: TestClient, jan: dict[str, str], pola: dict
) -> None:
    dane = {"date": "2026-11-01", "amount": "-12.50", "description": "Kawa"} | pola

    assert client.post(URL, headers=jan, json=dane).status_code == 422


def test_kategoria_systemowa_i_wlasna_sa_dozwolone(
    client: TestClient, jan: dict[str, str]
) -> None:
    wlasna = client.post("/api/categories", headers=jan, json={"name": "Hobby"}).json()[
        "id"
    ]

    assert dodaj(client, jan, category_id=kategoria(client, jan, "Paliwo"))[
        "category_id"
    ]
    assert dodaj(client, jan, category_id=wlasna)["category_id"] == wlasna


def test_nieistniejaca_kategoria_daje_422(
    client: TestClient, jan: dict[str, str]
) -> None:
    dane = {
        "date": "2026-11-01",
        "amount": "-1",
        "description": "x",
        "category_id": 999999,
    }

    assert client.post(URL, headers=jan, json=dane).status_code == 422


def test_lista_od_najnowszych_z_paginacja(
    client: TestClient, jan: dict[str, str]
) -> None:
    for dzien in range(1, 6):
        dodaj(client, jan, date=f"2026-11-0{dzien}", description=f"Dzien {dzien}")

    strona = lista(client, jan, page=2, page_size=2)

    assert strona["total"] == 5
    assert [t["description"] for t in strona["items"]] == ["Dzien 3", "Dzien 2"]
    assert (
        lista(client, jan, page=3, page_size=2)["items"][0]["description"] == "Dzien 1"
    )


@pytest.mark.parametrize(
    "parametry",
    [
        {"page": 0},
        {"page_size": 0},
        {"page_size": 201},
        {"q": ""},
        {"date_from": "2026-11-02", "date_to": "2026-11-01"},
        {"uncategorized": True, "category_id": 1},
    ],
    ids=[
        "strona-0",
        "rozmiar-0",
        "rozmiar-201",
        "puste-szukanie",
        "odwrocone-daty",
        "sprzeczne",
    ],
)
def test_bledne_parametry_listy_daja_422(
    client: TestClient, jan: dict[str, str], parametry: dict
) -> None:
    assert client.get(URL, headers=jan, params=parametry).status_code == 422


def test_filtry(client: TestClient, jan: dict[str, str]) -> None:
    paliwo = kategoria(client, jan, "Paliwo")
    dodaj(
        client,
        jan,
        date="2026-10-31",
        description="Orlen",
        category_id=paliwo,
        kind="card",
    )
    dodaj(
        client,
        jan,
        date="2026-11-05",
        description="Wypłata",
        amount="5000",
        kind="transfer",
    )
    dodaj(client, jan, date="2026-11-10", description="Bilety", counterparty="Helios")

    def opisy(**p: object) -> list[str]:
        return [t["description"] for t in lista(client, jan, **p)["items"]]

    assert opisy(date_from="2026-11-01") == ["Bilety", "Wypłata"]
    assert opisy(date_to="2026-11-05") == ["Wypłata", "Orlen"]
    assert opisy(date_from="2026-11-05", date_to="2026-11-05") == ["Wypłata"]
    assert opisy(category_id=paliwo) == ["Orlen"]
    # „Helios” rozpoznaje słownik (Rozrywka), więc bez kategorii zostaje tylko „Wypłata”.
    assert opisy(uncategorized=True) == ["Wypłata"]
    assert opisy(kind="card") == ["Orlen"]
    assert opisy(q="ORL") == ["Orlen"]
    assert opisy(q="helios") == ["Bilety"]


def test_szukanie_traktuje_znaki_specjalne_doslownie(
    client: TestClient, jan: dict[str, str]
) -> None:
    dodaj(client, jan, description="Rabat 50% na kawę")
    dodaj(client, jan, description="Zakupy")

    assert [t["description"] for t in lista(client, jan, q="%")["items"]] == [
        "Rabat 50% na kawę"
    ]
    assert lista(client, jan, q="_")["total"] == 0


def test_pobranie_jednej_transakcji(client: TestClient, jan: dict[str, str]) -> None:
    transakcja = dodaj(client, jan)

    assert client.get(f"{URL}/{transakcja['id']}", headers=jan).json() == transakcja


def test_edycja(client: TestClient, jan: dict[str, str]) -> None:
    transakcja = dodaj(client, jan)
    paliwo = kategoria(client, jan, "Paliwo")

    odpowiedz = client.patch(
        f"{URL}/{transakcja['id']}",
        headers=jan,
        json={"amount": "-200.00", "description": "Tankowanie", "category_id": paliwo},
    )

    assert odpowiedz.status_code == 200
    assert odpowiedz.json() | {"id": 0} == transakcja | {
        "id": 0,
        "amount": "-200.00",
        "description": "Tankowanie",
        "category_id": paliwo,
        "categorized_by": "manual",
    }


def test_edycja_usuwa_kategorie_przez_null(
    client: TestClient, jan: dict[str, str]
) -> None:
    transakcja = dodaj(client, jan, category_id=kategoria(client, jan, "Paliwo"))

    odpowiedz = client.patch(
        f"{URL}/{transakcja['id']}", headers=jan, json={"category_id": None}
    )

    assert odpowiedz.json()["category_id"] is None


@pytest.mark.parametrize("pole", ["date", "amount", "currency", "description", "kind"])
def test_null_w_polu_wymaganym_daje_422(
    client: TestClient, jan: dict[str, str], pole: str
) -> None:
    transakcja = dodaj(client, jan)

    assert (
        client.patch(
            f"{URL}/{transakcja['id']}", headers=jan, json={pole: None}
        ).status_code
        == 422
    )


def test_edycja_z_nieznana_kategoria_daje_422(
    client: TestClient, jan: dict[str, str]
) -> None:
    transakcja = dodaj(client, jan)

    odpowiedz = client.patch(
        f"{URL}/{transakcja['id']}", headers=jan, json={"category_id": 999999}
    )

    assert odpowiedz.status_code == 422


def importowana(db_session: Session, email: str) -> Transaction:
    """Transakcja jak z importu wyciągu: przez API nie da się jej jeszcze utworzyć (etap 4)."""
    user = db_session.query(User).filter_by(email=email).one()
    transakcja = Transaction(
        user_id=user.id,
        date=dt.date(2026, 11, 1),
        amount=Decimal("-99.99"),
        description="ZABKA",
        source=TransactionSource.PDF,
        kind=TransactionKind.CARD,
        dedup_hash="a" * 64,
    )
    db_session.add(transakcja)
    db_session.commit()
    return transakcja


@pytest.mark.parametrize(
    "zmiana",
    [
        {"amount": "-1.00"},
        {"date": "2026-01-01"},
        {"currency": "EUR"},
        {"counterparty": "X"},
    ],
)
def test_dane_bankowe_z_importu_sa_zablokowane(
    client: TestClient, jan: dict[str, str], db_session: Session, zmiana: dict
) -> None:
    transakcja = importowana(db_session, "jan@example.com")

    odpowiedz = client.patch(f"{URL}/{transakcja.id}", headers=jan, json=zmiana)

    assert odpowiedz.status_code == 409
    assert (
        client.get(f"{URL}/{transakcja.id}", headers=jan).json()["amount"] == "-99.99"
    )


def test_w_imporcie_mozna_zmienic_kategorie_rodzaj_i_opis(
    client: TestClient, jan: dict[str, str], db_session: Session
) -> None:
    transakcja = importowana(db_session, "jan@example.com")
    zmiana = {
        "category_id": kategoria(client, jan, "Zakupy spożywcze"),
        "kind": "blik",
        "description": "Żabka",
    }

    odpowiedz = client.patch(f"{URL}/{transakcja.id}", headers=jan, json=zmiana)

    assert odpowiedz.status_code == 200
    assert {k: odpowiedz.json()[k] for k in zmiana} == zmiana


def test_usuniecie(client: TestClient, jan: dict[str, str]) -> None:
    transakcja = dodaj(client, jan)

    assert client.delete(f"{URL}/{transakcja['id']}", headers=jan).status_code == 204
    assert client.get(f"{URL}/{transakcja['id']}", headers=jan).status_code == 404
    assert client.delete(f"{URL}/{transakcja['id']}", headers=jan).status_code == 404


def test_usuniecie_kategorii_zostawia_transakcje(
    client: TestClient, jan: dict[str, str]
) -> None:
    wlasna = client.post("/api/categories", headers=jan, json={"name": "Hobby"}).json()[
        "id"
    ]
    transakcja = dodaj(client, jan, category_id=wlasna)

    client.delete(f"/api/categories/{wlasna}", headers=jan)

    assert (
        client.get(f"{URL}/{transakcja['id']}", headers=jan).json()["category_id"]
        is None
    )
