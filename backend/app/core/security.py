"""Hashowanie haseł (Argon2) i tokeny logowania (JWT)."""

import datetime as dt
import secrets

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.config import get_settings
from app.core.jwt_key import get_jwt_secret

# Domyślne parametry biblioteki to zalecany profil RFC 9106 (Argon2id).
_password_hasher = PasswordHasher()
# Hash losowego hasła do porównań, gdy konto nie istnieje (zob. verify_password_against_dummy).
_DUMMY_PASSWORD_HASH = _password_hasher.hash(secrets.token_hex(32))


class InvalidTokenError(Exception):
    """Token jest nieprawidłowy, podrobiony albo wygasł."""


def hash_password(password: str) -> str:
    """Zwraca hash z losową solą: to samo hasło daje za każdym razem inny wynik."""
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Sprawdza hasło. Uszkodzony hash oznacza brak dopasowania, a nie błąd serwera."""
    try:
        return _password_hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def verify_password_against_dummy() -> None:
    """Zużywa tyle samo czasu co sprawdzenie prawdziwego hasła, a wynik nie ma znaczenia."""
    verify_password("", _DUMMY_PASSWORD_HASH)


def create_access_token(user_id: int) -> str:
    """Tworzy token. Zawartość JWT da się odczytać, więc jest w nim tylko identyfikator."""
    settings = get_settings()
    now = dt.datetime.now(dt.UTC)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + dt.timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, get_jwt_secret(), algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> int:
    """Zwraca identyfikator użytkownika albo zgłasza InvalidTokenError."""
    try:
        payload = jwt.decode(
            token,
            get_jwt_secret(),
            # Jawna lista blokuje tokeny z algorytmem podanym przez nadawcę, np. "none".
            algorithms=[get_settings().JWT_ALGORITHM],
            options={"require": ["exp", "sub"]},
        )
        return int(payload["sub"])
    except (jwt.InvalidTokenError, ValueError) as error:
        raise InvalidTokenError from error
