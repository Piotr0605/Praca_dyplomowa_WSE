"""Profil pliku CSV zapisany przez użytkownika w kreatorze mapowania kolumn.

Profile wbudowane (np. ING) są plikami JSON w `app/parsers/profiles/` i nie trafiają do tej tabeli:
są częścią kodu, mają testy i zmieniają się razem z aplikacją.
"""

from typing import Any

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.types import CreatedAt


class BankProfile(Base):
    __tablename__ = "bank_profiles"
    # Ponowny zapis profilu o tej samej nazwie zastępuje jego ustawienia.
    __table_args__ = (UniqueConstraint("user_id", "bank_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    bank_name: Mapped[str] = mapped_column(String(100))
    # Ustawienia odczytu w postaci `CsvProfile` (kodowanie, separator, kolumny, format daty).
    config: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[CreatedAt]
