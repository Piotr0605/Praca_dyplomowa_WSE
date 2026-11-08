"""Import wyciągu: odczyt, kontrola, wykrycie duplikatów i zapis nowych transakcji.

Obsługiwane są wyciągi PDF z ING (z kontrolą sum) i pliki CSV opisane profilem: wbudowanym
(`app/parsers/profiles/`) albo zapisanym przez użytkownika w kreatorze mapowania kolumn.

Plik nie jest zapisywany na serwerze. Podgląd i zatwierdzenie przyjmują go osobno,
więc dane bankowe nie zostają w plikach tymczasowych.
"""

from dataclasses import dataclass
from decimal import Decimal
from pathlib import PurePath

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import BankProfile, ImportBatch, Transaction
from app.models.enums import TransactionSource
from app.parsers import ing_pdf
from app.parsers.common import normalize_description
from app.parsers.csv_detect import profile_matches
from app.parsers.csv_generic import CsvTransaction, parse_csv
from app.parsers.csv_profile import CsvProfile, builtin_profiles
from app.parsers.ing_pdf import ParsedTransaction, StatementSummary
from app.schemas.imports import BankProfileRead, ImportPreview, PreviewTransaction

__all__ = ["MAX_FILE_SIZE", "normalize_description"]

MAX_FILE_SIZE = 5 * 1024 * 1024


class StatementMismatchError(Exception):
    """Odczytane transakcje nie zgadzają się z sumami kontrolnymi wyciągu."""

    def __init__(self, problems: list[str]) -> None:
        super().__init__("; ".join(problems))
        self.problems = problems


class UnknownCsvFormatError(Exception):
    """Plik CSV nie pasuje do żadnego profilu: potrzebne mapowanie kolumn."""


class ProfileNotFoundError(Exception):
    """Nie ma profilu o tym kluczu wśród wbudowanych i profili użytkownika."""


@dataclass(frozen=True)
class ReadStatement:
    format: str
    bank: str
    transactions: list[ParsedTransaction] | list[CsvTransaction]
    summary: StatementSummary | None
    skipped: int


def is_pdf(data: bytes) -> bool:
    return data.startswith(b"%PDF")


def profiles(
    session: Session, user_id: int
) -> list[tuple[BankProfileRead, CsvProfile]]:
    """Profile użytkownika, a po nich wbudowane: własny profil ma pierwszeństwo przy dopasowaniu."""
    own = session.scalars(
        select(BankProfile)
        .where(BankProfile.user_id == user_id)
        .order_by(BankProfile.bank_name)
    )
    result = [
        (
            BankProfileRead(key=f"user:{p.id}", bank_name=p.bank_name, builtin=False),
            CsvProfile.model_validate(p.config),
        )
        for p in own
    ]
    result += [
        (
            BankProfileRead(key=f"builtin:{name}", bank_name=p.bank_name, builtin=True),
            p,
        )
        for name, p in builtin_profiles().items()
    ]
    return result


def get_profile(session: Session, user_id: int, key: str) -> CsvProfile:
    for info, profile in profiles(session, user_id):
        if info.key == key:
            return profile
    raise ProfileNotFoundError(key)


def match_profile(
    session: Session, user_id: int, data: bytes
) -> tuple[BankProfileRead, CsvProfile] | None:
    return next(
        (
            (info, profile)
            for info, profile in profiles(session, user_id)
            if profile_matches(data, profile)
        ),
        None,
    )


def save_profile(session: Session, user_id: int, profile: CsvProfile) -> None:
    """Zapisuje profil; profil o tej samej nazwie dostaje nowe ustawienia."""
    config = profile.model_dump(mode="json")
    session.execute(
        insert(BankProfile)
        .values(user_id=user_id, bank_name=profile.bank_name, config=config)
        .on_conflict_do_update(
            index_elements=["user_id", "bank_name"], set_={"config": config}
        )
    )


