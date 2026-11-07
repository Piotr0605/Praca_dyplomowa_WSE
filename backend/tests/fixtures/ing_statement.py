"""Generator sztucznego wyciągu ING w PDF, o tym samym układzie co prawdziwy.

Wszystkie dane są zmyślone. Układ (pozycje kolumn, linie oddzielające wiersze, nagłówek z sumami,
transakcja dzielona między strony) odpowiada wyciągom opisanym w app/parsers/README.md.

Użycie poza testami: python -m tests.fixtures.ing_statement plik.pdf
"""

import io
import sys
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

FONT_DIRS = [
    Path("/usr/share/fonts/truetype/dejavu"),
    Path("/Library/Fonts"),
    Path.home() / "Library/Fonts",
]
WIDTH, HEIGHT = 595, 842
COLUMNS = {"date": 40, "party": 117, "title": 238, "details": 354, "amount_right": 554}
LINE_HEIGHT = 9.4
FOOTER_TOP = 800


def _register_fonts() -> None:
    if "Sans" in pdfmetrics.getRegisteredFontNames():
        return
    for directory in FONT_DIRS:
        regular, bold = directory / "DejaVuSans.ttf", directory / "DejaVuSans-Bold.ttf"
        if regular.exists() and bold.exists():
            pdfmetrics.registerFont(TTFont("Sans", str(regular)))
            pdfmetrics.registerFont(TTFont("Sans-Bold", str(bold)))
            return
    raise RuntimeError("Brak czcionki DejaVuSans (pakiet fonts-dejavu-core)")


@dataclass
class FakeTransaction:
    booking: str
    date: str
    amount: Decimal
    title: list[str]
    party: list[str] = field(default_factory=list)
    code: str | None = None
    reference: str = ""


def amount_text(amount: Decimal) -> str:
    sign = "-" if amount < 0 else ""
    whole, fraction = f"{abs(amount):.2f}".split(".")
    groups = f"{int(whole):,}".replace(",", " ")
    return f"{sign}{groups},{fraction} PLN"


def sample_transactions() -> list[FakeTransaction]:
    """Przypadki szczególne z prawdziwych wyciągów, na zmyślonych danych."""
    card = [
        "10500031-1915031/19730",
        "Nazwa i adres odbiorcy: SKLEP TESTOWY",
        "WARSZAWA",
    ]
    saver = [
        "11 2222 3333 4444 5555 6666 7777",
        "Nazwa i adres odbiorcy: JAN TESTOWY",
        "ul. Przykładowa 1",
    ]
    rows = [
        FakeTransaction(
            "01.10.2026",
            "01.10.2026",
            Decimal("-45.99"),
            ["Płatność kartą 29.09.2026", "Nr karty 1234xx5678"],
            card,
            "TR.KART",
        ),
        FakeTransaction(
            "01.10.2026",
            "01.10.2026",
            Decimal("-4.60"),
            ["przelew Smart Saver", "Płatność kartą 29.09.2026", "Kwota: 45,99 PLN"],
            saver,
        ),
        FakeTransaction(
            "02.10.2026",
            "02.10.2026",
            Decimal("-1403.86"),
            ["Płatność BLIK 02.10.2026", "Nr transakcji 12345678901", "sklep.example"],
            [
                "79 1050 0028 1000 0024 1009 3963",
                "Nazwa i adres odbiorcy: PayU",
                "ul. Testowa 2 Poznań",
            ],
            "TR.BLIK",
        ),
        FakeTransaction(
            "03.10.2026",
            "03.10.2026",
            Decimal("5120.00"),
            ["Wynagrodzenie wrzesień"],
            [
                "21 1090 2590 0000 0001 6154 5165",
                "Nazwa i adres płatnika: FIRMA TESTOWA",
                "SPÓŁKA Z O.O.",
                "ul. Fabryczna 3 Białystok",
            ],
            "PRZELEW",
        ),
        FakeTransaction(
            "04.10.2026",
            "04.10.2026",
            Decimal("-106.41"),
            ["Płatność kartą 02.10.2026", "25,00 EUR", "Nr karty 1234xx5678"],
            ["10500031-1915031/19730", "Nazwa i adres odbiorcy: SERWIS ONLINE"],
            "TR.KART",
        ),
        FakeTransaction(
            "04.10.2026",
            "04.10.2026",
            Decimal("-3.19"),
            [
                "Prowizja za przewalutowanie",
                "Płatność kartą 02.10.2026",
                "Nr karty 1234xx5678",
            ],
            ["10501823-8042562/11021", "Nazwa i adres odbiorcy: SERWIS ONLINE"],
            "TR.KART",
        ),
        FakeTransaction(
            "05.10.2026",
            "05.10.2026",
            Decimal("113.98"),
            ["Zwrot płatności kartą 03.10.2026", "Nr karty 1234xx5678"],
            ["10500031-1915031/19730", "Nazwa i adres płatnika: Restauracja Testowa"],
            "TR.KART",
        ),
        FakeTransaction(
            "06.10.2026",
            "06.10.2026",
            Decimal("-500.00"),
            ["Przelew własny"],
            ["99 1111 2222 3333 4444 5555 6666", "Nazwa i adres odbiorcy: JAN TESTOWY"],
            "PRZELEW",
        ),
        FakeTransaction(
            "07.10.2026",
            "07.10.2026",
            Decimal("2000.00"),
            ["Wpłata gotówki BLIK 07.10.2026", "Nr transakcji 98765432101"],
            [
                "79 1050 0028 1000 0024 1009 3963",
                "Nazwa i adres płatnika: ul. Testowa 9",
            ],
            "TR.BLIK",
        ),
        FakeTransaction(
            "08.10.2026",
            "08.10.2026",
            Decimal("-50.00"),
            [
                "Przelew na telefon +48xxxxxx123",
                "Przelew na telefon",
                "Dla Anna",
                "Od JAN TESTOWY",
            ],
            ["12 3456 7890 1234 5678 9012 3456", "Nazwa i adres odbiorcy: Anna"],
            "P.BLIK",
        ),
    ]
    # Dopełnienie zwykłymi płatnościami, żeby tabela zajęła więcej niż jedną stronę.
    for day in range(9, 24):
        rows.append(
            FakeTransaction(
                f"{day:02d}.10.2026",
                f"{day:02d}.10.2026",
                Decimal(f"-{day}.25"),
                [f"Płatność kartą {day - 2:02d}.10.2026", "Nr karty 1234xx5678"],
                [
                    "10500031-1915031/19730",
                    f"Nazwa i adres odbiorcy: SKLEP NR {day}",
                    "BIAŁYSTOK",
                ],
                "TR.KART",
            )
        )
    for index, row in enumerate(rows):
        row.reference = f"2026{index:014d}"
    return rows


