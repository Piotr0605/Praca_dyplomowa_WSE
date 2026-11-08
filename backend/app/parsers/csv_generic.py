"""Odczyt pliku CSV z banku według profilu (`csv_profile.CsvProfile`).

Plik CSV nie zawiera sum kontrolnych jak wyciąg PDF, dlatego każdy wiersz z datą operacji musi dać się
odczytać w całości. Wiersz z błędną datą lub kwotą zatrzymuje import zamiast zostać po cichu pominięty.
Pomijane są tylko wiersze bez daty (metadane i stopka pod tabelą) oraz bez kwoty (np. blokady kartowe).
"""

import csv
import datetime as dt
import hashlib
import io
import re
from collections import Counter
from dataclasses import dataclass, replace
from decimal import Decimal

from app.models.enums import TransactionKind
from app.parsers.common import CARD_NUMBER_RE, clean, normalize_description
from app.parsers.csv_profile import CsvProfile
from app.parsers.ing_pdf import detect_kind

HEADER_SEARCH_ROWS = 50
MAX_ERRORS = 5
MAX_AMOUNT = Decimal(10) ** 10  # NUMERIC(12, 2)
AMOUNT_RE = re.compile(r"[+-]?\d+(?:\.\d{1,2})?")
CURRENCY_RE = re.compile(r"[A-Z]{3}")
TRAILING_CURRENCY_RE = re.compile(r"(?<=\d)\s*[A-Za-z]{3}$")


class CsvFormatError(Exception):
    """Plik nie pasuje do profilu albo zawiera wiersze, których nie da się odczytać."""


@dataclass(frozen=True)
class CsvTransaction:
    date: dt.date
    booking_date: dt.date | None
    amount: Decimal
    currency: str
    description: str
    counterparty: str | None
    kind: TransactionKind
    dedup_hash: str


@dataclass(frozen=True)
class CsvStatement:
    transactions: list[CsvTransaction]
    # Wiersze z datą, ale bez kwoty: blokady kartowe i operacje informacyjne.
    skipped: int


def decode(data: bytes, encoding: str) -> str:
    try:
        return data.decode(encoding)
    except UnicodeDecodeError as error:
        raise CsvFormatError(
            f"Plik nie jest zapisany w kodowaniu {encoding}"
        ) from error


def read_rows(text: str, delimiter: str) -> list[list[str]]:
    try:
        return [
            [cell.strip() for cell in row]
            for row in csv.reader(io.StringIO(text), delimiter=delimiter)
        ]
    except csv.Error as error:
        raise CsvFormatError(f"Nieprawidłowy plik CSV: {error}") from error


def unique_headers(row: list[str]) -> list[str]:
    """Nazwy kolumn bez powtórzeń: druga „Waluta” to „Waluta (2)”, pusta nazwa to „Kolumna 5”."""
    seen: Counter[str] = Counter()
    headers = []
    for index, cell in enumerate(row, start=1):
        name = clean(cell) or f"Kolumna {index}"
        seen[name] += 1
        headers.append(name if seen[name] == 1 else f"{name} ({seen[name]})")
    return headers


def find_header(rows: list[list[str]], required: list[str]) -> int | None:
    """Pierwszy wiersz zawierający wszystkie kolumny wymagane przez profil."""
    for index, row in enumerate(rows[:HEADER_SEARCH_ROWS]):
        if set(required) <= set(unique_headers(row)):
            return index
    return None


def parse_amount_text(text: str, decimal_separator: str) -> Decimal | None:
    """Kwota w zapisie banku, np. `-1 403,86`, `1.403,86 PLN`, `-1403.86`. Pusta komórka: None."""
    value = TRAILING_CURRENCY_RE.sub("", text.replace("\xa0", " ")).replace(" ", "")
    if not value:
        return None
    thousands = "." if decimal_separator == "," else ","
    value = value.replace(thousands, "").replace(decimal_separator, ".")
    if not AMOUNT_RE.fullmatch(value):
        raise ValueError(text)
    return Decimal(value)


def parse_date_text(text: str, date_format: str) -> dt.date:
    """Data z komórki; pomija ewentualną godzinę zapisaną po spacji."""
    parts = text.split()
    if not parts:
        raise ValueError("pusta data")
    return dt.datetime.strptime(parts[0], date_format).date()


def guess_kind(description: str, kind_text: str | None) -> TransactionKind:
    """Rodzaj operacji: najpierw reguły ING, potem słowa kluczowe używane przez inne banki."""
    kind = detect_kind(description, kind_text)
    if kind is not TransactionKind.OTHER:
        return kind
    lowered = f"{kind_text or ''} {description}".lower()
    for words, found in (
        (("prowizj", "opłat"), TransactionKind.FEE),
        (("bankomat", "gotówk"), TransactionKind.CASH),
        (("blik",), TransactionKind.BLIK),
        (("kart",), TransactionKind.CARD),
        (("przelew",), TransactionKind.TRANSFER),
    ):
        if any(word in lowered for word in words):
            return found
    return TransactionKind.OTHER


