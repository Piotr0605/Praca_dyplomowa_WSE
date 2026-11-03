# Dziennik prac

Zapis kolejnych dni pracy nad aplikacją: co zostało zrobione, dlaczego właśnie tak, jakie były problemy
i jak sprawdzono, że działa. Materiał źródłowy do rozdziałów pracy o realizacji i weryfikacji systemu.

Numeracja dni odpowiada planowi w [`TYDZIEN_1.md`](TYDZIEN_1.md) (i kolejnych tygodni), a nie dacie
kalendarzowej. Data w nawiasie to faktyczny dzień wykonania.

---

## Tydzień 1, dzień 1: środowisko pracy (wykonano 2.11.2026)

**Zrobione**
- Sprawdzenie narzędzi na komputerze deweloperskim (macOS 26.6, Apple Silicon). Wyniki: [`RAPORT_SRODOWISKA.md`](RAPORT_SRODOWISKA.md).
- Doinstalowanie brakujących elementów: Node.js v26.13.0 (LTS), rozszerzenia VS Code (Python, Pylance, Ruff, ESLint, Tailwind CSS, Docker), polecenie `code` w terminalu.
- Środowisko wirtualne Pythona `backend/.venv` (Python 3.13) i plik `.env` z losowo wygenerowanymi sekretami.

**Decyzje i uzasadnienie**
- **Python 3.13 zamiast 3.12.** Wersja już zainstalowana lokalnie (przez `uv`) i aktualnie wspierana. Ta sama wersja lokalnie i w obrazie Dockera eliminuje różnice w zachowaniu między środowiskami. Systemowy Python 3.9 nie jest używany.
- **Node.js w katalogu użytkownika** (`~/.local/share/node`), z oficjalnej paczki nodejs.org po weryfikacji sumy SHA-256. Nie wymaga uprawnień administratora ani Homebrew.
- **Sekrety generowane losowo** (`openssl rand -hex`) zamiast wartości przykładowych. Plik `.env` jest w `.gitignore` i ma uprawnienia 600 (odczyt tylko dla właściciela).

**Weryfikacja:** `docker run hello-world`, wersje wszystkich narzędzi, lista rozszerzeń VS Code.

---

## Tydzień 1, dzień 2: baza danych w Dockerze (wykonano 2.11.2026)

**Zrobione**
- [`docker-compose.yml`](../docker-compose.yml) z usługą `db`: PostgreSQL 16, dane w wolumenie `pgdata`, healthcheck `pg_isready`.

**Decyzje i uzasadnienie**
- **Port wystawiony tylko na `127.0.0.1`.** Baza jest dostępna z komputera dewelopera, ale nie z sieci lokalnej (np. innych urządzeń w tym samym Wi-Fi). Element modelu prywatności opisanego w planie (sekcja 9).
- **Healthcheck.** Docker wie, kiedy baza jest faktycznie gotowa na połączenia, a nie tylko „uruchomiona”. Backend czeka na ten stan (`depends_on: condition: service_healthy`).
- **Wolumen nazwany.** Dane przetrwają zatrzymanie i usunięcie kontenera; kasuje je dopiero `docker compose down -v`.

**Problem i rozwiązanie**
Port 5432 był zajęty przez kontener innego projektu na tym samym komputerze. Zamiast wyłączać tamten projekt,
port po stronie hosta stał się konfigurowalny (`DB_HOST_PORT` w `.env`, domyślnie 5432, lokalnie 5433).
Wewnątrz sieci Dockera baza nadal działa na 5432, więc reszta systemu nie wymaga zmian. To samo zabezpiecza
uruchomienie na innym komputerze (np. podczas obrony), na którym port może być zajęty.

**Weryfikacja**
- `psql` w kontenerze: PostgreSQL 16.15,
- połączenie z hosta (psycopg) przez `127.0.0.1:5433`,
- zapis rekordu, `docker compose down` i ponowne uruchomienie: rekord nadal w bazie (wolumen działa).

---

## Tydzień 1, dzień 3: backend FastAPI (wykonano 3.11.2026)

**Zrobione**

