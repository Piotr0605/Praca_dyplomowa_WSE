"""porady: dane do badania

Pola ai_advice potrzebne w badaniu P4 (docs/BADANIA.md): wersja promptu, temperatura i czas odpowiedzi,
żeby każdą poradę dało się powtórzyć i porównać między dostawcami.

Revision ID: 5b8c2d41e7a9
Revises: 7c1e5a9d3b20
Create Date: 2026-11-11 18:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# Identyfikatory rewizji używane przez Alembic.
revision: str = "5b8c2d41e7a9"
down_revision: str | Sequence[str] | None = "7c1e5a9d3b20"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Zmiana schematu w przód."""
    op.add_column(
        "ai_advice",
        sa.Column(
            "prompt_version", sa.String(length=20), nullable=False, server_default="?"
        ),
    )
    op.add_column(
        "ai_advice", sa.Column("temperature", sa.Numeric(3, 2), nullable=True)
    )
    op.add_column(
        "ai_advice", sa.Column("response_time_ms", sa.Integer(), nullable=True)
    )


def downgrade() -> None:
    """Zmiana schematu w tył."""
    op.drop_column("ai_advice", "response_time_ms")
    op.drop_column("ai_advice", "temperature")
    op.drop_column("ai_advice", "prompt_version")
