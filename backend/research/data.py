"""Dane badania: zbiór D1 (wyciągi PDF) i D2 (etykiety kategorii) z docs/BADANIA.md.

Prawdziwe pliki leżą tylko w data/private/. Funkcje zwracają dane do obliczeń w pamięci;
skrypty wypisują wyłącznie wyniki zbiorcze.
"""

import csv
import json
from dataclasses import dataclass
from pathlib import Path

from app.categorization.engine import TransactionText
from app.core.text import fold
from app.models.enums import TransactionKind
from app.parsers.common import normalize_description
from app.parsers.ing_pdf import parse_ing_pdf
from app.services.categorization_service import SYSTEM_RULES_FILE

PRIVATE_DIR = Path(__file__).resolve().parents[2] / "data" / "private"
LABELS_FILE = PRIVATE_DIR / "etykiety.csv"

# Kategorie systemowe z migracji `kategorie_systemowe` (test sprawdza zgodność z bazą).
SYSTEM_CATEGORIES = (
    "Jedzenie",
    "Zakupy spożywcze",
    "Restauracje",
    "Transport",
    "Paliwo",
    "Mieszkanie",
    "Rachunki",
    "Subskrypcje",
    "Rozrywka",
    "Zdrowie",
    "Odzież",
    "Edukacja",
    "Prezenty",
    "Przelewy własne",
    "Inne",
    "Wynagrodzenie",
)
OWN_TRANSFER_CATEGORY = "Przelewy własne"


@dataclass(frozen=True)
class Item:
    """Transakcja w badaniu: miesiąc (numer wyciągu), tekst do kategoryzacji i klucz etykiety."""

    month: int
    key: str
    text: TransactionText


def load_statements(directory: Path = PRIVATE_DIR) -> list[Item]:
    """Transakcje z wyciągów PDF; miesiąc to numer wyciągu w kolejności okresów (1–6)."""
    statements = sorted(
        (parse_ing_pdf(path.read_bytes()) for path in directory.glob("*.pdf")),
        key=lambda s: s.summary.period_start,
    )
    return [
        Item(
            month=number,
            key=t.dedup_hash,
            text=TransactionText(t.description, t.counterparty, t.amount, t.kind),
        )
        for number, statement in enumerate(statements, start=1)
        for t in sorted(statement.transactions, key=lambda t: t.date)
    ]


def load_labels(path: Path = LABELS_FILE) -> dict[str, str]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8", newline="") as file:
        return {
            row["klucz"]: row["kategoria"]
            for row in csv.DictReader(file, delimiter=";")
        }


def save_labels(labels: dict[str, str], path: Path = LABELS_FILE) -> None:
    """Zapis przez plik tymczasowy: przerwanie nie zostawi uszkodzonych etykiet."""
    temporary = path.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file, delimiter=";")
        writer.writerow(["klucz", "kategoria"])
        writer.writerows(sorted(labels.items()))
    temporary.chmod(0o600)
    temporary.replace(path)


def is_own_transfer(item: Item) -> bool:
    """Przelewy własne rozpoznaje parser, a nie kategoryzacja: liczone osobno (BADANIA.md, 3.3)."""
    return item.text.kind is TransactionKind.OWN_TRANSFER


def group_key(item: Item) -> str:
    """Grupa do etykietowania: kontrahent, a bez niego opis bez dat."""
    if item.text.counterparty:
        return fold(item.text.counterparty)
    return "opis: " + normalize_description(item.text.description)[:60]


def system_rules_definition() -> dict:
    return json.loads(SYSTEM_RULES_FILE.read_text(encoding="utf-8"))
