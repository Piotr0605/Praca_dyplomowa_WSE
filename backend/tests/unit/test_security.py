"""Testy haseł i tokenów logowania."""

import datetime as dt
import stat
from pathlib import Path

import jwt
import pytest
from pydantic import ValidationError

from app.core.config import Settings, get_settings
from app.core.jwt_key import get_jwt_secret, load_or_create_key
from app.core.security import (
    InvalidTokenError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def podpisz(payload: dict, klucz: str | None = None, algorytm: str = "HS256") -> str:
    return jwt.encode(payload, klucz or get_jwt_secret(), algorithm=algorytm)


def za_godzine() -> dt.datetime:
    return dt.datetime.now(dt.UTC) + dt.timedelta(hours=1)


def test_hash_to_argon2id_bez_jawnego_hasla() -> None:
    wynik = hash_password("Tajne-hasło-123")

    assert wynik.startswith("$argon2id$")
    assert "Tajne-hasło-123" not in wynik


def test_to_samo_haslo_daje_rozne_hashe() -> None:
    assert hash_password("to-samo-haslo") != hash_password("to-samo-haslo")


@pytest.mark.parametrize("haslo", ["proste-haslo", "zażółć gęślą jaźń", "x" * 200])
def test_poprawne_haslo_pasuje(haslo: str) -> None:
    assert verify_password(haslo, hash_password(haslo)) is True


def test_bledne_haslo_nie_pasuje() -> None:
    assert verify_password("Haslo-1", hash_password("haslo-1")) is False


@pytest.mark.parametrize("uszkodzony", ["", "nie-hash", "$argon2id$v=19$uszkodzony"])
def test_uszkodzony_hash_nie_powoduje_bledu(uszkodzony: str) -> None:
    assert verify_password("haslo", uszkodzony) is False


def test_token_zwraca_identyfikator_uzytkownika() -> None:
    assert decode_access_token(create_access_token(42)) == 42


def test_token_zawiera_tylko_identyfikator_i_czasy() -> None:
    zawartosc = jwt.decode(create_access_token(42), options={"verify_signature": False})

    assert set(zawartosc) == {"sub", "iat", "exp"}


def test_token_wygasa_po_czasie_z_ustawien() -> None:
    zawartosc = jwt.decode(create_access_token(42), options={"verify_signature": False})

    assert (
        zawartosc["exp"] - zawartosc["iat"]
        == get_settings().ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


def test_wygasly_token_jest_odrzucany() -> None:
    wygasly = podpisz(
        {"sub": "42", "exp": dt.datetime.now(dt.UTC) - dt.timedelta(seconds=1)}
    )

    with pytest.raises(InvalidTokenError):
        decode_access_token(wygasly)


def test_token_z_innego_klucza_jest_odrzucany() -> None:
    obcy = podpisz({"sub": "42", "exp": za_godzine()}, klucz="inny-klucz-" + "x" * 32)

    with pytest.raises(InvalidTokenError):
        decode_access_token(obcy)


def test_zmieniona_zawartosc_tokenu_jest_odrzucana() -> None:
    naglowek, _, podpis = create_access_token(1).split(".")
    obca_tresc = podpisz({"sub": "2", "exp": za_godzine()}).split(".")[1]

    with pytest.raises(InvalidTokenError):
        decode_access_token(f"{naglowek}.{obca_tresc}.{podpis}")


def test_token_bez_podpisu_jest_odrzucany() -> None:
    bez_podpisu = jwt.encode(
        {"sub": "42", "exp": za_godzine()}, key="", algorithm="none"
    )

    with pytest.raises(InvalidTokenError):
        decode_access_token(bez_podpisu)


def test_token_podpisany_innym_algorytmem_jest_odrzucany() -> None:
    inny = podpisz({"sub": "42", "exp": za_godzine()}, algorytm="HS512")

    with pytest.raises(InvalidTokenError):
        decode_access_token(inny)


def test_token_bez_identyfikatora_jest_odrzucany() -> None:
    with pytest.raises(InvalidTokenError):
        decode_access_token(podpisz({"exp": za_godzine()}))


def test_token_bez_czasu_waznosci_jest_odrzucany() -> None:
    with pytest.raises(InvalidTokenError):
        decode_access_token(podpisz({"sub": "42"}))


def test_identyfikator_niebedacy_liczba_jest_odrzucany() -> None:
    with pytest.raises(InvalidTokenError):
        decode_access_token(podpisz({"sub": "nie-liczba", "exp": za_godzine()}))


@pytest.mark.parametrize("smieci", ["", "abc", "a.b.c"])
def test_napis_niebedacy_tokenem_jest_odrzucany(smieci: str) -> None:
    with pytest.raises(InvalidTokenError):
        decode_access_token(smieci)


def test_klucz_jest_generowany_raz_i_chroniony(tmp_path: Path) -> None:
    plik = tmp_path / "jwt_secret"

    pierwszy = load_or_create_key(plik)
    drugi = load_or_create_key(plik)

    assert pierwszy == drugi
    assert len(pierwszy) == 64
    assert stat.S_IMODE(plik.stat().st_mode) == 0o600


def test_rozne_instalacje_maja_rozne_klucze(tmp_path: Path) -> None:
    assert load_or_create_key(tmp_path / "a") != load_or_create_key(tmp_path / "b")


def test_uszkodzony_plik_klucza_zatrzymuje_start(tmp_path: Path) -> None:
    plik = tmp_path / "jwt_secret"
    plik.write_text("za-krotki")

    with pytest.raises(RuntimeError):
        load_or_create_key(plik)


@pytest.mark.parametrize(
    "klucz",
    ["wygeneruj_np_openssl_rand_hex_32", "krotki"],
    ids=["publiczny", "za-krotki"],
)
def test_niebezpieczny_klucz_jest_odrzucany(
    klucz: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@localhost/db")
    monkeypatch.setenv("JWT_SECRET_KEY", klucz)

    with pytest.raises(ValidationError, match="JWT_SECRET_KEY") as blad:
        Settings(_env_file=None)

    assert klucz not in str(blad.value)


@pytest.mark.parametrize("algorytm", ["none", "HS512"])
def test_inny_algorytm_w_ustawieniach_jest_odrzucany(
    algorytm: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@localhost/db")
    monkeypatch.setenv("JWT_ALGORITHM", algorytm)

    with pytest.raises(ValidationError, match="JWT_ALGORITHM"):
        Settings(_env_file=None)
