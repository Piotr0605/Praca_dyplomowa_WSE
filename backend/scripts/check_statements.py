"""Sprawdza parser na prawdziwych wyciągach, nie ujawniając ich treści.

Wypisuje wyłącznie liczby: transakcje, zgodność z sumami kontrolnymi i rodzaje operacji.
Opisy, kontrahenci i kwoty pojedynczych transakcji nie są wypisywane.

Użycie (z katalogu backend/, pliki w data/private/):
    DATABASE_URL=postgresql+psycopg://x:x@localhost/x .venv/bin/python -m scripts.check_statements
"""

import collections
import sys
from pathlib import Path

from app.parsers.ing_pdf import StatementParseError, parse_ing_pdf, validate_statement

DEFAULT_DIR = Path(__file__).resolve().parents[2] / "data" / "private"


def main(directory: Path) -> int:
    files = sorted(directory.glob("*.pdf"))
    if not files:
        print(f"Brak plików PDF w {directory}")
        return 1
    failed = 0
    references: list[str] = []
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
    print(f"numery operacji: {len(references)}, unikalnych: {len(set(references))}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DIR))
