"""Rejestracja i logowanie."""

from psycopg.errors import UniqueViolation
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import (
    hash_password,
    verify_password,
    verify_password_against_dummy,
)
from app.models import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import MAX_PASSWORD_LENGTH, normalize_email


class EmailAlreadyRegisteredError(Exception):
    """Konto z tym adresem już istnieje."""


def register_user(session: Session, email: str, password: str) -> User:
    """Tworzy konto. E-mail musi być już znormalizowany.

    Duplikat wykrywa ograniczenie UNIQUE, a nie wcześniejsze zapytanie SELECT: tylko baza
    daje pewność przy dwóch jednoczesnych rejestracjach tego samego adresu.
    """
    try:
        user = UserRepository(session).add(email, hash_password(password))
        session.commit()
    except IntegrityError as error:
        session.rollback()
        if isinstance(error.orig, UniqueViolation):
            raise EmailAlreadyRegisteredError from error
        raise
    return user


def authenticate_user(session: Session, email: str, password: str) -> User | None:
    """Zwraca użytkownika albo None, tak samo dla złego hasła i nieistniejącego konta."""
    user = UserRepository(session).get_by_email(normalize_email(email))
    if user is None or len(password) > MAX_PASSWORD_LENGTH:
        # Argon2 liczy się też tutaj: czas odpowiedzi nie zdradza, czy konto istnieje.
        verify_password_against_dummy()
        return None
    return user if verify_password(password, user.password_hash) else None
