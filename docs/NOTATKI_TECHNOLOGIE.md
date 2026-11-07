# Notatki do rozdziału „Wykorzystane technologie”

Stan po tygodniu 4. Wersje pochodzą z plików projektu (`requirements*.txt`, `package.json`, `docker-compose.yml`).
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
| Bezpieczeństwo | argon2-cffi | 25.1 | hashowanie haseł algorytmem Argon2id |
| Bezpieczeństwo | PyJWT | 2.15 | tokeny logowania JWT |
| Analityka | Pandas | 3.1 | agregacje i analizy (od etapu 6) |
| Import | pdfplumber | 0.11 | odczyt wyciągów PDF: znaki i linie tabeli ze współrzędnymi |
| Testy | ReportLab | 5.1 | generowanie sztucznych wyciągów PDF do testów (tylko obraz deweloperski) |
| Frontend | React | 19 | interfejs użytkownika z komponentów |
| Frontend | TypeScript | 7 | statyczne typowanie kodu frontendu |
| Frontend | Vite | 8 | serwer deweloperski i budowanie aplikacji |
| Frontend | Tailwind CSS | 4 | stylowanie klasami narzędziowymi |
| Frontend | React Router | 8.5 | nawigacja między stronami, trasy dostępne po zalogowaniu |
| Frontend | TanStack Query | 5.107 | pobieranie danych z API, pamięć podręczna, odświeżanie po zmianach |
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

**Argon2id.** Zwycięzca Password Hashing Competition, zalecany przez OWASP [źródło do uzupełnienia]. Wymaga dużo czasu
i pamięci, więc masowe zgadywanie haseł po wycieku bazy jest kosztowne. Użyto profilu RFC 9106: 64 MiB, 3 iteracje, 4 wątki.

**JWT.** Token podpisany kluczem pozwala obsługiwać logowanie bez przechowywania sesji po stronie serwera. Zawartość
tokenu można odczytać, dlatego zawiera on wyłącznie identyfikator użytkownika i czasy. Klucz jest generowany przy pierwszym
uruchomieniu, więc w publicznym repozytorium nie ma żadnego klucza.

**React, TypeScript, Vite.** Komponenty odpowiadają częściom interfejsu (karty, wykresy, tabele), a TypeScript wykrywa
niezgodności z API przed uruchomieniem kodu.

**React Router i TanStack Query.** Router obsługuje strony aplikacji i trasy chronione logowaniem. TanStack Query
przechowuje odpowiedzi API i odświeża je po zmianach danych, więc komponenty nie muszą same zarządzać stanem
pobierania. Po wylogowaniu pamięć podręczna jest czyszczona, żeby dane poprzedniego użytkownika nie zostały w przeglądarce.

**Izolacja danych.** Każde zapytanie do bazy zawiera `user_id` zalogowanej osoby, a cudzy zasób daje tę samą odpowiedź
co nieistniejący (404). Skuteczność sprawdzają testy izolacji i celowe usuwanie zabezpieczeń (dziennik, tydzień 3).

**pdfplumber i kontrola sum.** Wyciąg PDF nie ma struktury tabeli, więc transakcje są odtwarzane ze współrzędnych
znaków i linii tabeli. Wiarygodność odczytu zapewnia porównanie z sumami kontrolnymi z nagłówka wyciągu: niezgodny
import jest odrzucany w całości. Na 6 prawdziwych wyciągach zgodność wynosi 100% (1113 transakcji).

**Docker Compose.** Jedno polecenie uruchamia cały system bez ręcznej instalacji bazy czy środowisk. Sprawdzono to na
świeżym klonie repozytorium (dziennik, dzień 7).

**Architektura lokalna.** System działa na komputerze użytkownika, a porty są dostępne tylko przez `127.0.0.1`. Dane
finansowe są przechowywane i przetwarzane lokalnie, a poza urządzenie, tylko na żądanie użytkownika, trafiają wyłącznie
zanonimizowane agregaty (plan, sekcja 9).

## Zapewnienie jakości (materiał do rozdziału o weryfikacji)

- Testy automatyczne uruchamiane przy każdej zmianie w GitHub Actions, na czystej maszynie z prawdziwą bazą PostgreSQL.
- Gałąź `main` jest chroniona: scalenie wymaga Pull Requesta i zielonych testów.
- Skuteczność testów sprawdzano, wprowadzając celowe błędy; po uzupełnieniu testów wszystkie są wykrywane (dziennik, tydzień 1 dzień 6 oraz tydzień 2 dni 3 i 5).
- Osobny test porównuje schemat bazy z modeli i z migracji, wykrywając zmiany niewidoczne dla `alembic check` (dziennik, tydzień 2, dzień 5).
- Zachowanie przy awarii zweryfikowano w przeglądarce: zatrzymanie bazy lub backendu jest widoczne na ekranie stanu (dziennik, dzień 5).

## Do uzupełnienia w pracy
- Odwołania do literatury i dokumentacji technologii.
- Porównanie z alternatywami, jeśli wymaga tego promotor (np. Django, MySQL, Vue).
- Moduły z kolejnych etapów: uwierzytelnianie, import CSV, dashboard (Recharts), moduł AI.
