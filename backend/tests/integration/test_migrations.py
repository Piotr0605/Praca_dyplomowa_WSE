"""Dane, które muszą istnieć po zastosowaniu migracji."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import engine
from app.models import Category


def test_kategorie_systemowe_po_migracji() -> None:
    with Session(engine) as session:
        kategorie = session.execute(
            select(Category.name, Category.is_income).where(Category.user_id.is_(None))
        ).all()

    assert len(kategorie) == 16
    assert {nazwa for nazwa, _ in kategorie} >= {
        "Zakupy spożywcze",
        "Przelewy własne",
        "Odzież",
    }
    assert [nazwa for nazwa, przychod in kategorie if przychod] == ["Wynagrodzenie"]
