"""Reguły kategoryzacji zapamiętane z poprawek użytkownika: podgląd i usuwanie."""

import datetime as dt

from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy import delete, func, select

from app.api.deps import CurrentUser
from app.core.database import DbSession
from app.models import Category, CategoryRule, Transaction
from app.models.enums import RuleMatchType, RuleSource

router = APIRouter(prefix="/rules", tags=["rules"])


class RuleRead(BaseModel):
    id: int
    pattern: str
    match_type: RuleMatchType
    category_id: int
    category_name: str
    # Ile transakcji ma obecnie kategorię nadaną przez tę regułę lub z niej zapamiętaną.
    transactions: int
    created_at: dt.datetime


@router.get("")
def list_rules(user: CurrentUser, db: DbSession) -> list[RuleRead]:
    used = (
        select(Transaction.category_rule_id, func.count().label("n"))
        .where(Transaction.user_id == user.id)
        .group_by(Transaction.category_rule_id)
        .subquery()
    )
    rows = db.execute(
        select(CategoryRule, Category.name, func.coalesce(used.c.n, 0))
        .join(Category, Category.id == CategoryRule.category_id)
        .outerjoin(used, used.c.category_rule_id == CategoryRule.id)
        .where(CategoryRule.user_id == user.id, CategoryRule.source == RuleSource.USER)
        .order_by(CategoryRule.created_at.desc(), CategoryRule.id.desc())
    )
    return [
        RuleRead(
            id=rule.id,
            pattern=rule.pattern,
            match_type=rule.match_type,
            category_id=rule.category_id,
            category_name=name,
            transactions=count,
            created_at=rule.created_at,
        )
        for rule, name, count in rows
    ]


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rule(rule_id: int, user: CurrentUser, db: DbSession) -> Response:
    """Usuwa regułę. Transakcje zachowują kategorię; nowe nie będą już według niej przypisywane."""
    result = db.execute(
        delete(CategoryRule).where(
            CategoryRule.id == rule_id, CategoryRule.user_id == user.id
        )
    )
    if result.rowcount == 0:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Nie ma takiej reguły")
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