class _Row:
    def __init__(self, cells: list[str], index: dict[str, int]) -> None:
        self.cells = cells
        self.index = index

    def get(self, name: str | None) -> str:
        if name is None:
            return ""
        position = self.index[name]
        return self.cells[position] if position < len(self.cells) else ""


def _amount(row: _Row, profile: CsvProfile) -> Decimal | None:
    columns, separator = profile.columns, profile.decimal_separator
    if columns.amount is not None:
        return parse_amount_text(row.get(columns.amount), separator)
    credit = parse_amount_text(row.get(columns.credit), separator)
    debit = parse_amount_text(row.get(columns.debit), separator)
    if credit and debit:
        raise ValueError("kwota jednocześnie w uznaniach i obciążeniach")
    if credit:
        return abs(credit)
    if debit:
        return -abs(debit)
    return None


def _parse_row(
    row: _Row, profile: CsvProfile
) -> tuple[CsvTransaction, str, bool] | None:
    """Transakcja, klucz duplikatów i czy klucz wymaga numeru kolejnego; None dla wiersza bez kwoty."""
    columns = profile.columns
    date_text = row.get(columns.date)
    try:
        date = parse_date_text(date_text, profile.date_format)
    except ValueError:
        raise ValueError(f"data „{date_text}” nie pasuje do formatu") from None
    booking_text = row.get(columns.booking_date)
    try:
        booking_date = (
            parse_date_text(booking_text, profile.date_format) if booking_text else None
        )
    except ValueError:
        raise ValueError(
            f"data księgowania „{booking_text}” nie pasuje do formatu"
        ) from None
    try:
        amount = _amount(row, profile)
    except ValueError as error:
        raise ValueError(f"nie rozpoznano kwoty ({error})") from None
    if not amount:
        return None
    if abs(amount) >= MAX_AMOUNT:
        raise ValueError("kwota jest za duża")

    currency = row.get(columns.currency).upper() or profile.default_currency
    if not CURRENCY_RE.fullmatch(currency):
        raise ValueError(f"waluta „{currency}” nie jest kodem ISO, np. PLN")
    counterparty = clean(row.get(columns.counterparty))[:255] or None
    kind_text = clean(row.get(columns.kind)) or None
    title = clean(" ".join(row.get(name) for name in columns.description))
    description = (
        clean(CARD_NUMBER_RE.sub("", title)) or counterparty or kind_text or "Operacja"
    )[:500]
    reference = re.sub(r"[\s'\"]", "", row.get(columns.reference))

    if reference:
        namespace = profile.reference_namespace or profile.bank_name
        key = f"{namespace}:{reference}"
    else:
        # Bez numeru operacji: data, kwota, waluta, opis i kontrahent. Numer kolejny dopisuje
        # `parse_csv`, żeby dwa identyczne zakupy tego samego dnia nie były uznane za duplikat.
        key = "|".join(
            [
                "CSV",
                date.isoformat(),
                str(amount),
                currency,
                normalize_description(description),
                (counterparty or "").lower(),
            ]
        )
    transaction = CsvTransaction(
        date=date,
        booking_date=booking_date,
        amount=amount,
        currency=currency,
        description=description,
        counterparty=counterparty,
        kind=guess_kind(title, kind_text),
        dedup_hash="",
    )
    return transaction, key, not reference


def parse_csv(data: bytes, profile: CsvProfile) -> CsvStatement:
    rows = read_rows(decode(data, profile.encoding), profile.delimiter)
    required = profile.columns.names()
    header = find_header(rows, required)
    if header is None:
        raise CsvFormatError(
            f"Plik nie pasuje do profilu „{profile.bank_name}”: brak wiersza nagłówka z kolumnami "
            + ", ".join(f"„{name}”" for name in required)
        )
    index = {name: i for i, name in enumerate(unique_headers(rows[header]))}

    transactions: list[CsvTransaction] = []
    errors: list[str] = []
    skipped = 0
    occurrences: Counter[str] = Counter()
    for line, cells in enumerate(rows[header + 1 :], start=header + 2):
        row = _Row(cells, index)
        # Wiersz bez cyfr w kolumnie daty to metadane albo stopka, a nie transakcja.
        if not any(char.isdigit() for char in row.get(profile.columns.date)):
            continue
        try:
            parsed = _parse_row(row, profile)
        except ValueError as error:
            errors.append(f"wiersz {line}: {error}")
            if len(errors) == MAX_ERRORS:
                break
            continue
        if parsed is None:
            skipped += 1
            continue
        transaction, key, numbered = parsed
        if numbered:
            occurrences[key] += 1
            key = f"{key}|{occurrences[key]}"
        transactions.append(
            replace(transaction, dedup_hash=hashlib.sha256(key.encode()).hexdigest())
        )
    if errors:
        raise CsvFormatError("Nie udało się odczytać pliku: " + "; ".join(errors))
    if not transactions:
        raise CsvFormatError("Plik nie zawiera żadnej transakcji")
    return CsvStatement(transactions, skipped)
