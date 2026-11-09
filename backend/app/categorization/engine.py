"""Kategoryzacja transakcji: czysta funkcja bez bazy danych.

Tej samej funkcji używa aplikacja (import, ręczne dodanie, przypisanie wstecz) i symulacja w badaniu
(docs/BADANIA.md, H2), więc wynik badania opisuje dokładnie to, co robi system.

Kolejność dopasowania:
1. przelew własny (rozpoznany przez parser) → kategoria „Przelewy własne”,
2. reguły użytkownika: najpierw dokładny kontrahent, potem fragment tekstu,
3. reguły systemowe (słownik `system_rules.json`),
4. brak dopasowania → transakcja czeka na przypisanie.
W obrębie jednej grupy wygrywa wyższy priorytet, a przy równym dłuższy wzorzec, bo jest bardziej
konkretny („uber eats” przed „uber”).
"""

import re
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal
from functools import cache

from app.core.text import fold
from app.models.enums import CategorizedBy, RuleMatchType, RuleSource, TransactionKind

MATCH_ORDER = {
    RuleMatchType.EXACT_COUNTERPARTY: 0,
    RuleMatchType.CONTAINS: 1,
    RuleMatchType.REGEX: 1,
}


@dataclass(frozen=True)
class Rule:
    pattern: str
    match_type: RuleMatchType
    category_id: int
    source: RuleSource
    priority: int = 0
    # Tylko wpływy (1) albo tylko wydatki (-1), np. „wynagrodzenie” nie dotyczy wydatków.
    sign: int | None = None
    # Identyfikator reguły użytkownika w bazie; reguły systemowe go nie mają.
    id: int | None = None


@dataclass(frozen=True)
class TransactionText:
    description: str
    counterparty: str | None
    amount: Decimal
    kind: TransactionKind


@dataclass(frozen=True)
class Match:
    category_id: int
    categorized_by: CategorizedBy
    rule: Rule | None


@cache
def _word_pattern(pattern: str) -> re.Pattern[str]:
    """Wzorzec jako całe słowa: „bp” pasuje do „BP STACJA 12”, ale nie do „ABPX”."""
    return re.compile(rf"(?<![a-z0-9]){re.escape(fold(pattern))}(?![a-z0-9])")


def rule_matches(rule: Rule, transaction: TransactionText) -> bool:
    if rule.sign is not None and (transaction.amount > 0) != (rule.sign > 0):
        return False
    if rule.match_type is RuleMatchType.EXACT_COUNTERPARTY:
        return fold(transaction.counterparty or "") == fold(rule.pattern)
    text = fold(f"{transaction.description} {transaction.counterparty or ''}")
    if rule.match_type is RuleMatchType.REGEX:
        return re.search(rule.pattern, text) is not None
    return _word_pattern(rule.pattern).search(text) is not None


def _ordered(rules: Iterable[Rule]) -> list[Rule]:
    return sorted(
        rules,
        key=lambda r: (MATCH_ORDER[r.match_type], -r.priority, -len(r.pattern)),
    )


def categorize(
    transaction: TransactionText,
    user_rules: Iterable[Rule],
    system_rules: Iterable[Rule],
    own_transfer_category_id: int | None,
) -> Match | None:
    if (
        transaction.kind is TransactionKind.OWN_TRANSFER
        and own_transfer_category_id is not None
    ):
        return Match(own_transfer_category_id, CategorizedBy.SYSTEM_RULE, None)
    for rules, by in (
        (user_rules, CategorizedBy.USER_RULE),
        (system_rules, CategorizedBy.SYSTEM_RULE),
    ):
        for rule in _ordered(rules):
            if rule_matches(rule, transaction):
                return Match(rule.category_id, by, rule)
    return None


def rule_from_correction(transaction: TransactionText, category_id: int) -> Rule | None:
    """Reguła zapamiętana z poprawki użytkownika: ten sam kontrahent → ta sama kategoria.

    Bez nazwy kontrahenta reguła nie powstaje. Sam opis (np. „Płatność kartą 29.09.2026”)
    jest zbyt ogólny i reguła z niego przypisałaby kategorię niepodobnym transakcjom.
    """
    counterparty = (transaction.counterparty or "").strip()
    if not counterparty:
        return None
    return Rule(
        pattern=counterparty,
        match_type=RuleMatchType.EXACT_COUNTERPARTY,
        category_id=category_id,
        source=RuleSource.USER,
    )


def same_rule(a: Rule, b: Rule) -> bool:
    """Ta sama reguła niezależnie od kategorii: nowa poprawka zastępuje starą."""
    return a.match_type == b.match_type and fold(a.pattern) == fold(b.pattern)
