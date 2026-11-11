"""Odpowiedzi analityki. Kwoty są dodatnie i w PLN; w JSON jako tekst (np. "12.50"), bez utraty dokładności."""

import datetime as dt
from decimal import Decimal

from pydantic import BaseModel


class TotalsRead(BaseModel):
    income: Decimal
    expenses: Decimal
    balance: Decimal
    # Część przychodów, która nie została wydana (0,25 = 25%); bez przychodów: null.
    savings_rate: float | None


class SummaryRead(TotalsRead):
    date_from: dt.date
    date_to: dt.date
    # Ile netto przelano na własne konta (np. oszczędnościowe); nie jest wydatkiem.
    own_transfers_net: Decimal
    transactions: int
    uncategorized: int
    days: int
    avg_daily_expense: Decimal
    # Transakcje w innej walucie niż PLN, pominięte w obliczeniach.
    other_currency: int


class CategoryAmount(BaseModel):
    category_id: int | None
    name: str
    color: str | None
    amount: Decimal
    # Udział w sumie wydatków albo przychodów okresu (0–1).
    share: float
    count: int


class ByCategoryRead(BaseModel):
    expenses: list[CategoryAmount]
    income: list[CategoryAmount]


class MonthRead(TotalsRead):
    month: str
    # Niepełny miesiąc (dane zaczynają się w jego trakcie albo jeszcze trwa) zaniża sumy.
    complete: bool


class ChangeRead(BaseModel):
    category_id: int | None
    name: str
    color: str | None
    current: Decimal
    previous: Decimal | None
    average: Decimal | None
    change_previous: float | None
    change_average: float | None


class ChangesRead(BaseModel):
    month: str | None
    complete: bool
    # Miesiąc poprzedni i miesiące średniej: tylko pełne. Puste, gdy brak danych do porównania.
    previous_month: str | None
    average_months: list[str]
    items: list[ChangeRead]


class CounterpartyRead(BaseModel):
    name: str
    amount: Decimal
    count: int


class ExpenseRead(BaseModel):
    date: dt.date
    amount: Decimal
    counterparty: str | None
    description: str
    category: str


class TopRead(BaseModel):
    counterparties: list[CounterpartyRead]
    largest: list[ExpenseRead]
