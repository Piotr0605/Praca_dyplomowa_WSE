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

**Organizacja repozytorium (3.11.2026)**
Utworzono gałąź `main` (stabilna wersja) i `develop` (bieżąca praca). Dotychczasowy stan (dni 1–3) trafił
na `main` i został oznaczony tagiem `tydzien-1-dzien-3`. Od teraz zmiany powstają na `develop` i przechodzą
na `main` przez Pull Request po weryfikacji (zasady: `PLAN_IMPLEMENTACJI.md`, sekcja 7).

Gałąź `main` objęto ochroną na GitHubie: wymagany Pull Request (również dla administratora), zakaz force push
i usuwania gałęzi, wymóg rozwiązania komentarzy w PR. Zweryfikowano próbą bezpośredniego `git push` na `main`,
którą serwer odrzucił (`GH006: Protected branch update failed`). Usunięto starą gałąź roboczą
`claude/lucid-planck-yt04l8` (jej historia w całości zawiera się w `main`).

**Dalej:** dzień 4, Alembic (migracje schematu bazy).

---

## Tydzień 1, dzień 4: migracje bazy danych, Alembic (wykonano 3.11.2026)

**Po co migracje.** Schemat bazy (tabele, kolumny, ograniczenia) będzie się zmieniał co tydzień: dojdą
użytkownicy, transakcje, kategorie, reguły. Migracja to plik Pythona opisujący jedną zmianę schematu
(`upgrade()`) i sposób jej wycofania (`downgrade()`). Pliki są wersjonowane w Gicie razem z kodem, więc
stan bazy da się odtworzyć na każdym komputerze jednym poleceniem, a każda zmiana ma swoją historię.
Alternatywa, czyli `Base.metadata.create_all()`, tworzy tylko brakujące tabele i nie potrafi zmienić istniejących.

**Zrobione**

| Plik | Rola |
|---|---|
| `backend/alembic.ini` | konfiguracja Alembic; nazwy plików migracji z datą i godziną |
| `backend/alembic/env.py` | połączenie Alembic z aplikacją: adres bazy z `DATABASE_URL`, metadane modeli z `Base.metadata` |
| `backend/alembic/script.py.mako` | szablon nowej migracji (typy Pythona 3.13, opisy po polsku) |
| `backend/alembic/README.md` | ściąga poleceń i zasady pracy z migracjami |
| `backend/app/core/database.py` | konwencja nazw ograniczeń w `Base.metadata` |
| `backend/app/models/__init__.py` | miejsce rejestracji modeli (import w `env.py`) |
| `backend/start.sh`, `Dockerfile`, `docker-compose.yml` | start kontenera: `alembic upgrade head`, potem `uvicorn` |

**Decyzje i uzasadnienie**
- **Adres bazy tylko z `.env`, nie z `alembic.ini`.** Hasło nie trafia do repozytorium, a aplikacja i migracje
  zawsze łączą się z tą samą bazą (jedno źródło konfiguracji: klasa `Settings`).
- **Autogenerate.** `env.py` importuje pakiet `app.models` i przekazuje `Base.metadata`, więc
  `alembic revision --autogenerate` porównuje modele z bazą i sam pisze migrację. Włączone `compare_type=True`
  wykrywa też zmiany typów kolumn. Wygenerowaną migrację zawsze się czyta przed commitem: Alembic nie odróżnia
  np. zmiany nazwy kolumny od usunięcia jednej i dodania drugiej (co skasowałoby dane).
- **Konwencja nazw ograniczeń** (`pk_<tabela>`, `uq_<tabela>_<kolumna>`, `fk_<tabela>_<kolumna>_<tabela_docelowa>`,
  `ix_<tabela>_<kolumna>`). Bez niej PostgreSQL nadaje nazwy automatycznie, a migracja, która później zmienia lub
  usuwa ograniczenie, musi znać jego dokładną nazwę. Stałe nazwy czynią migracje przewidywalnymi i czytelnymi
  w komunikatach błędów (np. naruszenie `uq_transactions_user_id_dedup_hash` od razu mówi, co się stało).
