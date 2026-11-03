"""Połączenie z bazą PostgreSQL przez SQLAlchemy 2.0."""

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy import MetaData, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

# Engine zarządza pulą połączeń. pool_pre_ping sprawdza połączenie przed użyciem,
# dzięki czemu restart kontenera bazy nie zostawia "martwych" połączeń w puli.
engine = create_engine(get_settings().DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


# Stałe, przewidywalne nazwy ograniczeń (np. uq_transactions_user_id, fk_transactions_user_id_users).
# Bez tego PostgreSQL nadaje nazwy automatycznie, a Alembic nie potrafi potem
# niezawodnie zmienić ani usunąć takiego ograniczenia w kolejnej migracji.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Klasa bazowa wszystkich modeli ORM (tabel)."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def get_db() -> Iterator[Session]:
    """Zależność FastAPI: jedna sesja bazy na jedno zapytanie HTTP, zawsze zamykana."""
    with SessionLocal() as session:
        yield session


# Skrót do wstrzykiwania sesji w endpointach: `def endpoint(db: DbSession): ...`
DbSession = Annotated[Session, Depends(get_db)]
