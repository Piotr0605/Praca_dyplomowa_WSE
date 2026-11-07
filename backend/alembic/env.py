"""Środowisko uruchomieniowe migracji Alembic.

Łączy Alembic z aplikacją:
- adres bazy pochodzi z tych samych ustawień co aplikacja (DATABASE_URL w .env),
- `target_metadata` to metadane wszystkich modeli ORM, dzięki czemu
  `alembic revision --autogenerate` porównuje modele z bazą i sam proponuje zmiany.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

import app.models  # noqa: F401  (import rejestruje wszystkie modele w Base.metadata)
from app.core.config import get_settings
from app.core.database import Base

config = context.config

if config.config_file_name is not None:
    # disable_existing_loggers=False: migracje uruchamiane z testów nie mogą wyłączać logów aplikacji.
    fileConfig(config.config_file_name, disable_existing_loggers=False)

# Testy podają adres swojej bazy. Znak % trzeba podwoić ze względu na format pliku .ini.
if not config.get_main_option("sqlalchemy.url"):
    config.set_main_option(
        "sqlalchemy.url", get_settings().DATABASE_URL.replace("%", "%%")
    )

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Tryb offline: generuje skrypt SQL bez łączenia się z bazą (`alembic upgrade head --sql`)."""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Tryb online: wykonuje migracje na działającej bazie."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        # Migracje uruchamiane są jednorazowo, więc pula połączeń nie jest potrzebna.
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # Autogenerate wykrywa też zmiany typów kolumn (np. VARCHAR(50) -> VARCHAR(100)).
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
