"""Reguła kategoryzacji: systemowa lub zapamiętana z poprawki użytkownika."""

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.enums import RuleMatchType, RuleSource
from app.models.types import CreatedAt, enum_column


class CategoryRule(Base):
    __tablename__ = "category_rules"
    # Reguła systemowa nie ma właściciela, a reguła użytkownika musi go mieć.
    __table_args__ = (
        CheckConstraint(
            "(source = 'system') = (user_id IS NULL)",
            name="source_matches_owner",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    pattern: Mapped[str] = mapped_column(String(255))
    match_type: Mapped[RuleMatchType] = mapped_column(
        enum_column(RuleMatchType, "rule_match_type")
    )
    # Reguła bez kategorii nie ma sensu, więc znika razem z nią.
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"), index=True
    )
    # Większa liczba oznacza pierwszeństwo przy kilku pasujących regułach.
    priority: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    source: Mapped[RuleSource] = mapped_column(enum_column(RuleSource, "rule_source"))
    created_at: Mapped[CreatedAt]
