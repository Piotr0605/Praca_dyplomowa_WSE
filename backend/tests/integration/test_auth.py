"""Testy rejestracji, logowania i dostępu do danych zalogowanego użytkownika."""

import datetime as dt
import json
import logging

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.jwt_key import get_jwt_secret
from app.core.security import create_access_token, verify_password
from app.models import User
from app.schemas.user import MAX_PASSWORD_LENGTH, MIN_PASSWORD_LENGTH
from app.services import auth_service

EMAIL = "jan@example.com"
HASLO = "Bardzo-Dobre-Haslo-1"


def zarejestruj(client: TestClient, email: str = EMAIL, haslo: str = HASLO):
    return client.post("/api/auth/register", json={"email": email, "password": haslo})


def zaloguj(client: TestClient, email: str = EMAIL, haslo: str = HASLO):
    return client.post("/api/auth/login", data={"username": email, "password": haslo})


def naglowek(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_rejestracja_zwraca_dane_bez_hasla(client: TestClient) -> None:
    odpowiedz = zarejestruj(client)

    assert odpowiedz.status_code == 201
    assert set(odpowiedz.json()) == {"id", "email", "created_at"}
    assert odpowiedz.json()["email"] == EMAIL


def test_haslo_w_bazie_jest_hashem_argon2(
    client: TestClient, db_session: Session
) -> None:
    zarejestruj(client)

    uzytkownik = db_session.scalar(select(User).where(User.email == EMAIL))

    assert uzytkownik.password_hash.startswith("$argon2id$")
    assert verify_password(HASLO, uzytkownik.password_hash)


def test_email_jest_zapisywany_malymi_literami(client: TestClient) -> None:
    assert zarejestruj(client, email="Jan.Kowalski@Example.COM").json()["email"] == (
        "jan.kowalski@example.com"
    )


def test_duplikat_emaila_daje_409(client: TestClient) -> None:
    zarejestruj(client)

    assert zarejestruj(client).status_code == 409


def test_duplikat_innymi_literami_daje_409(client: TestClient) -> None:
    zarejestruj(client)

    assert zarejestruj(client, email=EMAIL.upper()).status_code == 409


def test_po_duplikacie_mozna_dalej_uzywac_bazy(client: TestClient) -> None:
    zarejestruj(client)
    zarejestruj(client)

    assert zarejestruj(client, email="anna@example.com").status_code == 201


@pytest.mark.parametrize(
    "haslo",
    ["x" * (MIN_PASSWORD_LENGTH - 1), "x" * (MAX_PASSWORD_LENGTH + 1)],
    ids=["za-krotkie", "za-dlugie"],
)
def test_haslo_poza_limitem_daje_422(client: TestClient, haslo: str) -> None:
    assert zarejestruj(client, haslo=haslo).status_code == 422


@pytest.mark.parametrize(
    "haslo",
    ["x" * MIN_PASSWORD_LENGTH, "x" * MAX_PASSWORD_LENGTH],
    ids=["minimum", "maksimum"],
)
def test_haslo_na_granicy_limitu_jest_przyjmowane(
    client: TestClient, haslo: str
) -> None:
    assert zarejestruj(client, haslo=haslo).status_code == 201


@pytest.mark.parametrize("email", ["", "bez-malpy", "a@", "@example.com"])
def test_bledny_email_daje_422(client: TestClient, email: str) -> None:
    assert zarejestruj(client, email=email).status_code == 422


def test_blad_walidacji_nie_odsyla_hasla(client: TestClient) -> None:
    odpowiedz = zarejestruj(client, haslo="SEKRET-krot")

    assert odpowiedz.status_code == 422
    assert "SEKRET" not in odpowiedz.text
    assert "input" not in odpowiedz.text


def test_logowanie_zwraca_token_otwierajacy_me(client: TestClient) -> None:
    zarejestruj(client)

    odpowiedz = zaloguj(client)

    assert odpowiedz.status_code == 200
    assert odpowiedz.json()["token_type"] == "bearer"
    me = client.get("/api/auth/me", headers=naglowek(odpowiedz.json()["access_token"]))
    assert me.status_code == 200
    assert me.json()["email"] == EMAIL


def test_logowanie_nie_zalezy_od_wielkosci_liter_w_emailu(client: TestClient) -> None:
    zarejestruj(client)

    assert zaloguj(client, email=EMAIL.upper()).status_code == 200


def test_zle_haslo_i_nieznany_email_daja_te_sama_odpowiedz(client: TestClient) -> None:
    zarejestruj(client)

    zle_haslo = zaloguj(client, haslo="Zupelnie-Inne-Haslo")
    nieznany = zaloguj(client, email="nikt@example.com")

    assert zle_haslo.status_code == nieznany.status_code == 401
    assert zle_haslo.json() == nieznany.json()
    assert zle_haslo.headers["www-authenticate"] == "Bearer"


def test_nieznany_email_tez_liczy_hash(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bez tego czas odpowiedzi zdradzałby, czy konto istnieje."""
    wywolania = []
    monkeypatch.setattr(
        auth_service, "verify_password_against_dummy", lambda: wywolania.append(True)
    )

    zaloguj(client, email="nikt@example.com")

    assert wywolania == [True]


def test_zbyt_dlugie_haslo_przy_logowaniu_daje_401(client: TestClient) -> None:
    zarejestruj(client)

    assert zaloguj(client, haslo="x" * (MAX_PASSWORD_LENGTH + 1)).status_code == 401


def test_zbyt_dlugie_haslo_nie_jest_liczone_argon2(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Limit chroni serwer: bardzo długie hasło nie może trafić do prawdziwego porównania."""
    zarejestruj(client)

    def nie_powinno_byc_wywolane(*_: object) -> bool:
        raise AssertionError("Zbyt długie hasło trafiło do verify_password")

    monkeypatch.setattr(auth_service, "verify_password", nie_powinno_byc_wywolane)

    assert zaloguj(client, haslo="x" * (MAX_PASSWORD_LENGTH + 1)).status_code == 401


def test_me_bez_tokenu_daje_401(client: TestClient) -> None:
    assert client.get("/api/auth/me").status_code == 401


def test_me_ze_smieciowym_tokenem_daje_401(client: TestClient) -> None:
    assert client.get("/api/auth/me", headers=naglowek("abc")).status_code == 401


def test_me_z_wygaslym_tokenem_daje_401(client: TestClient) -> None:
    uzytkownik_id = zarejestruj(client).json()["id"]
    wygasly = jwt.encode(
        {
            "sub": str(uzytkownik_id),
            "exp": dt.datetime.now(dt.UTC) - dt.timedelta(seconds=1),
        },
        get_jwt_secret(),
        algorithm="HS256",
    )

    assert client.get("/api/auth/me", headers=naglowek(wygasly)).status_code == 401


def test_token_usunietego_uzytkownika_daje_401(
    client: TestClient, db_session: Session
) -> None:
    uzytkownik_id = zarejestruj(client).json()["id"]
    token = create_access_token(uzytkownik_id)

    db_session.delete(db_session.get(User, uzytkownik_id))
    db_session.commit()

    assert client.get("/api/auth/me", headers=naglowek(token)).status_code == 401


def test_me_zwraca_dane_wlasciciela_tokenu(client: TestClient) -> None:
    zarejestruj(client)
    zarejestruj(client, email="anna@example.com")

    token = zaloguj(client, email="anna@example.com").json()["access_token"]

    assert (
        client.get("/api/auth/me", headers=naglowek(token)).json()["email"]
        == "anna@example.com"
    )


def test_haslo_i_hash_nie_trafiaja_do_odpowiedzi_ani_logow(
    client: TestClient, db_session: Session, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)

    odpowiedzi = [
        zarejestruj(client),
        zarejestruj(client),
        zarejestruj(client, email="b@example.com", haslo="Krotk13"),
        zaloguj(client),
        zaloguj(client, haslo="Inne-Zle-Haslo-77"),
    ]
    token = odpowiedzi[3].json()["access_token"]
    odpowiedzi.append(client.get("/api/auth/me", headers=naglowek(token)))
    uzytkownik = db_session.scalar(select(User).where(User.email == EMAIL))

    tresc = " ".join(o.text for o in odpowiedzi) + json.dumps(caplog.text)
    for sekret in (HASLO, "Krotk13", "Inne-Zle-Haslo-77", uzytkownik.password_hash):
        assert sekret not in tresc
