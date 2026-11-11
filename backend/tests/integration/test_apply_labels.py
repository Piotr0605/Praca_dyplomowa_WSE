"""Testy przeniesienia etykiet z badania na konto użytkownika (scripts/apply_labels.py)."""

import datetime as dt
import io

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Category, CategoryRule, Transaction, User
from scripts.apply_labels import apply_labels, read_labels
from tests.fixtures.csv_samples import make_ing_csv
from tests.integration.helpers import konto


def importuj(client: TestClient, naglowek: dict, dane: bytes | None = None) -> None:
    odpowiedz = client.post(
        "/api/imports/confirm",
        headers=naglowek,
        files={"file": ("h.csv", dane or make_ing_csv(), "text/csv")},
    )
    assert odpowiedz.status_code == 201


def uzytkownik(db: Session, email: str) -> int:
    return db.scalar(select(User.id).where(User.email == email))


def klucze(db: Session, user_id: int) -> dict[str, list[str]]:
    """Klucze duplikatów po kontrahencie (prowizja nie ma kontrahenta: „brak”)."""
    wynik: dict[str, list[str]] = {}
    for t in db.scalars(select(Transaction).where(Transaction.user_id == user_id)):
        wynik.setdefault(t.counterparty or "brak", []).append(t.dedup_hash)
    return wynik


def stan(db: Session, user_id: int) -> dict[str, tuple[str | None, str | None]]:
    rows = db.execute(
        select(Transaction.counterparty, Category.name, Transaction.categorized_by)
        .outerjoin(Category, Category.id == Transaction.category_id)
        .where(Transaction.user_id == user_id)
    )
    return {(k or "brak"): (n, by.value if by else None) for k, n, by in rows}


@pytest.fixture
def naglowek_jana(client: TestClient) -> dict[str, str]:
    naglowek = konto(client, "jan@example.com")
    importuj(client, naglowek)
    return naglowek


@pytest.fixture
def jan(db_session: Session, naglowek_jana: dict) -> int:
    return uzytkownik(db_session, "jan@example.com")


def etykiety_jana(db: Session, jan: int) -> dict[str, str]:
    """Przelew własny (JAN TESTOWY) bez etykiety, jak w narzędziu do etykietowania."""
    nazwy = {
        "SKLEP TESTOWY WARSZAWA": "Zakupy spożywcze",
        "PayU ul. Testowa 2 Poznań": "Rozrywka",
        "FIRMA PRZYKŁADOWA SP. Z O.O.": "Wynagrodzenie",
        "BANKOMAT TESTOWY": "Gotówka",
        "brak": "Opłaty bankowe",
    }
    k = klucze(db, jan)
    return {h: nazwa for kontrahent, nazwa in nazwy.items() for h in k[kontrahent]} | {
        "klucz-spoza-konta": "Inne"
    }


def test_etykiety_trafiaja_na_konto(db_session: Session, jan: int) -> None:
    wynik = apply_labels(db_session, jan, etykiety_jana(db_session, jan))

    assert wynik.labelled == 6
    assert wynik.labels_without_transaction == 1
    assert wynik.new_categories == 2
    s = stan(db_session, jan)
    assert s["SKLEP TESTOWY WARSZAWA"] == ("Zakupy spożywcze", "manual")
    assert s["PayU ul. Testowa 2 Poznań"] == ("Rozrywka", "manual")
    assert s["BANKOMAT TESTOWY"] == ("Gotówka", "manual")
    assert s["brak"] == ("Opłaty bankowe", "manual")
    assert s["JAN TESTOWY"] == ("Przelewy własne", "system_rule")


def test_reguly_tylko_tam_gdzie_slownik_sie_myli(db_session: Session, jan: int) -> None:
    wynik = apply_labels(db_session, jan, etykiety_jana(db_session, jan))

    wzorce = set(
        db_session.scalars(
            select(CategoryRule.pattern).where(CategoryRule.user_id == jan)
        )
    )
    # Wynagrodzenie słownik rozpoznaje sam; prowizja nie ma kontrahenta.
    assert wzorce == {
        "SKLEP TESTOWY WARSZAWA",
        "PayU ul. Testowa 2 Poznań",
        "BANKOMAT TESTOWY",
    }
    assert wynik.rules == 3


def test_nowe_transakcje_korzystaja_z_regul(
    client: TestClient, db_session: Session, jan: int, naglowek_jana: dict
) -> None:
    apply_labels(db_session, jan, etykiety_jana(db_session, jan))
    wiersz = ("2026-11-02", "2026-11-03", "BANKOMAT TESTOWY", "Wypłata gotówki 02.11.2026",
              "", "'202611030000000077'", "-50,00", "")  # fmt: skip
    importuj(client, naglowek_jana, make_ing_csv([wiersz]))

    nowa = db_session.scalar(
        select(Transaction).where(
            Transaction.user_id == jan, Transaction.date == dt.date(2026, 11, 2)
        )
    )
    assert nowa.categorized_by.value == "user_rule"
    nazwa = db_session.scalar(
        select(Category.name).where(Category.id == nowa.category_id)
    )
    assert nazwa == "Gotówka"


def test_rozne_etykiety_u_kontrahenta_bez_reguly(db_session: Session, jan: int) -> None:
    sklep = [
        t.dedup_hash
        for t in db_session.scalars(
            select(Transaction).where(
                Transaction.user_id == jan,
                Transaction.counterparty == "SKLEP TESTOWY WARSZAWA",
            )
        )
    ]
    assert len(sklep) == 2
    wynik = apply_labels(
        db_session, jan, {sklep[0]: "Zakupy spożywcze", sklep[1]: "Odzież"}
    )
    assert (wynik.mixed_counterparties, wynik.rules) == (1, 0)


def test_ponowne_uruchomienie(db_session: Session, jan: int) -> None:
    etykiety = etykiety_jana(db_session, jan)
    apply_labels(db_session, jan, etykiety)
    drugi = apply_labels(db_session, jan, etykiety)

    assert drugi.new_categories == 0
    assert (
        len(
            db_session.scalars(
                select(CategoryRule.id).where(CategoryRule.user_id == jan)
            ).all()
        )
        == 3
    )


def test_inny_uzytkownik_nietkniety(
    client: TestClient, db_session: Session, jan: int
) -> None:
    importuj(client, konto(client, "anna@example.com"))
    anna = uzytkownik(db_session, "anna@example.com")
    przed = stan(db_session, anna)

    apply_labels(db_session, jan, etykiety_jana(db_session, jan))

    assert stan(db_session, anna) == przed
    assert not db_session.scalars(
        select(Category).where(Category.user_id == anna)
    ).all()


def test_odczyt_etykiet() -> None:
    plik = io.StringIO('klucz;kategoria\nk1;Zakupy spożywcze\nk2;"Kino; teatr"\n')
    assert read_labels(plik) == {"k1": "Zakupy spożywcze", "k2": "Kino; teatr"}
