# Notatki do rozdziału „Wykorzystane technologie”

Stan po tygodniu 1. Wersje pochodzą z plików projektu (`requirements*.txt`, `package.json`, `docker-compose.yml`).
Szersze opisy działania każdej technologii: [`TYDZIEN_1.md`](TYDZIEN_1.md), sekcja 2.

## Zestawienie

| Warstwa | Technologia | Wersja | Rola w systemie |
|---|---|---|---|
| Baza danych | PostgreSQL | 16 | przechowywanie danych użytkowników i transakcji |
| Backend | Python | 3.13 | język implementacji serwera i analityki |
| Backend | FastAPI | 0.162 | REST API, walidacja, dokumentacja OpenAPI |
| Backend | Uvicorn | 0.54 | serwer ASGI uruchamiający FastAPI |
| Backend | Pydantic Settings | 2.16 | konfiguracja ze zmiennych środowiskowych, walidowana przy starcie |
| Backend | SQLAlchemy | 2.1 | mapowanie obiektowo-relacyjne (ORM), pula połączeń |
| Backend | Alembic | 1.20 | wersjonowane migracje schematu bazy |
| Analityka | Pandas | 3.1 | import CSV i agregacje (używane od etapu 4) |
| Frontend | React | 19 | interfejs użytkownika z komponentów |
| Frontend | TypeScript | 7 | statyczne typowanie kodu frontendu |
| Frontend | Vite | 8 | serwer deweloperski i budowanie aplikacji |
| Frontend | Tailwind CSS | 4 | stylowanie klasami narzędziowymi |
| Jakość | pytest, httpx2 | 9.2, 2.16 | testy automatyczne API |
| Jakość | Ruff | 0.17 | linter i formatter Pythona |
| Jakość | oxlint, Prettier | 1.89, 3.9 | linter i formatter TypeScriptu |
| Infrastruktura | Docker, Docker Compose | 29, v5 | uruchamianie całego systemu w kontenerach |
| Infrastruktura | Git, GitHub, GitHub Actions | – | kontrola wersji i ciągła integracja (CI) |

## Uzasadnienie głównych wyborów

**PostgreSQL.** Kwoty wymagają dokładnego typu `NUMERIC`, bo typy zmiennoprzecinkowe dają błędy zaokrągleń. Relacje
i ograniczenia `UNIQUE` pozwalają wymusić poprawność danych, np. brak duplikatów przy imporcie, na poziomie bazy.
Transakcyjne migracje schematu sprawiają, że nieudana zmiana jest wycofywana w całości (sprawdzone testem, patrz dziennik, dzień 4).

**FastAPI.** Typy Pythona służą jednocześnie do walidacji danych i generowania dokumentacji API. Python daje też
bezpośredni dostęp do Pandas i bibliotek klienckich modeli językowych, potrzebnych w kolejnych etapach.

**SQLAlchemy i Alembic.** Zapytania parametryzowane chronią przed SQL injection. Migracje wersjonowane razem z kodem
pozwalają odtworzyć schemat bazy na dowolnym komputerze.

**React, TypeScript, Vite.** Komponenty odpowiadają częściom interfejsu (karty, wykresy, tabele), a TypeScript wykrywa
niezgodności z API przed uruchomieniem kodu.

**Docker Compose.** Jedno polecenie uruchamia cały system bez ręcznej instalacji bazy czy środowisk. Sprawdzono to na
świeżym klonie repozytorium (dziennik, dzień 7).

**Architektura lokalna.** System działa na komputerze użytkownika, a porty są dostępne tylko przez `127.0.0.1`. Dane
finansowe są przechowywane i przetwarzane lokalnie, a poza urządzenie, tylko na żądanie użytkownika, trafiają wyłącznie
zanonimizowane agregaty (plan, sekcja 9).

## Zapewnienie jakości (materiał do rozdziału o weryfikacji)

- Testy automatyczne uruchamiane przy każdej zmianie w GitHub Actions, na czystej maszynie z prawdziwą bazą PostgreSQL.
- Gałąź `main` jest chroniona: scalenie wymaga Pull Requesta i zielonych testów.
- Skuteczność testów sprawdzono, wprowadzając celowe błędy; wszystkie 4 zostały wykryte (dziennik, dzień 6).
- Zachowanie przy awarii zweryfikowano w przeglądarce: zatrzymanie bazy lub backendu jest widoczne na ekranie stanu (dziennik, dzień 5).

## Do uzupełnienia w pracy
- Odwołania do literatury i dokumentacji technologii.
- Porównanie z alternatywami, jeśli wymaga tego promotor (np. Django, MySQL, Vue).
- Moduły z kolejnych etapów: uwierzytelnianie, import CSV, dashboard (Recharts), moduł AI.