- **Migracje przy każdym starcie backendu** (`start.sh`). Baza zawsze ma schemat zgodny z kodem; po `git pull`
  wystarczy restart kontenera. `set -e` zatrzymuje start, gdy migracja się nie powiedzie: lepiej, żeby aplikacja
  nie ruszyła wcale, niż działała na niezgodnym schemacie. `exec` przekazuje procesowi serwera sygnały zatrzymania,
  więc `docker compose stop` wyłącza go od razu i czysto.
- **PostgreSQL wykonuje migracje w transakcji** (transactional DDL). Nieudana migracja jest wycofywana w całości,
  a baza nie zostaje w stanie „w połowie zmienionym”. To jedna z przewag PostgreSQL nad np. MySQL w tym zastosowaniu.

**Weryfikacja**

Pełny cykl sprawdzono na tymczasowym modelu testowym (dwie tabele z kluczem obcym, unikalnością i indeksem),
usuniętym po teście:

| Test | Wynik |
|---|---|
| start backendu bez migracji | `alembic upgrade head` w logach, w bazie tabela `alembic_version`, health HTTP 200 |
| `alembic revision --autogenerate` | wykryte 2 nowe tabele i indeks; plik `20261103_1050_<rev>_test_cyklu_migracji.py` |
| `alembic upgrade head` | tabele utworzone |
| nazwy ograniczeń w bazie | `pk_test_a`, `pk_test_b`, `uq_test_a_email`, `fk_test_b_a_id_test_a`, `ix_test_b_a_id` |
| `alembic check` po upgrade | „No new upgrade operations detected” (modele i baza zgodne) |
| `alembic downgrade -1` | tabele usunięte, została tylko `alembic_version` |
| celowo błędna migracja | start przerwany (`UndefinedTable`), API nie odpowiada, w `alembic_version` brak wpisu (transakcja wycofana) |
| po usunięciu błędnej migracji | backend startuje, health HTTP 200 |
| `ruff check`, `ruff format --check` | bez uwag |

**Dalej:** dzień 5, frontend (React + Vite + TypeScript, Tailwind CSS, strona statusu).

---

## Tydzień 1, dzień 5: frontend (wykonano 4.11.2026)

### Co zostało zrobione
Powstała aplikacja React, która w przeglądarce pokazuje stan systemu: „API: OK, Baza: OK”. Po raz pierwszy
działa cała ścieżka: przeglądarka → frontend → API → baza danych. To główny cel tygodnia 1.

| Plik | Rola |
|---|---|
| `frontend/package.json`, `package-lock.json` | zależności: React 19, Vite 8, TypeScript 7, Tailwind CSS 4, oxlint, Prettier |
| `frontend/vite.config.ts` | wtyczki React i Tailwind, stały port 5173 |
| `frontend/src/types/api.ts` | typ odpowiedzi `/api/health` |
| `frontend/src/api/client.ts` | funkcja `getHealth()` wywołująca API |
| `frontend/src/components/HealthStatus.tsx` | komponent ze statusem API i bazy |
| `frontend/src/App.tsx`, `index.html`, `public/favicon.svg` | strona główna, polski język i tytuł, własna ikona |
| `frontend/Dockerfile`, `.dockerignore` | obraz `node:26-slim` w trybie deweloperskim |
| `docker-compose.yml` | usługa `frontend` |

### Dlaczego
- **Ekran statusu przed funkcjami biznesowymi.** Każda kolejna funkcja przejdzie przez te same warstwy. Sprawdzenie
  ich teraz, na najprostszym przypadku, oddziela późniejsze błędy logiki od błędów konfiguracji (CORS, porty, Docker).
- **Vite + TypeScript.** Vite odświeża stronę natychmiast po zapisie pliku, a TypeScript wykrywa błędy, np. literówkę
  w nazwie pola z API, jeszcze przed uruchomieniem.
- **Tailwind CSS.** Style powstają bezpośrednio w komponentach, a do paczki trafiają tylko użyte klasy (CSS: 9 kB).
- **oxlint zamiast planowanego ESLint.** Aktualny szablon Vite instaluje go domyślnie, a konfiguracja mieści się
  w kilku wierszach. To decyzja analogiczna do Ruffa w backendzie: jedno szybkie narzędzie. Plan zaktualizowano.
