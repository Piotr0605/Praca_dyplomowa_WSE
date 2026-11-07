"""Dane wejściowe i odpowiedzi API dotyczące transakcji."""

import datetime as dt
from decimal import Decimal
from typing import Annotated, Self

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)

from app.models.enums import TransactionKind, TransactionSource


def _not_zero(amount: Decimal) -> Decimal:
    if amount == 0:
        raise ValueError("kwota nie może być zerowa")
    return amount


# Zakres zgodny z NUMERIC(12,2) w bazie. W JSON kwota wraca jako tekst, np. "-12.50",
# bo liczba w JSON to float i mogłaby stracić dokładność.
Amount = Annotated[
    Decimal, Field(max_digits=12, decimal_places=2), AfterValidator(_not_zero)
]
Currency = Annotated[
    str, StringConstraints(pattern=r"^[A-Za-z]{3}$"), AfterValidator(str.upper)
]
Description = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)
]
Counterparty = Annotated[str, StringConstraints(strip_whitespace=True, max_length=255)]


class TransactionCreate(BaseModel):
    date: dt.date
    amount: Amount = Field(description="Ujemna kwota oznacza wydatek")
    currency: Currency = "PLN"
    description: Description
    counterparty: Counterparty | None = None
    category_id: int | None = None
    kind: TransactionKind = TransactionKind.OTHER


class TransactionUpdate(BaseModel):
    """Zmieniane są tylko przysłane pola. `category_id: null` usuwa kategorię."""

    date: dt.date | None = None
    amount: Amount | None = None
    currency: Currency | None = None
    description: Description | None = None
    counterparty: Counterparty | None = None
    category_id: int | None = None
    kind: TransactionKind | None = None

    @model_validator(mode="after")
    def required_fields_are_not_null(self) -> Self:
        for field in ("date", "amount", "currency", "description", "kind"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"pole {field} nie może być puste")
        return self


class TransactionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    date: dt.date
    booking_date: dt.date | None
    amount: Decimal
    currency: str
    description: str
    counterparty: str | None
    category_id: int | None
    kind: TransactionKind
    source: TransactionSource
    created_at: dt.datetime


class TransactionPage(BaseModel):
    items: list[TransactionRead]
    total: int
    page: int
    page_size: int
