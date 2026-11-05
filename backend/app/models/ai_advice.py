"""Porada wygenerowana przez model językowy wraz z danymi, które do niego wysłano."""

import datetime as dt
from typing import Any

from sqlalchemy import CheckConstraint, Date, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.types import CreatedAt


class AIAdvice(Base):
    __tablename__ = "ai_advice"
    __table_args__ = (
        CheckConstraint("period_end >= period_start", name="period_order"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    period_start: Mapped[dt.date] = mapped_column(Date)
    period_end: Mapped[dt.date] = mapped_column(Date)
    provider: Mapped[str] = mapped_column(String(30))
    model: Mapped[str] = mapped_column(String(100))
    # Wyłącznie zanonimizowane agregaty: pozwala sprawdzić, co opuściło komputer.
    prompt_payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    response_text: Mapped[str] = mapped_column(Text)
    tokens_in: Mapped[int | None] = mapped_column(Integer)
    tokens_out: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[CreatedAt]
