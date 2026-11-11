"""Analityka: podsumowanie okresu, kategorie, trend miesięczny, zmiany i najwięksi odbiorcy.

Bez podanego okresu liczony jest cały zakres danych użytkownika. Zasady liczenia opisuje
`app/services/analytics_service.py`."""

import datetime as dt
from typing import Annotated

import pandas as pd
from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser
from app.core.database import DbSession
from app.models import Transaction
from app.schemas.analytics import (
    ByCategoryRead,
    CategoryAmount,
    ChangeRead,
    ChangesRead,
    CounterpartyRead,
    ExpenseRead,
    MonthRead,
    SummaryRead,
    TopRead,
)
from app.services import analytics_service as analytics
from app.services.analytics_service import to_money

router = APIRouter(prefix="/analytics", tags=["analytics"])

# Wystarczy na kilka lat historii; więcej nie zmieści się czytelnie na wykresie.
MAX_MONTHS = 36


def _data_range(db: Session, user_id: int) -> tuple[dt.date, dt.date] | None:
    first, last = db.execute(
        select(func.min(Transaction.date), func.max(Transaction.date)).where(
            Transaction.user_id == user_id
        )
    ).one()
    return (first, last) if first is not None else None


def _period(
    db: Session, user_id: int, date_from: dt.date | None, date_to: dt.date | None
) -> tuple[dt.date, dt.date]:
    if date_from and date_to and date_from > date_to:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "date_from jest po date_to"
        )
    data = _data_range(db, user_id)
    today = dt.date.today()
    start = date_from or (data[0] if data else today)
    end = date_to or (data[1] if data else today)
    return (start, max(start, end))


def _totals(t: analytics.Totals) -> dict:
    return {
        "income": to_money(t.income),
        "expenses": to_money(t.expenses),
        "balance": to_money(t.balance),
        "savings_rate": t.savings_rate,
    }


@router.get("/summary")
def summary(
    user: CurrentUser,
    db: DbSession,
    date_from: dt.date | None = None,
    date_to: dt.date | None = None,
) -> SummaryRead:
    """Przychody, wydatki, saldo i stopa oszczędności okresu."""
    start, end = _period(db, user.id, date_from, date_to)
    frame = analytics.load_frame(db, user.id, start, end)
    s = analytics.summary(frame.data, start, end)
    return SummaryRead(
        **_totals(s.totals),
        date_from=start,
        date_to=end,
        own_transfers_net=to_money(s.own_transfers_net),
        transactions=s.transactions,
        uncategorized=s.uncategorized,
        days=s.days,
        avg_daily_expense=to_money(s.avg_daily_expense),
        other_currency=frame.other_currency,
    )


@router.get("/by-category")
def by_category(
    user: CurrentUser,
    db: DbSession,
    date_from: dt.date | None = None,
    date_to: dt.date | None = None,
) -> ByCategoryRead:
    """Sumy i udziały kategorii, osobno po stronie wydatków i przychodów."""
    start, end = _period(db, user.id, date_from, date_to)
    rows = analytics.category_totals(analytics.load_frame(db, user.id, start, end).data)

    def side(name: str) -> list[CategoryAmount]:
        part = rows[rows["side"] == name]
        total = int(part["amount"].sum())
        return [
            CategoryAmount(
                category_id=analytics.optional_id(r.category_id),
                name=r.category,
                color=r.color,
                amount=to_money(r.amount),
                share=round(int(r.amount) / total, 4) if total else 0.0,
                count=int(r.count),
            )
            for r in part.itertuples()
        ]

    return ByCategoryRead(expenses=side("expense"), income=side("income"))


@router.get("/monthly")
def monthly(
    user: CurrentUser,
    db: DbSession,
    months: Annotated[int, Query(ge=1, le=MAX_MONTHS)] = 12,
) -> list[MonthRead]:
    """Przychody i wydatki w ostatnich miesiącach z danymi."""
    data = _data_range(db, user.id)
    if data is None:
        return []
    frame = analytics.load_frame(db, user.id)
    return [
        MonthRead(month=m.month, complete=m.complete, **_totals(m.totals))
        for m in analytics.monthly(frame.data, data[0], dt.date.today(), months)
    ]


@router.get("/changes")
def changes(
    user: CurrentUser,
    db: DbSession,
    month: Annotated[str | None, Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")] = None,
) -> ChangesRead:
    """Wydatki w kategoriach w miesiącu (domyślnie ostatnim pełnym) na tle poprzedniego miesiąca
    i średniej z do 3 pełnych miesięcy przed nim."""
    data = _data_range(db, user.id)
    if data is None:
        return ChangesRead(
            month=month,
            complete=False,
            previous_month=None,
            average_months=[],
            items=[],
        )
    df = analytics.load_frame(db, user.id).data
    months = analytics.monthly(df, data[0], dt.date.today(), MAX_MONTHS)
    complete = {pd.Period(m.month, "M") for m in months if m.complete}
    if month is not None:
        chosen = pd.Period(month, "M")
    elif complete:
        chosen = max(complete)
    else:
        chosen = pd.Period(months[-1].month, "M")

    previous = chosen - 1 if chosen - 1 in complete else None
    average = [
        chosen - k
        for k in range(analytics.AVERAGE_MONTHS, 0, -1)
        if chosen - k in complete
    ]
    return ChangesRead(
        month=str(chosen),
        complete=chosen in complete,
        previous_month=str(previous) if previous else None,
        average_months=[str(p) for p in average],
        items=[
            ChangeRead(
                category_id=c.category_id,
                name=c.category,
                color=c.color,
                current=to_money(c.current),
                previous=None if c.previous is None else to_money(c.previous),
                average=None if c.average is None else to_money(c.average),
                change_previous=c.change_previous,
                change_average=c.change_average,
            )
            for c in analytics.changes(df, chosen, complete)
        ],
    )


@router.get("/top")
def top(
    user: CurrentUser,
    db: DbSession,
    date_from: dt.date | None = None,
    date_to: dt.date | None = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
) -> TopRead:
    """Odbiorcy, którym zapłacono najwięcej, i największe pojedyncze wydatki okresu."""
    start, end = _period(db, user.id, date_from, date_to)
    df = analytics.load_frame(db, user.id, start, end).data
    return TopRead(
        counterparties=[
            CounterpartyRead(name=c.name, amount=to_money(c.amount), count=c.count)
            for c in analytics.top_counterparties(df, limit)
        ],
        largest=[
            ExpenseRead(
                date=e.date,
                amount=to_money(e.amount),
                counterparty=e.counterparty,
                description=e.description,
                category=e.category,
            )
            for e in analytics.largest_expenses(df, limit)
        ],
    )
