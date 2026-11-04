# Tydzień 1 (2–8 listopada 2026): fundament aplikacji

**Cel tygodnia:** po wpisaniu jednego polecenia `docker compose up --build` uruchamiają się trzy kontenery
(baza, backend, frontend), a strona w przeglądarce pokazuje komunikat „API działa, baza działa”.
Na tym etapie nie ma jeszcze żadnej funkcji biznesowej. Budujemy „rury”, przez które później popłyną dane.

Dlaczego od tego zaczynamy? Każda późniejsza funkcja (logowanie, import, porady) przechodzi przez
wszystkie warstwy: React → FastAPI → SQLAlchemy → PostgreSQL. Jeśli połączenie między warstwami działa
od pierwszego tygodnia, każdą kolejną funkcję dokładamy w znane miejsce i od razu ją widać w przeglądarce.

---

## 1. Jak to wygląda po uruchomieniu

```
                    Twój komputer (Docker Compose)
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  Przeglądarka ──► frontend:5173 ──HTTP/JSON──► backend:8000 ──SQL──► db:5432
│  (Ty)             React + Vite                  FastAPI + Uvicorn     PostgreSQL
│                                                    │                  (wolumen
│                                                    └─ /docs (Swagger)  pgdata)
└──────────────────────────────────────────────────────────────────────┘
```

| Adres | Co tam jest |
|---|---|
| http://localhost:5173 | aplikacja React (na razie strona statusu) |
| http://localhost:8000/docs | automatyczna dokumentacja API (Swagger UI), można klikać i testować endpointy |
| http://localhost:8000/api/health | `{"status": "ok", "database": "ok"}` |
| localhost:5432 | baza PostgreSQL (podgląd np. w DBeaver lub pgAdmin) |

---

## 2. Technologie tygodnia 1: co to jest, jak działa, po co nam to

### Docker i Docker Compose
- **Co to:** Docker uruchamia programy w *kontenerach*, czyli odizolowanych „pudełkach” z własnym systemem plików
  i zainstalowanymi zależnościami. Przepis na pudełko to `Dockerfile`, gotowe pudełko to *obraz*.
  Docker Compose opisuje w jednym pliku `docker-compose.yml`, jakie kontenery mają działać razem.
- **Jak działa:** Compose tworzy wspólną sieć, w której kontenery widzą się po nazwach usług.
  Backend łączy się z bazą pod adresem `db:5432`, a nie `localhost`. Dane bazy trzymamy w *wolumenie*
  (`pgdata`), więc nie znikają po zatrzymaniu kontenera.
- **Po co nam:** jedno polecenie stawia cały system na dowolnym komputerze (u Ciebie, u promotora, na obronie).
  Nie trzeba ręcznie instalować PostgreSQL. Dane zostają lokalnie, co jest argumentem prywatności w pracy.

### PostgreSQL
- **Co to:** relacyjna baza danych SQL, open source.
- **Jak działa:** dane w tabelach z typami i relacjami (klucze obce), transakcje ACID, ograniczenia `UNIQUE`.
- **Po co nam:** pieniądze wymagają typu `NUMERIC` (dokładne kwoty, bez błędów zaokrągleń `float`),
  relacji użytkownik → transakcje → kategorie i ograniczenia `UNIQUE(user_id, dedup_hash)` blokującego duplikaty przy imporcie.
  `JSONB` przyda się do zapisu danych wysłanych do AI.

### Python + FastAPI + Uvicorn
- **Co to:** FastAPI to framework do budowy REST API. Uvicorn to serwer, który go uruchamia (ASGI).
- **Jak działa:** funkcja oznaczona dekoratorem `@router.get("/api/health")` staje się endpointem.
  Typy parametrów i odpowiedzi (adnotacje Pythona + Pydantic) FastAPI wykorzystuje do walidacji wejścia,
  serializacji do JSON i wygenerowania dokumentacji OpenAPI pod `/docs`.
  *Dependency Injection* (`Depends(get_db)`) dostarcza do funkcji np. sesję bazy, a później zalogowanego użytkownika.
- **Po co nam:** mało kodu, automatyczna dokumentacja (dobra do pracy i do testowania), natywna współpraca z Pandas
  i bibliotekami OpenAI/Anthropic.

### Pydantic + pydantic-settings
- **Co to:** biblioteka do walidacji danych na podstawie typów.
- **Jak działa:** definiujesz klasę z polami i typami. Pydantic sprawdza dane i zamienia je na właściwe typy
  albo zwraca czytelny błąd (FastAPI odsyła go jako HTTP 422). `pydantic-settings` wczytuje konfigurację ze zmiennych
  środowiskowych / pliku `.env` i waliduje ją przy starcie.
