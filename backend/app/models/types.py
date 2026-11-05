"""Typy kolumn używane w wielu modelach."""

import datetime as dt
from enum import Enum as PyEnum
from typing import Annotated

from sqlalchemy import DateTime, Enum, func
from sqlalchemy.orm import mapped_column

# Czas utworzenia ustawia baza, więc jest poprawny także przy zapisie spoza aplikacji.
CreatedAt = Annotated[
    dt.datetime,
    mapped_column(DateTime(timezone=True), server_default=func.now()),
]


def enum_column(enum_class: type[PyEnum], name: str) -> Enum:
    """Wartości wyliczeniowe jako tekst z ograniczeniem CHECK.

    Natywny typ ENUM PostgreSQL trudno później zmieniać w migracjach. Tekst z CHECK
    daje tę samą ochronę, a w bazie zapisane są czytelne wartości, np. `own_transfer`.
    """
    return Enum(
        enum_class,
        name=name,
        native_enum=False,
        create_constraint=True,
        length=32,
        values_callable=lambda members: [member.value for member in members],
    )
