"""Testy API importu plików CSV: profile, rozpoznanie formatu, kreator mapowania, duplikaty, izolacja."""

import json

import pytest
from fastapi.testclient import TestClient

from tests.fixtures.csv_samples import ING_ROWS, make_ing_csv, make_other_bank_csv
from tests.fixtures.ing_statement import make_ing_statement, sample_transactions
from tests.integration.helpers import konto

ING_CSV = make_ing_csv()
INNY = make_other_bank_csv()
ING_NOWYCH = len(ING_ROWS) - 1  # jedna blokada kartowa bez kwoty

PROFIL_INNEGO = {
    "bank_name": "Bank Przykładowy",
    "encoding": "utf-8-sig",
    "delimiter": ",",
    "date_format": "%d/%m/%Y",
    "decimal_separator": ".",
    "columns": {
        "date": "Data operacji",
        "credit": "Uznania",
        "debit": "Obciążenia",
        "currency": "Waluta",
        "description": ["Opis"],
        "counterparty": "Odbiorca/Nadawca",
    },
}


@pytest.fixture
def jan(client: TestClient) -> dict[str, str]:
    return konto(client, "jan@example.com")


@pytest.fixture
def anna(client: TestClient) -> dict[str, str]:
    return konto(client, "anna@example.com")


def wyslij(
    client: TestClient,
    naglowek: dict,
    etap: str,
    dane: bytes = ING_CSV,
    nazwa: str = "historia.csv",
    **pola,
):
    return client.post(
        f"/api/imports/{etap}",
        headers=naglowek,
        files={"file": (nazwa, dane, "text/csv")},
        data={k: json.dumps(v) if isinstance(v, dict) else v for k, v in pola.items()},
    )


def transakcje(client: TestClient, naglowek: dict) -> list[dict]:
    odpowiedz = client.get(
        "/api/transactions", headers=naglowek, params={"page_size": 100}
    )
    return odpowiedz.json()["items"]


def test_lista_profili_zawiera_ing(client: TestClient, jan: dict) -> None:
    profile = client.get("/api/imports/banks", headers=jan).json()
    assert {"key": "builtin:ing", "bank_name": "ING", "builtin": True} in profile


def test_profile_wymagaja_logowania(client: TestClient) -> None:
    assert client.get("/api/imports/banks").status_code == 401
    assert (
        client.post(
            "/api/imports/detect", files={"file": ("a.csv", ING_CSV)}
        ).status_code
        == 401
    )


def test_plik_ing_rozpoznany_bez_mapowania(client: TestClient, jan: dict) -> None:
    wykrycie = wyslij(client, jan, "detect").json()
    assert wykrycie["matched"]["key"] == "builtin:ing"

    podglad = wyslij(client, jan, "preview").json()
    assert podglad["format"] == "csv"
    assert podglad["bank"] == "ING"
    assert podglad["verified"] is False
    assert podglad["opening_balance"] is None
    assert (podglad["total"], podglad["new"], podglad["skipped"]) == (
        ING_NOWYCH,
        ING_NOWYCH,
        1,
    )
    assert (podglad["period_start"], podglad["period_end"]) == (
        "2026-10-01",
        "2026-10-09",
    )
    assert transakcje(client, jan) == []


def test_zapis_i_ponowny_import(client: TestClient, jan: dict) -> None:
    zapis = wyslij(client, jan, "confirm")
    assert zapis.status_code == 201
    assert zapis.json()["bank"] == "ING"
    assert zapis.json()["rows_imported"] == ING_NOWYCH

    zapisane = transakcje(client, jan)
    assert len(zapisane) == ING_NOWYCH
    assert {t["source"] for t in zapisane} == {"csv"}

    ponownie = wyslij(client, jan, "confirm").json()
    assert (ponownie["rows_imported"], ponownie["rows_duplicated"]) == (0, ING_NOWYCH)
    assert wyslij(client, jan, "preview").json()["new"] == 0


def test_nieznany_plik_wymaga_mapowania(client: TestClient, jan: dict) -> None:
    odpowiedz = wyslij(client, jan, "preview", INNY)
    assert odpowiedz.status_code == 422
    assert "kreatorze mapowania" in odpowiedz.json()["detail"]

    wykrycie = wyslij(client, jan, "detect", INNY).json()
    assert wykrycie["matched"] is None
    assert wykrycie["columns"]["credit"] == "Uznania"
    assert wykrycie["headers"][0] == "Data operacji"
    assert len(wykrycie["sample_rows"]) == 4


def test_kreator_mapowania_i_zapamietany_profil(client: TestClient, jan: dict) -> None:
    podglad = wyslij(client, jan, "preview", INNY, profile=PROFIL_INNEGO).json()
    assert (podglad["bank"], podglad["total"]) == ("Bank Przykładowy", 4)
    assert podglad["debits_count"] == 3

    zapis = wyslij(
        client, jan, "confirm", INNY, profile=PROFIL_INNEGO, save_profile="true"
    )
    assert zapis.status_code == 201
    assert zapis.json()["rows_imported"] == 4

    profile = client.get("/api/imports/banks", headers=jan).json()
    wlasny = next(p for p in profile if not p["builtin"])
    assert wlasny["bank_name"] == "Bank Przykładowy"
    assert profile[0] == wlasny, "własny profil ma pierwszeństwo przed wbudowanymi"

    # Kolejny plik z tego banku jest rozpoznawany bez kreatora.
    assert wyslij(client, jan, "detect", INNY).json()["matched"] == wlasny
    assert wyslij(client, jan, "preview", INNY).json()["duplicates"] == 4


