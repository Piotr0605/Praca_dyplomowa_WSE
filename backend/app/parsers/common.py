"""Elementy wspólne parserów wyciągów PDF i plików CSV."""

import re

DATE_RE = re.compile(r"\d{2}\.\d{2}\.\d{4}")
# Numer karty nie jest potrzebny do analizy, więc nie trafia do bazy.
CARD_NUMBER_RE = re.compile(r"Nr karty \S+")


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def normalize_description(text: str) -> str:
    """Opis do porównań w kategoryzacji (etap 5): małe litery, bez dat i nadmiarowych spacji."""
    return re.sub(r"\s+", " ", DATE_RE.sub("", text.lower())).strip()
