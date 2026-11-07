"""Tworzenie i usuwanie baz testowych."""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import URL, create_engine, make_url, text

from app.core.config import get_settings

BACKEND_DIR = Path(__file__).resolve().parent.parent


def database_url_for_tests(suffix: str = "_test") -> URL:
    url = make_url(get_settings().DATABASE_URL)
    return url.set(database=f"{url.database}{suffix}")


def _execute_as_admin(url: URL, *statements: str) -> None:
    """Wykonuje polecenia na serwerze. Odmawia pracy na bazie, która nie jest testowa."""
    if "_test" not in (url.database or ""):
        raise ValueError(f"Odmowa zmiany bazy, która nie jest testowa: {url.database}")
    admin = create_engine(
        make_url(get_settings().DATABASE_URL), isolation_level="AUTOCOMMIT"
    )
    with admin.connect() as connection:
        for statement in statements:
            connection.execute(text(statement))
    admin.dispose()


def recreate_database(url: URL) -> None:
    """Tworzy pustą bazę testową."""
    _execute_as_admin(
        url,
        f'DROP DATABASE IF EXISTS "{url.database}" WITH (FORCE)',
        f'CREATE DATABASE "{url.database}"',
    )


def drop_database(url: URL) -> None:
    _execute_as_admin(url, f'DROP DATABASE IF EXISTS "{url.database}" WITH (FORCE)')


def run_migrations(url: URL) -> None:
    config = Config(BACKEND_DIR / "alembic.ini")
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    config.set_main_option(
        "sqlalchemy.url", url.render_as_string(hide_password=False).replace("%", "%%")
    )
    command.upgrade(config, "head")
