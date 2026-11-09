"""Symulacja kategoryzacji na 6 miesiącach (badanie H2, docs/BADANIA.md, 3.3).

Uruchomienie z katalogu backend/ (po etykietowaniu: python -m research.label):
    .venv/bin/python -m research.simulate            # wypisuje wyniki
    .venv/bin/python -m research.simulate --zapisz   # oraz zapisuje je w docs/badania/

Wariant A: tylko słownik reguł systemowych. Wariant B: słownik i reguły z poprawek. Każda błędna
kategoria w miesiącu m jest „poprawiana” zgodnie z etykietą i tworzy regułę tą samą funkcją co
aplikacja; reguła działa od miesiąca m+1. Wypisywane są wyłącznie wyniki zbiorcze.
"""

import datetime as dt
import json
import math
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

from app.categorization.engine import Rule, categorize, rule_from_correction, same_rule
from app.models.enums import RuleMatchType, RuleSource
from research.data import (
    OWN_TRANSFER_CATEGORY,
    SYSTEM_CATEGORIES,
    Item,
    is_own_transfer,
    load_labels,
    load_statements,
    system_rules_definition,
)

RESULTS_DIR = Path(__file__).resolve().parents[2] / "docs" / "badania"
TEST_MONTHS = (4, 5, 6)


@dataclass(frozen=True)
class Outcome:
    month: int
    key: str
    label: str
    predicted: str | None

    @property
    def correct(self) -> bool:
        return self.predicted == self.label


@dataclass(frozen=True)
class MonthMetrics:
    variant: str
    month: int
    n: int
    accuracy: float
    coverage: float
    precision: float | None
    corrections_per_100: float


def system_rules(definition: dict, ids: dict[str, int]) -> list[Rule]:
    return [
        Rule(
            pattern=pattern,
            match_type=RuleMatchType.CONTAINS,
            category_id=ids[group["category"]],
            source=RuleSource.SYSTEM,
            sign=group.get("sign"),
        )
        for group in definition["rules"]
        for pattern in group["contains"]
    ]


def simulate(
    items: list[Item], labels: dict[str, str], definition: dict
) -> dict[str, list[Outcome]]:
    names = sorted({*SYSTEM_CATEGORIES, *labels.values()})
    ids = {name: number for number, name in enumerate(names, start=1)}
    by_id = {number: name for name, number in ids.items()}
    system = system_rules(definition, ids)
    own = ids[OWN_TRANSFER_CATEGORY]
    labelled = [i for i in items if i.key in labels and not is_own_transfer(i)]

    results: dict[str, list[Outcome]] = {"A": [], "B": []}
    user_rules: list[Rule] = []
    for month in sorted({i.month for i in labelled}):
        month_items = [i for i in labelled if i.month == month]
        for variant in ("A", "B"):
            rules = user_rules if variant == "B" else []
            for item in month_items:
                match = categorize(item.text, rules, system, own)
                results[variant].append(
                    Outcome(
                        month,
                        item.key,
                        labels[item.key],
                        by_id[match.category_id] if match else None,
                    )
                )
        # Poprawki z miesiąca m działają od miesiąca m+1, jak w protokole badania.
        for outcome, item in zip(
            [o for o in results["B"] if o.month == month], month_items, strict=True
        ):
            if outcome.correct:
                continue
            rule = rule_from_correction(item.text, ids[outcome.label])
            if rule is not None:
                user_rules[:] = [r for r in user_rules if not same_rule(r, rule)]
                user_rules.append(rule)
    return results


def month_metrics(variant: str, outcomes: list[Outcome]) -> list[MonthMetrics]:
    metrics = []
    for month in sorted({o.month for o in outcomes}):
        rows = [o for o in outcomes if o.month == month]
        covered = [o for o in rows if o.predicted is not None]
        correct = sum(o.correct for o in rows)
        metrics.append(
            MonthMetrics(
                variant=variant,
                month=month,
                n=len(rows),
                accuracy=correct / len(rows),
                coverage=len(covered) / len(rows),
                precision=(
                    sum(o.correct for o in covered) / len(covered) if covered else None
                ),
                corrections_per_100=100 * (len(rows) - correct) / len(rows),
            )
        )
    return metrics