def delete_profile(session: Session, user_id: int, profile_id: int) -> bool:
    result = session.execute(
        delete(BankProfile).where(
            BankProfile.id == profile_id, BankProfile.user_id == user_id
        )
    )
    session.commit()
    return result.rowcount > 0


def read_statement(
    session: Session,
    user_id: int,
    data: bytes,
    *,
    profile: CsvProfile | None = None,
    profile_key: str | None = None,
) -> ReadStatement:
    if is_pdf(data):
        # Kontrola sum: niezgodny wyciąg nie może trafić do bazy nawet częściowo.
        statement = ing_pdf.parse_ing_pdf(data)
        problems = ing_pdf.validate_statement(statement)
        if problems:
            raise StatementMismatchError(problems)
        return ReadStatement(
            "pdf", ing_pdf.BANK, statement.transactions, statement.summary, 0
        )

    if profile is None and profile_key is not None:
        profile = get_profile(session, user_id, profile_key)
    if profile is None:
        matched = match_profile(session, user_id, data)
        if matched is None:
            raise UnknownCsvFormatError
        profile = matched[1]
    csv_statement = parse_csv(data, profile)
    return ReadStatement(
        "csv",
        profile.bank_name,
        csv_statement.transactions,
        None,
        csv_statement.skipped,
    )


def _existing_hashes(session: Session, user_id: int, hashes: list[str]) -> set[str]:
    query = select(Transaction.dedup_hash).where(
        Transaction.user_id == user_id, Transaction.dedup_hash.in_(hashes)
    )
    return set(session.scalars(query))


def preview_import(
    session: Session,
    user_id: int,
    data: bytes,
    *,
    profile: CsvProfile | None = None,
    profile_key: str | None = None,
) -> ImportPreview:
    statement = read_statement(
        session, user_id, data, profile=profile, profile_key=profile_key
    )
    transactions = statement.transactions
    existing = _existing_hashes(session, user_id, [t.dedup_hash for t in transactions])
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
        for t in transactions
    ]
    credits = [t.amount for t in transactions if t.amount > 0]
    debits = [-t.amount for t in transactions if t.amount < 0]
    summary = statement.summary
    dates = [t.date for t in transactions]
    duplicates = sum(row.duplicate for row in rows)
    return ImportPreview(
        format=statement.format,
        bank=statement.bank,
        period_start=summary.period_start if summary else min(dates),
        period_end=summary.period_end if summary else max(dates),
        opening_balance=summary.opening_balance if summary else None,
        closing_balance=summary.closing_balance if summary else None,
        verified=summary is not None,
        credits_count=len(credits),
        credits_sum=sum(credits, Decimal(0)),
        debits_count=len(debits),
        debits_sum=sum(debits, Decimal(0)),
        total=len(rows),
        new=len(rows) - duplicates,
        duplicates=duplicates,
        skipped=statement.skipped,
        transactions=rows,
    )


def confirm_import(
    session: Session,
    user_id: int,
    data: bytes,
    filename: str,
    *,
    profile: CsvProfile | None = None,
    profile_key: str | None = None,
    remember_profile: bool = False,
) -> ImportBatch:
    statement = read_statement(
        session, user_id, data, profile=profile, profile_key=profile_key
    )
    # Profil z kreatora zapisujemy dopiero wtedy, gdy plik dał się według niego odczytać.
    if remember_profile and profile is not None:
        save_profile(session, user_id, profile)
    batch = ImportBatch(
        user_id=user_id,
        bank=statement.bank,
        # Tylko nazwa pliku, bez ścieżki, którą mogłaby przesłać przeglądarka.
        filename=PurePath(filename.replace("\\", "/")).name[:255] or "wyciag",
        rows_total=len(statement.transactions),
    )
    session.add(batch)
    session.flush()

    source = (
        TransactionSource.PDF if statement.format == "pdf" else TransactionSource.CSV
    )
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
            "source": source,
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
