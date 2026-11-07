"""Punkt wejścia aplikacji FastAPI (uruchamiany przez: uvicorn app.main:app)."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import auth, categories, health, transactions
from app.core.config import get_settings
from app.core.jwt_key import get_jwt_secret

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # Problem z kluczem ma zatrzymać start, a nie wyjść dopiero przy pierwszym logowaniu.
    get_jwt_secret()
    yield


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    _: Request, error: RequestValidationError
) -> JSONResponse:
    """Błąd walidacji bez odrzuconej wartości: domyślnie wróciłoby w nim np. za krótkie hasło."""
    details = [
        {key: value for key, value in item.items() if key not in {"input", "ctx"}}
        for item in error.errors()
    ]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content=jsonable_encoder({"detail": details}),
    )


app.include_router(health.router, prefix=settings.API_PREFIX)
app.include_router(auth.router, prefix=settings.API_PREFIX)
app.include_router(categories.router, prefix=settings.API_PREFIX)
app.include_router(transactions.router, prefix=settings.API_PREFIX)
