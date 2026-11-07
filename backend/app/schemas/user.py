"""Dane wejściowe i odpowiedzi API dotyczące kont."""

import datetime as dt
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field, SecretStr

MIN_PASSWORD_LENGTH = 12
MAX_PASSWORD_LENGTH = 128


def normalize_email(email: str) -> str:
    """E-mail w jednej postaci: bez białych znaków i małymi literami."""
    return email.strip().lower()


NormalizedEmail = Annotated[EmailStr, AfterValidator(normalize_email)]


class UserCreate(BaseModel):
    email: NormalizedEmail
    # SecretStr: hasło nie pojawi się przez przypadek w logach ani w repr obiektu.
    password: SecretStr = Field(
        min_length=MIN_PASSWORD_LENGTH, max_length=MAX_PASSWORD_LENGTH
    )


class UserRead(BaseModel):
    """Dane konta w odpowiedzi API. Celowo bez hasła i jego hasha."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    created_at: dt.datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
