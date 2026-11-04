# Inteligentny system do analizy finansów osobistych z modułem doradczym AI

Praca dyplomowa (WSE). Aplikacja webowa, która importuje historię transakcji z banku (CSV)
lub przyjmuje wydatki dodane ręcznie, przypisuje je do kategorii, pokazuje strukturę wydatków
i — na podstawie **zagregowanych i zanonimizowanych** danych — generuje porady oszczędnościowe
przy pomocy modelu językowego (OpenAI / Anthropic).

> Zasada projektu: **liczy kod (Pandas), model językowy tylko interpretuje wyniki.**

## Stos technologiczny

| Warstwa         | Technologie                                                    |
|-----------------|----------------------------------------------------------------|
| Backend         | Python 3.13, FastAPI, Pydantic v2, SQLAlchemy 2.0, Alembic     |
| Analityka       | Pandas                                                          |
| AI              | OpenAI API / Anthropic API (wymienny „provider”)                |
| Baza danych     | PostgreSQL 16 (Docker)                                          |
| Uwierzytelnianie| JWT, hasła haszowane Argon2                                     |
| Frontend        | React + TypeScript (Vite), Tailwind CSS, Recharts               |
| Testy           | pytest, httpx2                                                  |
| Infrastruktura  | Docker Compose, Git/GitHub, GitHub Actions (CI)                 |

## Struktura repozytorium

```
.
├── backend/
│   ├── app/
│   │   ├── main.py              # punkt wejścia FastAPI
│   │   ├── core/                # konfiguracja, bezpieczeństwo (JWT, Argon2), sesja DB
│   │   ├── api/
│   │   │   ├── deps.py          # zależności: get_db, get_current_user
│   │   │   └── routes/          # auth, transactions, categories, imports, analytics, advice
│   │   ├── models/              # modele SQLAlchemy (tabele)
│   │   ├── schemas/             # schematy Pydantic (wejście/wyjście API)
│   │   ├── repositories/        # dostęp do danych — ZAWSZE filtrowany po user_id
│   │   ├── services/            # logika biznesowa: import, kategoryzacja, analityka
│   │   ├── parsers/             # parsery CSV banków (wzorzec: klasa bazowa + rejestr)
│   │   └── ai/
│   │       ├── anonymizer.py    # usuwanie danych osobowych (regex)
│   │       ├── prompt_builder.py# budowa promptu z agregatów
│   │       └── providers/       # openai.py, anthropic.py, mock.py
│   ├── alembic/                 # migracje schematu bazy
│   └── tests/
│       ├── unit/                # pytest: parsery, kategoryzacja, analityka, anonimizacja
│       ├── integration/         # TestClient: endpointy API + izolacja użytkowników
│       └── fixtures/            # sztuczne pliki CSV do testów
├── frontend/
│   └── src/
│       ├── api/                 # klient HTTP + funkcje wywołujące backend
│       ├── components/          # ui/, charts/, layout/, transactions/
│       ├── pages/               # Login, Register, Dashboard, Transactions, Import, Advice
│       ├── hooks/  context/     # useAuth, AuthContext itp.
│       ├── types/               # typy TS zgodne ze schematami API
│       └── utils/               # formatowanie kwot, dat
├── data/samples/                # sztuczne dane demonstracyjne
├── docs/                        # plan, architektura, diagramy, zrzuty ekranu do pracy
├── .github/workflows/           # CI: testy + lint
├── docker-compose.yml           # (tydzień 1) db + backend + frontend
└── .env.example
```

## Plan prac

Szczegółowy plan krok po kroku: [`docs/PLAN_IMPLEMENTACJI.md`](docs/PLAN_IMPLEMENTACJI.md).
Co zostało zrobione każdego dnia i dlaczego: [`docs/DZIENNIK_PRAC.md`](docs/DZIENNIK_PRAC.md).

## Uruchomienie

Wymagania: Git i Docker Desktop z Docker Compose. Bazy, Pythona ani Node.js nie trzeba instalować osobno.

```bash
git clone https://github.com/Piotr0605/Praca_dyplomowa_WSE.git
cd Praca_dyplomowa_WSE
cp .env.example .env
docker compose up --build
```

Pierwsze uruchomienie pobiera obrazy i zależności, więc trwa dłużej i wymaga internetu. Później wystarczy
`docker compose up`. Przy starcie backend sam wykonuje migracje bazy.

Przed dłuższym użyciem zmień w `.env` wartości `POSTGRES_PASSWORD` (także w `DATABASE_URL`) i `JWT_SECRET_KEY`,
np. na wynik `openssl rand -hex 32`.

| Adres | Co tam jest |
|---|---|
| http://localhost:5173 | aplikacja |
| http://localhost:8000/docs | dokumentacja API (Swagger UI) |
| http://localhost:8000/api/health | stan API i bazy |

### Zajęte porty

Komunikat `port is already allocated` oznacza, że port zajmuje inny program. Zmień port w `.env` i uruchom ponownie:

| Zmienna | Domyślnie | Uwagi |
|---|---|---|
| `DB_HOST_PORT` | 5432 | |
| `BACKEND_HOST_PORT` | 8000 | ten sam port wpisz w `VITE_API_URL`; zmienią się też adresy API z tabeli powyżej |

Port frontendu (5173) jest stały, bo tylko ten adres jest dopuszczony przez CORS w backendzie.

### Przydatne polecenia

| Cel | Polecenie |
|---|---|
| Zatrzymanie (dane zostają) | `docker compose down` |
| Zatrzymanie i **usunięcie danych** | `docker compose down -v` |
| Testy backendu | `docker compose exec backend pytest` |
| Lint backendu | `docker compose exec backend ruff check .` |
| Po zmianie zależności frontendu | `docker compose up --build -V` |
| Migracje bazy | zobacz [`backend/alembic/README.md`](backend/alembic/README.md) |
