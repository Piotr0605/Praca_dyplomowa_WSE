"""Modele ORM (tabele bazy danych).

Każdy nowy model importujemy tutaj. alembic/env.py importuje ten pakiet, więc wszystkie
modele trafiają do Base.metadata i `alembic revision --autogenerate` widzi je bez dodatkowej konfiguracji.
"""

from app.models.ai_advice import AIAdvice
from app.models.bank_profile import BankProfile
from app.models.category import Category
from app.models.category_rule import CategoryRule
from app.models.import_batch import ImportBatch
from app.models.transaction import Transaction
from app.models.user import User

__all__ = [
    "AIAdvice",
    "BankProfile",
    "Category",
    "CategoryRule",
    "ImportBatch",
    "Transaction",
    "User",
]
