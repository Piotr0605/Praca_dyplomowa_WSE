"""Konfiguracja aplikacji wczytywana ze zmiennych środowiskowych (plik .env).

Pydantic sprawdza typy przy starcie: brak wymaganej zmiennej (np. DATABASE_URL)
zatrzymuje aplikację z czytelnym komunikatem, zamiast błędu w przypadkowym miejscu.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        # .env zawiera też zmienne innych usług (np. POSTGRES_*, VITE_*), więc je pomijamy.
        extra="ignore",
    )

    APP_NAME: str = "Asystent finansów osobistych"
    API_PREFIX: str = "/api"

    DATABASE_URL: str

    # Adresy, z których przeglądarka może wywoływać API (CORS).
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    """Jedna instancja ustawień na cały proces (wczytanie .env tylko raz)."""
    return Settings()