def mcnemar_exact(b: int, c: int) -> float:
    """Dokładny test McNemara (dwustronny): b i c to pary niezgodne (A dobrze, B źle i odwrotnie)."""
    n = b + c
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, k) for k in range(min(b, c) + 1)) / 2**n
    return min(1.0, 2 * tail)


def wilson(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95-procentowy przedział ufności Wilsona dla proporcji."""
    if n == 0:
        return (0.0, 1.0)
    p = successes / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (centre - half, centre + half)


def evaluate(results: dict[str, list[Outcome]]) -> dict:
    a = {o.key: o for o in results["A"] if o.month in TEST_MONTHS}
    b = {o.key: o for o in results["B"] if o.month in TEST_MONTHS}
    a_only = sum(a[k].correct and not b[k].correct for k in a)
    b_only = sum(b[k].correct and not a[k].correct for k in a)
    n = len(a)
    acc = {v: sum(o.correct for o in d.values()) for v, d in (("A", a), ("B", b))}
    per_month = {m.month: m for m in month_metrics("B", results["B"])}
    p_value = mcnemar_exact(a_only, b_only)
    h2b = None
    if 2 in per_month and 6 in per_month:
        h2b = per_month[6].corrections_per_100 <= per_month[2].corrections_per_100 / 2
    return {
        "test_months": list(TEST_MONTHS),
        "n_test": n,
        "accuracy_test": {v: acc[v] / n if n else None for v in acc},
        "wilson_95": {v: wilson(acc[v], n) for v in acc},
        "discordant": {"A_dobrze_B_zle": a_only, "A_zle_B_dobrze": b_only},
        "mcnemar_p": p_value,
        "H2a": n > 0 and acc["B"] > acc["A"] and p_value < 0.05,
        "H2b": h2b,
        "H2c": n > 0 and acc["B"] / n >= 0.85,
    }


def _format(results: dict[str, list[Outcome]], summary: dict) -> str:
    lines = ["wariant  miesiąc  n    trafność  pokrycie  precyzja  poprawek/100"]
    for variant in ("A", "B"):
        for m in month_metrics(variant, results[variant]):
            precision = f"{m.precision:8.1%}" if m.precision is not None else "       —"
            lines.append(
                f"{variant:8} {m.month:7}  {m.n:4} {m.accuracy:8.1%}  {m.coverage:8.1%}  "
                f"{precision}  {m.corrections_per_100:11.1f}"
            )
    lines.append(json.dumps(summary, ensure_ascii=False, indent=2))
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    items = load_statements()
    labels = load_labels()
    to_label = [i for i in items if not is_own_transfer(i)]
    labelled = sum(i.key in labels for i in to_label)
    print(
        f"Transakcje: {len(items)}, przelewy własne (poza oceną): {len(items) - len(to_label)}, "
        f"z etykietą: {labelled} z {len(to_label)}"
    )
    if not labelled:
        print("Brak etykiet: najpierw uruchom python -m research.label")
        return 1
    definition = system_rules_definition()
    results = simulate(items, labels, definition)
    summary = {
        "rules_version": definition["version"],
        "date": dt.date.today().isoformat(),
        "labelled": labelled,
        "unlabelled": len(to_label) - labelled,
        **evaluate(results),
    }
    print(_format(results, summary))
    if "--zapisz" in argv:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        data = {
            "summary": summary,
            "months": [
                asdict(m) for v in ("A", "B") for m in month_metrics(v, results[v])
            ],
        }
        path = RESULTS_DIR / "h2_kategoryzacja.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
        print(f"Zapisano wyniki zbiorcze: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
