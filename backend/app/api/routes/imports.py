"""Import wyciągów: profile plików CSV, rozpoznanie formatu, podgląd, zatwierdzenie i historia."""

from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from pydantic import ValidationError
from sqlalchemy import select

from app.api.deps import CurrentUser
from app.core.database import DbSession
from app.models import ImportBatch
from app.parsers.csv_detect import detect as detect_csv
from app.parsers.csv_generic import CsvFormatError
from app.parsers.csv_profile import CsvProfile, Delimiter, Encoding
from app.parsers.ing_pdf import StatementParseError
from app.schemas.imports import (
    BankProfileRead,
    ColumnSuggestion,
    CsvDetection,
    ImportBatchRead,
    ImportPreview,
)
from app.services import import_service
from app.services.import_service import (
    MAX_FILE_SIZE,
    ProfileNotFoundError,
    StatementMismatchError,
    UnknownCsvFormatError,
)

router = APIRouter(prefix="/imports", tags=["imports"])

StatementFile = Annotated[
    UploadFile,
    File(description="Wyciąg ING w formacie PDF albo plik CSV z banku"),
]
ProfileJson = Annotated[
    str | None,
    Form(
        max_length=10_000,
        description="Ustawienia z kreatora mapowania (JSON w formacie profilu CSV)",
    ),
]
ProfileKey = Annotated[
    str | None,
    Form(max_length=50, description="Klucz zapisanego profilu, np. `builtin:ing`"),
]
READ_ERRORS = (
    StatementParseError,
    StatementMismatchError,
    CsvFormatError,
    UnknownCsvFormatError,
    ProfileNotFoundError,
)


def _read(file: UploadFile) -> bytes:
    data = file.file.read(MAX_FILE_SIZE + 1)
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(
            status.HTTP_413_CONTENT_TOO_LARGE,
            f"Plik jest większy niż {MAX_FILE_SIZE // (1024 * 1024)} MB",
        )
    return data


def _profile(raw: str | None) -> CsvProfile | None:
    if raw is None:
        return None
    try:
        return CsvProfile.model_validate_json(raw)
    except ValidationError as error:
        # Bez pola `input`: komunikat nie powtarza przesłanych danych.
        detail = [
            {"loc": ["profile", *e["loc"]], "msg": e["msg"], "type": e["type"]}
            for e in error.errors()
        ]
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail) from error


def _read_error(error: Exception) -> HTTPException:
    if isinstance(error, ProfileNotFoundError):
        return HTTPException(status.HTTP_404_NOT_FOUND, "Nie ma takiego profilu")
    if isinstance(error, StatementMismatchError):
        detail = "Odczyt niezgodny z sumami kontrolnymi wyciągu: " + "; ".join(
            error.problems
        )
    elif isinstance(error, StatementParseError):
        detail = f"Nie rozpoznano wyciągu ING: {error}"
    elif isinstance(error, UnknownCsvFormatError):
        detail = (
            "Nie rozpoznano formatu pliku CSV. Wskaż kolumny w kreatorze mapowania."
        )
    else:
        detail = str(error)
    return HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail)


@router.get("/banks")
def banks(user: CurrentUser, db: DbSession) -> list[BankProfileRead]:
    """Profile plików CSV: zapisane przez użytkownika i wbudowane."""
    return [info for info, _ in import_service.profiles(db, user.id)]


@router.delete("/banks/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bank(profile_id: int, user: CurrentUser, db: DbSession) -> None:
    """Usuwa własny profil. Profili wbudowanych nie można usunąć."""
    if not import_service.delete_profile(db, user.id, profile_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Nie ma takiego profilu")


@router.post("/detect")
def detect(
    file: StatementFile,
    user: CurrentUser,
    db: DbSession,
    encoding: Annotated[Encoding | None, Form()] = None,
    delimiter: Annotated[Delimiter | None, Form()] = None,
) -> CsvDetection:
    """Rozpoznaje format pliku CSV i proponuje mapowanie kolumn. Niczego nie zapisuje."""
    data = _read(file)
    if import_service.is_pdf(data):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Wyciąg PDF nie wymaga mapowania kolumn",
        )
    try:
        found = detect_csv(data, encoding=encoding, delimiter=delimiter)
    except CsvFormatError as error:
        raise _read_error(error) from error
    # Ręcznie wybrane kodowanie lub separator oznacza, że użytkownik chce mapowania.
    matched = (
        None
        if encoding or delimiter
        else import_service.match_profile(db, user.id, data)
    )
    return CsvDetection(
        encoding=found.encoding,
        delimiter=found.delimiter,
        header_row=found.header_row,
        headers=found.headers,
        sample_rows=found.sample_rows,
        columns=ColumnSuggestion.model_validate(found.columns),
        date_format=found.date_format,
        decimal_separator=found.decimal_separator,
        missing=found.missing,
        matched=matched[0] if matched else None,
    )


@router.post("/preview")
def preview(
    file: StatementFile,
    user: CurrentUser,
    db: DbSession,
    profile: ProfileJson = None,
    profile_key: ProfileKey = None,
) -> ImportPreview:
    """Odczytuje plik i pokazuje, co zostanie zapisane. Niczego nie zapisuje."""
    data = _read(file)
    try:
        return import_service.preview_import(
            db, user.id, data, profile=_profile(profile), profile_key=profile_key
        )
    except READ_ERRORS as error:
        raise _read_error(error) from error


@router.post("/confirm", status_code=status.HTTP_201_CREATED)
def confirm(
    file: StatementFile,
    user: CurrentUser,
    db: DbSession,
    profile: ProfileJson = None,
    profile_key: ProfileKey = None,
    save_profile: Annotated[
        bool, Form(description="Zapamiętaj ustawienia z kreatora jako profil banku")
    ] = False,
) -> ImportBatchRead:
    """Zapisuje nowe transakcje; duplikaty z wcześniejszych importów są pomijane."""
    data = _read(file)
    try:
        batch = import_service.confirm_import(
            db,
            user.id,
            data,
            file.filename or "wyciag",
            profile=_profile(profile),
            profile_key=profile_key,
            remember_profile=save_profile,
        )
    except READ_ERRORS as error:
        raise _read_error(error) from error
    return ImportBatchRead.model_validate(batch)


@router.get("")
def history(user: CurrentUser, db: DbSession) -> list[ImportBatchRead]:
    batches = db.scalars(
        select(ImportBatch)
        .where(ImportBatch.user_id == user.id)
        .order_by(ImportBatch.created_at.desc(), ImportBatch.id.desc())
    )
    return [ImportBatchRead.model_validate(b) for b in batches]
