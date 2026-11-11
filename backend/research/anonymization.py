"""Pomiar anonimizacji na korpusie D4 (badanie P3, H3; docs/BADANIA.md, 3.4).

Uruchomienie z katalogu backend/:
    .venv/bin/python -m research.anonymization                    # część robocza
    .venv/bin/python -m research.anonymization --przyklady        # oraz przykłady błędów (tylko robocza)
    .venv/bin/python -m research.anonymization --poza-slownikiem  # zestaw kontrolny: imiona spoza słownika
    .venv/bin/python -m research.anonymization --testowa --zapisz # pomiar na części testowej i zapis wyniku

Przykłady błędów nie są dostępne dla części testowej: służy ona tylko do pomiaru.
"""

import datetime as dt
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

from app.ai.anonymizer import Masked, anonymize
from app.ai.names import FIRST_NAMES
from app.core.text import fold
from research.corpus import NEGATIVE_TYPES, PII_TYPES, Item, Span, load
from research.simulate import wilson

RESULTS_DIR = Path(__file__).resolve().parents[2] / "docs" / "badania"
FIXED_FORMAT = ("IBAN", "KARTA", "TELEFON", "EMAIL", "PESEL")
_NAMES = frozenset(fold(n) for n in FIRST_NAMES)


def covered(span: Span, masked: list[Masked]) -> bool:
    """Wszystkie znaki fragmentu (poza spacjami) leżą w zamaskowanych fragmentach."""
    return all(
        any(m.start <= i < m.end for m in masked) for i in range(span.start, span.end)
    )


def overlaps(a_start: int, a_end: int, b_start: int, b_end: int) -> bool:
    return a_start < b_end and b_start < a_end


def in_dictionary(text: str) -> bool:
    return any(fold(word) in _NAMES for word in text.replace("-", " ").split())


@dataclass
class Counts:
    found: int = 0
    total: int = 0

    def add(self, ok: bool) -> None:
        self.total += 1
        self.found += ok

    def rate(self) -> float | None:
        return self.found / self.total if self.total else None

    def report(self) -> dict:
        low, high = wilson(self.found, self.total)
        return {
            "wykryte": self.found,
            "wszystkie": self.total,
            "odsetek": self.rate(),
            "wilson_95": [low, high],
        }


@dataclass
class Result:
    recall: dict[str, Counts] = field(
        default_factory=lambda: {t: Counts() for t in PII_TYPES}
    )
    names_in_dictionary: Counts = field(default_factory=Counts)
    names_outside_dictionary: Counts = field(default_factory=Counts)
    precision: Counts = field(default_factory=Counts)
    overmasked: dict[str, Counts] = field(
        default_factory=lambda: {t: Counts() for t in NEGATIVE_TYPES}
    )
    misses: list[tuple[str, str, str]] = field(default_factory=list)
    false_alarms: list[tuple[str, str]] = field(default_factory=list)


def evaluate(items: list[Item]) -> Result:
    result = Result()
    for item in items:
        masked = anonymize(item.text).spans
        pii = [s for s in item.spans if s.type in PII_TYPES]
        for span in pii:
            ok = covered(span, masked)
            result.recall[span.type].add(ok)
            if span.type == "OSOBA":
                fragment = item.text[span.start : span.end]
                (
                    result.names_in_dictionary
                    if in_dictionary(fragment)
                    else result.names_outside_dictionary
                ).add(ok)
            if not ok:
                result.misses.append(
                    (span.type, item.text[span.start : span.end], item.text)
                )
        for m in masked:
            ok = any(overlaps(m.start, m.end, s.start, s.end) for s in pii)
            result.precision.add(ok)
            if not ok:
                result.false_alarms.append((item.text[m.start : m.end], item.text))
        for span in item.spans:
            if span.type in NEGATIVE_TYPES:
                result.overmasked[span.type].add(
                    any(overlaps(m.start, m.end, span.start, span.end) for m in masked)
                )
    return result


def summary(result: Result, part: str) -> dict:
    fixed = Counts(
        sum(result.recall[t].found for t in FIXED_FORMAT),
        sum(result.recall[t].total for t in FIXED_FORMAT),
    )
    names = result.recall["OSOBA"]
    precision = result.precision.rate() or 0
    return {
        "czesc": part,
        "data": dt.date.today().isoformat(),
        "czulosc": {t: c.report() for t, c in result.recall.items()},
        "czulosc_staly_format": fixed.report(),
        "czulosc_osoby_w_slowniku": result.names_in_dictionary.report(),
        "czulosc_osoby_poza_slownikiem": result.names_outside_dictionary.report(),
        "precyzja": result.precision.report(),
        "nadmierne_maskowanie": {t: c.report() for t, c in result.overmasked.items()},
        "H3_staly_format_99": (fixed.rate() or 0) >= 0.99,
        "H3_osoby_90": (names.rate() or 0) >= 0.90,
        "H3_precyzja_90": precision >= 0.90,
    }


def main(argv: list[str]) -> int:
    part = next(
        (
            p
            for p in ("testowa", "poza_slownikiem")
            if f"--{p.replace('_', '-')}" in argv
        ),
        "robocza",
    )
    result = evaluate(load(part))
    data = summary(result, part)
    for t, c in result.recall.items():
        print(f"czułość {t:8} {c.found:4}/{c.total:<4} {(c.rate() or 0):.1%}")
    for label, c in (
        ("osoby w słowniku", result.names_in_dictionary),
        ("osoby poza słownikiem", result.names_outside_dictionary),
        ("precyzja", result.precision),
        *((f"nadmierne maskowanie {t}", c) for t, c in result.overmasked.items()),
    ):
        print(f"{label:28} {c.found:4}/{c.total:<4} {(c.rate() or 0):.1%}")
    print({k: v for k, v in data.items() if k.startswith("H3")})
    if "--przyklady" in argv:
        if part == "testowa":
            print("Przykłady błędów tylko dla części roboczej.")
            return 2
        print("\nNiewykryte:")
        for kind, fragment, text in result.misses[:40]:
            print(f"  {kind:8} {fragment!r:40} w: {text}")
        print("\nZamaskowane niepotrzebnie:")
        for fragment, text in result.false_alarms[:40]:
            print(f"  {fragment!r:40} w: {text}")
    if "--zapisz" in argv:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        target = RESULTS_DIR / f"h3_anonimizacja_{part}.json"
        target.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
        print(f"Zapisano: {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