class _Writer:
    def __init__(self, pages_estimate: int) -> None:
        self.buffer = io.BytesIO()
        self.canvas = canvas.Canvas(self.buffer, pagesize=(WIDTH, HEIGHT))
        self.page = 1
        self.pages_estimate = pages_estimate

    def text(
        self,
        x: float,
        top: float,
        value: str,
        size: float = 7,
        bold: bool = False,
        right: bool = False,
    ) -> None:
        font = "Sans-Bold" if bold else "Sans"
        self.canvas.setFont(font, size)
        y = HEIGHT - top - size
        if right:
            self.canvas.drawRightString(x, y, value)
        else:
            self.canvas.drawString(x, y, value)

    def line(self, top: float) -> None:
        self.canvas.setLineWidth(0.5)
        self.canvas.line(34, HEIGHT - top, 560, HEIGHT - top)

    def table_header(self, top: float) -> float:
        # Jak w prawdziwym wyciągu: mniejsza czcionka, dwie linie.
        self.text(44, top - 3, "Data księgowania", size=5.5, bold=True)
        self.text(44, top + 4, "/ Data transakcji", size=5.5, bold=True)
        self.text(COLUMNS["party"], top, "Dane kontrahenta", bold=True)
        self.text(COLUMNS["title"], top, "Tytuł", bold=True)
        self.text(COLUMNS["details"], top, "Szczegóły / nr transakcji", bold=True)
        self.text(531, top, "Kwota", bold=True)
        self.line(top + 20)
        return top + 20

    def next_page(self) -> float:
        self.text(
            34,
            FOOTER_TOP,
            f"Strona: {self.page} z {self.pages_estimate}. Wyciąg z rachunku",
        )
        self.canvas.showPage()
        self.page += 1
        return self.table_header(46)


# Szerokość kolumn: tekst dłuższy niż kolumna jest zawijany, jak w prawdziwym wyciągu.
COLUMN_WIDTHS = {"party": 115, "title": 112, "details": 100}


def _wrap(lines: list[str], width: float) -> list[str]:
    wrapped = []
    for line in lines:
        current = ""
        for word in line.split():
            candidate = f"{current} {word}".strip()
            if current and pdfmetrics.stringWidth(candidate, "Sans", 7) > width:
                wrapped.append(current)
                current = word
            else:
                current = candidate
        wrapped.append(current)
    return wrapped


def _column_lines(row: FakeTransaction) -> dict[str, list[str]]:
    details = [row.code, row.reference] if row.code else [row.reference]
    columns = {"party": row.party, "title": row.title, "details": details}
    return {name: _wrap(lines, COLUMN_WIDTHS[name]) for name, lines in columns.items()}


