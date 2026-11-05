"""Reguły modelu danych, których nie wolno złamać przy dodawaniu kolejnych tabel."""

from sqlalchemy import Numeric

from app.core.database import Base
from app.models import Transaction

TABELE_BEZ_WLASCICIELA = {"users"}


def test_wszystkie_tabele_sa_zarejestrowane() -> None:
    assert set(Base.metadata.tables) == {
        "users",
        "categories",
        "transactions",
        "import_batches",
        "category_rules",
        "ai_advice",
    }


def test_kazda_tabela_danych_ma_wlasciciela() -> None:
    """Izolacja danych opiera się na user_id: nowa tabela nie może go pominąć."""
    for nazwa, tabela in Base.metadata.tables.items():
        if nazwa not in TABELE_BEZ_WLASCICIELA:
            assert "user_id" in tabela.columns, f"Tabela {nazwa} nie ma kolumny user_id"


def test_kwota_jest_dokladna() -> None:
    typ = Transaction.__table__.c.amount.type

    assert isinstance(typ, Numeric)
    assert typ.asdecimal is True
    assert (typ.precision, typ.scale) == (12, 2)
