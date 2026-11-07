"""Import wyciągów bankowych: podgląd, zatwierdzenie i historia importów."""

from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from sqlalchemy import select

from app.api.deps import CurrentUser
from app.core.database import DbSession
from app.models import ImportBatch
from app.parsers.ing_pdf import StatementParseError
from app.schemas.imports import ImportBatchRead, ImportPreview
from app.services.import_service import (
    MAX_FILE_SIZE,
    StatementMismatchError,
    confirm_import,
    preview_import,
)

router = APIRouter(prefix="/imports", tags=["imports"])

StatementFile = Annotated[
    UploadFile, File(description="Wyciąg z rachunku ING w formacie PDF")
]


def _read(file: UploadFile) -> bytes:
    data = file.file.read(MAX_FILE_SIZE + 1)
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(
            status.HTTP_413_CONTENT_TOO_LARGE,
            f"Plik jest większy niż {MAX_FILE_SIZE // (1024 * 1024)} MB",
        )
    return data


def _statement_error(error: Exception) -> HTTPException:
    if isinstance(error, StatementMismatchError):
        detail = "Odczyt niezgodny z sumami kontrolnymi wyciągu: " + "; ".join(
            error.problems
        )
    else:
        detail = f"Nie rozpoznano wyciągu ING: {error}"
    return HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail)


@router.post("/preview")
def preview(file: StatementFile, user: CurrentUser, db: DbSession) -> ImportPreview:
    """Odczytuje wyciąg i pokazuje, co zostanie zapisane. Niczego nie zapisuje."""
    try:
        return preview_import(db, user.id, _read(file))
    except (StatementParseError, StatementMismatchError) as error:
        raise _statement_error(error) from error


@router.post("/confirm", status_code=status.HTTP_201_CREATED)
def confirm(file: StatementFile, user: CurrentUser, db: DbSession) -> ImportBatchRead:
    """Zapisuje nowe transakcje z wyciągu; duplikaty z wcześniejszych importów są pomijane."""
    try:
        batch = confirm_import(db, user.id, _read(file), file.filename or "wyciag.pdf")
    except (StatementParseError, StatementMismatchError) as error:
        raise _statement_error(error) from error
    return ImportBatchRead.model_validate(batch)


@router.get("")
def history(user: CurrentUser, db: DbSession) -> list[ImportBatchRead]:
    batches = db.scalars(
        select(ImportBatch)
        .where(ImportBatch.user_id == user.id)
        .order_by(ImportBatch.created_at.desc(), ImportBatch.id.desc())
    )
    return [ImportBatchRead.model_validate(b) for b in batches]
