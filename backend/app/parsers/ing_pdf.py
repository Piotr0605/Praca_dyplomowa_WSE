"""Odczyt wyciągu z rachunku ING w formacie PDF.

Układ wyciągu (opis w parsers/README.md): nagłówek z saldami i sumami kontrolnymi oraz tabela
z kolumnami Data, Dane kontrahenta, Tytuł, Szczegóły i Kwota. Wiersze tabeli oddzielają poziome
linie, a transakcja może zaczynać się na jednej stronie i kończyć na następnej.

Tekst PDF nie ma struktury tabeli, dlatego słowa są przypisywane do kolumn według współrzędnych,
a do transakcji według linii oddzielających wiersze.
"""

import datetime as dt
import hashlib
import io
import itertools
import re
from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal

import pdfplumber

from app.models.enums import TransactionKind

BANK = "ING"
DATE_RE = re.compile(r"\d{2}\.\d{2}\.\d{4}")
AMOUNT_RE = re.compile(r"(-?\d{1,3}(?: \d{3})*,\d{2}) PLN")
REFERENCE_RE = re.compile(r"\d{18}")
OPERATION_DATE_RE = re.compile(
    r"(?:Płatność kartą|Zwrot płatności kartą|Płatność BLIK|gotówki BLIK) (\d{2}\.\d{2}\.\d{4})"
)
CARD_NUMBER_RE = re.compile(r"Nr karty \S+")
COUNTERPARTY_LABEL_RE = re.compile(r"Nazwa i adres (?:odbiorcy|płatnika):")
# Najmniejsza długość linii uznawanej za granicę wiersza tabeli (szerokość tabeli to ok. 520 pkt).
ROW_LINE_MIN_WIDTH = 400
AMOUNT_COLUMN_MIN_X = 460


class StatementParseError(Exception):
    """Plik nie jest wyciągiem ING w obsługiwanym formacie."""


@dataclass(frozen=True)
class StatementSummary:
    period_start: dt.date
    period_end: dt.date
    opening_balance: Decimal
    closing_balance: Decimal
    credits_count: int
    credits_sum: Decimal
    debits_count: int
    debits_sum: Decimal


@dataclass(frozen=True)
class ParsedTransaction:
    date: dt.date
    booking_date: dt.date
    amount: Decimal
    currency: str
    description: str
    counterparty: str | None
    kind: TransactionKind
    bank_reference: str

    @property
    def dedup_hash(self) -> str:
        """Numer operacji nadany przez bank jest unikalny, więc dwa takie same zakupy nie są duplikatem."""
        return hashlib.sha256(f"{BANK}:{self.bank_reference}".encode()).hexdigest()


@dataclass(frozen=True)
class ParsedStatement:
    summary: StatementSummary
    transactions: list[ParsedTransaction]


@dataclass
class _Row:
    columns: list[list[tuple[float, float, str]]] = field(
        default_factory=lambda: [[] for _ in range(5)]
    )

    def add(self, column: int, top: float, x0: float, text: str) -> None:
        self.columns[column].append((top, x0, text))

    def text(self, column: int) -> str:
        """Tekst kolumny w kolejności czytania: linie od góry, w linii od lewej."""
        lines: dict[int, list[tuple[float, str]]] = defaultdict(list)
        for top, x0, text in self.columns[column]:
            lines[round(top / 2)].append((x0, text))
        return "\n".join(
            " ".join(t for _, t in sorted(lines[k])) for k in sorted(lines)
        )


def parse_amount(text: str) -> Decimal:
    return Decimal(text.replace(" ", "").replace(",", "."))


def parse_date(text: str) -> dt.date:
    return dt.datetime.strptime(text, "%d.%m.%Y").date()


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def detect_kind(title: str, bank_type: str | None) -> TransactionKind:
    """Rodzaj operacji na podstawie tytułu i kodu operacji z kolumny „Szczegóły”."""
    lowered = title.lower()
    if (
        "przelew smart saver" in lowered
        or "przelew własny" in lowered
        or "wpłata na cel" in lowered
    ):
        return TransactionKind.OWN_TRANSFER
    if "zwrot płatności" in lowered:
        return TransactionKind.REFUND
    if "prowizja" in lowered or lowered.startswith("opł."):
        return TransactionKind.FEE
    if "wypłata gotówki" in lowered or "wpłata gotówki" in lowered:
        return TransactionKind.CASH
    if bank_type == "TR.KART":
        return TransactionKind.CARD
    if bank_type in {"TR.BLIK", "P.BLIK"}:
        return TransactionKind.BLIK
    if bank_type in {"PRZELEW", "PZ", "EXPRESS", "ST.ZLEC"}:
        return TransactionKind.TRANSFER
    return TransactionKind.OTHER


