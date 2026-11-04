"""Wspólne elementy testów."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> Iterator[TestClient]:
    """Klient HTTP wysyłający zapytania do aplikacji bez uruchamiania serwera."""
    with TestClient(app) as test_client:
        yield test_client
    # Podmiany zależności z jednego testu nie mogą wpływać na kolejne.
    app.dependency_overrides.clear()