- **Po co nam (w tygodniu 1):** klasa `Settings` w `core/config.py`. Brak `DATABASE_URL` = aplikacja nie wystartuje
  i powie dlaczego, zamiast wywrócić się później w losowym miejscu.

### SQLAlchemy 2.0
- **Co to:** ORM, czyli mapowanie klas Pythona na tabele bazy.
- **Jak działa:** `engine` zarządza pulą połączeń, `Session` to „jednostka pracy” (zmiany zatwierdzasz `commit()`).
  Modele piszemy jako klasy z polami `Mapped[...]`.
- **Po co nam:** zapytania w Pythonie zamiast ręcznego SQL, ochrona przed SQL injection (parametryzacja),
  łatwe filtrowanie po `user_id` w repozytoriach. W tygodniu 1 tylko konfigurujemy połączenie i klasę bazową modeli.

### Alembic
- **Co to:** narzędzie do migracji schematu bazy (to samo, czym Git jest dla kodu, Alembic jest dla struktury tabel).
- **Jak działa:** każda zmiana schematu to plik w `alembic/versions/` z funkcjami `upgrade()` i `downgrade()`.
  `alembic revision --autogenerate` porównuje modele SQLAlchemy z bazą i generuje migrację, `alembic upgrade head`
  ją wykonuje. W bazie tabela `alembic_version` pamięta, która wersja jest aktualna.
- **Po co nam:** schemat bazy jest wersjonowany razem z kodem, każdy (i kontener przy starcie) może odtworzyć bazę
  od zera. W tygodniu 1 robimy `alembic init` i konfigurację, pierwsze tabele powstaną w tygodniu 2.

### React + TypeScript + Vite
- **Co to:** React buduje interfejs z komponentów (funkcja zwracająca kawałek UI). TypeScript dodaje typy do JavaScriptu.
  Vite to serwer deweloperski i narzędzie do budowania.
- **Jak działa:** komponent ma stan (`useState`); gdy stan się zmienia, React przerysowuje tylko to, co trzeba.
  Vite serwuje pliki z natychmiastowym przeładowaniem po zapisie (HMR), a przy `npm run build` tworzy zoptymalizowane pliki statyczne.
- **Po co nam:** interfejs złożony z niezależnych części (karty, wykresy, tabela). TypeScript wyłapie np. literówkę
  w nazwie pola z API przed uruchomieniem. W tygodniu 1: jeden komponent `HealthStatus`, który woła `/api/health`.

### Tailwind CSS
- **Co to:** CSS w postaci klas narzędziowych (`p-4`, `rounded-lg`, `text-emerald-600`).
- **Jak działa:** klasy piszesz od razu w JSX, a przy budowaniu Tailwind zostawia w pliku CSS tylko użyte style.
- **Po co nam:** szybkie, spójne stylowanie bez osobnych plików CSS dla każdego komponentu.

### pytest + httpx2
- **Co to:** pytest uruchamia testy (funkcje `test_*` z `assert`). httpx2 to klient HTTP, przez który `TestClient`
  FastAPI wysyła zapytania do aplikacji bez stawiania serwera.
- **Po co nam:** od pierwszego dnia mamy test `GET /api/health → 200`. Każdy kolejny tydzień dokłada testy.
  Wyniki testów i pokrycie kodu to materiał do rozdziału o weryfikacji systemu.

### Ruff + GitHub Actions (CI)
- **Ruff:** bardzo szybki linter i formatter Pythona (zastępuje flake8, isort, black).
- **GitHub Actions:** plik `.github/workflows/ci.yml` sprawia, że przy każdym `git push` GitHub uruchamia lint i testy
  na czystej maszynie z bazą PostgreSQL. Zielony znaczek = kod działa nie tylko „u mnie”.

---

## 3. Dzień po dniu

### Poniedziałek 2.11: środowisko
- [x] Zainstaluj: **Git**, **Docker Desktop** (Windows: z WSL2), **Python 3.13**, **Node.js LTS**, **VS Code**
  (rozszerzenia: Python, Pylance, Ruff, oxc (oxlint), Tailwind CSS IntelliSense, Docker)
- [x] Sklonuj repozytorium, utwórz `.env` z `.env.example`
- [x] Sprawdź: `docker --version`, `docker compose version`, `python --version`, `node --version`

