"""Wartości wyliczeniowe modeli."""

from enum import StrEnum


class TransactionSource(StrEnum):
    """Skąd pochodzi transakcja."""

    PDF = "pdf"
    CSV = "csv"
    MANUAL = "manual"


class TransactionKind(StrEnum):
    """Rodzaj operacji, rozpoznany z wyciągu lub ustawiony ręcznie."""

    CARD = "card"
    BLIK = "blik"
    TRANSFER = "transfer"
    # Przelew między kontami użytkownika, np. Smart Saver: nie jest wydatkiem ani przychodem.
    OWN_TRANSFER = "own_transfer"
    REFUND = "refund"
    CASH = "cash"
    FEE = "fee"
    OTHER = "other"


class RuleMatchType(StrEnum):
    """Sposób dopasowania reguły kategoryzacji."""

    CONTAINS = "contains"
    EXACT_COUNTERPARTY = "exact_counterparty"
    REGEX = "regex"


class RuleSource(StrEnum):
    """Kto utworzył regułę: system czy użytkownik poprawką kategorii."""

    SYSTEM = "system"
    USER = "user"
