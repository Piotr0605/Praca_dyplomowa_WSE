"""Połączenie z bazą PostgreSQL przez SQLAlchemy 2.0."""

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

# Engine zarządza pulą połączeń. pool_pre_ping sprawdza połączenie przed użyciem,
# dzięki czemu restart kontenera bazy nie zostawia "martwych" połączeń w puli.
engine = create_engine(get_settings().DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """Klasa bazowa wszystkich modeli ORM (tabel)."""


def get_db() -> Iterator[Session]:
    """Zależność FastAPI: jedna sesja bazy na jedno zapytanie HTTP, zawsze zamykana."""
    with SessionLocal() as session:
        yield session


# Skrót do wstrzykiwania sesji w endpointach: `def endpoint(db: DbSession): ...`
DbSession = Annotated[Session, Depends(get_db)]
