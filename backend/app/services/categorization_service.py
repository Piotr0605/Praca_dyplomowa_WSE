"""Kategoryzacja w aplikacji: reguły z bazy i słownika, przypisanie przy imporcie i wstecz, statystyka."""

import json
from dataclasses import dataclass
from decimal import Decimal
from functools import cache
from pathlib import Path

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.categorization.engine import (
    Match,
    Rule,
    TransactionText,
    categorize,
    rule_from_correction,
    same_rule,
)
from app.models import Category, CategoryRule, Transaction
from app.models.enums import CategorizedBy, RuleMatchType, RuleSource, TransactionKind

SYSTEM_RULES_FILE = (
    Path(__file__).resolve().parents[1] / "categorization" / "system_rules.json"
)
OWN_TRANSFER_CATEGORY = "Przelewy własne"


@cache
def system_rule_definitions() -> tuple[dict, ...]:
    """Słownik z pliku: nazwy kategorii zamiast identyfikatorów, bo te nadaje baza."""
    data = json.loads(SYSTEM_RULES_FILE.read_text(encoding="utf-8"))
    return tuple(data["rules"])


def system_rules_version() -> str:
    return json.loads(SYSTEM_RULES_FILE.read_text(encoding="utf-8"))["version"]


@dataclass(frozen=True)
class RuleSet:
    user: list[Rule]
    system: list[Rule]
    own_transfer_category_id: int | None

    def categorize(self, transaction: TransactionText) -> Match | None:
        return categorize(
            transaction, self.user, self.system, self.own_transfer_category_id
        )


def _system_category_ids(session: Session) -> dict[str, int]:
    rows = session.execute(
        select(Category.name, Category.id).where(Category.user_id.is_(None))
    )
    return {name: category_id for name, category_id in rows}


def load_rules(session: Session, user_id: int) -> RuleSet:
    ids = _system_category_ids(session)
    system = [
        Rule(
            pattern=pattern,
            match_type=RuleMatchType.CONTAINS,
            category_id=ids[group["category"]],
            source=RuleSource.SYSTEM,
            sign=group.get("sign"),
        )
        for group in system_rule_definitions()
        for pattern in group["contains"]
    ]
    user = [
        Rule(
            pattern=r.pattern,
            match_type=r.match_type,
            category_id=r.category_id,
            source=RuleSource.USER,
            priority=r.priority,
            id=r.id,
        )
        for r in session.scalars(
            select(CategoryRule).where(
                CategoryRule.user_id == user_id,
                CategoryRule.source == RuleSource.USER,
            )
        )
    ]
    return RuleSet(user, system, ids.get(OWN_TRANSFER_CATEGORY))


def text_of(
    description: str, counterparty: str | None, amount: Decimal, kind: TransactionKind
) -> TransactionText:
    return TransactionText(description, counterparty, amount, kind)


def category_fields(match: Match | None) -> dict[str, object]:
    """Pola transakcji wynikające z dopasowania (albo puste, gdy reguła nie pasuje)."""
    if match is None:
        return {"category_id": None, "categorized_by": None, "category_rule_id": None}
    return {
        "category_id": match.category_id,
        "categorized_by": match.categorized_by,
        "category_rule_id": match.rule.id if match.rule else None,
    }


def apply_rules(
    session: Session, user_id: int, *, recategorize: bool = False, commit: bool = True
) -> int:
    """Przypisuje kategorie według reguł i zwraca liczbę zmienionych transakcji.

    Domyślnie tylko transakcjom bez kategorii. Z `recategorize=True` przelicza też kategorie
    nadane wcześniej przez reguły, np. po zapamiętaniu nowej reguły użytkownika („zastosuj do
    podobnych”). Decyzji użytkownika nie zmienia nigdy: kategoria ustawiona ręcznie, także
    ręcznie usunięta, zostaje.
    """
    rules = load_rules(session, user_id)
    query = select(Transaction).where(
        Transaction.user_id == user_id,
        or_(
            Transaction.categorized_by.is_(None),
            Transaction.categorized_by != CategorizedBy.MANUAL,
        ),
    )
    if not recategorize:
        query = query.where(Transaction.category_id.is_(None))
    changed = 0
    for transaction in session.scalars(query):
        match = rules.categorize(
            text_of(
                transaction.description,
                transaction.counterparty,
                transaction.amount,
                transaction.kind,
            )
        )
        if match is None and not recategorize:
            continue
        fields = category_fields(match)
        if any(getattr(transaction, k) != v for k, v in fields.items()):
            for field, value in fields.items():
                setattr(transaction, field, value)
            changed += 1
    if commit:
        session.commit()
    return changed


def remember_correction(
    session: Session, user_id: int, transaction: Transaction, category_id: int
) -> CategoryRule | None:
    """Poprawka kategorii zapamiętana jako reguła użytkownika (albo zmiana istniejącej)."""
    rule = rule_from_correction(
        text_of(
            transaction.description,
            transaction.counterparty,
            transaction.amount,
            transaction.kind,
        ),
        category_id,
    )
    if rule is None:
        return None
    candidates = session.scalars(
        select(CategoryRule).where(
            CategoryRule.user_id == user_id,
            CategoryRule.source == RuleSource.USER,
            CategoryRule.match_type == rule.match_type,
        )
    )
    existing = next(
        (
            r
            for r in candidates
            if same_rule(
                rule,
                Rule(r.pattern, r.match_type, r.category_id, RuleSource.USER),
            )
        ),
        None,
    )
    if existing is not None:
        existing.category_id = category_id
        return existing
    saved = CategoryRule(
        user_id=user_id,
        pattern=rule.pattern,
        match_type=rule.match_type,
        category_id=category_id,
        source=RuleSource.USER,
    )
    session.add(saved)
    session.flush()
    return saved


@dataclass(frozen=True)
class CategorizationStats:
    total: int
    system_rule: int
    user_rule: int
    manual: int
    uncategorized: int


def stats(session: Session, user_id: int) -> CategorizationStats:
    """Ile transakcji skategoryzował słownik, reguły użytkownika i sam użytkownik (badanie, H2)."""
    rows: dict[CategorizedBy | None, int] = {
        by: count
        for by, count in session.execute(
            select(Transaction.categorized_by, func.count())
            .where(Transaction.user_id == user_id, Transaction.category_id.is_not(None))
            .group_by(Transaction.categorized_by)
        )
    }
    total = (
        session.scalar(
            select(func.count())
            .select_from(Transaction)
            .where(Transaction.user_id == user_id)
        )
        or 0
    )
    categorized = sum(rows.values())
    return CategorizationStats(
        total=total,
        system_rule=rows.get(CategorizedBy.SYSTEM_RULE, 0),
        user_rule=rows.get(CategorizedBy.USER_RULE, 0),
        # Kategorie nadane przed etapem 5 (bez informacji, kto je nadał) liczymy jako ręczne.
        manual=rows.get(CategorizedBy.MANUAL, 0) + rows.get(None, 0),
        uncategorized=total - categorized,
    )
