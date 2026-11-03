#!/bin/sh
# Start backendu: najpierw migracje bazy, potem serwer API.
# `set -e` przerywa start, jeśli migracja się nie powiedzie: aplikacja nie ruszy
# z nieaktualnym schematem bazy, a błąd będzie widoczny w `docker compose logs backend`.
set -e

echo "Migracje bazy danych: alembic upgrade head"
alembic upgrade head

# `exec` zastępuje powłokę procesem uvicorn, dzięki czemu sygnał zatrzymania
# z `docker compose stop` trafia bezpośrednio do serwera (szybkie, czyste wyłączenie).
# Dodatkowe argumenty (np. --reload w trybie deweloperskim) przekazuje docker-compose.yml.
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 "$@"
