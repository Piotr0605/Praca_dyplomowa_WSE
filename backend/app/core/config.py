"""Konfiguracja aplikacji wczytywana ze zmiennych środowiskowych (plik .env).

Pydantic sprawdza typy przy starcie: brak wymaganej zmiennej (np. DATABASE_URL)
zatrzymuje aplikację z czytelnym komunikatem, zamiast błędu w przypadkowym miejscu.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

MIN_JWT_KEY_LENGTH = 32
# Przykład z wcześniejszej wersji .env.example: jest publiczny, więc nie może podpisywać tokenów.
PUBLIC_EXAMPLE_JWT_KEYS = {"wygeneruj_np_openssl_rand_hex_32"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        # .env zawiera też zmienne innych usług (np. POSTGRES_*, VITE_*), więc je pomijamy.
        extra="ignore",
        # Błędna wartość może być sekretem, np. za krótkim kluczem: nie wypisujemy jej w logach.
        hide_input_in_errors=True,
    )

    APP_NAME: str = "Asystent finansów osobistych"
    API_PREFIX: str = "/api"

    DATABASE_URL: str

    # Adresy, z których przeglądarka może wywoływać API (CORS).
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    # Pusty klucz oznacza: wygeneruj losowy i zapisz w JWT_SECRET_FILE (zob. core/jwt_key.py).
    JWT_SECRET_KEY: str = ""
    JWT_SECRET_FILE: Path = Path("/data/jwt_secret")
    # Tylko algorytmy HMAC: wartość "none" wyłączałaby podpis.
    JWT_ALGORITHM: Literal["HS256", "HS384", "HS512"] = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60, gt=0)

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def validate_jwt_secret_key(cls, value: str) -> str:
        if value in PUBLIC_EXAMPLE_JWT_KEYS:
            raise ValueError(
                "to publiczny przykład: zostaw JWT_SECRET_KEY pusty albo podaj własny"
            )
        if value and len(value) < MIN_JWT_KEY_LENGTH:
            raise ValueError(f"klucz musi mieć co najmniej {MIN_JWT_KEY_LENGTH} znaki")
        return value


@lru_cache
def get_settings() -> Settings:
    """Jedna instancja ustawień na cały proces (wczytanie .env tylko raz)."""
    return Settings()
