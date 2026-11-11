"""Dostawca `mock`: porady bez internetu i kosztów (development, testy, pokaz bez kluczy API).

Rekomendacje są budowane deterministycznie z pakietu agregatów i używają wyłącznie liczb z pakietu,
więc przechodzą kontrolę zgodności liczb (badanie H4a).
"""

from decimal import Decimal

from app.ai.providers.base import AdviceResult, messages_for

MODEL = "mock-1"


def _amount(value: str) -> Decimal:
    return Decimal(value)


def _pln(value: Decimal) -> str:
    return f"{value:.2f}".replace(".", ",")


class MockProvider:
    def generate_advice(self, payload: dict) -> AdviceResult:
        summary = payload["podsumowanie"]
        expenses = payload["wydatki_wedlug_kategorii"]
        sections = [
            "## Podsumowanie",
            (
                f"W okresie {payload['okres']['od']} – {payload['okres']['do']} wydatki wyniosły "
                f"{_pln(_amount(summary['wydatki']))} zł przy przychodach "
                f"{_pln(_amount(summary['przychody']))} zł."
            ),
            "",
            "## Rekomendacje",
        ]
        for i, category in enumerate(expenses[:3], start=1):
            saving = _amount(category["kwota"]) * Decimal("0.10")
            sections += [
                f"### {i}. Przyjrzyj się kategorii {category['kategoria']}",
                (
                    f"Wydatki w tej kategorii to {_pln(_amount(category['kwota']))} zł "
                    f"({category['liczba_transakcji']} transakcji). Ograniczenie ich o 10% "
                    f"zmniejszyłoby wydatki okresu. Szacowana oszczędność: {_pln(saving)} zł miesięcznie."
                ),
            ]
        if len(expenses) < 3:
            sections += [
                f"### {len(expenses) + 1}. Za mało danych",
                "W tym okresie jest zbyt mało kategorii wydatków, żeby zaproponować więcej rad.",
            ]
        text = "\n".join(sections)
        system, message = messages_for(payload)
        return AdviceResult(
            text=text,
            model=MODEL,
            # Przybliżenie długości w tokenach: wystarcza do testów kosztu i limitów.
            tokens_in=(len(system) + len(message)) // 4,
            tokens_out=len(text) // 4,
            response_time_ms=1,
        )
