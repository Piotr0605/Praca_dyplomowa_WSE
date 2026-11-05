"""Kategoria transakcji: systemowa (user_id = NULL) albo utworzona przez użytkownika."""

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint, false
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Category(Base):
    __tablename__ = "categories"
    # Domyślnie NULL != NULL, więc bez tej opcji dwie kategorie systemowe mogłyby mieć tę samą nazwę.
    __table_args__ = (
        UniqueConstraint("user_id", "name", postgresql_nulls_not_distinct=True),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(100))
    # Kolor w formacie #RRGGBB.
    color: Mapped[str | None] = mapped_column(String(7))
    icon: Mapped[str | None] = mapped_column(String(50))
    is_income: Mapped[bool] = mapped_column(Boolean, server_default=false())
