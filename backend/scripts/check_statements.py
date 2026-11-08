"""Sprawdza parser na prawdziwych wyciągach, nie ujawniając ich treści.

Wypisuje wyłącznie liczby: transakcje, zgodność z sumami kontrolnymi i rodzaje operacji.
Opisy, kontrahenci i kwoty pojedynczych transakcji nie są wypisywane.

Pliki CSV są odczytywane profilem wbudowanym (np. ING). Dla operacji obecnych także w wyciągach PDF
skrypt porównuje kwoty i daty. Gdy plik nie pasuje do profilu, wypisuje nazwy kolumn z nagłówka
(to nazwy nadane przez bank, bez danych osobowych) i propozycję detektora.

Użycie (z katalogu backend/, pliki w data/private/):
    DATABASE_URL=postgresql+psycopg://x:x@localhost/x .venv/bin/python -m scripts.check_statements
"""

import collections
import sys
from pathlib import Path

from app.parsers.csv_detect import detect, profile_matches
from app.parsers.csv_generic import CsvFormatError, parse_csv
from app.parsers.csv_profile import builtin_profiles
from app.parsers.ing_pdf import (
    ParsedTransaction,
    StatementParseError,
    parse_ing_pdf,
    validate_statement,
)

DEFAULT_DIR = Path(__file__).resolve().parents[2] / "data" / "private"


def check_csv(path: Path, number: int, pdf: dict[str, ParsedTransaction]) -> bool:
    data = path.read_bytes()
    profile = next(
        (p for p in builtin_profiles().values() if profile_matches(data, p)), None
    )
    if profile is None:
        try:
            found = detect(data)
        except CsvFormatError as error:
            print(f"plik CSV {number}: nie rozpoznano formatu: {error}")
            return False
        print(
            f"plik CSV {number}: nie pasuje do profilu wbudowanego; kodowanie {found.encoding}, "
            f"separator {found.delimiter!r}, wiersz nagłówka {found.header_row + 1}"
        )
        print("    kolumny:", found.headers)
        print("    propozycja:", {k: v for k, v in found.columns.items() if v})
        print("    format daty:", found.date_format, "brakuje:", found.missing)
        return False
    try:
        statement = parse_csv(data, profile)
    except CsvFormatError as error:
        # Komunikat może zawierać treść komórki, więc wypisujemy tylko numery wierszy.
        rows = [part.split(":")[0] for part in str(error).split("; ")]
        print(f"plik CSV {number}: błąd odczytu ({profile.bank_name}): {rows}")
        return False
    transactions = statement.transactions
    common = [t for t in transactions if t.dedup_hash in pdf]
    amount_diff = sum(t.amount != pdf[t.dedup_hash].amount for t in common)
    date_diff = sum(t.date != pdf[t.dedup_hash].date for t in common)
    kinds = collections.Counter(t.kind.value for t in transactions)
    print(
        f"plik CSV {number} ({profile.bank_name}): transakcji {len(transactions)}, "
        f"pominiętych bez kwoty {statement.skipped}, wspólnych z PDF {len(common)}, "
        f"różnych kwot {amount_diff}, różnych dat {date_diff}, rodzaje {dict(kinds)}"
    )
    return amount_diff == 0


def main(directory: Path) -> int:
    files = sorted(directory.glob("*.pdf"))
    csv_files = sorted(directory.glob("*.csv"))
    if not files and not csv_files:
        print(f"Brak plików PDF i CSV w {directory}")
        return 1
    failed = 0
    references: list[str] = []
    pdf: dict[str, ParsedTransaction] = {}
    for number, path in enumerate(files, start=1):
        try:
            statement = parse_ing_pdf(path.read_bytes())
        except StatementParseError as error:
            print(f"wyciąg {number}: błąd odczytu: {error}")
            failed += 1
            continue
        problems = validate_statement(statement)
        failed += bool(problems)
        references += [t.bank_reference for t in statement.transactions]
        pdf.update({t.dedup_hash: t for t in statement.transactions})
        kinds = collections.Counter(t.kind.value for t in statement.transactions)
        print(
            f"wyciąg {number}: transakcji {len(statement.transactions)}, "
            f"zgodność z sumami: {'TAK' if not problems else 'NIE'}, rodzaje {dict(kinds)}"
        )
        for problem in problems:
            # Liczby operacji można pokazać; sum pojedynczego wyciągu nie wypisujemy.
            print(
                "   ",
                problem if problem.startswith("liczba") else problem.split(":")[0],
            )
    if files:
        print(f"numery operacji: {len(references)}, unikalnych: {len(set(references))}")
    for number, path in enumerate(csv_files, start=1):
        failed += not check_csv(path, number, pdf)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DIR))
