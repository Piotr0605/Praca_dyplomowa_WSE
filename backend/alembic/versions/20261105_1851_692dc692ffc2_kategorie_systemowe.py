"""kategorie systemowe

Kategorie startowe dostępne dla każdego użytkownika (user_id = NULL).
Lista jest celowo zapisana w migracji: późniejsze zmiany to nowe migracje, a nie edycja tej.

Revision ID: 692dc692ffc2
Revises: b9af2a01d937
Create Date: 2026-11-05 18:51:23.051624

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# Identyfikatory rewizji używane przez Alembic.
revision: str = "692dc692ffc2"
down_revision: str | Sequence[str] | None = "b9af2a01d937"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

KATEGORIE_WYDATKOW = (
    "Jedzenie",
    "Zakupy spożywcze",
    "Restauracje",
    "Transport",
    "Paliwo",
    "Mieszkanie",
    "Rachunki",
    "Subskrypcje",
    "Rozrywka",
    "Zdrowie",
    "Odzież",
    "Edukacja",
    "Prezenty",
    "Przelewy własne",
    "Inne",
)
KATEGORIE_PRZYCHODOW = ("Wynagrodzenie",)

# Widok tabeli tylko na potrzeby tej migracji: nie zależy od późniejszych zmian w modelach.
categories = sa.table(
    "categories",
    sa.column("user_id", sa.Integer),
    sa.column("name", sa.String),
    sa.column("is_income", sa.Boolean),
)


def upgrade() -> None:
    """Dodaje kategorie systemowe."""
    op.bulk_insert(
        categories,
        [
            {"user_id": None, "name": nazwa, "is_income": False}
            for nazwa in KATEGORIE_WYDATKOW
        ]
        + [
            {"user_id": None, "name": nazwa, "is_income": True}
            for nazwa in KATEGORIE_PRZYCHODOW
        ],
    )


def downgrade() -> None:
    """Usuwa kategorie systemowe. Kategorie użytkowników zostają."""
    op.execute(
        categories.delete().where(
            categories.c.user_id.is_(None),
            categories.c.name.in_(KATEGORIE_WYDATKOW + KATEGORIE_PRZYCHODOW),
        )
    )