def _table_columns(words: list[dict]) -> list[float] | None:
    """Lewe krawędzie kolumn Dane kontrahenta, Tytuł i Szczegóły oraz granica kolumny kwot.

    Słowa nagłówka muszą leżeć w jednej linii ze słowem „kontrahenta”: na pierwszej stronie
    są też inne „Dane” (np. „Dane posiadacza”), które nie wyznaczają kolumn.
    """
    anchor = next((w for w in words if w["text"] == "kontrahenta"), None)
    if anchor is None:
        return None
    header = {
        w["text"]: w
        for w in words
        if abs(w["top"] - anchor["top"]) < 2
        and w["text"] in {"Dane", "Tytuł", "Szczegóły"}
    }
    if not {"Dane", "Tytuł", "Szczegóły"} <= header.keys():
        return None
    return [
        header["Dane"]["x0"] - 2,
        header["Tytuł"]["x0"] - 2,
        header["Szczegóły"]["x0"] - 2,
        AMOUNT_COLUMN_MIN_X,
    ]


def _column(x0: float, bounds: list[float]) -> int:
    return sum(x0 >= bound for bound in bounds)


def _parse_summary(page: pdfplumber.page.Page) -> StatementSummary:
    text = page.extract_text() or ""
    period = re.search(rf"Nr \d+ / ({DATE_RE.pattern}) - ({DATE_RE.pattern})", text)
    credits = re.search(r"Suma uznań \((\d+)\)", text)
    debits = re.search(r"Suma obciążeń \((\d+)\)", text)
    if not (period and credits and debits):
        raise StatementParseError("Nie znaleziono okresu lub sum kontrolnych wyciągu")

    words = page.extract_words()
    # Lista, a nie słownik: „Saldo końcowe” i „Saldo dostępne” leżą w tym samym wierszu.
    labels = [w for w in words if w["text"] in {"Saldo", "Suma"}]

    def value_below(label: str, row: int) -> Decimal:
        """Kwota pod etykietą: słowa w tej samej kolumnie, do 30 pkt niżej."""
        # Etykiety z pierwszej kolumny o tej nazwie: w tym samym wierszu jest też „Saldo dostępne”.
        same = [w for w in labels if w["text"] == label]
        column_x = min(w["x0"] for w in same)
        anchor = sorted(
            (w for w in same if w["x0"] - column_x < 5), key=lambda w: w["top"]
        )[row]
        column = [
            w
            for w in words
            if abs(w["x0"] - anchor["x0"]) < 120
            and w["x0"] >= anchor["x0"] - 1
            and anchor["top"] < w["top"] < anchor["top"] + 30
        ]
        lines: dict[int, list[dict]] = defaultdict(list)
        for w in column:
            if w["x0"] < anchor["x0"] + 125:
                lines[round(w["top"])].append(w)
        joined = " ".join(
            " ".join(w["text"] for w in sorted(lines[k], key=lambda w: w["x0"]))
            for k in sorted(lines)
        )
        match = AMOUNT_RE.search(joined)
        if not match:
            raise StatementParseError(f"Nie znaleziono kwoty pod etykietą „{label}”")
        return parse_amount(match.group(1))

    return StatementSummary(
        period_start=parse_date(period.group(1)),
        period_end=parse_date(period.group(2)),
        opening_balance=value_below("Saldo", 0),
        closing_balance=value_below("Saldo", 1),
        credits_count=int(credits.group(1)),
        credits_sum=value_below("Suma", 0),
        debits_count=int(debits.group(1)),
        debits_sum=value_below("Suma", 1),
    )


def _page_rows(page: pdfplumber.page.Page) -> list[_Row]:
    words = page.extract_words()
    bounds = _table_columns(words)
    if bounds is None:
        return []
    header_top = min(w["top"] for w in words if w["text"] == "kontrahenta")
    footer_top = min(
        (w["top"] for w in words if w["text"].startswith("Strona:")),
        default=page.height,
    )

    widths: dict[float, float] = defaultdict(float)
    for edge in page.edges:
        if edge["orientation"] == "h":
            widths[round(edge["top"], 1)] += edge["x1"] - edge["x0"]
    lines = sorted(
        y
        for y, width in widths.items()
        if width > ROW_LINE_MIN_WIDTH and header_top < y < footer_top
    )
    if not lines:
        return []
    # Pierwsza linia pod nagłówkiem zamyka nagłówek tabeli; ostatni wiersz może nie mieć linii zamykającej.
    edges = [*lines, footer_top]
    rows = []
    for top, bottom in itertools.pairwise(edges):
        row = _Row()
        for word in _words_from_chars(page.chars, bounds, top, bottom):
            row.add(*word)
        if any(row.columns):
            rows.append(row)
    return rows


