"""Konto użytkownika."""

from sqlalchemy import CheckConstraint, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.types import CreatedAt


class User(Base):
    __tablename__ = "users"
    # E-mail zapisujemy małymi literami. Bez tego Ala@x.pl i ala@x.pl byłyby dwoma kontami.
    __table_args__ = (CheckConstraint("email = lower(email)", name="email_lowercase"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    # 254 znaki to maksymalna długość adresu e-mail (RFC 5321).
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[CreatedAt]
