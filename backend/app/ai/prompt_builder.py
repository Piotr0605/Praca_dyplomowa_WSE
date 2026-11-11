"""Pakiet danych dla modelu językowego: wyłącznie zanonimizowane agregaty, nigdy pojedyncze transakcje.

Model dostaje sumy w kategoriach, zmiany miesięczne i stopę oszczędności, policzone tymi samymi funkcjami
co dashboard (`analytics_service`). Nazwy kategorii użytkownika przechodzą przez anonimizację, bo mogą
zawierać dane osobowe (np. „Pożyczka dla Ani”). Do modelu nie trafiają: pojedyncze transakcje, kontrahenci,
tytuły przelewów, numery kont ani e-mail użytkownika. Pakiet można obejrzeć przed wysłaniem
(`GET /api/advice/preview-payload`), a jego kopia jest zapisywana przy każdej poradzie.

Temperatura i wersja promptu są stałe (badanie P4: powtarzalność porad).
"""

import datetime as dt
import json
from decimal import Decimal

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.anonymizer import anonymize
from app.models import Category
from app.services import analytics_service as analytics
from app.services.analytics_service import to_money

PROMPT_VERSION = "2026-11-11"
TEMPERATURE = Decimal("0.2")
# Krótsze listy niż na dashboardzie: mniejszy pakiet to niższy koszt, a porady i tak dotyczą największych pozycji.
MAX_CATEGORIES = 12
MAX_CHANGES = 8
TREND_MONTHS = 6

SYSTEM_PROMPT = """Jesteś doradcą finansów osobistych. Na podstawie danych w JSON (agregaty wydatków \
i przychodów jednej osoby, kwoty w złotych) przygotuj od 3 do 5 rekomendacji oszczędnościowych.

Zasady:
- Używaj wyłącznie liczb z danych wejściowych albo prostych działań na nich (różnica, procent); \
nie wymyślaj żadnych kwot, cen ani statystyk.
- Fragmenty w nawiasach kwadratowych, np. [OSOBA], to zanonimizowane dane: nie zgaduj, co zawierały.
- Nie oceniaj osoby; oceniaj strukturę wydatków.
- Jeśli dane nie wystarczają do jakiejś rady, napisz to wprost zamiast zgadywać.

Format odpowiedzi (Markdown, po polsku):
## Podsumowanie
2–3 zdania o strukturze finansów w tym okresie.

## Rekomendacje
Dla każdej rekomendacji:
### <numer>. <krótki tytuł>
<uzasadnienie z liczbami z danych> Szacowana oszczędność: <kwota> zł miesięcznie."""


def _category_name(name: str, is_system: bool) -> str:
    return name if is_system else anonymize(name).text


def build_payload(
    session: Session, user_id: int, date_from: dt.date, date_to: dt.date
) -> dict:
    """Agregaty okresu dla modelu. Deterministyczny dla niezmienionych danych (cache porad)."""
    frame = analytics.load_frame(session, user_id, date_from, date_to)
    s = analytics.summary(frame.data, date_from, date_to)
    rows = analytics.category_totals(frame.data)
    system_ids = _system_category_ids(session)

    def side(name: str) -> list[dict]:
        part = rows[rows["side"] == name].head(MAX_CATEGORIES)
        total = int(rows[rows["side"] == name]["amount"].sum())
        return [
            {
                "kategoria": _category_name(
                    r.category, analytics.optional_id(r.category_id) in system_ids
                ),
                "kwota": str(to_money(r.amount)),
                "udzial": round(int(r.amount) / total, 3) if total else 0.0,
                "liczba_transakcji": int(r.count),
            }
            for r in part.itertuples()
        ]

    # Trend i zmiany liczone na całej historii, żeby miesiąc porównywał się z poprzednimi.
    full = analytics.load_frame(session, user_id).data
    data_range = (full["date"].min().date(), full["date"].max().date())
    months = analytics.monthly(full, data_range[0], dt.date.today(), TREND_MONTHS)
    complete = {
        pd.Period(m.month, "M")
        for m in analytics.monthly(full, data_range[0], dt.date.today(), 120)
        if m.complete
    }
    month = pd.Period(date_to.strftime("%Y-%m"), "M")
    changes = [
        {
            "kategoria": _category_name(c.category, c.category_id in system_ids),
            "biezacy_miesiac": str(to_money(c.current)),
            "poprzedni_miesiac": None
            if c.previous is None
            else str(to_money(c.previous)),
            "zmiana": c.change_previous,
        }
        for c in analytics.changes(full, month, complete)[:MAX_CHANGES]
    ]

    return {
        "wersja": PROMPT_VERSION,
        "okres": {
            "od": date_from.isoformat(),
            "do": date_to.isoformat(),
            "dni": s.days,
            "pelny_miesiac": month in complete,
        },
        "podsumowanie": {
            "przychody": str(to_money(s.totals.income)),
            "wydatki": str(to_money(s.totals.expenses)),
            "saldo": str(to_money(s.totals.balance)),
            "stopa_oszczednosci": s.totals.savings_rate,
            "przelewy_na_wlasne_konta": str(to_money(s.own_transfers_net)),
            "liczba_transakcji": s.transactions,
            "sredni_dzienny_wydatek": str(to_money(s.avg_daily_expense)),
        },
        "wydatki_wedlug_kategorii": side("expense"),
        "wplywy_wedlug_kategorii": side("income"),
        "zmiany_w_kategoriach_wydatkow": changes,
        "trend_miesieczny": [
            {
                "miesiac": m.month,
                "przychody": str(to_money(m.totals.income)),
                "wydatki": str(to_money(m.totals.expenses)),
                "pelny": m.complete,
            }
            for m in months
        ],
    }


def _system_category_ids(session: Session) -> set[int | None]:
    """Nazwy kategorii systemowych i „Bez kategorii” (bez identyfikatora) są wspólne i bezpieczne."""
    return set(
        session.scalars(select(Category.id).where(Category.user_id.is_(None)))
    ) | {None}


def user_message(payload: dict) -> str:
    return "Dane finansowe (agregaty, kwoty w PLN):\n" + json.dumps(
        payload, ensure_ascii=False, indent=1
    )
