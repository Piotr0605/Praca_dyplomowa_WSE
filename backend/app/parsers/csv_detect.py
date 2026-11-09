"""Rozpoznanie formatu nieznanego pliku CSV: propozycja profilu do potwierdzenia przez użytkownika.

Kolejność: kodowanie → separator → wiersz nagłówka → role kolumn (po nazwach, potem po zawartości)
→ format daty i separator dziesiętny. Wynik to propozycja, a nie pewność: kreator mapowania pokazuje
ją razem z przykładowymi wierszami, a użytkownik ją potwierdza lub poprawia.
"""

import re
from collections import Counter
from dataclasses import dataclass, field

from app.core.text import fold
from app.parsers.csv_generic import (
    HEADER_SEARCH_ROWS,
    CsvFormatError,
    decode,
    find_header,
    parse_amount_text,
    parse_date_text,
    read_rows,
    unique_headers,
)
from app.parsers.csv_profile import DATE_FORMATS, DELIMITERS, CsvProfile

SAMPLE_ROWS = 5
CONTENT_ROWS = 30
POLISH_LETTERS = set("ąćęłńóśźżĄĆĘŁŃÓŚŹŻ")

# Nazwy kolumn spotykane w eksportach banków, od najbardziej do najmniej konkretnej.
SYNONYMS: dict[str, tuple[str, ...]] = {
    "booking_date": (
        "data ksiegowania",
        "data waluty",
        "booking date",
        "value date",
    ),
    "date": (
        "data transakcji",
        "data operacji",
        "data zlecenia",
        "transaction date",
        "data",
        "date",
    ),
    "amount": (
        "kwota transakcji",
        "kwota operacji",
        "kwota",
        "amount",
        "wartosc",
    ),
    "credit": ("uznania", "uznanie", "wplywy", "wplyw", "credit", "przychody"),
    "debit": ("obciazenia", "obciazenie", "wydatki", "wydatek", "debit", "rozchody"),
    "currency": ("waluta", "currency"),
    "counterparty": (
        "dane kontrahenta",
        "kontrahent",
        "nadawca / odbiorca",
        "nadawca/odbiorca",
        "odbiorca/nadawca",
        "nazwa odbiorcy",
        "odbiorca",
        "nadawca",
        "counterparty",
        "payee",
    ),
    "description": (
        "tytul",
        "tytul operacji",
        "opis operacji",
        "opis",
        "title",
        "description",
    ),
    "kind": (
        "typ transakcji",
        "typ operacji",
        "rodzaj operacji",
        "rodzaj",
        "szczegoly",
        "typ",
        "type",
    ),
    "reference": (
        "nr transakcji",
        "numer transakcji",
        "id transakcji",
        "nr referencyjny",
        "identyfikator",
        "reference",
        "transaction id",
    ),
}
# Kolumny, które tylko przypominają kwotę: saldo, blokada, kwota w walucie obcej.
NOT_AMOUNT = ("saldo", "blokad", "w walucie", "balance")
DECIMAL_RE = re.compile(r"([.,])\d{1,2}(?:\s*[A-Za-z]{3})?$")


@dataclass
class Detection:
    encoding: str
    delimiter: str
    header_row: int
    headers: list[str]
    sample_rows: list[list[str]]
    columns: dict[str, str | list[str] | None]
    date_format: str | None
    decimal_separator: str
    missing: list[str] = field(default_factory=list)


def guess_encoding(data: bytes) -> str:
    try:
        data.decode("utf-8-sig")
        return "utf-8-sig"
    except UnicodeDecodeError:
        pass
    # cp1250 i ISO-8859-2 różnią się m.in. kodami „ą”, „ś” i „ź”: wygrywa to, które daje więcej polskich liter.
    scores = {}
    for encoding in ("cp1250", "iso-8859-2"):
        try:
            text = data.decode(encoding)
        except UnicodeDecodeError:
            continue
        scores[encoding] = sum(c in POLISH_LETTERS for c in text) - sum(
            0x80 <= ord(c) < 0xA0 for c in text
        )
    if not scores:
        raise CsvFormatError("Nie rozpoznano kodowania pliku")
    return max(scores, key=lambda e: scores[e])