def test_profil_bez_zapamietania(client: TestClient, jan: dict) -> None:
    wyslij(client, jan, "confirm", INNY, profile=PROFIL_INNEGO)
    profile = client.get("/api/imports/banks", headers=jan).json()
    assert all(p["builtin"] for p in profile)


def test_ponowny_zapis_profilu_zastepuje_ustawienia(
    client: TestClient, jan: dict
) -> None:
    wyslij(client, jan, "confirm", INNY, profile=PROFIL_INNEGO, save_profile="true")
    zmieniony = {**PROFIL_INNEGO, "default_currency": "EUR"}
    wyslij(client, jan, "confirm", INNY, profile=zmieniony, save_profile="true")

    wlasne = [
        p
        for p in client.get("/api/imports/banks", headers=jan).json()
        if not p["builtin"]
    ]
    assert len(wlasne) == 1


def test_profil_ktory_nie_pasuje_nie_zostaje_zapisany(
    client: TestClient, jan: dict
) -> None:
    odpowiedz = wyslij(
        client, jan, "confirm", ING_CSV, profile=PROFIL_INNEGO, save_profile="true"
    )
    assert odpowiedz.status_code == 422
    assert "kodowaniu utf-8-sig" in odpowiedz.json()["detail"]
    assert all(
        p["builtin"] for p in client.get("/api/imports/banks", headers=jan).json()
    )
    assert transakcje(client, jan) == []


def test_bledny_profil(client: TestClient, jan: dict) -> None:
    zly = {**PROFIL_INNEGO, "delimiter": ":"}
    odpowiedz = wyslij(client, jan, "preview", INNY, profile=zly)
    assert odpowiedz.status_code == 422
    assert odpowiedz.json()["detail"][0]["loc"] == ["profile", "delimiter"]

    nie_json = wyslij(client, jan, "preview", INNY, profile="{nie json")
    assert nie_json.status_code == 422


def test_wybor_profilu_po_kluczu(client: TestClient, jan: dict) -> None:
    assert (
        wyslij(client, jan, "preview", profile_key="builtin:ing").json()["total"]
        == ING_NOWYCH
    )
    assert wyslij(client, jan, "preview", profile_key="builtin:brak").status_code == 404
    assert wyslij(client, jan, "preview", profile_key="user:999").status_code == 404


def test_wymuszone_kodowanie_wylacza_dopasowanie(client: TestClient, jan: dict) -> None:
    wykrycie = wyslij(client, jan, "detect", encoding="cp1250", delimiter=";").json()
    assert wykrycie["matched"] is None
    assert wyslij(client, jan, "detect", delimiter=":").status_code == 422


def test_pdf_nie_wymaga_mapowania(client: TestClient, jan: dict) -> None:
    odpowiedz = wyslij(client, jan, "detect", make_ing_statement(), "wyciag.pdf")
    assert odpowiedz.status_code == 422


def test_pdf_i_csv_tej_samej_operacji_to_duplikat(
    client: TestClient, jan: dict
) -> None:
    """Profil ING używa tego samego klucza (numer operacji) co parser PDF."""
    wyslij(client, jan, "confirm", make_ing_statement(), "wyciag.pdf")
    pierwsza = sample_transactions()[0]
    z_pdf = (
        "2026-09-29", "2026-10-01", "SKLEP", "Płatność kartą", "TR.KART",
        f"'{pierwsza.reference}'", "-45,99", "",
    )  # fmt: skip
    nowa = ("2026-10-30", "2026-10-30", "X", "Inna", "", "'202699999999999999'", "-1,00", "")  # fmt: skip
    podglad = wyslij(client, jan, "preview", make_ing_csv([z_pdf, nowa])).json()
    assert (podglad["duplicates"], podglad["new"]) == (1, 1)


def test_cudzy_profil_jest_niewidoczny(
    client: TestClient, jan: dict, anna: dict
) -> None:
    wyslij(client, jan, "confirm", INNY, profile=PROFIL_INNEGO, save_profile="true")
    profil_jana = next(
        p
        for p in client.get("/api/imports/banks", headers=jan).json()
        if not p["builtin"]
    )
    numer = int(profil_jana["key"].split(":")[1])

    assert all(
        p["builtin"] for p in client.get("/api/imports/banks", headers=anna).json()
    )
    assert wyslij(client, anna, "detect", INNY).json()["matched"] is None
    assert (
        wyslij(
            client, anna, "preview", INNY, profile_key=profil_jana["key"]
        ).status_code
        == 404
    )
    assert client.delete(f"/api/imports/banks/{numer}", headers=anna).status_code == 404
    assert client.delete(f"/api/imports/banks/{numer}", headers=jan).status_code == 204
    assert client.delete(f"/api/imports/banks/{numer}", headers=jan).status_code == 404


def test_ten_sam_plik_u_dwoch_uzytkownikow(
    client: TestClient, jan: dict, anna: dict
) -> None:
    wyslij(client, jan, "confirm")
    assert wyslij(client, anna, "confirm").json()["rows_imported"] == ING_NOWYCH
