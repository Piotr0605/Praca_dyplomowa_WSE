"""Testy konfiguracji: aplikacja ma odmówić startu bez wymaganych ustawień."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_brak_database_url_zatrzymuje_start(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(ValidationError, match="DATABASE_URL"):
        Settings(_env_file=None)


def test_dodatkowe_zmienne_w_env_sa_pomijane(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@localhost/db")
    monkeypatch.setenv("VITE_API_URL", "http://localhost:8000")

    settings = Settings(_env_file=None)

    assert settings.DATABASE_URL == "postgresql+psycopg://u:p@localhost/db"
