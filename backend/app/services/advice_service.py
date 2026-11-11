"""Generowanie porad: pakiet agregatów → dostawca AI → zapis w ai_advice.

Ograniczenie kosztów:
- cache: ta sama porada wraca bez pytania modelu, dopóki okres, dane (ten sam pakiet), dostawca,
  model i wersja promptu się nie zmieniły;
- dzienny limit wygenerowanych porad na użytkownika (odpowiedzi z cache się nie liczą).
"""

import datetime as dt
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.prompt_builder import PROMPT_VERSION, TEMPERATURE, build_payload
from app.ai.providers import current_provider
from app.core.config import get_settings
from app.models import AIAdvice, Transaction


class NoTransactionsError(Exception):
    """W wybranym okresie nie ma transakcji, więc nie ma z czego budować porady."""


class DailyLimitError(Exception):
    """Wyczerpany dzienny limit porad."""

    def __init__(self, limit: int) -> None:
        super().__init__(str(limit))
        self.limit = limit


@dataclass(frozen=True)
class GeneratedAdvice:
    advice: AIAdvice
    cached: bool


def payload_for(
    session: Session, user_id: int, date_from: dt.date, date_to: dt.date
) -> dict:
    count = session.scalar(
        select(func.count())
        .select_from(Transaction)
        .where(
            Transaction.user_id == user_id,
            Transaction.date >= date_from,
            Transaction.date <= date_to,
        )
    )
    if not count:
        raise NoTransactionsError
    return build_payload(session, user_id, date_from, date_to)


def _cached(
    session: Session,
    user_id: int,
    date_from: dt.date,
    date_to: dt.date,
    provider: str,
    payload: dict,
) -> AIAdvice | None:
    latest = session.scalars(
        select(AIAdvice)
        .where(
            AIAdvice.user_id == user_id,
            AIAdvice.period_start == date_from,
            AIAdvice.period_end == date_to,
            AIAdvice.provider == provider,
            AIAdvice.prompt_version == PROMPT_VERSION,
        )
        .order_by(AIAdvice.id.desc())
        .limit(1)
    ).first()
    if latest is not None and latest.prompt_payload == payload:
        return latest
    return None


def _check_daily_limit(session: Session, user_id: int) -> None:
    limit = get_settings().ADVICE_DAILY_LIMIT
    today = (
        select(func.count())
        .select_from(AIAdvice)
        .where(
            AIAdvice.user_id == user_id,
            func.date(AIAdvice.created_at) == dt.date.today(),
        )
    )
    if (session.scalar(today) or 0) >= limit:
        raise DailyLimitError(limit)


def generate_advice(
    session: Session, user_id: int, date_from: dt.date, date_to: dt.date
) -> GeneratedAdvice:
    payload = payload_for(session, user_id, date_from, date_to)
    provider_name, provider = current_provider()
    cached = _cached(session, user_id, date_from, date_to, provider_name, payload)
    if cached is not None:
        return GeneratedAdvice(cached, cached=True)

    _check_daily_limit(session, user_id)
    result = provider.generate_advice(payload)
    advice = AIAdvice(
        user_id=user_id,
        period_start=date_from,
        period_end=date_to,
        provider=provider_name,
        model=result.model,
        prompt_payload=payload,
        response_text=result.text,
        tokens_in=result.tokens_in,
        tokens_out=result.tokens_out,
        prompt_version=PROMPT_VERSION,
        temperature=TEMPERATURE,
        response_time_ms=result.response_time_ms,
    )
    session.add(advice)
    session.commit()
    return GeneratedAdvice(advice, cached=False)


def history(session: Session, user_id: int) -> list[AIAdvice]:
    return list(
        session.scalars(
            select(AIAdvice)
            .where(AIAdvice.user_id == user_id)
            .order_by(AIAdvice.id.desc())
        )
    )
