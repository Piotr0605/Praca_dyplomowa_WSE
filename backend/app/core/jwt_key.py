"""Klucz podpisujący tokeny JWT.

Klucz można podać w JWT_SECRET_KEY. Jeśli jest pusty, powstaje losowy przy pierwszym
uruchomieniu i zostaje w pliku poza repozytorium. Dzięki temu `cp .env.example .env`
wystarcza do startu, a w publicznym repozytorium nie ma żadnego klucza, którego ktoś
mógłby użyć do podrobienia tokenu.
"""

import os
import secrets
from functools import lru_cache
from pathlib import Path

from app.core.config import MIN_JWT_KEY_LENGTH, get_settings


def load_or_create_key(path: Path) -> str:
    """Odczytuje klucz z pliku albo tworzy nowy, dostępny tylko dla właściciela pliku."""
    try:
        # O_EXCL: plik musi być nowy, więc istniejący klucz nigdy nie zostanie nadpisany.
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        key = path.read_text(encoding="utf-8").strip()
        if len(key) < MIN_JWT_KEY_LENGTH:
            raise RuntimeError(
                f"Plik klucza JWT {path} jest pusty lub za krótki"
            ) from None
        return key

    key = secrets.token_hex(32)
    with os.fdopen(descriptor, "w", encoding="utf-8") as file:
        file.write(key)
    return key


@lru_cache
def get_jwt_secret() -> str:
    settings = get_settings()
    return settings.JWT_SECRET_KEY or load_or_create_key(settings.JWT_SECRET_FILE)
