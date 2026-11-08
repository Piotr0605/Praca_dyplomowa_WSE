"""Profile plików CSV zapisane przez użytkowników (kreator mapowania kolumn).

Revision ID: 0dc3d36f8de6
Revises: 692dc692ffc2
Create Date: 2026-11-07 21:42:35.516738

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# Identyfikatory rewizji używane przez Alembic.
revision: str = "0dc3d36f8de6"
down_revision: str | Sequence[str] | None = "692dc692ffc2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Zmiana schematu w przód."""
    op.create_table(
        "bank_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("bank_name", sa.String(length=100), nullable=False),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_bank_profiles_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_bank_profiles")),
        sa.UniqueConstraint(
            "user_id", "bank_name", name=op.f("uq_bank_profiles_user_id_bank_name")
        ),
    )


def downgrade() -> None:
    """Wycofanie zmiany (przywraca poprzedni schemat)."""
    op.drop_table("bank_profiles")