def guess_delimiter(text: str) -> str:
    """Separator, przy którym najwięcej wierszy ma tę samą liczbę kolumn (większą niż 1)."""
    lines = [line for line in text.splitlines() if line.strip()][:200]
    best, best_score = None, 0
    for delimiter in DELIMITERS:
        counts = Counter(len(row) for row in read_rows("\n".join(lines), delimiter))
        counts.pop(1, None)
        counts.pop(0, None)
        score = counts.most_common(1)[0][1] if counts else 0
        if score > best_score:
            best, best_score = delimiter, score
    if best is None:
        raise CsvFormatError("Nie rozpoznano separatora kolumn")
    return best


def _match(header: str, role: str) -> tuple[int, int] | None:
    """Siła dopasowania nazwy kolumny do roli: (dokładna 3, początek 2, zawiera 1; wcześniejszy synonim)."""
    name = fold(header)
    if role in {"amount", "credit", "debit"} and any(w in name for w in NOT_AMOUNT):
        return None
    best = None
    for position, synonym in enumerate(SYNONYMS[role]):
        if name == synonym:
            strength = 3
        elif name.startswith(synonym):
            strength = 2
        elif synonym in name and len(synonym) > 4:
            strength = 1
        else:
            continue
        candidate = (strength, -position)
        if best is None or candidate > best:
            best = candidate
    return best


def _header_score(row: list[str]) -> int:
    return sum(any(_match(cell, role) for role in SYNONYMS) for cell in row if cell)


def find_header_row(rows: list[list[str]]) -> int:
    scores = [_header_score(row) for row in rows[:HEADER_SEARCH_ROWS]]
    if scores and max(scores) >= 2:
        return scores.index(max(scores))
    # Brak znanych nazw: pierwszy wiersz o typowej dla pliku liczbie kolumn.
    widths = Counter(len(row) for row in rows if len(row) > 1)
    if not widths:
        raise CsvFormatError("Plik nie zawiera tabeli")
    width = widths.most_common(1)[0][0]
    return next(i for i, row in enumerate(rows) if len(row) == width)


def guess_date_format(values: list[str]) -> str | None:
    values = [v for v in values if any(c.isdigit() for c in v)]
    if not values:
        return None
    for date_format in DATE_FORMATS:
        try:
            for value in values:
                parse_date_text(value, date_format)
        except ValueError:
            continue
        return date_format
    return None


def guess_decimal_separator(values: list[str]) -> str:
    """Separator dziesiętny to ostatni znak „,” lub „.” przed jedną lub dwiema cyframi na końcu kwoty."""
    votes: Counter[str] = Counter()
    for value in values:
        if found := DECIMAL_RE.search(value.strip()):
            votes[found.group(1)] += 1
    return "." if votes["."] > votes[","] else ","


def _amounts_parse(values: list[str], separator: str) -> bool:
    """Wszystkie wartości to kwoty, a co najmniej połowa ma część dziesiętną (numer konta jej nie ma)."""
    filled = [v for v in values if v]
    if not filled or 2 * sum(bool(DECIMAL_RE.search(v)) for v in filled) < len(filled):
        return False
    try:
        for value in filled:
            parse_amount_text(value, separator)
    except ValueError:
        return False
    return True


def _is_date(value: str, date_format: str) -> bool:
    try:
        parse_date_text(value, date_format)
    except ValueError:
        return False
    return True


def _column_values(rows: list[list[str]], position: int) -> list[str]:
    return [row[position] if position < len(row) else "" for row in rows]


