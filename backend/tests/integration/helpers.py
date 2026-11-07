"""Pomocnicze funkcje testów API."""

from fastapi.testclient import TestClient

HASLO = "Bardzo-Dobre-Haslo-1"


def konto(client: TestClient, email: str) -> dict[str, str]:
    """Rejestruje użytkownika i zwraca nagłówek z jego tokenem."""
    assert (
        client.post(
            "/api/auth/register", json={"email": email, "password": HASLO}
        ).status_code
        == 201
    )
    token = client.post(
        "/api/auth/login", data={"username": email, "password": HASLO}
    ).json()
    return {"Authorization": f"Bearer {token['access_token']}"}
