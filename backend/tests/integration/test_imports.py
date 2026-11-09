"""Testy importu wyciągów: podgląd, zapis, duplikaty, błędy i izolacja."""

import io
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from reportlab.pdfgen import canvas

from app.services.import_service import MAX_FILE_SIZE, normalize_description
from tests.fixtures.ing_statement import make_ing_statement, sample_transactions
from tests.integration.helpers import konto

WYCIAG = make_ing_statement()
LICZBA = len(sample_transactions())


@pytest.fixture
def jan(client: TestClient) -> dict[str, str]:
    return konto(client, "jan@example.com")


def wyslij(
    client: TestClient,
    naglowek: dict,
    etap: str,
    dane: bytes = WYCIAG,
    nazwa: str = "wyciag.pdf",
):
    return client.post(
        f"/api/imports/{etap}",
        headers=naglowek,
        files={"file": (nazwa, dane, "application/pdf")},
    )


def liczba_transakcji(client: TestClient, naglowek: dict) -> int:
    return client.get("/api/transactions", headers=naglowek).json()["total"]


def test_wymaga_logowania(client: TestClient) -> None:
    assert (
        client.post(
            "/api/imports/preview", files={"file": ("a.pdf", WYCIAG)}
        ).status_code
        == 401
    )


def test_podglad_niczego_nie_zapisuje(client: TestClient, jan: dict) -> None:
    odpowiedz = wyslij(client, jan, "preview")

    assert odpowiedz.status_code == 200
    podglad = odpowiedz.json()
    assert (podglad["total"], podglad["new"], podglad["duplicates"]) == (
        LICZBA,
        LICZBA,
        0,
    )
    assert podglad["bank"] == "ING"
    assert podglad["credits_count"] + podglad["debits_count"] == LICZBA
    assert liczba_transakcji(client, jan) == 0


def test_zatwierdzenie_zapisuje_transakcje(client: TestClient, jan: dict) -> None:
    odpowiedz = wyslij(client, jan, "confirm")

    assert odpowiedz.status_code == 201
    assert odpowiedz.json() | {"id": 0, "created_at": ""} == {
        "id": 0,
        "bank": "ING",
        "filename": "wyciag.pdf",
        "rows_total": LICZBA,
        "rows_imported": LICZBA,
        "rows_duplicated": 0,
        "created_at": "",
    }
    transakcje = client.get(
        "/api/transactions", headers=jan, params={"page_size": 200}
    ).json()["items"]
    assert len(transakcje) == LICZBA
    assert {t["source"] for t in transakcje} == {"pdf"}
    assert sum(Decimal(t["amount"]) for t in transakcje) == sum(
        t.amount for t in sample_transactions()
    )


def test_ponowny_import_nie_dubluje(client: TestClient, jan: dict) -> None:
    wyslij(client, jan, "confirm")

    podglad = wyslij(client, jan, "preview").json()
    drugi = wyslij(client, jan, "confirm").json()

    assert (podglad["new"], podglad["duplicates"]) == (0, LICZBA)
    assert all(t["duplicate"] for t in podglad["transactions"])
    assert (drugi["rows_imported"], drugi["rows_duplicated"]) == (0, LICZBA)
    assert liczba_transakcji(client, jan) == LICZBA


def test_czesciowo_nowy_wyciag(client: TestClient, jan: dict) -> None:
    pierwsze = sample_transactions()[:5]
    wyslij(client, jan, "confirm", make_ing_statement(pierwsze))

    podglad = wyslij(client, jan, "preview").json()

    assert (podglad["new"], podglad["duplicates"]) == (LICZBA - 5, 5)


def test_inny_uzytkownik_importuje_ten_sam_plik_niezaleznie(
    client: TestClient, jan: dict
) -> None:
    wyslij(client, jan, "confirm")
    anna = konto(client, "anna@example.com")

    odpowiedz = wyslij(client, anna, "confirm").json()

    assert odpowiedz["rows_imported"] == LICZBA
    assert liczba_transakcji(client, jan) == LICZBA


def test_historia_importow_tylko_wlasnych(client: TestClient, jan: dict) -> None:
    wyslij(client, jan, "confirm")
    wyslij(client, jan, "confirm")
    anna = konto(client, "anna@example.com")

    historia = client.get("/api/imports", headers=jan).json()

    assert [h["rows_imported"] for h in historia] == [0, LICZBA]
    assert client.get("/api/imports", headers=anna).json() == []


@pytest.mark.parametrize("etap", ["preview", "confirm"])
def test_wyciag_niezgodny_z_sumami_jest_odrzucany(
    client: TestClient, jan: dict, etap: str
) -> None:
    zepsuty = make_ing_statement(summary_override={"debits_sum": Decimal("1.00")})

    odpowiedz = wyslij(client, jan, etap, zepsuty)

    assert odpowiedz.status_code == 422
    assert "sumami kontrolnymi" in odpowiedz.json()["detail"]
    assert liczba_transakcji(client, jan) == 0
    assert client.get("/api/imports", headers=jan).json() == []


@pytest.mark.parametrize("dane", [b"to nie jest PDF", b"%PDF-1.4 uszkodzony"])
def test_plik_niebedacy_wyciagiem_daje_422(
    client: TestClient, jan: dict, dane: bytes
) -> None:
    assert wyslij(client, jan, "preview", dane).status_code == 422


def test_pdf_innego_banku_podpowiada_csv(client: TestClient, jan: dict) -> None:
    """Parser PDF obsługuje tylko ING: dla innego PDF komunikat wskazuje eksport CSV."""
    bufor = io.BytesIO()
    strona = canvas.Canvas(bufor)
    strona.drawString(72, 750, "Bank Przykladowy - wyciag z rachunku")
    strona.save()

    odpowiedz = wyslij(client, jan, "preview", bufor.getvalue())

    assert odpowiedz.status_code == 422
    komunikat = odpowiedz.json()["detail"]
    assert "tylko z ING" in komunikat
    assert "formacie CSV" in komunikat


def test_zbyt_duzy_plik_daje_413(client: TestClient, jan: dict) -> None:
    assert (
        wyslij(client, jan, "preview", b"%PDF" + b"0" * MAX_FILE_SIZE).status_code
        == 413
    )


def test_brak_pliku_daje_422(client: TestClient, jan: dict) -> None:
    assert client.post("/api/imports/preview", headers=jan).status_code == 422


def test_nazwa_pliku_bez_sciezki(client: TestClient, jan: dict) -> None:
    odpowiedz = wyslij(
        client, jan, "confirm", nazwa="C:\\Users\\jan\\Pobrane\\wyciag_10.pdf"
    )

    assert odpowiedz.json()["filename"] == "wyciag_10.pdf"


def test_dane_bankowe_z_importu_sa_zablokowane_do_edycji(
    client: TestClient, jan: dict
) -> None:
    wyslij(client, jan, "confirm")
    transakcja = client.get("/api/transactions", headers=jan).json()["items"][0]

    odpowiedz = client.patch(
        f"/api/transactions/{transakcja['id']}", headers=jan, json={"amount": "-1.00"}
    )

    assert odpowiedz.status_code == 409


def test_normalizacja_opisu() -> None:
    assert (
        normalize_description("Płatność  kartą 29.09.2026 SKLEP")
        == "płatność kartą sklep"
    )
