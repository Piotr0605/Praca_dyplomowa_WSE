"""Testy kategorii: systemowe tylko do odczytu, własne pod pełną kontrolą właściciela."""

import pytest
from fastapi.testclient import TestClient

from tests.integration.helpers import konto

URL = "/api/categories"


@pytest.fixture
def jan(client: TestClient) -> dict[str, str]:
    return konto(client, "jan@example.com")


def systemowa_id(
    client: TestClient, naglowek: dict[str, str], nazwa: str = "Inne"
) -> int:
    return next(
        k["id"] for k in client.get(URL, headers=naglowek).json() if k["name"] == nazwa
    )


def test_lista_wymaga_logowania(client: TestClient) -> None:
    assert client.get(URL).status_code == 401


def test_lista_zawiera_kategorie_systemowe(
    client: TestClient, jan: dict[str, str]
) -> None:
    kategorie = client.get(URL, headers=jan).json()

    assert len(kategorie) == 16
    assert all(k["is_system"] for k in kategorie)


def test_dodanie_wlasnej_kategorii(client: TestClient, jan: dict[str, str]) -> None:
    odpowiedz = client.post(
        URL, headers=jan, json={"name": "  Hobby ", "color": "#aabbcc"}
    )

    assert odpowiedz.status_code == 201
    assert odpowiedz.json() | {"id": 0} == {
        "id": 0,
        "name": "Hobby",
        "color": "#AABBCC",
        "icon": None,
        "is_income": False,
        "is_system": False,
    }
    assert len(client.get(URL, headers=jan).json()) == 17


def test_wlasne_kategorie_sa_po_systemowych(
    client: TestClient, jan: dict[str, str]
) -> None:
    client.post(URL, headers=jan, json={"name": "Aaa"})

    assert client.get(URL, headers=jan).json()[-1]["name"] == "Aaa"


@pytest.mark.parametrize("nazwa", ["Hobby", "HOBBY", "inne", "Zakupy Spożywcze"])
def test_zajeta_nazwa_daje_409(
    client: TestClient, jan: dict[str, str], nazwa: str
) -> None:
    client.post(URL, headers=jan, json={"name": "Hobby"})

    assert client.post(URL, headers=jan, json={"name": nazwa}).status_code == 409


@pytest.mark.parametrize(
    "dane",
    [
        {"name": ""},
        {"name": "   "},
        {"name": "x" * 101},
        {"name": "A", "color": "red"},
        {"name": "A", "color": "#12345"},
        {"name": "A", "icon": "x" * 51},
    ],
    ids=["pusta", "spacje", "za-dluga", "kolor-slowo", "kolor-krotki", "ikona-dluga"],
)
def test_bledne_dane_daja_422(
    client: TestClient, jan: dict[str, str], dane: dict
) -> None:
    assert client.post(URL, headers=jan, json=dane).status_code == 422


def test_edycja_wlasnej_kategorii(client: TestClient, jan: dict[str, str]) -> None:
    kategoria = client.post(URL, headers=jan, json={"name": "Hobby"}).json()

    odpowiedz = client.patch(
        f"{URL}/{kategoria['id']}", headers=jan, json={"name": "Pasje"}
    )

    assert odpowiedz.status_code == 200
    assert odpowiedz.json()["name"] == "Pasje"


def test_edycja_bez_zmiany_nazwy_nie_zglasza_konfliktu(
    client: TestClient, jan: dict[str, str]
) -> None:
    kategoria = client.post(URL, headers=jan, json={"name": "Hobby"}).json()

    odpowiedz = client.patch(
        f"{URL}/{kategoria['id']}", headers=jan, json={"name": "hobby"}
    )

    assert odpowiedz.status_code == 200


def test_edycja_na_zajeta_nazwe_daje_409(
    client: TestClient, jan: dict[str, str]
) -> None:
    kategoria = client.post(URL, headers=jan, json={"name": "Hobby"}).json()

    odpowiedz = client.patch(
        f"{URL}/{kategoria['id']}", headers=jan, json={"name": "Paliwo"}
    )

    assert odpowiedz.status_code == 409


def test_null_nie_kasuje_nazwy(client: TestClient, jan: dict[str, str]) -> None:
    kategoria = client.post(
        URL, headers=jan, json={"name": "Hobby", "color": "#000000"}
    ).json()

    odpowiedz = client.patch(
        f"{URL}/{kategoria['id']}", headers=jan, json={"name": None, "color": None}
    )

    assert odpowiedz.json()["name"] == "Hobby"
    assert odpowiedz.json()["color"] is None


@pytest.mark.parametrize("metoda", ["patch", "delete"])
def test_kategorii_systemowej_nie_mozna_zmienic(
    client: TestClient, jan: dict[str, str], metoda: str
) -> None:
    adres = f"{URL}/{systemowa_id(client, jan)}"
    odpowiedz = getattr(client, metoda)(
        adres, headers=jan, **({"json": {"name": "X"}} if metoda == "patch" else {})
    )

    assert odpowiedz.status_code == 403
    assert systemowa_id(client, jan) is not None


def test_usuniecie_wlasnej_kategorii(client: TestClient, jan: dict[str, str]) -> None:
    kategoria = client.post(URL, headers=jan, json={"name": "Hobby"}).json()

    assert client.delete(f"{URL}/{kategoria['id']}", headers=jan).status_code == 204
    assert len(client.get(URL, headers=jan).json()) == 16


@pytest.mark.parametrize("metoda", ["patch", "delete"])
def test_nieistniejaca_kategoria_daje_404(
    client: TestClient, jan: dict[str, str], metoda: str
) -> None:
    odpowiedz = getattr(client, metoda)(
        f"{URL}/999999", headers=jan, **({"json": {}} if metoda == "patch" else {})
    )

    assert odpowiedz.status_code == 404
