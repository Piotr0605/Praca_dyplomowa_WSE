"""Pojedyncza operacja finansowa użytkownika."""

import datetime as dt
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.enums import TransactionKind, TransactionSource
from app.models.types import CreatedAt, enum_column


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        # Dla transakcji ręcznych dedup_hash to NULL: dwie takie same kawy tego samego dnia są dozwolone.
        UniqueConstraint("user_id", "dedup_hash"),
        CheckConstraint("char_length(currency) = 3", name="currency_code"),
        # Główne zapytanie aplikacji: transakcje jednego użytkownika z wybranego okresu.
        Index("ix_transactions_user_id_date", "user_id", "date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    # Data operacji (np. płatności kartą) służy do analizy. Księgowanie bywa o kilka dni późniejsze.
    date: Mapped[dt.date] = mapped_column(Date)
    booking_date: Mapped[dt.date | None] = mapped_column(Date)
    # Kwota ujemna oznacza wydatek. NUMERIC, bo float daje błędy zaokrągleń.
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3), server_default="PLN")
    description: Mapped[str] = mapped_column(Text)
    description_normalized: Mapped[str | None] = mapped_column(Text)
    counterparty: Mapped[str | None] = mapped_column(String(255))
    # Usunięcie kategorii lub importu zostawia transakcję, tylko bez powiązania.
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), index=True
    )
    import_batch_id: Mapped[int | None] = mapped_column(
        ForeignKey("import_batches.id", ondelete="SET NULL"), index=True
    )
    source: Mapped[TransactionSource] = mapped_column(
        enum_column(TransactionSource, "transaction_source")
    )
    kind: Mapped[TransactionKind] = mapped_column(
        enum_column(TransactionKind, "transaction_kind"),
        server_default=TransactionKind.OTHER.value,
    )
    # SHA-256 zapisany szesnastkowo: numeru transakcji z banku albo daty, kwoty i opisu.
    dedup_hash: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[CreatedAt]
