"""Transakcje użytkownika: lista z filtrami, dodawanie ręczne, edycja i usuwanie."""

import datetime as dt
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response, status

from app.api.deps import CurrentUser
from app.core.database import DbSession
from app.models.enums import TransactionKind
from app.repositories.transaction_repository import (
    TransactionFilters,
    TransactionRepository,
)
from app.schemas.transaction import (
    TransactionCreate,
    TransactionPage,
    TransactionRead,
    TransactionUpdate,
)
from app.services.transaction_service import (
    ImportedFieldLockedError,
    TransactionNotFoundError,
    UnknownCategoryError,
    create_transaction,
    delete_transaction,
    get_transaction,
    update_transaction,
)

router = APIRouter(prefix="/transactions", tags=["transactions"])

NOT_FOUND = HTTPException(status.HTTP_404_NOT_FOUND, "Transakcja nie istnieje")
# 422, a nie 404: błąd dotyczy pola w przesłanych danych. Cudza kategoria wygląda jak nieistniejąca.
UNKNOWN_CATEGORY = HTTPException(
    status.HTTP_422_UNPROCESSABLE_CONTENT, "Nieznana kategoria"
)


@router.get("")
def list_transactions(
    user: CurrentUser,
    db: DbSession,
    date_from: dt.date | None = None,
    date_to: dt.date | None = None,
    category_id: int | None = None,
    uncategorized: bool = False,
    kind: TransactionKind | None = None,
    q: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
) -> TransactionPage:
    if date_from and date_to and date_from > date_to:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "date_from jest po date_to"
        )
    if uncategorized and category_id is not None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "uncategorized wyklucza category_id"
        )
    filters = TransactionFilters(
        date_from, date_to, category_id, uncategorized, kind, q
    )
    items, total = TransactionRepository(db).list(
        user.id, filters, offset=(page - 1) * page_size, limit=page_size
    )
    return TransactionPage(
        items=[TransactionRead.model_validate(t) for t in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", status_code=status.HTTP_201_CREATED)
def create(
    data: TransactionCreate, user: CurrentUser, db: DbSession
) -> TransactionRead:
    try:
        return TransactionRead.model_validate(create_transaction(db, user.id, data))
    except UnknownCategoryError as error:
        raise UNKNOWN_CATEGORY from error


@router.get("/{transaction_id}")
def read(transaction_id: int, user: CurrentUser, db: DbSession) -> TransactionRead:
    try:
        return TransactionRead.model_validate(
            get_transaction(db, user.id, transaction_id)
        )
    except TransactionNotFoundError as error:
        raise NOT_FOUND from error


@router.patch("/{transaction_id}")
def update(
    transaction_id: int, data: TransactionUpdate, user: CurrentUser, db: DbSession
) -> TransactionRead:
    try:
        return TransactionRead.model_validate(
            update_transaction(db, user.id, transaction_id, data)
        )
    except TransactionNotFoundError as error:
        raise NOT_FOUND from error
    except UnknownCategoryError as error:
        raise UNKNOWN_CATEGORY from error
    except ImportedFieldLockedError as error:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"W transakcji z importu nie można zmienić: {error}",
        ) from error


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(transaction_id: int, user: CurrentUser, db: DbSession) -> Response:
    try:
        delete_transaction(db, user.id, transaction_id)
    except TransactionNotFoundError as error:
        raise NOT_FOUND from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)
