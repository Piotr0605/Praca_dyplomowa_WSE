"""Automatyczna kategoryzacja: przypisanie kategorii wstecz i statystyka skuteczności."""

from fastapi import APIRouter
from pydantic import BaseModel

from app.api.deps import CurrentUser
from app.core.database import DbSession
from app.services import categorization_service

router = APIRouter(prefix="/categorization", tags=["categorization"])


class ApplyResult(BaseModel):
    categorized: int


class StatsRead(BaseModel):
    total: int
    system_rule: int
    user_rule: int
    manual: int
    uncategorized: int
    # Wersja słownika reguł systemowych: wynik badania dotyczy konkretnej wersji.
    rules_version: str


@router.post("/apply")
def apply(user: CurrentUser, db: DbSession, recategorize: bool = False) -> ApplyResult:
    """Przypisuje kategorie według reguł transakcjom bez kategorii, a z `recategorize=true`
    przelicza też kategorie nadane wcześniej przez reguły. Decyzji użytkownika nie zmienia."""
    return ApplyResult(
        categorized=categorization_service.apply_rules(
            db, user.id, recategorize=recategorize
        )
    )


@router.get("/stats")
def stats(user: CurrentUser, db: DbSession) -> StatsRead:
    """Ile transakcji skategoryzował słownik, reguły użytkownika i sam użytkownik."""
    result = categorization_service.stats(db, user.id)
    return StatsRead(
        **result.__dict__, rules_version=categorization_service.system_rules_version()
    )
