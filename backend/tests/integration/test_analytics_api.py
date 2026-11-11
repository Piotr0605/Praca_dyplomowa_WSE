"""Testy API analityki: wyciąg ze Smart Saver, transakcje ręczne, okresy, izolacja użytkowników."""

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from tests.fixtures.ing_statement import make_ing_statement
from tests.integration.helpers import konto


@pytest.fixture
def jan(client: TestClient) -> dict[str, str]:
    return konto(client, "jan@example.com")


def importuj_wyciag(client: TestClient, naglowek: dict) -> None:
    odpowiedz = client.post(
        "/api/imports/confirm",
        headers=naglowek,
        files={"file": ("wyciag.pdf", make_ing_statement(), "application/pdf")},
    )
    assert odpowiedz.status_code == 201


def dodaj(client: TestClient, naglowek: dict, data: str, kwota: str, **pola) -> None:
    odpowiedz = client.post(
        "/api/transactions",
        headers=naglowek,
        json={"date": data, "amount": kwota, "description": pola.pop("opis", "x")}
        | pola,
    )
    assert odpowiedz.status_code == 201, odpowiedz.text


def kategoria(client: TestClient, naglowek: dict, nazwa: str) -> int:
    kategorie = client.get("/api/categories", headers=naglowek).json()
    return next(k["id"] for k in kategorie if k["name"] == nazwa)


def test_wymaga_logowania(client: TestClient) -> None:
    for sciezka in ("summary", "by-category", "monthly", "changes", "top"):
        assert client.get(f"/api/analytics/{sciezka}").status_code == 401


def test_wyciag_ze_smart_saver(client: TestClient, jan: dict) -> None:
    """Przelewy własne (Smart Saver 4,60 i przelew własny 500,00) nie są wydatkiem.

    Wydatki: płatności 1853,20. Przychody: wynagrodzenie 5120,00, wpłata gotówki 2000,00 i zwrot
    113,98 w „Restauracje”: w okresie nie ma wydatków w tej kategorii, więc saldo kategorii jest
    wpływem. Razem 7233,98. Saldo 5380,78 = suma kwot poza przelewami własnymi. Daty to daty operacji
    (płatność kartą z 29.09 zaksięgowana 1.10)."""
    importuj_wyciag(client, jan)
    s = client.get("/api/analytics/summary", headers=jan).json()

    assert (s["income"], s["expenses"], s["balance"]) == (
        "7233.98",
        "1853.20",
        "5380.78",
    )
    assert s["own_transfers_net"] == "504.60"
    assert (s["date_from"], s["date_to"]) == ("2026-09-29", "2026-10-21")
    assert s["savings_rate"] == round(5380.78 / 7233.98, 4)
    assert s["days"] == 23
    assert s["avg_daily_expense"] == str(
        (Decimal("1853.20") / 23).quantize(Decimal("0.01"))
    )

    # Niezależne sprawdzenie: suma wszystkich kwot z listy transakcji poza przelewami własnymi.
    lista = client.get(
        "/api/transactions", headers=jan, params={"page_size": 200}
    ).json()["items"]
    assert sum(
        Decimal(t["amount"]) for t in lista if t["kind"] != "own_transfer"
    ) == Decimal(s["balance"])
    assert s["transactions"] == len(lista) - 2


def test_kategorie_i_udzialy(client: TestClient, jan: dict) -> None:
    importuj_wyciag(client, jan)
    wynik = client.get("/api/analytics/by-category", headers=jan).json()

    wydatki = wynik["expenses"]
    assert sum(Decimal(k["amount"]) for k in wydatki) == Decimal("1853.20")
    assert sum(k["share"] for k in wydatki) == pytest.approx(1, abs=0.001)
    kwoty = [Decimal(k["amount"]) for k in wydatki]
    assert kwoty == sorted(kwoty, reverse=True)
    assert "Przelewy własne" not in {k["name"] for k in wydatki + wynik["income"]}
    assert sum(Decimal(k["amount"]) for k in wynik["income"]) == Decimal("7233.98")
    restauracje = next(k for k in wynik["income"] if k["name"] == "Restauracje")
    assert (restauracje["amount"], restauracje["color"]) == ("113.98", "#e34948")


def test_okres_zawęża_dane(client: TestClient, jan: dict) -> None:
    importuj_wyciag(client, jan)
    s = client.get(
        "/api/analytics/summary",
        headers=jan,
        params={"date_from": "2026-09-29", "date_to": "2026-10-02"},
    ).json()
    # 29.09: karta 45,99 (Smart Saver 4,60 poza wydatkami); 02.10: 1403,86 + 106,41 + 3,19.
    assert (s["income"], s["expenses"], s["own_transfers_net"]) == (
        "0.00",
        "1559.45",
        "4.60",
    )
    assert s["savings_rate"] is None
    assert s["days"] == 4


