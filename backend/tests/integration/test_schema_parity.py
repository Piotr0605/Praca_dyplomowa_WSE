"""Modele i migracje muszą opisywać ten sam schemat.

`alembic check` nie porównuje ograniczeń CHECK ani wartości domyślnych. Ten test tworzy dwie bazy,
z modeli i z migracji, i porównuje je w katalogu PostgreSQL. Definicje zapisuje tam sam PostgreSQL,
więc różny zapis tej samej reguły w kodzie nie daje fałszywego alarmu.
"""

from typing import Any

from sqlalchemy import URL, Engine, create_engine, text

from app.core.database import Base
from tests.db_helpers import database_url_for_tests, drop_database, recreate_database

COLUMNS = """
    SELECT table_name, column_name, data_type, character_maximum_length,
           numeric_precision, numeric_scale, is_nullable, column_default
    FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name <> 'alembic_version'
"""
CONSTRAINTS = """
    SELECT conrelid::regclass::text, conname, pg_get_constraintdef(oid)
    FROM pg_constraint
    WHERE connamespace = 'public'::regnamespace AND conrelid::regclass::text <> 'alembic_version'
"""
INDEXES = """
    SELECT tablename, indexname, indexdef
    FROM pg_indexes
    WHERE schemaname = 'public' AND tablename <> 'alembic_version'
"""


def read_schema(engine: Engine) -> dict[str, set[tuple[Any, ...]]]:
    with engine.connect() as connection:
        return {
            "kolumny": {tuple(row) for row in connection.execute(text(COLUMNS))},
            "ograniczenia": {
                tuple(row) for row in connection.execute(text(CONSTRAINTS))
            },
            "indeksy": {tuple(row) for row in connection.execute(text(INDEXES))},
        }


def schema_from_models(url: URL) -> dict[str, set[tuple[Any, ...]]]:
    recreate_database(url)
    engine = create_engine(url)
    try:
        Base.metadata.create_all(engine)
        return read_schema(engine)
    finally:
        engine.dispose()
        drop_database(url)


def test_migracje_daja_ten_sam_schemat_co_modele(test_engine: Engine) -> None:
    z_migracji = read_schema(test_engine)
    z_modeli = schema_from_models(database_url_for_tests("_test_modele"))

    for rodzaj in ("kolumny", "ograniczenia", "indeksy"):
        assert z_migracji[rodzaj], f"Brak danych o: {rodzaj}"
        tylko_w_modelach = z_modeli[rodzaj] - z_migracji[rodzaj]
        tylko_w_migracjach = z_migracji[rodzaj] - z_modeli[rodzaj]
        assert not tylko_w_modelach and not tylko_w_migracjach, (
            f"Różnica ({rodzaj}): tylko w modelach {tylko_w_modelach}, "
            f"tylko w migracjach {tylko_w_migracjach}"
        )
