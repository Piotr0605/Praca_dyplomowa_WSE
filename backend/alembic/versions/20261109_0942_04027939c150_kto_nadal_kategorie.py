"""kto nadał kategorię

Pola transactions.categorized_by i category_rule_id: miara skuteczności kategoryzacji (badanie, H2).

Revision ID: 04027939c150
Revises: 0dc3d36f8de6
Create Date: 2026-11-09 09:42:20.438836

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# Identyfikatory rewizji używane przez Alembic.
revision: str = "04027939c150"
down_revision: str | Sequence[str] | None = "0dc3d36f8de6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Zmiana schematu w przód."""
    op.add_column(
        "transactions",
        sa.Column(
            "categorized_by",
            sa.Enum(
                "system_rule",
                "user_rule",
                "manual",
                name="categorized_by",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=True,
        ),
    )
    op.add_column(
        "transactions", sa.Column("category_rule_id", sa.Integer(), nullable=True)
    )
    op.create_index(
        op.f("ix_transactions_category_rule_id"),
        "transactions",
        ["category_rule_id"],
        unique=False,
    )
    op.create_foreign_key(
        op.f("fk_transactions_category_rule_id_category_rules"),
        "transactions",
        "category_rules",
        ["category_rule_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Wycofanie zmiany (przywraca poprzedni schemat)."""
    op.drop_constraint(
        op.f("fk_transactions_category_rule_id_category_rules"),
        "transactions",
        type_="foreignkey",
    )
    op.drop_index(op.f("ix_transactions_category_rule_id"), table_name="transactions")
    op.drop_column("transactions", "category_rule_id")
    op.drop_column("transactions", "categorized_by")
