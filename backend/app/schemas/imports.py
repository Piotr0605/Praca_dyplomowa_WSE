"""Odpowiedzi API dotyczące importu wyciągów."""

import datetime as dt
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.enums import TransactionKind


class PreviewTransaction(BaseModel):
    date: dt.date
    booking_date: dt.date
    amount: Decimal
    currency: str
    description: str
    counterparty: str | None
    kind: TransactionKind
    duplicate: bool


class ImportPreview(BaseModel):
    bank: str
    period_start: dt.date
    period_end: dt.date
    opening_balance: Decimal
    closing_balance: Decimal
    credits_count: int
    credits_sum: Decimal
    debits_count: int
    debits_sum: Decimal
    total: int
    new: int
    duplicates: int
    transactions: list[PreviewTransaction]


class ImportBatchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    bank: str
    filename: str
    rows_total: int
    rows_imported: int
    rows_duplicated: int
    created_at: dt.datetime
