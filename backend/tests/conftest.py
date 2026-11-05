"""Wspólne elementy testów: osobna baza danych i klient HTTP.

Testy nie dotykają bazy deweloperskiej. Na początku przebiegu powstaje od zera baza
<nazwa>_test ze schematem z migracji, a każdy test działa w transakcji wycofywanej na końcu.
"""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.main import app
from tests.db_helpers import database_url_for_tests, recreate_database, run_migrations


@pytest.fixture(scope="session")
def test_engine() -> Iterator[Engine]:
    url = database_url_for_tests()
    recreate_database(url)
    run_migrations(url)
    engine = create_engine(url)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(test_engine: Engine) -> Iterator[Session]:
    """Sesja w transakcji wycofywanej po teście. `commit` w kodzie zamyka tylko punkt zapisu."""
    with test_engine.connect() as connection:
        transaction = connection.begin()
        session = Session(
            bind=connection,
            join_transaction_mode="create_savepoint",
            autoflush=False,
            expire_on_commit=False,
        )
        yield session
        session.close()
        transaction.rollback()


@pytest.fixture
def client(db_session: Session) -> Iterator[TestClient]:
    """Klient HTTP, którego zapytania korzystają z bazy testowej."""

    def get_test_db() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_db] = get_test_db
    with TestClient(app) as test_client:
        yield test_client
    # Podmiany zależności z jednego testu nie mogą wpływać na kolejne.
    app.dependency_overrides.clear()
