"""Zależności FastAPI wspólne dla endpointów."""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.core.config import get_settings
from app.core.database import DbSession
from app.core.security import InvalidTokenError, decode_access_token
from app.models import User
from app.repositories.user_repository import UserRepository

_oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{get_settings().API_PREFIX}/auth/login"
)


def get_current_user(
    token: Annotated[str, Depends(_oauth2_scheme)], db: DbSession
) -> User:
    """Ustala użytkownika z tokenu. Każdy błąd daje tę samą odpowiedź 401."""
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Nieprawidłowy lub wygasły token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        user_id = decode_access_token(token)
    except InvalidTokenError as error:
        raise unauthorized from error

    # Konto mogło zostać usunięte, gdy token był jeszcze ważny.
    user = UserRepository(db).get_by_id(user_id)
    if user is None:
        raise unauthorized
    return user


# Skrót dla endpointów wymagających logowania: `def endpoint(user: CurrentUser): ...`
CurrentUser = Annotated[User, Depends(get_current_user)]
