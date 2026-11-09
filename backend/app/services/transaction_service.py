"""Reguły dotyczące transakcji."""

from sqlalchemy.orm import Session

from app.models import Transaction
from app.models.enums import CategorizedBy, TransactionSource
from app.repositories.category_repository import CategoryRepository
from app.repositories.transaction_repository import TransactionRepository
from app.schemas.transaction import TransactionCreate, TransactionUpdate
from app.services.categorization_service import (
    category_fields,
    load_rules,
    remember_correction,
    text_of,
)

# W transakcji z importu można poprawić opis, rodzaj i kategorię. Data, kwota i waluta pochodzą
# z banku: są podstawą sum kontrolnych wyciągu i wykrywania duplikatów.
IMPORTED_EDITABLE_FIELDS = {"category_id", "kind", "description"}


class TransactionNotFoundError(Exception):
    """Transakcja nie istnieje albo należy do innego użytkownika."""


class UnknownCategoryError(Exception):
    """Kategoria nie istnieje albo należy do innego użytkownika."""


class ImportedFieldLockedError(Exception):
    """Próba zmiany danych bankowych w transakcji z importu."""

    def __init__(self, fields: set[str]) -> None:
        super().__init__(", ".join(sorted(fields)))
        self.fields = fields


def _check_category(session: Session, user_id: int, category_id: int | None) -> None:
    """Kategoria musi być systemowa albo użytkownika. Baza tego nie wymusza, bo kategoria
    systemowa nie ma właściciela, a prosty klucz obcy nie wyrazi warunku „systemowa albo moja”."""
    if (
        category_id is not None
        and CategoryRepository(session).get_visible(user_id, category_id) is None
    ):
        raise UnknownCategoryError


def get_transaction(session: Session, user_id: int, transaction_id: int) -> Transaction:
    transaction = TransactionRepository(session).get(user_id, transaction_id)
    if transaction is None:
        raise TransactionNotFoundError
    return transaction


def create_transaction(
    session: Session, user_id: int, data: TransactionCreate
) -> Transaction:
    _check_category(session, user_id, data.category_id)
    values = data.model_dump()
    if data.category_id is not None:
        values["categorized_by"] = CategorizedBy.MANUAL
    else:
        # Bez wybranej kategorii: ta sama kategoryzacja co przy imporcie.
        match = load_rules(session, user_id).categorize(
            text_of(data.description, data.counterparty, data.amount, data.kind)
        )
        values |= category_fields(match)
    # Transakcja ręczna nie ma dedup_hash: dwa takie same zakupy tego samego dnia są dozwolone.
    transaction = TransactionRepository(session).add(
        user_id, source=TransactionSource.MANUAL, **values
    )
    session.commit()
    return transaction


def update_transaction(
    session: Session, user_id: int, transaction_id: int, data: TransactionUpdate
) -> Transaction:
    transaction = get_transaction(session, user_id, transaction_id)
    changes = data.model_dump(exclude_unset=True)
    if transaction.source != TransactionSource.MANUAL:
        locked = set(changes) - IMPORTED_EDITABLE_FIELDS
        if locked:
            raise ImportedFieldLockedError(locked)
    corrected = False
    if "category_id" in changes:
        _check_category(session, user_id, changes["category_id"])
        if changes["category_id"] == transaction.category_id:
            # Zapis formularza bez zmiany kategorii nie jest poprawką.
            del changes["category_id"]
        else:
            # Decyzja użytkownika ma pierwszeństwo: przeliczanie reguł jej nie nadpisze,
            # także gdy użytkownik usunął kategorię.
            changes["categorized_by"] = CategorizedBy.MANUAL
            changes["category_rule_id"] = None
            corrected = changes["category_id"] is not None
    for field, value in changes.items():
        setattr(transaction, field, value)
    if corrected:
        rule = remember_correction(
            session, user_id, transaction, changes["category_id"]
        )
        # Reguła powstała z tej poprawki: interfejs proponuje zastosowanie jej do podobnych.
        transaction.category_rule_id = rule.id if rule else None
    session.commit()
    return transaction


def delete_transaction(session: Session, user_id: int, transaction_id: int) -> None:
    TransactionRepository(session).delete(
        get_transaction(session, user_id, transaction_id)
    )
    session.commit()