def make_ing_statement(
    transactions: list[FakeTransaction] | None = None,
    *,
    summary_override: dict | None = None,
) -> bytes:
    """Zwraca sztuczny wyciąg PDF. `summary_override` pozwala celowo zepsuć sumy kontrolne."""
    _register_fonts()
    rows = transactions or sample_transactions()
    credits = [r.amount for r in rows if r.amount > 0]
    debits = [-r.amount for r in rows if r.amount < 0]
    opening = Decimal("1000.00")
    summary = {
        "opening": opening,
        "closing": opening + sum(credits, Decimal(0)) - sum(debits, Decimal(0)),
        "credits_count": len(credits),
        "credits_sum": sum(credits, Decimal(0)),
        "debits_count": len(debits),
        "debits_sum": sum(debits, Decimal(0)),
    } | (summary_override or {})

    w = _Writer(pages_estimate=3)
    w.text(447, 49, "Nr 10 / 01.10.2026 - 31.10.2026", bold=True)
    w.text(34, 129, "Dane posiadacza", size=9, bold=True)
    w.text(34, 147, "JAN TESTOWY")
    w.text(34, 237, "Saldo początkowe", bold=True)
    w.text(34, 245, "/ saldo końcowe poprzedniego wyciągu:", size=5, bold=True)
    w.text(34, 253, amount_text(summary["opening"]))
    w.text(168, 237, f"Suma uznań ({summary['credits_count']}):", bold=True)
    w.text(168, 246, amount_text(summary["credits_sum"]))
    w.text(301, 237, "Limit zadłużenia:", bold=True)
    w.text(301, 246, "0,00 PLN")
    w.text(435, 237, "Kwota prowizji zaległej:", bold=True)
    w.text(435, 246, "0,00 PLN")
    w.text(34, 264, "Saldo końcowe:", bold=True)
    w.text(34, 272, amount_text(summary["closing"]))
    w.text(168, 264, f"Suma obciążeń ({summary['debits_count']}):", bold=True)
    w.text(168, 272, amount_text(summary["debits_sum"]))
    w.text(301, 264, "Kwota zablokowana:", bold=True)
    w.text(301, 272, "-12,00 PLN")
    w.text(435, 264, "Saldo dostępne:", bold=True)
    w.text(435, 272, amount_text(summary["closing"]))
    top = w.table_header(309)

    for row in rows:
        lines = _column_lines(row)
        height = max(2, *(len(v) for v in lines.values())) * LINE_HEIGHT + 14
        remaining = FOOTER_TOP - 12 - top
        if height > remaining:
            fits = int((remaining - 14) // LINE_HEIGHT)
            if fits >= 2:
                # Transakcja dzielona między strony: początek tutaj, bez linii zamykającej.
                w.text(COLUMNS["date"], top + 8, row.booking, size=8, bold=True)
                w.text(COLUMNS["date"], top + 8 + LINE_HEIGHT, row.date)
                for name, values in lines.items():
                    for i, value in enumerate(values[:fits]):
                        w.text(COLUMNS[name], top + 5 + i * LINE_HEIGHT, value)
                w.text(
                    COLUMNS["amount_right"],
                    top + 10,
                    amount_text(row.amount),
                    size=9,
                    bold=True,
                    right=True,
                )
                top = w.next_page()
                rest = {name: values[fits:] for name, values in lines.items()}
                rest_height = max(1, *(len(v) for v in rest.values())) * LINE_HEIGHT + 6
                for name, values in rest.items():
                    for i, value in enumerate(values):
                        w.text(COLUMNS[name], top + 5 + i * LINE_HEIGHT, value)
                top += rest_height
                w.line(top)
                continue
            top = w.next_page()
        w.text(COLUMNS["date"], top + 8, row.booking, size=8, bold=True)
        w.text(COLUMNS["date"], top + 8 + LINE_HEIGHT, row.date)
        for name, values in lines.items():
            for i, value in enumerate(values):
                w.text(COLUMNS[name], top + 5 + i * LINE_HEIGHT, value)
        w.text(
            COLUMNS["amount_right"],
            top + 10,
            amount_text(row.amount),
            size=9,
            bold=True,
            right=True,
        )
        top += height
        w.line(top)

    w.text(34, FOOTER_TOP, f"Strona: {w.page} z {w.page}. Wyciąg z rachunku")
    w.canvas.showPage()
    w.canvas.save()
    return w.buffer.getvalue()


if __name__ == "__main__":
    Path(sys.argv[1]).write_bytes(make_ing_statement())
    print(f"Zapisano {sys.argv[1]}")
