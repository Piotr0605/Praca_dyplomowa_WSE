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
| Testy           | pytest, HTTPX                                                   |
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
│       ├── integration/         # HTTPX: endpointy API + izolacja użytkowników
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

Instrukcja pojawi się po zakończeniu etapu 1 (docelowo: `docker compose up --build`).
