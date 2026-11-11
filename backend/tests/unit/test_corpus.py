"""Korpus D4 (research/corpus.py): powtarzalność, poprawność oznaczeń i rozłączność części."""

from itertools import pairwise

import pytest

from app.ai.names import FIRST_NAMES as DICTIONARY
from app.core.text import fold
from research.corpus import (
    FIRST_NAMES,
    NEGATIVE_TYPES,
    PII_TYPES,
    RARE_FIRST_NAMES,
    SEEDS,
    SURNAMES,
    generate,
    generate_outside,
    load,
)


@pytest.mark.parametrize("part", list(SEEDS))
def test_zapisany_korpus_odtwarzalny_z_ziarna(part: str) -> None:
    """Część testowa jest zamrożona: zmiana generatora nie może jej po cichu zmienić."""
    assert load(part) == generate(part)


@pytest.mark.parametrize("part", list(SEEDS))
def test_oznaczenia_w_granicach_tekstu_i_rozlaczne(part: str) -> None:
    for item in load(part):
        spans = sorted(item.spans, key=lambda s: s.start)
        for span in spans:
            assert 0 <= span.start < span.end <= len(item.text)
            assert span.type in PII_TYPES + NEGATIVE_TYPES
            assert (
                item.text[span.start : span.end].strip()
                == item.text[span.start : span.end]
            )
        for a, b in pairwise(spans):
            assert a.end <= b.start


def test_pule_czesci_rozlaczne() -> None:
    assert not set(FIRST_NAMES["A"]) & set(FIRST_NAMES["B"])
    assert not set(SURNAMES["A"]) & set(SURNAMES["B"])


def test_zestaw_poza_slownikiem() -> None:
    """Zestaw kontrolny jest odtwarzalny, a jego imiona naprawdę leżą poza słownikiem anonimizatora."""
    assert load("poza_slownikiem") == generate_outside()
    slownik = {fold(n) for n in DICTIONARY}
    assert not {fold(n) for n in RARE_FIRST_NAMES} & slownik
