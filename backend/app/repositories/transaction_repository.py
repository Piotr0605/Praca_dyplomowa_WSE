"""Dostęp do tabeli transactions. Każda metoda wymaga user_id."""

import datetime as dt
from dataclasses import dataclass

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.models import Transaction
from app.models.enums import TransactionKind


@dataclass(frozen=True)
class TransactionFilters:
    date_from: dt.date | None = None
    date_to: dt.date | None = None
    category_id: int | None = None
    uncategorized: bool = False
    kind: TransactionKind | None = None
    search: str | None = None


class TransactionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def _owned(self, user_id: int) -> Select[tuple[Transaction]]:
        return select(Transaction).where(Transaction.user_id == user_id)

    def get(self, user_id: int, transaction_id: int) -> Transaction | None:
        """Cudza transakcja zachowuje się jak nieistniejąca."""
        return self._session.scalar(
            self._owned(user_id).where(Transaction.id == transaction_id)
        )

    def list(
        self, user_id: int, filters: TransactionFilters, offset: int, limit: int
    ) -> tuple[list[Transaction], int]:
        query = self._owned(user_id)
        if filters.date_from is not None:
            query = query.where(Transaction.date >= filters.date_from)
        if filters.date_to is not None:
            query = query.where(Transaction.date <= filters.date_to)
        if filters.category_id is not None:
            query = query.where(Transaction.category_id == filters.category_id)
        if filters.uncategorized:
            query = query.where(Transaction.category_id.is_(None))
        if filters.kind is not None:
            query = query.where(Transaction.kind == filters.kind)
        if filters.search:
            # autoescape: znaki % i _ w szukanym tekście są zwykłymi znakami, a nie wzorcem.
            query = query.where(
                or_(
                    Transaction.description.icontains(filters.search, autoescape=True),
                    Transaction.counterparty.icontains(filters.search, autoescape=True),
                )
            )

        total = self._session.scalar(select(func.count()).select_from(query.subquery()))
        items = self._session.scalars(
            query.order_by(Transaction.date.desc(), Transaction.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(items), total or 0

    def add(self, user_id: int, **values: object) -> Transaction:
        transaction = Transaction(user_id=user_id, **values)
        self._session.add(transaction)
        self._session.flush()
        return transaction

    def delete(self, transaction: Transaction) -> None:
        self._session.delete(transaction)
        self._session.flush()
