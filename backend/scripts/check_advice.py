"""Kontrola zgodności liczb zapisanych porad z ich pakietami (badanie H4a).

Uruchomienie z katalogu głównego projektu:
    docker compose exec -T backend python -m scripts.check_advice EMAIL

Wypisuje wyniki zbiorcze i liczby bez pokrycia (same wartości liczbowe, bez treści porad).
"""

import sys

from sqlalchemy import select

from app.models import AIAdvice
from research.advice_numbers import check


def main(argv: list[str]) -> int:
    from app.core.database import SessionLocal
    from app.repositories.user_repository import UserRepository

    if not argv or argv[0].startswith("-"):
        print(__doc__)
        return 2
    with SessionLocal() as session:
        user = UserRepository(session).get_by_email(argv[0].strip().lower())
        if user is None:
            print("Nie ma konta o tym adresie.")
            return 1
        rows = list(
            session.scalars(
                select(AIAdvice)
                .where(AIAdvice.user_id == user.id)
                .order_by(AIAdvice.id)
            )
        )
    if not rows:
        print("Brak zapisanych porad.")
        return 0
    all_numbers = all_uncovered = 0
    for advice in rows:
        report = check(advice.response_text, advice.prompt_payload)
        all_numbers += len(report.numbers)
        all_uncovered += len(report.uncovered)
        state = "OK" if not report.uncovered else "DO PRZEGLĄDU"
        print(
            f"porada {advice.id} ({advice.provider}, {advice.period_start}–{advice.period_end}): "
            f"liczb {len(report.numbers)}, pokrytych {report.covered} — {state}"
        )
        for number in report.uncovered:
            print(f"   bez pokrycia: {number.text}")
    share = (all_numbers - all_uncovered) / all_numbers if all_numbers else 1.0
    print(f"\nRazem liczb: {all_numbers}, pokrytych: {share:.1%} (próg H4a: ≥ 95%)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
