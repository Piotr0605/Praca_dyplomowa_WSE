"""Porady AI: generowanie, historia i podgląd pakietu danych przed wysłaniem."""

import datetime as dt
from typing import Any

from fastapi import APIRouter, HTTPException, status

from app.ai.providers import AdviceProviderError
from app.api.deps import CurrentUser
from app.core.database import DbSession
from app.schemas.advice import AdviceRead, AdviceRequest, AdviceResponse
from app.services.advice_service import (
    DailyLimitError,
    NoTransactionsError,
    generate_advice,
    history,
    payload_for,
)

router = APIRouter(prefix="/advice", tags=["advice"])

NO_TRANSACTIONS = HTTPException(
    status.HTTP_422_UNPROCESSABLE_CONTENT, "W wybranym okresie nie ma transakcji"
)


@router.post("")
def generate(data: AdviceRequest, user: CurrentUser, db: DbSession) -> AdviceResponse:
    try:
        result = generate_advice(db, user.id, data.date_from, data.date_to)
    except NoTransactionsError as error:
        raise NO_TRANSACTIONS from error
    except DailyLimitError as error:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"Dzienny limit porad ({error.limit}) został wyczerpany, spróbuj jutro",
        ) from error
    except AdviceProviderError as error:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(error)) from error
    return AdviceResponse(
        advice=AdviceRead.model_validate(result.advice), cached=result.cached
    )


@router.get("")
def list_advice(user: CurrentUser, db: DbSession) -> list[AdviceRead]:
    return [AdviceRead.model_validate(a) for a in history(db, user.id)]


@router.get("/preview-payload")
def preview_payload(
    date_from: dt.date, date_to: dt.date, user: CurrentUser, db: DbSession
) -> dict[str, Any]:
    """Dokładnie te dane, które poszłyby do modelu dla tego okresu: nic poza agregatami."""
    if date_from > date_to:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "date_from jest po date_to"
        )
    try:
        return payload_for(db, user.id, date_from, date_to)
    except NoTransactionsError as error:
        raise NO_TRANSACTIONS from error
