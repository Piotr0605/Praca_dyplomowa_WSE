"""Porównywanie tekstów bez względu na wielkość liter i polskie znaki."""

import unicodedata


def fold(text: str) -> str:
    """Małe litery bez polskich znaków i nadmiarowych spacji: „Żabka” i „ZABKA” dają to samo."""
    text = text.lower().replace("ł", "l")
    text = unicodedata.normalize("NFKD", text)
    return " ".join("".join(c for c in text if not unicodedata.combining(c)).split())