def test_bledny_okres(client: TestClient, jan: dict) -> None:
    odpowiedz = client.get(
        "/api/analytics/summary",
        headers=jan,
        params={"date_from": "2026-10-05", "date_to": "2026-10-01"},
    )
    assert odpowiedz.status_code == 422


def test_konto_bez_transakcji(client: TestClient, jan: dict) -> None:
    s = client.get("/api/analytics/summary", headers=jan).json()
    assert (s["income"], s["expenses"], s["transactions"]) == ("0.00", "0.00", 0)
    assert client.get("/api/analytics/monthly", headers=jan).json() == []
    zmiany = client.get("/api/analytics/changes", headers=jan).json()
    assert zmiany["items"] == []
    top = client.get("/api/analytics/top", headers=jan).json()
    assert top == {"counterparties": [], "largest": []}


def test_trend_i_zmiany_miesieczne(client: TestClient, jan: dict) -> None:
    spoz = kategoria(client, jan, "Zakupy spożywcze")
    pensja = kategoria(client, jan, "Wynagrodzenie")
    # Lipiec niepełny (od 15.07), sierpień i wrzesień pełne, październik pełny.
    dodaj(client, jan, "2026-07-15", "-100.00", category_id=spoz)
    dodaj(client, jan, "2026-08-10", "-200.00", category_id=spoz)
    dodaj(client, jan, "2026-09-10", "-400.00", category_id=spoz)
    dodaj(client, jan, "2026-10-01", "3000.00", category_id=pensja)
    dodaj(client, jan, "2026-10-10", "-450.00", category_id=spoz)

    miesiace = client.get("/api/analytics/monthly", headers=jan).json()
    assert [(m["month"], m["expenses"], m["complete"]) for m in miesiace] == [
        ("2026-07", "100.00", False),
        ("2026-08", "200.00", True),
        ("2026-09", "400.00", True),
        ("2026-10", "450.00", True),
    ]
    assert miesiace[-1]["income"] == "3000.00"
    assert miesiace[-1]["savings_rate"] == 0.85

    # Domyślnie ostatni pełny miesiąc: październik; średnia z sierpnia i września (lipiec niepełny).
    zmiany = client.get("/api/analytics/changes", headers=jan).json()
    assert zmiany["month"] == "2026-10"
    assert zmiany["previous_month"] == "2026-09"
    assert zmiany["average_months"] == ["2026-08", "2026-09"]
    (pozycja,) = zmiany["items"]
    assert (pozycja["current"], pozycja["previous"], pozycja["average"]) == (
        "450.00",
        "400.00",
        "300.00",
    )
    assert (pozycja["change_previous"], pozycja["change_average"]) == (0.125, 0.5)

    wrzesien = client.get(
        "/api/analytics/changes", headers=jan, params={"month": "2026-09"}
    ).json()
    assert wrzesien["average_months"] == ["2026-08"]
    assert wrzesien["items"][0]["change_previous"] == 1.0

    assert (
        client.get(
            "/api/analytics/changes", headers=jan, params={"month": "2026-13"}
        ).status_code
        == 422
    )
    assert len(client.get("/api/analytics/monthly?months=2", headers=jan).json()) == 2


def test_najwieksi_odbiorcy_i_wydatki(client: TestClient, jan: dict) -> None:
    importuj_wyciag(client, jan)
    top = client.get("/api/analytics/top", headers=jan, params={"limit": 3}).json()

    assert top["counterparties"][0] == {
        "name": "PayU ul. Testowa 2 Poznań",
        "amount": "1403.86",
        "count": 1,
    }
    assert len(top["counterparties"]) == 3
    assert [e["amount"] for e in top["largest"]] == ["1403.86", "106.41", "50.00"]
    # Przelew własny (500,00) nie jest wydatkiem, więc nie ma go wśród największych.
    assert all(e["counterparty"] != "JAN TESTOWY" for e in top["largest"])


def test_inny_uzytkownik_nie_widzi_danych(client: TestClient, jan: dict) -> None:
    importuj_wyciag(client, jan)
    anna = konto(client, "anna@example.com")
    s = client.get("/api/analytics/summary", headers=anna).json()
    assert (s["transactions"], s["expenses"]) == (0, "0.00")
    assert client.get("/api/analytics/monthly", headers=anna).json() == []
    assert client.get("/api/analytics/top", headers=anna).json()["largest"] == []


def test_inna_waluta_pominieta(client: TestClient, jan: dict) -> None:
    dodaj(client, jan, "2026-10-01", "-10.00", currency="EUR")
    dodaj(client, jan, "2026-10-01", "-20.00")
    s = client.get("/api/analytics/summary", headers=jan).json()
    assert (s["expenses"], s["other_currency"]) == ("20.00", 1)
