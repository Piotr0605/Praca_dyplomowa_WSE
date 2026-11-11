"""Przenosi etykiety z badania (data/private/etykiety.csv) na konto użytkownika w aplikacji.

Etykieta to decyzja użytkownika, więc transakcja dostaje kategorię jako ustawioną ręcznie (`manual`).
Dla kontrahenta, którego wszystkie transakcje mają tę samą etykietę, a słownik przypisuje inną kategorię
albo żadnej, powstaje reguła użytkownika, tak jak po poprawce w aplikacji. Pozostałe transakcje bez
kategorii (np. spoza wyciągów PDF) dostają kategorię z reguł i słownika. Kategorie dodane w trakcie
etykietowania powstają jako własne kategorie użytkownika. Skrypt można uruchomić ponownie.

Plik etykiet leży poza katalogiem backendu, więc podaje się go na standardowe wejście
(z katalogu głównego projektu):
    docker compose exec -T backend python -m scripts.apply_labels EMAIL < data/private/etykiety.csv
    docker compose exec -T backend python -m scripts.apply_labels EMAIL --proba < data/private/etykiety.csv
Wypisywane są wyłącznie liczby.
"""

import csv
import sys
from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.text import fold
from app.models import Category, Transaction
from app.models.enums import CategorizedBy
from app.services.categorization_service import (
    apply_rules,
    load_rules,
    remember_correction,
    text_of,
)


@dataclass
class Summary:
    labelled: int = 0
    labels_without_transaction: int = 0
    new_categories: int = 0
    rules: int = 0
    mixed_counterparties: int = 0
    auto_categorized: int = 0
    uncategorized: int = 0


def _category_ids(
    session: Session, user_id: int, names: set[str], summary: Summary
) -> dict[str, int]:
    visible = {
        c.name: c.id
        for c in session.scalars(
            select(Category).where(
                (Category.user_id.is_(None)) | (Category.user_id == user_id)
            )
        )
    }
    for name in sorted(names - set(visible)):
        category = Category(user_id=user_id, name=name[:100])
        session.add(category)
        session.flush()
        visible[name] = category.id
        summary.new_categories += 1
    return visible


def apply_labels(session: Session, user_id: int, labels: dict[str, str]) -> Summary:
    summary = Summary()
    ids = _category_ids(session, user_id, set(labels.values()), summary)
    transactions = list(
        session.scalars(
            select(Transaction).where(
                Transaction.user_id == user_id,
                Transaction.dedup_hash.in_(list(labels)),
            )
        )
    )
    summary.labels_without_transaction = len(labels) - len(transactions)
    dictionary = load_rules(session, user_id)

    by_counterparty: dict[str, list[Transaction]] = defaultdict(list)
    for transaction in transactions:
        transaction.category_id = ids[labels[transaction.dedup_hash]]
        transaction.categorized_by = CategorizedBy.MANUAL
        transaction.category_rule_id = None
        summary.labelled += 1
        if transaction.counterparty:
            by_counterparty[fold(transaction.counterparty)].append(transaction)

    for group in by_counterparty.values():
        categories = {t.category_id for t in group}
        if len(categories) > 1:
            # Różne etykiety u jednego kontrahenta: reguła przypisałaby źle część transakcji.
            summary.mixed_counterparties += 1
            continue
        (category_id,) = categories
        predicted = [
            dictionary.categorize(
                text_of(t.description, t.counterparty, t.amount, t.kind)
            )
            for t in group
        ]
        if all(m is not None and m.category_id == category_id for m in predicted):
            continue  # słownik i tak przypisuje dobrze: reguła niepotrzebna
        rule = remember_correction(session, user_id, group[0], category_id)
        if rule is not None:
            summary.rules += 1
            for transaction in group:
                transaction.category_rule_id = rule.id
    session.flush()

    summary.auto_categorized = apply_rules(session, user_id, commit=False)
    # Sesja aplikacji nie zapisuje zmian automatycznie przed zapytaniem (autoflush=False).
    session.flush()
    summary.uncategorized = len(
        session.scalars(
            select(Transaction.id).where(
                Transaction.user_id == user_id, Transaction.category_id.is_(None)
            )
        ).all()
    )
    return summary


def read_labels(lines) -> dict[str, str]:
    return {
        row["klucz"]: row["kategoria"] for row in csv.DictReader(lines, delimiter=";")
    }


def main(argv: list[str]) -> int:
    from app.core.database import SessionLocal
    from app.repositories.user_repository import UserRepository

    if not argv or argv[0].startswith("-"):
        print(__doc__)
        return 2
    labels = read_labels(sys.stdin)
    if not labels:
        print("Brak etykiet na wejściu (plik data/private/etykiety.csv).")
        return 1
    with SessionLocal() as session:
        user = UserRepository(session).get_by_email(argv[0].strip().lower())
        if user is None:
            print("Nie ma konta o tym adresie.")
            return 1
        summary = apply_labels(session, user.id, labels)
        if "--proba" in argv:
            session.rollback()
            print("PRÓBA, nic nie zapisano.")
        else:
            session.commit()
    print(
        f"Etykiety: {len(labels)}, przypisane do transakcji: {summary.labelled}, "
        f"bez transakcji na koncie: {summary.labels_without_transaction}\n"
        f"Nowe kategorie: {summary.new_categories}, reguły: {summary.rules}, "
        f"kontrahenci z różnymi etykietami (bez reguły): {summary.mixed_counterparties}\n"
        f"Pozostałe skategoryzowane automatycznie: {summary.auto_categorized}, "
        f"bez kategorii: {summary.uncategorized}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
