"""Import wyciągu: odczyt, kontrola sum, wykrycie duplikatów i zapis nowych transakcji.

Plik nie jest zapisywany na serwerze. Podgląd i zatwierdzenie przyjmują go osobno,
więc dane bankowe nie zostają w plikach tymczasowych.
"""

import re
from pathlib import PurePath

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import ImportBatch, Transaction
from app.models.enums import TransactionSource
from app.parsers.ing_pdf import BANK, ParsedStatement, parse_ing_pdf, validate_statement
from app.schemas.imports import ImportPreview, PreviewTransaction

MAX_FILE_SIZE = 5 * 1024 * 1024
DATE_RE = re.compile(r"\d{2}\.\d{2}\.\d{4}")


class StatementMismatchError(Exception):
    """Odczytane transakcje nie zgadzają się z sumami kontrolnymi wyciągu."""

    def __init__(self, problems: list[str]) -> None:
        super().__init__("; ".join(problems))
        self.problems = problems


def normalize_description(text: str) -> str:
    """Opis do porównań w kategoryzacji (etap 5): małe litery, bez dat i nadmiarowych spacji."""
    return re.sub(r"\s+", " ", DATE_RE.sub("", text.lower())).strip()


def _read_checked(data: bytes) -> ParsedStatement:
    """Odczyt z kontrolą sum: niezgodny wyciąg nie może trafić do bazy nawet częściowo."""
    statement = parse_ing_pdf(data)
    problems = validate_statement(statement)
    if problems:
        raise StatementMismatchError(problems)
    return statement


def _existing_hashes(session: Session, user_id: int, hashes: list[str]) -> set[str]:
    query = select(Transaction.dedup_hash).where(
        Transaction.user_id == user_id, Transaction.dedup_hash.in_(hashes)
    )
    return set(session.scalars(query))


def preview_import(session: Session, user_id: int, data: bytes) -> ImportPreview:
    statement = _read_checked(data)
    existing = _existing_hashes(
        session, user_id, [t.dedup_hash for t in statement.transactions]
    )
    rows = [
        PreviewTransaction(
            date=t.date,
            booking_date=t.booking_date,
            amount=t.amount,
            currency=t.currency,
            description=t.description,
            counterparty=t.counterparty,
            kind=t.kind,
            duplicate=t.dedup_hash in existing,
        )
        for t in statement.transactions
    ]
    s = statement.summary
    duplicates = sum(row.duplicate for row in rows)
    return ImportPreview(
        bank=BANK,
        period_start=s.period_start,
        period_end=s.period_end,
        opening_balance=s.opening_balance,
        closing_balance=s.closing_balance,
        credits_count=s.credits_count,
        credits_sum=s.credits_sum,
        debits_count=s.debits_count,
        debits_sum=s.debits_sum,
        total=len(rows),
        new=len(rows) - duplicates,
        duplicates=duplicates,
        transactions=rows,
    )


def confirm_import(
    session: Session, user_id: int, data: bytes, filename: str
) -> ImportBatch:
    statement = _read_checked(data)
    batch = ImportBatch(
        user_id=user_id,
        bank=BANK,
        # Tylko nazwa pliku, bez ścieżki, którą mogłaby przesłać przeglądarka.
        filename=PurePath(filename.replace("\\", "/")).name[:255] or "wyciag.pdf",
        rows_total=len(statement.transactions),
    )
    session.add(batch)
    session.flush()

    values = [
        {
            "user_id": user_id,
            "date": t.date,
            "booking_date": t.booking_date,
            "amount": t.amount,
            "currency": t.currency,
            "description": t.description,
            "description_normalized": normalize_description(t.description),
            "counterparty": t.counterparty,
            "kind": t.kind,
            "source": TransactionSource.PDF,
            "import_batch_id": batch.id,
            "dedup_hash": t.dedup_hash,
        }
        for t in statement.transactions
    ]
    imported = 0
    if values:
        # ON CONFLICT DO NOTHING: duplikat pomija baza, także przy dwóch jednoczesnych importach.
        result = session.execute(
            insert(Transaction)
            .values(values)
            .on_conflict_do_nothing(index_elements=["user_id", "dedup_hash"])
            .returning(Transaction.id)
        )
        imported = len(result.all())
    batch.rows_imported = imported
    batch.rows_duplicated = len(values) - imported
    session.commit()
    return batch
