"""Anonimizacja tekstów, które mogłyby trafić do modelu językowego (badanie P3, docs/BADANIA.md).

Czysta funkcja `anonymize(text)` zwraca tekst z danymi osobowymi zastąpionymi znacznikami („[OSOBA]”,
„[IBAN]” …) oraz listę zamaskowanych fragmentów z typem i położeniem w tekście wejściowym. Lista służy
do pomiaru czułości i precyzji; oryginalnych wartości funkcja nie zwraca.

Wykrywanie:
- dane o stałym formacie (wyrażenia regularne): IBAN/NRB, numer karty (pełny z sumą kontrolną Luhna albo
  zamaskowany jak w wyciągach ING), telefon, e-mail, PESEL (z sumą kontrolną i poprawną datą, a po słowie
  „PESEL” zawsze);
- adres: ulica z numerem („ul.”, „al.”, „os.”, „pl.”) oraz kod pocztowy z miastem;
- imiona i nazwiska: imię ze słownika (`app/ai/names.py`) razem z sąsiednim nazwiskiem; osoby spoza
  słownika z kontekstu: po „Dla”/„Od”, po numerze rachunku albo przed adresem. Nazwy firm są chronione:
  imię tuż po słowie typu „SALON”, „PIEKARNIA” albo w nazwie ze „SP. Z O.O.” nie jest maskowane.

Znak „|” rozdziela niezależne pola (np. tytuł i nazwę kontrahenta).
"""

import re
from dataclasses import dataclass

from app.ai.names import FIRST_NAMES
from app.core.text import fold

PLACEHOLDERS = {
    "IBAN": "[IBAN]",
    "KARTA": "[KARTA]",
    "TELEFON": "[TELEFON]",
    "EMAIL": "[EMAIL]",
    "PESEL": "[PESEL]",
    "ADRES": "[ADRES]",
    "OSOBA": "[OSOBA]",
}

_FOLDED_NAMES = frozenset(fold(n) for n in FIRST_NAMES)


def _folded(words: str) -> frozenset[str]:
    return frozenset(fold(w) for w in words.split())


# Słowa, po których (albo przed którymi) imię jest częścią nazwy firmy, a nie osobą.
BUSINESS_WORDS = _folded(
    """
    sp spółka spolka s.a sa z o.o oo sp.k firma sklep salon studio hotel apteka dr kwiaciarnia piekarnia
    cukiernia kawiarnia restauracja pizzeria bar bistro zakład zaklad fryzjerski kosmetyczny kancelaria
    przedszkole szkoła szkola językowa jezykowa spółdzielnia spoldzielnia wspólnota wspolnota mieszkaniowa
    burgers premium market centrum gabinet klinika pracownia warsztat serwis hurtownia drogeria
    urząd urzad skarbowy gmina miasto bank towarzystwo fundacja stowarzyszenie parafia poczta polska
    zakład ubezpieczeń ubezpieczen społecznych spolecznych obrót obrot sprzedaż sprzedaz
    """
)
# Słowa, które kończą albo przerywają nazwę osoby.
STOP_WORDS = _folded(
    """
    dla od do za i w na z ze ul al os pl nr tel kontakt pesel przelew płatność platnosc kartą karta blik
    zwrot czynsz prezent składka skladka obiad zakupy opłata oplata faktura wynagrodzenie podatek kaucji
    spłata splata pożyczki pozyczki kieszonkowe korepetycje bilety środków srodkow własny wlasny wpłata
    wplata cel smart saver
    """
)


@dataclass(frozen=True)
class Masked:
    start: int
    end: int
    type: str


@dataclass(frozen=True)
class Anonymized:
    text: str
    spans: list[Masked]


EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
IBAN_RE = re.compile(r"(?<![\w])(?:PL ?)?\d{2}(?: ?\d{4}){6}(?!\d)", re.IGNORECASE)
CARD_MASKED_RE = re.compile(r"(?<!\w)\d{4,6}[xX*]{2,8}\d{4}(?!\w)")
CARD_FULL_RE = re.compile(r"(?<![\w])\d{4}(?:[ -]?\d{4}){3}(?!\d)")
PHONE_RE = re.compile(
    r"(?<![\w+])(?:\+48[ -]?|0048[ -]?)?(?=[\dx]{3}[ -]?[\dx]{3}[ -]?[\dx]{3}(?![\dx]))"
    r"(?:[\dx]{3}[ -]?){2}[\dx]{3}(?!\w)",
    re.IGNORECASE,
)
PESEL_RE = re.compile(r"(?<![\w])\d{11}(?!\d)")
PESEL_CONTEXT_RE = re.compile(r"pesel\W{0,3}(\d{11})(?!\d)", re.IGNORECASE)
STREET_RE = re.compile(
    r"(?<!\w)(?i:ul|al|os|pl)\.\s?(?:\d+\s)?(?:[^\W\d_][\w.-]*\s){1,4}\d+[a-zA-Z]?(?:/\d+[a-zA-Z]?)?(?!\w)"
)
POSTAL_RE = re.compile(r"(?<![\w-])\d{2}-\d{3}(?!\d)(?:\s+[^\W\d_][\w-]*)?")
WORD_RE = re.compile(r"[^\W\d_]+(?:[-.][^\W\d_]+)*\.?")


