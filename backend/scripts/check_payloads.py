"""Kontrola wycieków danych osobowych w pakietach dla modelu (badanie P3, kontrola na prawdziwych danych).

Dla każdego miesiąca z danymi użytkownika budowany jest dokładnie ten pakiet, który poszedłby do modelu,
i przeszukiwany pod kątem:
- wzorców danych o stałym formacie (IBAN, karta, telefon, e-mail, PESEL, adres) — tymi samymi regułami
  co anonimizator;
- imion z kontrahentów i opisów transakcji użytkownika (słowa ze słownika imion anonimizatora).

Uruchomienie z katalogu głównego projektu:
    docker compose exec -T backend python -m scripts.check_payloads EMAIL

Wypisywane są wyłącznie liczby wycieków (oczekiwane: 0), bez treści pakietów.
"""

import datetime as dt
import json
import sys

from sqlalchemy import func, select

from app.ai.anonymizer import _fixed_format
from app.ai.names import FIRST_NAMES
from app.ai.prompt_builder import build_payload
from app.core.text import fold
from app.models import Transaction

_NAMES = frozenset(fold(n) for n in FIRST_NAMES)


def month_range(month: str) -> tuple[dt.date, dt.date]:
    start = dt.date.fromisoformat(month + "-01")
    next_month = (start.replace(day=28) + dt.timedelta(days=4)).replace(day=1)
    return start, next_month - dt.timedelta(days=1)


def person_words(session, user_id: int) -> set[str]:
    """Imiona występujące w kontrahentach i opisach transakcji użytkownika."""
    words: set[str] = set()
    rows = session.execute(
        select(Transaction.counterparty, Transaction.description).where(
            Transaction.user_id == user_id
        )
    )
    for counterparty, description in rows:
        for word in fold(f"{counterparty or ''} {description or ''}").split():
            if word in _NAMES:
                words.add(word)
    return words


def main(argv: list[str]) -> int:
    from app.core.database import SessionLocal
    from app.repositories.user_repository import UserRepository

    if not argv or argv[0].startswith("-"):
        print(__doc__)
        return 2
    leaks_total = 0
    with SessionLocal() as session:
        user = UserRepository(session).get_by_email(argv[0].strip().lower())
        if user is None:
            print("Nie ma konta o tym adresie.")
            return 1
        first, last = session.execute(
            select(func.min(Transaction.date), func.max(Transaction.date)).where(
                Transaction.user_id == user.id
            )
        ).one()
        months = []
        current = first.replace(day=1) if first else None
        while current is not None and current <= last:
            months.append(current.strftime("%Y-%m"))
            current = (current + dt.timedelta(days=32)).replace(day=1)
        if first is None:
            print("Brak transakcji na koncie.")
            return 0
        names = person_words(session, user.id)
        print(f"Imion w danych transakcji (do sprawdzenia): {len(names)}")
        for month in months:
            start, end = month_range(month)
            payload = json.dumps(
                build_payload(session, user.id, start, end), ensure_ascii=False
            )
            patterns = _fixed_format(payload)
            folded_words = set(fold(payload).split())
            name_leaks = names & folded_words
            leaks = len(patterns) + len(name_leaks)
            leaks_total += leaks
            print(
                f"{month}: znaków {len(payload):6}, wzorce danych: {len(patterns)}, "
                f"imiona: {len(name_leaks)} → wycieki: {leaks}"
            )
    print(f"\nRazem wycieków: {leaks_total} (oczekiwane: 0)")
    return 0 if leaks_total == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
