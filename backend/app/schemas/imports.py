"""Odpowiedzi API dotyczące importu wyciągów i profili plików CSV."""

import datetime as dt
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.models.enums import TransactionKind


class PreviewTransaction(BaseModel):
    date: dt.date
    booking_date: dt.date | None
    amount: Decimal
    currency: str
    description: str
    counterparty: str | None
    kind: TransactionKind
    duplicate: bool


class ImportPreview(BaseModel):
    format: Literal["pdf", "csv"]
    bank: str
    period_start: dt.date
    period_end: dt.date
    # Salda i sumy kontrolne podaje tylko wyciąg PDF; dla CSV sumy są wyliczone z wierszy pliku.
    opening_balance: Decimal | None
    closing_balance: Decimal | None
    verified: bool
    credits_count: int
    credits_sum: Decimal
    debits_count: int
    debits_sum: Decimal
    total: int
    new: int
    duplicates: int
    # Wiersze z datą, ale bez kwoty (np. blokady kartowe), których nie zapisujemy.
    skipped: int
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


class BankProfileRead(BaseModel):
    # `builtin:ing` dla profilu dostarczonego z aplikacją, `user:12` dla zapisanego przez użytkownika.
    key: str
    bank_name: str
    builtin: bool


class ColumnSuggestion(BaseModel):
    date: str | None
    booking_date: str | None
    amount: str | None
    credit: str | None
    debit: str | None
    currency: str | None
    description: list[str]
    counterparty: str | None
    kind: str | None
    reference: str | None


class CsvDetection(BaseModel):
    """Propozycja ustawień do potwierdzenia w kreatorze mapowania kolumn."""

    encoding: str
    delimiter: str
    header_row: int
    headers: list[str]
    sample_rows: list[list[str]]
    columns: ColumnSuggestion
    date_format: str | None
    decimal_separator: str
    # Ustawienia, których nie udało się rozpoznać: użytkownik musi je wskazać.
    missing: list[str]
    # Profil, do którego plik pasuje: wtedy mapowanie nie jest potrzebne.
    matched: BankProfileRead | None