def guess_columns(
    headers: list[str], rows: list[list[str]]
) -> tuple[dict[str, str | list[str] | None], str | None, str]:
    """Role kolumn, format daty i separator dziesiętny."""
    candidates = sorted(
        (
            (score, role_order, role, position)
            for position, header in enumerate(headers)
            for role_order, role in enumerate(SYNONYMS)
            if (score := _match(header, role))
        ),
        key=lambda c: (c[0], -c[1]),
        reverse=True,
    )
    assigned: dict[str, int] = {}
    used: set[int] = set()
    for _, _, role, position in candidates:
        if role not in assigned and position not in used:
            assigned[role] = position
            used.add(position)

    values = {p: _column_values(rows, p) for p in range(len(headers))}
    # Zawartość weryfikuje nazwy: kolumna „Data” bez dat nie jest datą.
    date_format = None
    if "date" in assigned:
        date_format = guess_date_format(values[assigned["date"]])
        if date_format is None:
            used.discard(assigned.pop("date"))
    if "date" not in assigned:
        for position in range(len(headers)):
            if position not in used and (found := guess_date_format(values[position])):
                assigned["date"], date_format = position, found
                used.add(position)
                break

    if date_format is not None:
        # Dalej liczą się tylko wiersze transakcji: stopka pod tabelą nie ma daty w kolumnie daty.
        rows = [
            row
            for row, value in zip(rows, values[assigned["date"]], strict=True)
            if _is_date(value, date_format)
        ]
        values = {p: _column_values(rows, p) for p in range(len(headers))}

    money_roles = [r for r in ("amount", "credit", "debit") if r in assigned]
    separator = guess_decimal_separator(
        [v for r in money_roles for v in values[assigned[r]] if v]
    )
    for role in money_roles:
        if not _amounts_parse(values[assigned[role]], separator):
            used.discard(assigned.pop(role))
    if "amount" in assigned:
        for role in ("credit", "debit"):
            if role in assigned:
                used.discard(assigned.pop(role))
    elif not ("credit" in assigned and "debit" in assigned):
        for role in ("credit", "debit"):
            if role in assigned:
                used.discard(assigned.pop(role))
        # Bez znanej nazwy: najczęściej wypełniona kolumna z kwotami.
        found = [
            (sum(map(bool, values[p])), p, guess_decimal_separator(values[p]))
            for p in range(len(headers))
            if p not in used
        ]
        found = [f for f in found if f[0] and _amounts_parse(values[f[1]], f[2])]
        if found:
            _, position, separator = max(found, key=lambda f: (f[0], -f[1]))
            assigned["amount"] = position
            used.add(position)

    if "description" not in assigned:
        # Najdłuższe teksty w kolumnie, której nie przypisano innej roli.
        texts = [
            (sum(map(len, values[p])), p)
            for p in range(len(headers))
            if p not in used and any(values[p])
        ]
        if texts:
            assigned["description"] = max(texts)[1]

    columns: dict[str, str | list[str] | None] = {
        role: headers[assigned[role]] if role in assigned else None
        for role in SYNONYMS
        if role != "description"
    }
    columns["description"] = (
        [headers[assigned["description"]]] if "description" in assigned else []
    )
    return columns, date_format, separator


def detect(
    data: bytes, *, encoding: str | None = None, delimiter: str | None = None
) -> Detection:
    encoding = encoding or guess_encoding(data)
    text = decode(data, encoding)
    delimiter = delimiter or guess_delimiter(text)
    rows = read_rows(text, delimiter)
    header_row = find_header_row(rows)
    headers = unique_headers(rows[header_row])
    data_rows = [
        row for row in rows[header_row + 1 :] if sum(1 for cell in row if cell) >= 2
    ][:CONTENT_ROWS]
    columns, date_format, separator = guess_columns(headers, data_rows)
    missing = [
        role
        for role, ok in (
            ("date", columns["date"]),
            ("date_format", date_format),
            ("amount", columns["amount"] or (columns["credit"] and columns["debit"])),
            ("description", columns["description"]),
        )
        if not ok
    ]
    return Detection(
        encoding=encoding,
        delimiter=delimiter,
        header_row=header_row,
        headers=headers,
        sample_rows=[row[: len(headers)] for row in data_rows[:SAMPLE_ROWS]],
        columns=columns,
        date_format=date_format,
        decimal_separator=separator,
        missing=missing,
    )


def profile_matches(data: bytes, profile: CsvProfile) -> bool:
    """Czy plik ma kodowanie, separator i kolumny opisane w profilu."""
    try:
        rows = read_rows(decode(data, profile.encoding), profile.delimiter)
    except CsvFormatError:
        return False
    return find_header(rows, profile.columns.names()) is not None
