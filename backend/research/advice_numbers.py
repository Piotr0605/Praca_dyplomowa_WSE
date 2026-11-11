"""Zgodność liczb porady z wysłanym pakietem agregatów (badanie H4a, docs/BADANIA.md, 3.5).

Z tekstu porady wyciągane są kwoty („123,45 zł”) i procenty („12%”). Liczba jest uznana za pokrytą, gdy:
- występuje w pakiecie wprost (kwota, procent albo liczba transakcji),
- jest sumą albo różnicą dwóch kwot z pakietu,
- jest udziałem jednej kwoty z pakietu w drugiej (dla procentów),
- jest procentem kwoty z pakietu, przy czym ten procent występuje w pakiecie albo w tekście porady
  (np. „ograniczenie o 10% dałoby 25,00 zł”);
- procent spoza pakietu (parametr scenariusza, np. „o 10%”) jest pokryty tylko wtedy, gdy wynik tego
  procentu od kwoty z pakietu pada w tekście porady.

Pozostałe liczby wymagają ręcznego przeglądu; zasada zapisana przed pomiarem.
"""

import re
from dataclasses import dataclass
from decimal import Decimal
from itertools import combinations

AMOUNT_RE = re.compile(r"(\d{1,3}(?:[  ]\d{3})*(?:,\d{1,2})?|\d+(?:,\d{1,2})?)\s*zł")
PERCENT_RE = re.compile(r"(\d+(?:,\d+)?)\s*%")
COUNT_RE = re.compile(r"\b(\d+)\s+transakcj")
TOLERANCE = Decimal("0.01")
PERCENT_TOLERANCE = Decimal("0.5")


@dataclass(frozen=True)
class Found:
    value: Decimal
    kind: str  # amount | percent | count
    text: str


@dataclass(frozen=True)
class Report:
    numbers: list[Found]
    uncovered: list[Found]

    @property
    def covered(self) -> int:
        return len(self.numbers) - len(self.uncovered)


def _decimal(text: str) -> Decimal:
    return Decimal(
        text.replace(",", ".").replace(" ", "").replace(" ", "").replace(" ", "")
    )


def numbers_in_text(text: str) -> list[Found]:
    found = [
        Found(_decimal(m.group(1)), "amount", m.group())
        for m in AMOUNT_RE.finditer(text)
    ]
    found += [
        Found(_decimal(m.group(1)), "percent", m.group())
        for m in PERCENT_RE.finditer(text)
    ]
    found += [
        Found(Decimal(m.group(1)), "count", m.group()) for m in COUNT_RE.finditer(text)
    ]
    return found


def payload_numbers(payload: object) -> tuple[set[Decimal], set[Decimal], set[Decimal]]:
    """Kwoty, procenty (ułamki przeliczone na %) i liczby całkowite z pakietu."""
    amounts: set[Decimal] = set()
    percents: set[Decimal] = set()
    counts: set[Decimal] = set()

    def walk(value: object) -> None:
        if isinstance(value, dict):
            for v in value.values():
                walk(v)
        elif isinstance(value, list):
            for v in value:
                walk(v)
        elif isinstance(value, str) and re.fullmatch(r"-?\d+\.\d{2}", value):
            amounts.add(abs(Decimal(value)))
        elif isinstance(value, bool):
            return
        elif isinstance(value, float):
            percents.add(round(Decimal(str(value)) * 100, 2))
        elif isinstance(value, int):
            counts.add(Decimal(value))

    walk(payload)
    return amounts, percents, counts


def check(text: str, payload: dict) -> Report:
    amounts, percents, counts = payload_numbers(payload)
    found = numbers_in_text(text)
    text_percents = {f.value for f in found if f.kind == "percent"}
    pair_results = {
        result for a, b in combinations(amounts, 2) for result in (a + b, abs(a - b))
    }
    products = {
        round(amount * percent / 100, 2)
        for amount in amounts
        for percent in percents | text_percents
    }
    shares = {round(a / b * 100, 1) for a in amounts for b in amounts if b and a <= b}

    text_amounts = {f.value for f in found if f.kind == "amount"}
    # Procent-parametr scenariusza: jego wynik od kwoty z pakietu musi paść w tekście porady.
    used_percents = {
        percent
        for percent in text_percents
        for amount in amounts
        if any(
            abs(round(amount * percent / 100, 2) - t) <= TOLERANCE for t in text_amounts
        )
    }

    uncovered = []
    for number in found:
        if number.kind == "amount":
            ok = any(
                abs(number.value - candidate) <= TOLERANCE
                for candidate in amounts | pair_results | products
            )
        elif number.kind == "percent":
            ok = number.value in used_percents or any(
                abs(number.value - candidate) <= PERCENT_TOLERANCE
                for candidate in percents | shares
            )
        else:
            ok = number.value in counts
        if not ok:
            uncovered.append(number)
    return Report(found, uncovered)
