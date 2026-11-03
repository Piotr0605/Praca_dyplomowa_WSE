"""Modele ORM (tabele bazy danych).

Każdy nowy moduł z modelami importujemy tutaj, np. `from app.models.user import User`.
alembic/env.py importuje ten pakiet, więc wszystkie modele trafiają do Base.metadata
i `alembic revision --autogenerate` widzi je bez dodatkowej konfiguracji.
"""