def luhn_valid(digits: str) -> bool:
    total = 0
    for i, d in enumerate(int(c) for c in reversed(digits)):
        if i % 2:
            d = d * 2 - 9 if d * 2 > 9 else d * 2
        total += d
    return total % 10 == 0


def pesel_valid(digits: str) -> bool:
    weights = (1, 3, 7, 9, 1, 3, 7, 9, 1, 3)
    check = (
        10 - sum(int(d) * w for d, w in zip(digits, weights, strict=False)) % 10
    ) % 10
    month, day = int(digits[2:4]) % 20, int(digits[4:6])
    return check == int(digits[10]) and 1 <= month <= 12 and 1 <= day <= 31


def _fixed_format(text: str) -> list[Masked]:
    found = [Masked(m.start(), m.end(), "EMAIL") for m in EMAIL_RE.finditer(text)]
    found += [Masked(m.start(), m.end(), "IBAN") for m in IBAN_RE.finditer(text)]
    found += [
        Masked(m.start(), m.end(), "KARTA") for m in CARD_MASKED_RE.finditer(text)
    ]
    found += [
        Masked(m.start(), m.end(), "KARTA")
        for m in CARD_FULL_RE.finditer(text)
        if luhn_valid(re.sub(r"\D", "", m.group()))
    ]
    found += [
        Masked(m.start(1), m.end(1), "PESEL") for m in PESEL_CONTEXT_RE.finditer(text)
    ]
    found += [
        Masked(m.start(), m.end(), "PESEL")
        for m in PESEL_RE.finditer(text)
        if pesel_valid(m.group())
    ]
    found += [
        Masked(m.start(), m.end(), "TELEFON")
        for m in PHONE_RE.finditer(text)
        if sum(c.isdigit() for c in m.group()) >= 3
    ]
    found += [Masked(m.start(), m.end(), "ADRES") for m in STREET_RE.finditer(text)]
    found += [Masked(m.start(), m.end(), "ADRES") for m in POSTAL_RE.finditer(text)]
    return found


@dataclass(frozen=True)
class _Word:
    start: int
    end: int
    raw: str

    @property
    def key(self) -> str:
        return fold(self.raw.rstrip("."))

    @property
    def is_name(self) -> bool:
        return self.key in _FOLDED_NAMES

    @property
    def is_stop(self) -> bool:
        return self.key in STOP_WORDS

    @property
    def is_business(self) -> bool:
        return self.key in BUSINESS_WORDS or any(
            part in BUSINESS_WORDS for part in re.split(r"[.\-]", self.key) if part
        )

    @property
    def style(self) -> str:
        """Zapis słowa; wielka litera w środku („PayU”) to „mixed”, a części po łączniku liczą się osobno."""
        parts = [[c for c in p if c.isalpha()] for p in re.split(r"[-.]", self.raw)]
        parts = [p for p in parts if p]
        if all(c.isupper() for p in parts for c in p):
            return "upper"
        if all(c.islower() for p in parts for c in p):
            return "lower"
        if all(p[0].isupper() and all(c.islower() for c in p[1:]) for p in parts):
            return "title"
        return "mixed"


def _segments(text: str) -> list[list[_Word]]:
    """Słowa w każdym polu tekstu; liczby i znaki przerywają ciąg słów (None)."""
    segments = []
    for part in re.finditer(r"[^|]+", text):
        words: list = []
        position = part.start()
        for m in WORD_RE.finditer(part.group()):
            gap = part.group()[position - part.start() : m.start()]
            if words and re.search(r"[^\s]", gap):
                words.append(None)
            words.append(
                _Word(part.start() + m.start(), part.start() + m.end(), m.group())
            )
            position = part.start() + m.end()
        segments.append(words)
    return segments


def _is_surname(word: _Word | None, name: _Word) -> bool:
    return (
        word is not None
        and not word.is_stop
        and not word.is_business
        and len(word.key) > 1
        and (
            word.style == name.style
            or (name.style == "title" and word.style == "upper")
        )
    )


def _business_near(words: list, index: int) -> bool:
    neighbours = words[max(0, index - 2) : index] + words[index + 1 : index + 3]
    return any(w is not None and w.is_business for w in neighbours)


