"""Testy GET /api/health. Test integracyjny łączy się z prawdziwą bazą PostgreSQL."""

from collections.abc import Iterator

from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.core.database import get_db
from app.main import app


def test_health_z_dzialajaca_baza(client: TestClient) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_health_bez_bazy_zwraca_503(client: TestClient) -> None:
    class NiedostepnaBaza:
        def execute(self, *args: object, **kwargs: object) -> None:
            raise OperationalError("SELECT 1", {}, Exception("connection refused"))

    def get_db_bez_polaczenia() -> Iterator[NiedostepnaBaza]:
        yield NiedostepnaBaza()

    app.dependency_overrides[get_db] = get_db_bez_polaczenia

    response = client.get("/api/health")

    assert response.status_code == 503
    assert response.json() == {"status": "degraded", "database": "error"}


def test_cors_dopuszcza_adres_frontendu(client: TestClient) -> None:
    origin = "http://localhost:5173"

    response = client.get("/api/health", headers={"Origin": origin})

    assert response.headers["access-control-allow-origin"] == origin


def test_cors_nie_dopuszcza_innej_strony(client: TestClient) -> None:
    response = client.get(
        "/api/health", headers={"Origin": "https://obca-strona.example"}
    )

    assert "access-control-allow-origin" not in response.headers
