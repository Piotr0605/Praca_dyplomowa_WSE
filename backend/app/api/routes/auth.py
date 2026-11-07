"""Rejestracja, logowanie i dane zalogowanego użytkownika."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import CurrentUser
from app.core.database import DbSession
from app.core.security import create_access_token
from app.schemas.user import Token, UserCreate, UserRead
from app.services.auth_service import (
    EmailAlreadyRegisteredError,
    authenticate_user,
    register_user,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(data: UserCreate, db: DbSession) -> UserRead:
    try:
        user = register_user(db, data.email, data.password.get_secret_value())
    except EmailAlreadyRegisteredError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Konto z tym adresem e-mail już istnieje",
        ) from error
    return UserRead.model_validate(user)


@router.post("/login")
def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()], db: DbSession
) -> Token:
    """Pole `username` formularza to adres e-mail (standard OAuth2, wymagany przez Swaggera)."""
    user = authenticate_user(db, form.username, form.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nieprawidłowy e-mail lub hasło",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Token(access_token=create_access_token(user.id))


@router.get("/me")
def me(user: CurrentUser) -> UserRead:
    return UserRead.model_validate(user)
