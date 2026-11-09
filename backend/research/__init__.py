"""Narzędzia badania aplikacyjnego (docs/BADANIA.md). Działają na plikach z data/private/ bez bazy danych.

Import modeli wczytuje ustawienia aplikacji, które wymagają adresu bazy. Skrypty badawcze z bazy
nie korzystają, więc wystarczy adres zastępczy.
"""

import os

os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://badanie:x@localhost/badanie"
)