### Wtorek 3.11: baza w Dockerze
- [x] `docker-compose.yml` z usługą `db` (obraz `postgres:16`, zmienne z `.env`, wolumen `pgdata`, `healthcheck` z `pg_isready`)
- [x] `docker compose up db`, połączenie z bazą z kontenera (`psql`) i z hosta (port z `DB_HOST_PORT`), dane przetrwały restart
- [ ] (opcjonalnie) podgląd bazy w DBeaver/pgAdmin

```yaml
services:
  db:
    image: postgres:16
    env_file: .env
    ports: ["5432:5432"]
    volumes: [pgdata:/var/lib/postgresql/data]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $${POSTGRES_USER}"]
      interval: 5s
      retries: 10
volumes:
  pgdata:
```

### Środa 4.11: backend FastAPI
- [x] `backend/requirements.txt` (fastapi, uvicorn[standard], sqlalchemy, psycopg[binary], alembic, pydantic-settings, pandas)
  i `requirements-dev.txt` (pytest, httpx2, ruff)
- [x] `app/core/config.py` (klasa `Settings`), `app/core/database.py` (`engine`, `SessionLocal`, `get_db`, `Base`)
- [x] `app/main.py`: aplikacja, CORS dla `http://localhost:5173`, router z `GET /api/health` wykonującym `SELECT 1`
- [x] `backend/Dockerfile` i usługa `backend` w Compose (`depends_on: db: condition: service_healthy`)

```python
# app/api/routes/health.py (szkic)
@router.get("/health")
def health(db: Session = Depends(get_db)) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "ok"}
```

### Czwartek 5.11: Alembic
- [x] `alembic init alembic`, w `env.py` podpięcie `Base.metadata` i `settings.DATABASE_URL`
- [x] start kontenera backendu wykonuje `alembic upgrade head`, potem `uvicorn`
- [x] sprawdź, że w bazie pojawiła się tabela `alembic_version`

### Piątek 6.11: frontend
- [x] `npm create vite@latest frontend -- --template react-ts` (w istniejącym katalogu)
- [x] Tailwind CSS (wtyczka `@tailwindcss/vite`), oxlint (linter z szablonu Vite, zamiast ESLint) + Prettier
- [x] `src/api/client.ts` (adres z `VITE_API_URL`), komponent `HealthStatus` z zielonym/czerwonym statusem
- [x] `frontend/Dockerfile` (tryb dev) i usługa `frontend` w Compose

### Sobota 7.11: testy i CI
- [x] `tests/conftest.py` z `TestClient`, `tests/integration/test_health.py`, `tests/unit/test_config.py`
- [x] `ruff check` i `ruff format`
- [x] `.github/workflows/ci.yml`: Python + usługa `postgres`, `ruff check`, `pytest`; dodatkowo job `frontend` (lint, formatowanie, build)

### Niedziela 8.11: domknięcie i przygotowanie do kolejnych etapów
- [x] Pełny test: `docker compose down -v && docker compose up --build`, dodatkowo świeży klon repozytorium
- [x] Sekcja „Uruchomienie” w README
- [x] Pobrane z ING wyciągi z 6 miesięcy (PDF); format opisany w `backend/app/parsers/README.md`. To wejście do etapu 4.
- [x] Zapisanie wyciągów w `data/private/`
- [x] Notatki do rozdziału pracy „Wykorzystane technologie”: [`NOTATKI_TECHNOLOGIE.md`](NOTATKI_TECHNOLOGIE.md)

---

## 4. Definition of Done tygodnia 1
- [x] `docker compose up --build` uruchamia `db`, `backend`, `frontend` bez błędów
- [x] http://localhost:5173 pokazuje „API: OK, Baza: OK”
- [x] http://localhost:8000/docs działa (lokalnie port 8001, patrz `BACKEND_HOST_PORT`)
- [x] `pytest` przechodzi lokalnie i w GitHub Actions
- [x] Na GitHubie są PR-y etapu 1 z tagami `tydzien-1-dzien-*`, a w `PLAN_IMPLEMENTACJI.md` odhaczony postęp

## 5. Struktura plików po tygodniu 1

```
.
├── docker-compose.yml
├── .env.example
├── .github/workflows/ci.yml
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt / requirements-dev.txt
│   ├── alembic.ini
│   ├── alembic/ (env.py, versions/)
│   ├── app/
│   │   ├── main.py
│   │   ├── core/config.py, core/database.py
│   │   └── api/routes/health.py
│   └── tests/conftest.py, tests/integration/test_health.py
└── frontend/
    ├── Dockerfile
    ├── package.json, vite.config.ts, tsconfig.json
    └── src/main.tsx, App.tsx, api/client.ts, components/HealthStatus.tsx
```
