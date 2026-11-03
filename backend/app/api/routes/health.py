"""Endpoint diagnostyczny: czy API działa i czy ma połączenie z bazą."""

import logging

from fastapi import APIRouter, Response, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import DbSession

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health")
def health(response: Response, db: DbSession) -> dict[str, str]:
    """Zwraca 200, gdy baza odpowiada, albo 503, gdy API działa, ale bazy brak."""
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        logger.exception("Brak połączenia z bazą danych")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "degraded", "database": "error"}
    return {"status": "ok", "database": "ok"}
