"""kolory kategorii systemowych

Kolor to znacznik obok nazwy kategorii (lista transakcji, kategorie, dashboard). „Inne” i „Przelewy
własne” są szare: nie mówią nic o rodzaju wydatku. Kolory użytkownika w jego kategoriach nie zmieniają się.

Revision ID: 7c1e5a9d3b20
Revises: 04027939c150
Create Date: 2026-11-11 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# Identyfikatory rewizji używane przez Alembic.
revision: str = "7c1e5a9d3b20"
down_revision: str | Sequence[str] | None = "04027939c150"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

KOLORY = {
    "Jedzenie": "#eb6834",
    "Zakupy spożywcze": "#1baf7a",
    "Restauracje": "#e34948",
    "Transport": "#2a78d6",
    "Paliwo": "#184f95",
    "Mieszkanie": "#8b5e34",
    "Rachunki": "#eda100",
    "Subskrypcje": "#6250d6",
    "Rozrywka": "#e87ba4",
    "Zdrowie": "#008300",
    "Odzież": "#9085e9",
    "Edukacja": "#0e7490",
    "Prezenty": "#d55181",
    "Przelewy własne": "#898781",
    "Inne": "#b4b2a9",
    "Wynagrodzenie": "#006300",
}

# Widok tabeli tylko na potrzeby tej migracji: nie zależy od późniejszych zmian w modelach.
categories = sa.table(
    "categories",
    sa.column("user_id", sa.Integer),
    sa.column("name", sa.String),
    sa.column("color", sa.String),
)


def upgrade() -> None:
    """Nadaje kolory kategoriom systemowym."""
    for nazwa, kolor in KOLORY.items():
        op.execute(
            categories.update()
            .where(categories.c.user_id.is_(None), categories.c.name == nazwa)
            .values(color=kolor)
        )


def downgrade() -> None:
    """Usuwa kolory kategorii systemowych."""
    op.execute(
        categories.update()
        .where(categories.c.user_id.is_(None), categories.c.name.in_(list(KOLORY)))
        .values(color=None)
    )