def _people(text: str, fixed: list[Masked]) -> list[Masked]:
    found: list[Masked] = []
    for words in _segments(text):
        segment_business = any(w is not None and w.is_business for w in words)
        i = 0
        while i < len(words):
            word = words[i]
            if word is None:
                i += 1
                continue
            start, end = i, i
            if word.is_name and not _business_near(words, i):
                if i + 1 < len(words) and _is_surname(words[i + 1], word):
                    end = i + 1
                elif (
                    i > 0
                    and _is_surname(words[i - 1], word)
                    and words[i - 1].key not in _FOLDED_NAMES
                ):
                    start = i - 1
            elif _context_person(text, words, i, fixed) and not segment_business:
                end = i
                while (
                    end + 1 < len(words)
                    and end - i < 2
                    and _is_surname(words[end + 1], word)
                ):
                    end += 1
            else:
                i += 1
                continue
            found.append(Masked(words[start].start, words[end].end, "OSOBA"))
            i = end + 1
    return found


def _context_person(text: str, words: list, i: int, fixed: list[Masked]) -> bool:
    """Słowo spoza słownika jest osobą, gdy stoi po „Dla”/„Od” albo po numerze rachunku."""
    word = words[i]
    if word.is_stop or word.is_business or word.style == "mixed":
        return False
    previous = words[i - 1] if i > 0 else None
    if previous is not None and previous.key in {"dla", "od"}:
        return word.style != "lower"
    before = text[: word.start].rstrip()
    return any(m.type == "IBAN" and m.end == len(before) for m in fixed)


# Typowe końcówki polskich i ukraińskich nazwisk.
SURNAME_ENDINGS = (
    "ski", "ska", "cki", "cka", "dzki", "dzka", "wicz", "czyk", "czak", "ak", "ek", "uk", "yk", "enko",
)  # fmt: skip


def _name_like(word: _Word | None) -> bool:
    return (
        word is not None
        and not word.is_stop
        and not word.is_business
        and word.style != "mixed"
        and len(word.key) > 1
        and "." not in word.raw
    )


def _has_surname_ending(word: _Word) -> bool:
    key = word.key.split("-")[0]
    return len(key) >= 5 and key.endswith(SURNAME_ENDINGS)


def _context_rules(text: str, fixed: list[Masked]) -> list[Masked]:
    """Osoby spoza słownika imion: nazwisko z typową końcówką obok drugiego słowa, słowa tuż przed
    adresem i nazwa kontaktu przy przelewie na telefon."""
    found: list[Masked] = []
    addresses = [m.start for m in fixed if m.type == "ADRES"]
    folded = fold(text)
    phone_transfer = "przelew na telefon" in folded
    # Przy płatności kartą albo BLIK przed adresem stoi sklep, a nie osoba.
    payment = "platnosc" in folded
    for index, words in enumerate(_segments(text)):
        if any(w is not None and w.is_business for w in words):
            continue
        for i, word in enumerate(words):
            if not _name_like(word):
                continue
            # Nazwisko z typową końcówką obok słowa zapisanego tak samo (imię przed albo po).
            if _has_surname_ending(word):
                for j in (i - 1, i + 1):
                    if (
                        0 <= j < len(words)
                        and _name_like(words[j])
                        and words[j].style == word.style
                    ):
                        a, b = sorted((word, words[j]), key=lambda w: w.start)
                        found.append(Masked(a.start, b.end, "OSOBA"))
            # Jedno do trzech słów tuż przed adresem.
            following = text[word.end :]
            if not payment and any(
                word.end + len(following) - len(following.lstrip()) == a
                for a in addresses
            ):
                first = i
                while first > 0 and i - first < 2 and _name_like(words[first - 1]):
                    first -= 1
                found.append(Masked(words[first].start, word.end, "OSOBA"))
        # Przy przelewie na telefon pole kontrahenta (po „|”) to nazwa kontaktu.
        names = [w for w in words if w is not None]
        if (
            phone_transfer
            and index > 0
            and 0 < len(names) <= 3
            and all(map(_name_like, names))
        ):
            found.append(Masked(names[0].start, names[-1].end, "OSOBA"))
    return found


def _merge(spans: list[Masked]) -> list[Masked]:
    """Nakładające się fragmenty łączy w jeden; typ bierze z dłuższego."""
    result: list[Masked] = []
    for span in sorted(spans, key=lambda s: (s.start, -(s.end - s.start))):
        if result and span.start < result[-1].end:
            last = result[-1]
            longer = last if last.end - last.start >= span.end - span.start else span
            result[-1] = Masked(last.start, max(last.end, span.end), longer.type)
        else:
            result.append(span)
    return result


def anonymize(text: str) -> Anonymized:
    fixed = _fixed_format(text)
    spans = _merge(fixed + _people(text, fixed) + _context_rules(text, fixed))
    parts, position = [], 0
    for span in spans:
        parts += [text[position : span.start], PLACEHOLDERS[span.type]]
        position = span.end
    parts.append(text[position:])
    return Anonymized("".join(parts), spans)