| Plik | Rola |
|---|---|
| `backend/requirements.txt`, `requirements-dev.txt` | zależności z przypiętymi wersjami; narzędzia dev (pytest, httpx, ruff) osobno |
| `backend/app/core/config.py` | klasa `Settings` (pydantic-settings) czytająca `.env` |
| `backend/app/core/database.py` | `engine`, `SessionLocal`, `Base`, zależność `get_db` i alias `DbSession` |
| `backend/app/api/routes/health.py` | `GET /api/health`: wykonuje `SELECT 1` na bazie |
| `backend/app/main.py` | aplikacja FastAPI, CORS, podpięcie routera pod `/api` |
| `backend/Dockerfile`, `.dockerignore` | obraz `python:3.13-slim` |
| `docker-compose.yml` | usługa `backend` |

**Decyzje i uzasadnienie**
- **Przypięte wersje zależności** (`fastapi==0.162.0` itd.). Ten sam kod zbudowany za miesiąc lub na innym komputerze daje te same biblioteki. Bez tego nowa wersja biblioteki mogłaby zepsuć aplikację tuż przed obroną.
- **Konfiguracja walidowana przy starcie.** Brak `DATABASE_URL` zatrzymuje aplikację z czytelnym komunikatem. `extra="ignore"` pozwala trzymać w jednym `.env` zmienne wszystkich usług (baza, frontend).
- **Health zwraca 503, gdy baza nie odpowiada**, zamiast ogólnego błędu 500. Kod 503 (Service Unavailable) mówi precyzyjnie, że API działa, ale jego zależność nie. Frontend pokaże na tej podstawie „API: OK, Baza: błąd”.
- **Jedna sesja bazy na jedno zapytanie HTTP** (Dependency Injection, `Depends(get_db)`), zawsze zamykana po odpowiedzi. Zapis z `Annotated` (`db: DbSession`) to styl zalecany przez dokumentację FastAPI; alias będzie używany we wszystkich kolejnych endpointach.
- **`pool_pre_ping=True`.** Po restarcie kontenera bazy połączenia w puli są martwe; ta opcja sprawdza je przed użyciem, więc aplikacja sama wraca do działania bez restartu.
- **Obraz Dockera:** najpierw kopiowany jest tylko `requirements.txt`, potem kod. Warstwa z zależnościami jest cache'owana, więc zmiana kodu nie wymusza ponownej instalacji bibliotek. Aplikacja działa jako zwykły użytkownik (`appuser`), nie root, co ogranicza skutki ewentualnej luki.
- **Tryb deweloperski:** katalog `backend/` jest podmontowany do kontenera, a `uvicorn --reload --reload-dir app` restartuje serwer po zapisie pliku. Zmiany w kodzie są widoczne w sekundę, bez przebudowy obrazu. Obserwowany jest tylko katalog `app/` (bez tysięcy plików z `.venv`). Wersja produkcyjna bez przeładowania jest w planie na etap 9.
- **CORS tylko dla `http://localhost:5173`** (adres frontendu), a nie `*`. Inne strony otwarte w przeglądarce nie mogą wywoływać API.
- **Port API konfigurowalny** (`BACKEND_HOST_PORT`, domyślnie 8000, lokalnie 8001) z tego samego powodu co port bazy. `VITE_API_URL` musi wskazywać ten sam port.

**Problem i rozwiązanie**
Linter Ruff zgłosił regułę B008 (wywołanie funkcji `Depends()` w wartości domyślnej parametru). Zamiast wyłączać
regułę, kod przeszedł na zapis `Annotated[Session, Depends(get_db)]`, który jest jednocześnie zalecany przez FastAPI.

**Weryfikacja**

| Test | Wynik |
|---|---|
| `GET /api/health` | `{"status":"ok","database":"ok"}`, HTTP 200 |
| `GET /api/health` przy zatrzymanej bazie | `{"status":"degraded","database":"error"}`, HTTP 503 |
| ponowne uruchomienie bazy | HTTP 200 bez restartu backendu |
| `GET /docs` (Swagger UI) | HTTP 200 |
| nagłówek CORS dla `Origin: http://localhost:5173` | `access-control-allow-origin: http://localhost:5173` |
| użytkownik procesu w kontenerze | `appuser` (nie root) |
| zmiana pliku `config.py` | nowy tytuł API widoczny po ~3 s (hot reload) |
| `ruff check`, `ruff format --check` | bez uwag |

**Dalej:** dzień 4, Alembic (migracje schematu bazy).
