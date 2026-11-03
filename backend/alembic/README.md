# Migracje bazy danych (Alembic)

Polecenia uruchamiamy w kontenerze backendu, bo tam adres bazy (`db:5432`) jest osiągalny:

| Cel | Polecenie |
|---|---|
| Wygenerowanie migracji z różnic między modelami a bazą | `docker compose exec backend alembic revision --autogenerate -m "opis zmiany"` |
| Zastosowanie wszystkich migracji | `docker compose exec backend alembic upgrade head` |
| Cofnięcie ostatniej migracji | `docker compose exec backend alembic downgrade -1` |
| Aktualna wersja schematu | `docker compose exec backend alembic current` |
| Historia migracji | `docker compose exec backend alembic history` |

Przy każdym starcie kontenera backendu wykonuje się automatycznie `alembic upgrade head`.

Zasady:
- każda wygenerowana migracja jest **czytana przed commitem** (autogenerate nie wykrywa np. zmiany nazwy kolumny, widzi ją jako usunięcie i dodanie),
- każda migracja ma działające `downgrade()`,
- migracji już wypchniętych na `main` się nie edytuje; poprawka to nowa migracja.