- **Bez zewnętrznych czcionek, ikon i bibliotek z CDN.** Wynika to z modelu prywatności (plan, sekcja 9): każde takie
  pobranie byłoby zapytaniem do obcego serwera.

### W jaki sposób
- **Generowanie projektu:** `npm create vite@latest` z szablonem `react-ts`, następnie instalacja `tailwindcss`,
  `@tailwindcss/vite` i `prettier`. Usunięto przykładową zawartość szablonu.
- **Klient API (`client.ts`):** adres pochodzi z `VITE_API_URL`. Kod 503 jest traktowany jako prawidłowa odpowiedź, bo
  oznacza „API działa, baza nie”. Inny kod błędu albo brak odpowiedzi kończy się wyjątkiem.
- **Komponent `HealthStatus`:** rozróżnia trzy stany: sprawdzanie, OK, błąd. Sprawdza API przy wyświetleniu i co
  10 sekund, więc pokazuje awarię i powrót usługi bez przeładowania strony. `AbortController` przerywa zapytanie, gdy
  komponent znika ze strony. Obszar ma `aria-live`, więc czytniki ekranu ogłaszają zmianę stanu.
- **Docker:** katalog `frontend/` jest podmontowany do kontenera, co daje natychmiastowe odświeżanie. Proces działa
  jako zwykły użytkownik `node`, a `npm ci` instaluje dokładnie wersje z `package-lock.json`. Port jest wystawiony
  tylko na `127.0.0.1`, a `strictPort` nie pozwala Vite przejść na inny port (CORS dopuszcza wyłącznie 5173).

### Problemy i rozwiązania
| Problem | Rozwiązanie |
|---|---|
| Katalog `frontend/` miał już szkielet folderów, a generator oczekuje pustego katalogu | projekt wygenerowano w katalogu tymczasowym i skopiowano potrzebne pliki, zachowując szkielet |
| Szablon Vite dostarcza oxlint i TypeScript 7, a plan zakładał ESLint | przyjęto oxlint, zaktualizowano plan i rozszerzenie VS Code |
| Pakiety w `node_modules` zależą od systemu (macOS na komputerze, Linux w kontenerze), więc podmontowany katalog zastąpiłby te właściwe | osobny wolumen `/app/node_modules`; po zmianie zależności: `docker compose up --build -V` |
| Przeglądarka musi łączyć się z API przez port komputera (8001), a nie przez nazwę usługi `backend`, którą zna tylko sieć Dockera | `VITE_API_URL` wskazuje `http://localhost:<port>`; docelowo etap 9 zastąpi to wspólnym adresem przez nginx |
| Przy zatrzymanej bazie konsola przeglądarki pokazuje błąd `503` | to oczekiwane: przeglądarka zawsze zapisuje takie odpowiedzi w konsoli, a aplikacja obsługuje je i pokazuje „Baza: Błąd” |

### Weryfikacja
Stronę sprawdzono w prawdziwej przeglądarce (Chromium sterowany przez Playwright, narzędzie użyte jednorazowo, poza
repozytorium), bo samo zapytanie `curl` nie sprawdza CORS ani tego, co wyświetla React.

| Test | Wynik |
|---|---|
| wszystkie usługi działają | „API: OK, Baza: OK”, brak błędów konsoli (brak błędu CORS) |
| baza zatrzymana | „API: OK, Baza: Błąd” |
| backend zatrzymany | „API: Błąd, Baza: Błąd” |
| po przywróceniu usług | „API: OK, Baza: OK” |
| zatrzymanie i start bazy przy otwartej stronie | status zmienia się sam, bez przeładowania |
| zmiana tekstu w `App.tsx` | nowy tekst widoczny bez przeładowania (hot reload) |
| adresy, z którymi łączy się strona | wyłącznie `localhost:5173` i `localhost:8001` |
| adres nasłuchu frontendu | `127.0.0.1:5173` |
| użytkownik procesu w kontenerze | `node` (nie root) |
| `npm run lint`, `format:check`, `build` | bez uwag |

Zrzut ekranu: `docs/zrzuty/tydzien1_stan_systemu.png`.

### Dalej
Dzień 6: testy (`pytest`), Ruff i GitHub Actions.