def _words_from_chars(
    chars: list[dict], bounds: list[float], top: float, bottom: float
) -> list[tuple[int, float, float, str]]:
    """Słowa (kolumna, y, x, tekst) złożone ze znaków jednego wiersza tabeli.

    Nie korzystamy z `extract_words`: przy dolnej krawędzi strony znaki sąsiednich linii są
    zapisane w pliku naprzemiennie i pdfplumber dzieli wtedy daty i opisy na pojedyncze litery.
    Tutaj znaki są grupowane w linie według współrzędnej y, a słowa rozdzielane według odstępu.
    """
    lines: dict[tuple[int, float], list[dict]] = defaultdict(list)
    for char in chars:
        if top < char["top"] < bottom and char["text"].strip():
            lines[(_column(char["x0"], bounds), round(char["top"], 1))].append(char)

    words = []
    for (column, line_top), line in lines.items():
        line.sort(key=lambda c: c["x0"])
        current = [line[0]]
        for char in line[1:]:
            # Odstęp większy niż ok. 1/5 wysokości znaku oznacza spację między słowami.
            if char["x0"] - current[-1]["x1"] > 0.2 * char["size"]:
                words.append(
                    (
                        column,
                        line_top,
                        current[0]["x0"],
                        "".join(c["text"] for c in current),
                    )
                )
                current = []
            current.append(char)
        words.append(
            (column, line_top, current[0]["x0"], "".join(c["text"] for c in current))
        )
    return words


def _merge_continuations(rows: list[_Row]) -> list[_Row]:
    """Wiersz bez daty w pierwszej kolumnie to dokończenie transakcji z poprzedniej strony."""
    merged: list[_Row] = []
    for row in rows:
        if DATE_RE.search(row.text(0)) or not merged:
            merged.append(row)
            continue
        # Przesunięcie w pionie zachowuje kolejność: dokończenie trafia za dotychczasowy tekst.
        offset = 1_000 + max(
            (top for col in merged[-1].columns for top, _, _ in col), default=0
        )
        for column, items in enumerate(row.columns):
            merged[-1].columns[column].extend(
                (top + offset, x0, t) for top, x0, t in items
            )
    return merged


def _parse_row(row: _Row) -> ParsedTransaction:
    dates = DATE_RE.findall(row.text(0))
    amount = AMOUNT_RE.search(row.text(4).replace("\n", " "))
    details = row.text(3).split()
    reference = next((t for t in details if REFERENCE_RE.fullmatch(t)), None)
    if len(dates) < 2 or amount is None or reference is None:
        raise StatementParseError("Wiersz tabeli bez dat, kwoty lub numeru operacji")
    bank_type = next((t for t in details if not REFERENCE_RE.fullmatch(t)), None)

    title = _clean(row.text(2))
    party = _clean(row.text(1))
    label = COUNTERPARTY_LABEL_RE.search(party)
    counterparty = _clean(party[label.end() :]) if label else None
    operation_date = OPERATION_DATE_RE.search(title)
    # Numer karty nie jest potrzebny do analizy, więc nie trafia do bazy.
    description = (
        _clean(CARD_NUMBER_RE.sub("", title)) or counterparty or bank_type or "Operacja"
    )

    return ParsedTransaction(
        date=parse_date(operation_date.group(1))
        if operation_date
        else parse_date(dates[1]),
        booking_date=parse_date(dates[0]),
        amount=parse_amount(amount.group(1)),
        currency="PLN",
        description=description[:500],
        counterparty=counterparty[:255] if counterparty else None,
        kind=detect_kind(title, bank_type),
        bank_reference=reference,
    )


def parse_ing_pdf(data: bytes) -> ParsedStatement:
    """Odczytuje wyciąg. Nie sprawdza sum kontrolnych: robi to `validate_statement`."""
    if not data.startswith(b"%PDF"):
        raise StatementParseError("Plik nie jest dokumentem PDF")
    try:
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            if not pdf.pages:
                raise StatementParseError("Pusty dokument")
            summary = _parse_summary(pdf.pages[0])
            rows = [row for page in pdf.pages for row in _page_rows(page)]
    except StatementParseError:
        raise
    except Exception as error:  # uszkodzony lub nietypowy PDF
        raise StatementParseError("Nie udało się odczytać pliku PDF") from error
    return ParsedStatement(
        summary, [_parse_row(row) for row in _merge_continuations(rows)]
    )


def validate_statement(statement: ParsedStatement) -> list[str]:
    """Porównuje odczytane transakcje z sumami kontrolnymi wyciągu. Pusta lista oznacza zgodność."""
    s = statement.summary
    credits = [t.amount for t in statement.transactions if t.amount > 0]
    debits = [-t.amount for t in statement.transactions if t.amount < 0]
    problems = []
    if len(credits) != s.credits_count:
        problems.append(
            f"liczba uznań: odczytano {len(credits)}, wyciąg podaje {s.credits_count}"
        )
    if sum(credits, Decimal(0)) != s.credits_sum:
        problems.append(
            f"suma uznań: odczytano {sum(credits, Decimal(0))}, wyciąg podaje {s.credits_sum}"
        )
    if len(debits) != s.debits_count:
        problems.append(
            f"liczba obciążeń: odczytano {len(debits)}, wyciąg podaje {s.debits_count}"
        )
    if sum(debits, Decimal(0)) != s.debits_sum:
        problems.append(
            f"suma obciążeń: odczytano {sum(debits, Decimal(0))}, wyciąg podaje {s.debits_sum}"
        )
    if s.opening_balance + s.credits_sum - s.debits_sum != s.closing_balance:
        problems.append(
            "saldo początkowe + uznania − obciążenia nie daje salda końcowego"
        )
    return problems
