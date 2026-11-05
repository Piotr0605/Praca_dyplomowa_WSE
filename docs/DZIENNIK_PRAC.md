# Dziennik prac

Zapis kolejnych dni pracy nad aplikacją: co zostało zrobione, dlaczego, w jaki sposób, jakie problemy się pojawiły
i jak je rozwiązano oraz jak sprawdzono, że działa. Materiał źródłowy do rozdziałów pracy o realizacji i weryfikacji systemu.

Numeracja dni odpowiada planowi w [`TYDZIEN_1.md`](TYDZIEN_1.md) (i kolejnych tygodni), a nie dacie
kalendarzowej. Data w nawiasie to faktyczny dzień wykonania.

---

## Tydzień 1, dzień 1: środowisko pracy (wykonano 2.11.2026)

### Co zostało zrobione
Komputer deweloperski (macOS 26.6, Apple Silicon) przygotowano do pracy nad wszystkimi warstwami aplikacji.
Pełne wyniki kontroli: [`RAPORT_SRODOWISKA.md`](RAPORT_SRODOWISKA.md).

| Element | Stan po konfiguracji |
|---|---|
| Git, Docker Desktop, Docker Compose | były już zainstalowane, działają |
| Node.js | doinstalowano v26.13.0 (LTS), npm 11.20.0 |
| Python | wybrano 3.13, utworzono środowisko `backend/.venv` |
| VS Code | polecenie `code` w terminalu, rozszerzenia: Python, Pylance, Ruff, ESLint, Tailwind CSS, Docker |
| `.env` | utworzony z `.env.example`, z losowymi sekretami |

### Dlaczego
- **Kontrola na początku.** Późniejsze etapy zakładają działający Docker, Pythona i Node.js, a brak narzędzia wykryty
  w środku pracy nad kodem kosztuje więcej czasu.
- **Python 3.13 zamiast 3.12.** Ta wersja była już zainstalowana lokalnie. Ta sama wersja lokalnie i w obrazie Dockera
  ogranicza różnice w zachowaniu między środowiskami.
- **Losowe sekrety zamiast wartości przykładowych.** Hasło bazy i klucz JWT nie mogą być przewidywalne, nawet lokalnie.

### W jaki sposób
- **Kontrola:** sprawdzenie wersji narzędzi, uruchomienie kontenera testowego i sprawdzenie, czy wymagane porty są wolne.
- **Node.js:** oficjalna paczka z nodejs.org, zweryfikowana sumą SHA-256 i rozpakowana do `~/.local/share/node`,
  z dowiązaniami w `~/.local/bin`.
- **Python:** `uv venv --python 3.13 backend/.venv`, a wersja jest zapisana w `backend/.python-version`.
- **Sekrety:** `openssl rand -hex`. Plik `.env` jest w `.gitignore` i ma uprawnienia 600 (odczyt tylko dla właściciela).

### Problemy i rozwiązania
| Problem | Rozwiązanie |
|---|---|
| Brak Node.js i Homebrew | instalacja z oficjalnej paczki w katalogu użytkownika, bez uprawnień administratora |
| `python3` w systemie to wersja 3.9.6, za stara dla projektu | użycie Pythona 3.13 zarządzanego przez `uv`; wersji systemowej nie zmieniano |
| Polecenie `code` niedostępne w terminalu | dowiązanie w `~/.local/bin` do programu z aplikacji VS Code |

### Weryfikacja
| Test | Wynik |
|---|---|
| `docker run hello-world` | kontener uruchomiony |
| `node --version`, `npm --version` | v26.13.0, 11.20.0 |
| `backend/.venv/bin/python --version` | Python 3.13.13 |
| `code --list-extensions` | wymagane rozszerzenia na liście |
| `git check-ignore .env` | plik ignorowany przez Git |

### Dalej
Dzień 2: baza danych w Dockerze.

---

## Tydzień 1, dzień 2: baza danych w Dockerze (wykonano 2.11.2026)

### Co zostało zrobione
Plik [`docker-compose.yml`](../docker-compose.yml) z usługą `db`: PostgreSQL 16, dane w wolumenie `pgdata`,
sprawdzanie gotowości bazy i port dostępny tylko z tego komputera.

### Dlaczego
- **Port tylko na `127.0.0.1`.** Baza jest dostępna z komputera dewelopera, ale nie z sieci lokalnej (np. z innych
  urządzeń w tym samym Wi-Fi). To element modelu prywatności opisanego w planie (sekcja 9).
- **Healthcheck.** Docker wie, kiedy baza jest faktycznie gotowa na połączenia, a nie tylko uruchomiona. Backend czeka
  na ten stan.
- **Wolumen nazwany.** Dane przetrwają zatrzymanie i usunięcie kontenera. Kasuje je dopiero `docker compose down -v`.

### W jaki sposób
- Obraz `postgres:16`, a dane logowania pochodzą z `.env` przez zmienne `${POSTGRES_*}`.
- Healthcheck: `pg_isready` co 5 sekund, maksymalnie 10 prób.
- Port na komputerze jest ustawiany zmienną `DB_HOST_PORT` (domyślnie 5432).

### Problemy i rozwiązania
| Problem | Rozwiązanie |
|---|---|
| Port 5432 zajęty przez kontener innego projektu na tym samym komputerze | zamiast wyłączać tamten projekt, port na komputerze stał się konfigurowalny (`DB_HOST_PORT`, lokalnie 5433). Wewnątrz sieci Dockera baza nadal działa na 5432, więc reszta systemu nie wymaga zmian. To zabezpiecza też uruchomienie na innym komputerze, np. podczas obrony |

### Weryfikacja
| Test | Wynik |
|---|---|
| `psql` w kontenerze | PostgreSQL 16.15 |
| połączenie z komputera (psycopg) przez `127.0.0.1:5433` | działa, użytkownik `finanse` |
| zapis rekordu, `docker compose down`, ponowne uruchomienie | rekord nadal w bazie (wolumen działa); tabelę testową usunięto |

### Dalej
Dzień 3: backend FastAPI.

---

## Tydzień 1, dzień 3: backend FastAPI (wykonano 3.11.2026)

### Co zostało zrobione
Działające API z endpointem `GET /api/health`, który sprawdza połączenie z bazą, uruchamiane w kontenerze razem z bazą.

| Plik | Rola |
|---|---|
| `backend/requirements.txt`, `requirements-dev.txt` | zależności z przypiętymi wersjami; narzędzia deweloperskie (pytest, httpx, ruff) osobno |
| `backend/app/core/config.py` | klasa `Settings` (pydantic-settings) czytająca `.env` |
| `backend/app/core/database.py` | `engine`, `SessionLocal`, `Base`, zależność `get_db` i alias `DbSession` |
| `backend/app/api/routes/health.py` | `GET /api/health`: wykonuje `SELECT 1` na bazie |
| `backend/app/main.py` | aplikacja FastAPI, CORS, podpięcie routera pod `/api` |
| `backend/Dockerfile`, `.dockerignore` | obraz `python:3.13-slim` |
| `docker-compose.yml` | usługa `backend` |

### Dlaczego
- **Przypięte wersje zależności.** Ten sam kod zbudowany za miesiąc lub na innym komputerze dostaje te same biblioteki.
  Bez tego nowa wersja biblioteki mogłaby zepsuć aplikację tuż przed obroną.
- **Konfiguracja walidowana przy starcie.** Brak `DATABASE_URL` zatrzymuje aplikację z czytelnym komunikatem, a nie
  powoduje błędu w przypadkowym miejscu później.
- **Kod 503, gdy baza nie odpowiada, zamiast ogólnego 500.** Mówi precyzyjnie, że API działa, ale jego zależność nie.
  Frontend może na tej podstawie osobno pokazać stan API i bazy.
- **CORS tylko dla `http://localhost:5173`, a nie `*`.** Inne strony otwarte w przeglądarce nie mogą odczytywać
  odpowiedzi API.
- **Użytkownik inny niż root w kontenerze.** Ogranicza skutki ewentualnej luki w aplikacji.

### W jaki sposób
- **Ustawienia:** `extra="ignore"` pozwala trzymać w jednym `.env` zmienne wszystkich usług (baza, frontend).
- **Sesja bazy:** jedna na jedno zapytanie HTTP, wstrzykiwana przez `Depends(get_db)` i zawsze zamykana po odpowiedzi.
- **`pool_pre_ping=True`:** po restarcie bazy połączenia w puli są martwe; ta opcja sprawdza je przed użyciem, więc
  aplikacja sama wraca do działania.
- **Obraz Dockera:** najpierw kopiowany jest `requirements.txt`, potem kod. Warstwa z zależnościami jest cache'owana,
  więc zmiana kodu nie wymusza ponownej instalacji bibliotek.
- **Tryb deweloperski:** katalog `backend/` jest podmontowany do kontenera, a `uvicorn --reload` restartuje serwer po
  zapisie pliku, bez przebudowy obrazu. Wersja produkcyjna jest w planie na etap 9.

### Problemy i rozwiązania
| Problem | Rozwiązanie |
|---|---|
| Port 8000 zajęty przez kontener innego projektu | port API konfigurowalny (`BACKEND_HOST_PORT`, domyślnie 8000, lokalnie 8001); `VITE_API_URL` musi wskazywać ten sam port |
| Ruff zgłosił regułę B008 (wywołanie `Depends()` w wartości domyślnej parametru) | zamiast wyłączać regułę, kod przeszedł na zapis `Annotated[Session, Depends(get_db)]`, zalecany przez FastAPI; alias `DbSession` posłuży też w kolejnych endpointach |
| `--reload` obserwowałby tysiące plików w podmontowanym `.venv` | ograniczenie obserwacji do katalogu aplikacji: `--reload-dir app` |

### Weryfikacja
| Test | Wynik |
|---|---|
| `GET /api/health` | `{"status":"ok","database":"ok"}`, HTTP 200 |
| `GET /api/health` przy zatrzymanej bazie | `{"status":"degraded","database":"error"}`, HTTP 503 |
| ponowne uruchomienie bazy | HTTP 200 bez restartu backendu |
| `GET /docs` (Swagger UI) | HTTP 200 |
| nagłówek CORS dla `Origin: http://localhost:5173` | `access-control-allow-origin: http://localhost:5173` |
| użytkownik procesu w kontenerze | `appuser` (nie root) |
| zmiana pliku `config.py` | nowy tytuł API widoczny po ok. 3 s (hot reload) |
| `ruff check`, `ruff format --check` | bez uwag |

### Dalej
Organizacja repozytorium, a potem dzień 4: Alembic.

---

## Tydzień 1: organizacja repozytorium (wykonano 3.11.2026)

### Co zostało zrobione
- Utworzono gałąź `main` (stabilna wersja) i `develop` (bieżąca praca).
- Stan z dni 1–3 trafił na `main` i został oznaczony tagiem `tydzien-1-dzien-3`.
- Gałąź `main` objęto ochroną na GitHubie i ustawiono jako domyślną.
- Usunięto starą gałąź roboczą `claude/lucid-planck-yt04l8`, której historia w całości zawierała się w `main`.

### Dlaczego
- **Dwie gałęzie.** `main` ma być zawsze działającą wersją, a niedokończona praca zostaje na `develop`.
- **Tagi z adnotacją.** W pracy dyplomowej można odwołać się do konkretnego stanu kodu.
- **Ochrona `main`.** Chroni przed przypadkowym wypchnięciem niesprawdzonego kodu albo nadpisaniem historii.

### W jaki sposób
- Zmiany powstają na `develop` i przechodzą na `main` przez Pull Request po weryfikacji (zasady: `PLAN_IMPLEMENTACJI.md`, sekcja 7).
- Reguły ochrony ustawiono przez API GitHuba: wymagany Pull Request (również dla administratora), zakaz force push
  i usuwania gałęzi, wymóg rozwiązania komentarzy w PR.

### Problemy i rozwiązania
| Problem | Rozwiązanie |
|---|---|
| Na GitHubie nie było gałęzi `main`, a domyślna była gałąź robocza | utworzenie `main` i ustawienie jej jako domyślnej |
| GitHub odrzucił wypychanie, bo token zapisany w Pęku kluczy był nieważny | instalacja GitHub CLI (`gh`) i ponowne logowanie przez przeglądarkę |

### Weryfikacja
| Test | Wynik |
|---|---|
| szukanie `.env`, haseł i plików CSV w historii przed wypchnięciem | nie znaleziono |
| próba bezpośredniego `git push` na `main` | odrzucona przez serwer (`GH006: Protected branch update failed`) |

### Dalej
Dzień 4: Alembic.

---

## Tydzień 1, dzień 4: migracje bazy danych, Alembic (wykonano 3.11.2026)

### Co zostało zrobione
Skonfigurowano Alembic. Zmiany schematu bazy są teraz plikami w repozytorium, a backend stosuje je przy każdym starcie.

| Plik | Rola |
|---|---|
| `backend/alembic.ini` | konfiguracja Alembic; nazwy plików migracji z datą i godziną |
| `backend/alembic/env.py` | połączenie Alembic z aplikacją: adres bazy z `DATABASE_URL`, metadane modeli z `Base.metadata` |
| `backend/alembic/script.py.mako` | szablon nowej migracji |
| `backend/alembic/README.md` | ściąga poleceń i zasady pracy z migracjami |
| `backend/app/core/database.py` | konwencja nazw ograniczeń w `Base.metadata` |
| `backend/app/models/__init__.py` | miejsce rejestracji modeli (import w `env.py`) |
| `backend/start.sh`, `Dockerfile`, `docker-compose.yml` | start kontenera: `alembic upgrade head`, potem `uvicorn` |

### Dlaczego
- **Migracje zamiast `Base.metadata.create_all()`.** Schemat będzie się zmieniał co tydzień: dojdą użytkownicy,
  transakcje, kategorie i reguły. `create_all()` tworzy tylko brakujące tabele i nie potrafi zmienić istniejących.
  Migracja opisuje jedną zmianę (`upgrade()`) i sposób jej wycofania (`downgrade()`), a pliki są wersjonowane razem
  z kodem, więc stan bazy da się odtworzyć na każdym komputerze.
- **Adres bazy tylko z `.env`.** Hasło nie trafia do repozytorium, a aplikacja i migracje zawsze łączą się z tą samą bazą.
- **Konwencja nazw ograniczeń.** Bez niej PostgreSQL nadaje nazwy automatycznie, a migracja, która później zmienia lub
  usuwa ograniczenie, musi znać jego dokładną nazwę. Stałe nazwy są też czytelne w komunikatach błędów.
- **Migracje przy każdym starcie.** Baza zawsze ma schemat zgodny z kodem. Po pobraniu nowego kodu wystarczy restart
  kontenera. Lepiej, żeby aplikacja nie ruszyła wcale, niż działała na niezgodnym schemacie.

### W jaki sposób
- **Autogenerate:** `env.py` importuje pakiet `app.models` i przekazuje `Base.metadata`, więc
  `alembic revision --autogenerate` porównuje modele z bazą i sam pisze migrację. `compare_type=True` wykrywa też
  zmiany typów kolumn. Wygenerowaną migrację zawsze się czyta przed commitem, bo Alembic nie odróżnia np. zmiany nazwy
  kolumny od usunięcia jednej i dodania drugiej, co skasowałoby dane.
- **Nazwy:** `pk_<tabela>`, `uq_<tabela>_<kolumna>`, `fk_<tabela>_<kolumna>_<tabela_docelowa>`, `ix_<tabela>_<kolumna>`.
- **`start.sh`:** `set -e` przerywa start, gdy migracja się nie powiedzie, a `exec` przekazuje serwerowi sygnały
  zatrzymania, więc `docker compose stop` wyłącza go od razu.
- **Transakcje:** PostgreSQL wykonuje migracje w transakcji, więc nieudana zmiana jest wycofywana w całości.

### Problemy i rozwiązania
| Problem | Rozwiązanie |
|---|---|
| Katalog `backend/alembic/` już istniał, a domyślny `env.py` ma adres bazy w `alembic.ini` i nie zna modeli | szablon wygenerowano w katalogu tymczasowym, a pliki projektu napisano na jego podstawie |
| Z komputera nie da się uruchomić Alembica z `DATABASE_URL`, bo adres `db:5432` działa tylko w sieci Dockera | polecenia Alembica są uruchamiane w kontenerze (`docker compose exec backend ...`), opisane w `backend/alembic/README.md` |
| Zapytanie testowe o nazwy ograniczeń nie wykonało się przez błąd w cudzysłowach powłoki | SQL przekazano przez standardowe wejście i powtórzono cały test |

### Weryfikacja
Pełny cykl sprawdzono na tymczasowym modelu testowym (dwie tabele z kluczem obcym, unikalnością i indeksem), usuniętym po teście.

| Test | Wynik |
|---|---|
| start backendu bez migracji | `alembic upgrade head` w logach, w bazie tabela `alembic_version`, health HTTP 200 |
| `alembic revision --autogenerate` | wykryte 2 nowe tabele i indeks |
| `alembic upgrade head` | tabele utworzone |
| nazwy ograniczeń w bazie | `pk_test_a`, `pk_test_b`, `uq_test_a_email`, `fk_test_b_a_id_test_a`, `ix_test_b_a_id` |
| `alembic check` po upgrade | „No new upgrade operations detected” (modele i baza zgodne) |
| `alembic downgrade -1` | tabele usunięte, została tylko `alembic_version` |
| celowo błędna migracja | start przerwany (`UndefinedTable`), API nie odpowiada, w `alembic_version` brak wpisu |
| po usunięciu błędnej migracji | backend startuje, health HTTP 200 |
| `ruff check`, `ruff format --check` | bez uwag |

### Dalej
Dzień 5: frontend.

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

---

## Tydzień 1, dzień 6: testy i CI (wykonano 4.11.2026)

### Co zostało zrobione
Powstały pierwsze testy automatyczne i CI w GitHub Actions. Scalenie zmian do `main` wymaga teraz zielonych testów.

| Plik | Rola |
|---|---|
| `backend/tests/conftest.py` | fixture `client` (`TestClient` FastAPI) |
| `backend/tests/integration/test_health.py` | 4 testy: health z bazą, health bez bazy (503), CORS dla frontendu i dla obcej strony |
| `backend/tests/unit/test_config.py` | 2 testy: brak `DATABASE_URL` zatrzymuje start, dodatkowe zmienne są pomijane |
| `backend/pyproject.toml` | konfiguracja pytest |
| `backend/Dockerfile`, `docker-compose.yml` | obraz deweloperski zawiera pytest i ruff |
| `.github/workflows/ci.yml` | joby `backend` i `frontend` |

### Dlaczego
- **Testy od początku.** Każdy kolejny tydzień dokłada kod, a testy pokazują, czy zmiana nie zepsuła tego, co już działało.
  Ich wyniki są też materiałem do rozdziału o weryfikacji systemu.
- **CI na czystej maszynie.** Wykrywa problemy niewidoczne lokalnie, np. brak zależności w `requirements.txt` albo plik
  niedodany do commita.
- **Wymóg zielonych testów w ochronie `main`.** `main` ma być zawsze działającą wersją, a sama konwencja nie jest
  zabezpieczeniem, bo o testach można zapomnieć.
- **Prawdziwa baza PostgreSQL w teście integracyjnym i w CI.** Ten sam silnik co w aplikacji, więc test sprawdza faktyczne
  połączenie, a nie jego imitację. W CI krok `alembic upgrade head` sprawdza też, czy migracje działają od zera.
- **Job `frontend` ponad plan.** Plan obejmował tylko Pythona, ale frontend też może przestać się budować, a koszt
  dodania tego joba jest niewielki.

### W jaki sposób
- **Testy lokalnie:** `docker compose exec backend pytest`, w tej samej sieci co baza. Obraz wybiera plik zależności
  argumentem `REQUIREMENTS`: Compose przekazuje `requirements-dev.txt`, a domyślny jest `requirements.txt`.
- **Test braku bazy:** `app.dependency_overrides` podmienia `get_db` na sesję zgłaszającą `OperationalError`, więc awarię
  można odtworzyć bez wyłączania kontenera. Fixture czyści podmiany po każdym teście.
- **Workflow:** uruchamia się przy wypchnięciu na `main` i `develop` oraz przy każdym Pull Requeście. Job `backend` to
  PostgreSQL 16 jako `service`, `ruff check`, `ruff format --check`, `alembic upgrade head`, `pytest`. Job `frontend` to
  `npm ci`, lint, sprawdzenie formatowania i build z kontrolą typów. Uprawnienia ograniczono do `contents: read`.
- **Ochrona `main`:** joby `backend` i `frontend` ustawiono jako wymagane statusy przez API GitHuba.

### Problemy i rozwiązania
| Problem | Rozwiązanie |
|---|---|
| Pytest ostrzegał, że `httpx` jest przestarzały przy `TestClient` | zamiana na zalecany `httpx2` w `requirements-dev.txt`; ostrzeżenie zniknęło |
| Obraz backendu nie zawierał narzędzi testowych, a z komputera adres `db:5432` jest nieosiągalny | osobny argument budowania `REQUIREMENTS`, dzięki czemu testy działają w kontenerze |
| Zielone testy same niczego nie dowodzą, bo mogłyby przechodzić zawsze | celowe psucie kodu (patrz weryfikacja) i tymczasowy, zamknięty później PR z czerwonym testem |

### Weryfikacja
| Test | Wynik |
|---|---|
| `pytest` w kontenerze | 6 testów zaliczonych, bez ostrzeżeń |
| błąd: health nie ustawia kodu 503 | wykryty (1 test czerwony) |
| błąd: health zwraca zły stan bazy | wykryty (1 test czerwony) |
| błąd: CORS dopuszcza wszystkie strony | wykryty (1 test czerwony) |
| błąd: `DATABASE_URL` przestaje być wymagany | wykryty (1 test czerwony) |
| pierwszy przebieg GitHub Actions na `develop` | `backend` i `frontend`: sukces |
| tymczasowy PR #3 z celowo czerwonym testem | `backend`: FAILURE, stan scalania: `BLOCKED`; zamknięty bez scalania, gałąź usunięta |

### Dalej
Dzień 7: pełny test od zera, sekcja „Uruchomienie” w README, wyciąg CSV z ING.

---

## Tydzień 1, dzień 7: domknięcie etapu 1 (wykonano 4.11.2026)

### Co zostało zrobione
- Pełny test uruchomienia: `docker compose down -v && docker compose up --build`, a dodatkowo świeży klon repozytorium.
- Sekcja „Uruchomienie” w `README.md`: instalacja, adresy, zajęte porty, przydatne polecenia.
- Notatki do rozdziału pracy: `docs/NOTATKI_TECHNOLOGIE.md`.
- Uzupełnione kryteria ukończenia tygodnia i postęp w planie. Nazwę biblioteki testowej zmieniono w dokumentacji na `httpx2`.
- Katalog `data/private/` na wyciąg bankowy (ignorowany przez Git).

Wyciągi z ING są w `data/private/`, poza repozytorium. Analizę ich formatu opisuje kolejny wpis.

### Dlaczego
- **Test od zera.** Praca na istniejącym środowisku może ukrywać zależność od czegoś, co jest tylko na tym komputerze.
- **Świeży klon.** `down -v` czyści bazę, ale korzysta z plików w katalogu roboczym, w tym z plików ignorowanych przez Git. Dopiero
  klon sprawdza to, co faktycznie jest w repozytorium, czyli sytuację promotora lub komisji.
- **README.** Warunkiem przyjętym w planie jest uruchomienie systemu na innym komputerze bez dodatkowych wyjaśnień.

### W jaki sposób
- **Test 1:** `docker compose down -v`, po którym wolumen bazy powstaje od nowa, potem `docker compose up -d --build`.
- **Test 2:** `git clone` gałęzi `main` do pustego katalogu, `cp .env.example .env`, budowanie obrazów bez cache
  (`build --no-cache`), start jako osobny projekt Compose, a po teście usunięcie jego kontenerów, wolumenu i obrazów.
- W obu testach stan sprawdzono w prawdziwej przeglądarce (Chromium) oraz uruchomiono `pytest` w kontenerze.

### Problemy i rozwiązania
| Problem | Rozwiązanie |
|---|---|
| Na komputerze deweloperskim domyślne porty 5432 i 8000 zajmuje inny projekt, więc klon nie mógł działać na wartościach z `.env.example` | w klonie zmieniono tylko porty (5433, 8001), zgodnie z instrukcją z README. Domyślne porty nie zostały sprawdzone w tym teście |
| Polecenie `docker compose up --no-cache` nie istnieje | przebudowa osobnym poleceniem `docker compose build --no-cache`, a potem `up` |
| Czyszczenie mogło objąć dane innego projektu | sprawdzono przed testem, że wolumen tego projektu zawiera tylko pustą tabelę `alembic_version`, a wolumen tamtego projektu jest osobny; po teście tamte kontenery działały bez przerwy |

### Weryfikacja
| Test | Wynik |
|---|---|
| `down -v` + `up --build` | 3 kontenery działają, gotowe po 10 s (obrazy z cache) |
| świeży klon, build bez cache | 3 kontenery działają, gotowe po 36 s |
| ekran stanu w przeglądarce (oba testy) | „API: OK, Baza: OK”, brak błędów konsoli, połączenia tylko z `localhost` |
| `pytest` w kontenerze (oba testy) | 6 testów zaliczonych |
| `GET /docs` | HTTP 200 |

Czas 36 s dotyczy komputera, na którym obrazy bazowe (`postgres`, `python`, `node`) były już pobrane. Na nowym komputerze
pierwsze uruchomienie potrwa dłużej.

### Dalej
Analiza formatu wyciągów z ING.

---

## Tydzień 1: analiza wyciągów z ING i zmiana planu importu (wykonano 4.11.2026)

### Co zostało zrobione
Przeanalizowano 6 miesięcznych wyciągów z ING w formacie PDF. Do planu dodano parser PDF jako główną ścieżkę importu,
a format opisano w `backend/app/parsers/README.md`. Parser nie został jeszcze napisany (etap 4).

### Dlaczego
- **Plan zakładał import CSV, a pobrane wyciągi są w PDF.** Aplikacja ma działać na danych, które użytkownik faktycznie otrzymuje z banku.
- **PDF zawiera dane kontrolne.** Salda oraz liczby i sumy operacji pozwalają automatycznie wykryć błąd odczytu, zanim trafi do bazy.
- **Numer transakcji** daje pewniejszą deduplikację niż hash daty, kwoty i opisu: dwa identyczne zakupy tego samego dnia nie zostaną uznane za duplikat.

### W jaki sposób
- Porównano układ tabel i przypadki szczególne w 6 wyciągach oraz sprawdzono zgodność sald w nagłówkach.
- **Zakres:** parser PDF stał się wymaganiem MUST, a importer uniwersalny CSV SHOULD, z możliwością przeniesienia do bufora świątecznego.
- **Dane:** prawdziwe pliki pozostają poza repozytorium, a testy i pokaz opierają się na sztucznym PDF o tym samym układzie.

### Problemy i rozwiązania
| Problem | Rozwiązanie |
|---|---|
| Tekst PDF nie ma struktury tabeli, a transakcje przechodzą między stronami | odczyt według współrzędnych; wybór biblioteki po próbie na prawdziwych plikach w etapie 4 |
| Automatyczne przelewy oszczędnościowe zawyżyłyby wydatki | osobne oznaczanie przelewów własnych (etapy 4 i 5) |
| Pliki PDF nie były ignorowane przez Git poza `data/private/` | reguła `*.pdf` w `.gitignore`, z wyjątkiem sztucznych danych testowych |

### Weryfikacja
| Test | Wynik |
|---|---|
| saldo początkowe + uznania − obciążenia = saldo końcowe (6 wyciągów) | zgodne we wszystkich |
| saldo końcowe = saldo początkowe następnego wyciągu (5 przejść) | zgodne we wszystkich |
| `git check-ignore` dla pliku PDF poza `data/private/` | plik ignorowany |

Działanie parsera zostanie sprawdzone po jego napisaniu.

### Dalej
Tydzień 2: model danych i uwierzytelnianie.

---

## Tydzień 2, dzień 1: modele danych (wykonano 5.11.2026)

### Co zostało zrobione
Powstało 6 modeli SQLAlchemy w `backend/app/models/`: `User`, `Category`, `Transaction`, `ImportBatch`, `CategoryRule`,
`AIAdvice`. Tabel nie ma jeszcze w bazie deweloperskiej, bo pierwsza migracja powstanie w dniu 2.

### Dlaczego
- **Reguły w bazie, a nie tylko w kodzie.** Ograniczenia działają niezależnie od błędów aplikacji: duplikat transakcji albo niepoprawna wartość zostaną odrzucone także wtedy, gdy kod ich nie wykryje.
- **`booking_date` i `kind` w transakcji.** Wynikają z analizy wyciągów ING. Analiza ma opierać się na dacie operacji, a przelewy własne, np. Smart Saver, nie mogą zawyżać wydatków. Dodanie tych pól teraz oszczędza późniejszej zmiany struktury.
- **`NUMERIC(12,2)` dla kwot.** Typy zmiennoprzecinkowe dają błędy zaokrągleń, a tu suma 0,10 i 0,20 to dokładnie 0,30.
- **Usuwanie danych.** Usunięcie użytkownika kasuje wszystkie jego dane, co wspiera model prywatności. Usunięcie kategorii lub importu nie kasuje historii finansowej.

### W jaki sposób
- **Wartości wyliczeniowe** (`source`, `kind`, `match_type`) to tekst z ograniczeniem `CHECK` zamiast natywnego `ENUM` PostgreSQL, który trudniej później zmieniać w migracjach.
- **Unikalność kategorii:** `UNIQUE (user_id, name)` z opcją `NULLS NOT DISTINCT` z PostgreSQL 15+. Domyślnie wartości `NULL` uznawane są za różne, więc kategorie systemowe mogłyby się powtarzać.
- **Transakcje ręczne** mają `dedup_hash = NULL`, dzięki czemu dwa identyczne zakupy tego samego dnia są dozwolone, a duplikaty z importu nadal są blokowane.
- **E-mail:** `CHECK (email = lower(email))` gwarantuje, że wielkość liter nie utworzy drugiego konta.
- **Reguły kategoryzacji:** `CHECK` pilnuje, że reguła systemowa nie ma właściciela, a reguła użytkownika musi go mieć.
- **Indeks `(user_id, date)`** obsługuje główne zapytanie aplikacji: transakcje użytkownika z wybranego okresu.
- **Bez relacji ORM (`relationship`).** Klucze obce wystarczają na tym etapie; relacje dojdą w repozytoriach, gdy będą potrzebne.

### Problemy i rozwiązania
| Problem | Rozwiązanie |
|---|---|
| Testy trzech reguł unikalności przeszły z niewłaściwego powodu: skrypt wstawiał jawne numery `id`, więc odrzucenie wynikało z kolizji klucza głównego (`pk_users`, `pk_categories`) | ustawienie sekwencji `id` poza zakres i wymaganie konkretnej nazwy ograniczenia w każdym teście |
| Skrypt kontrolny potraktował `:1` w tekście JSON jako parametr zapytania | przekazanie JSON jako parametru z rzutowaniem na `jsonb` |
| Baza nie sprawdza, czy `category_id` należy do tego samego użytkownika: jedna kategoria może być systemowa, więc prosty klucz obcy tego nie wyrazi | sprawdzenie w warstwie aplikacji, zadanie do etapu 3 z testem izolacji |

### Weryfikacja
Na tymczasowej bazie PostgreSQL, usuniętej po teście, wykonano 24 sprawdzenia. Odrzucenia musiały pochodzić od oczekiwanego ograniczenia.

| Test | Wynik |
|---|---|
| e-mail wielkimi literami | odrzucony: `ck_users_email_lowercase` |
| zduplikowany e-mail | odrzucony: `uq_users_email` |
| powtórzona kategoria systemowa i użytkownika | odrzucone: `uq_categories_user_id_name` |
| ta sama nazwa kategorii u dwóch użytkowników | dozwolona |
| duplikat `dedup_hash` u tego samego użytkownika | odrzucony: `uq_transactions_user_id_dedup_hash` |
| ten sam hash u innego użytkownika, dwie identyczne transakcje ręczne | dozwolone |
| błędne `source`, `kind`, waluta, kwota poza zakresem, odwrócony okres porady | odrzucone |
| reguła systemowa z właścicielem, reguła użytkownika bez właściciela | odrzucone: `ck_category_rules_source_matches_owner` |
| 0,10 + 0,20 | dokładnie 0,30 |
| usunięcie kategorii | transakcja zostaje, reguła znika |
| usunięcie importu | transakcja zostaje |
| usunięcie użytkownika | wszystkie jego dane znikają; dane innego użytkownika i systemowe zostają |
| `pytest` (w tym 3 nowe testy reguł modelu, m.in. każda tabela danych ma `user_id`) | 9 testów zaliczonych |
| `ruff check`, `ruff format` | bez uwag |

Skrypt kontrolny był jednorazowy i nie ma go w repozytorium. Trwałe testy na bazie powstaną w dniu 5.

### Dalej
Dzień 2: pierwsza migracja i kategorie systemowe.

---

## Tydzień 2, dzień 2: pierwsza migracja i kategorie systemowe (wykonano 5.11.2026)

### Co zostało zrobione
- Pierwsza migracja tworzy 6 tabel, a druga dodaje 16 kategorii systemowych. Obie działają już w bazie deweloperskiej.
- Diagram ERD w `docs/diagramy/erd.md`.
- CI sprawdza teraz zgodność modeli z migracjami oraz cofanie migracji.
- Odłożone sprawy trafiły jako zadania do właściwych etapów planu.

### Dlaczego
- **Schemat i kategorie w osobnych migracjach.** Zmiana struktury i wstawienie danych to różne operacje, łatwiej je czytać i cofać osobno.
- **Lista kategorii zapisana w migracji**, a nie importowana z kodu aplikacji. Migracja ma działać tak samo także po przyszłych zmianach modeli.
- **`alembic check` i cofanie w CI.** Bez tego zmiana modelu bez migracji przeszłaby testy, a aplikacja nie działałaby na czystej bazie.
- **ERD generowany ze schematu**, a nie rysowany ręcznie, więc odpowiada faktycznym kolumnom.

### W jaki sposób
- Migrację schematu wygenerował `alembic revision --autogenerate`; plik przeczytano przed commitem.
- Kategorie dodaje `op.bulk_insert` na lekkim widoku tabeli `sa.table(...)`, niezależnym od modeli ORM.
- `downgrade()` usuwa tylko kategorie systemowe z tej listy.
- Kolory i ikony kategorii są na razie puste; zostaną dobrane pod wykresy w etapie 6.

### Problemy i rozwiązania
| Problem | Rozwiązanie |
|---|---|
| Ruff uznawał katalog `backend/alembic/` za własny pakiet i odrzucał kolejność importów w migracjach, co zatrzymałoby CI | `known-third-party = ["alembic"]` w `pyproject.toml` zamiast ręcznej poprawy każdej migracji |
| `alembic check` nie porównuje ograniczeń `CHECK`, więc ich późniejsza zmiana w modelu nie zostanie wykryta | sprawdzono je w bazie po migracji; przy zmianach trzeba pisać je w migracji ręcznie |
| Renderowanie diagramu narzędziem `mermaid-cli` zablokował mechanizm uprawnień, bo wymagało pobrania pakietu | diagram w formacie Mermaid, wyświetlany przez GitHub; poprawność wyglądu trzeba sprawdzić po wypchnięciu |

### Weryfikacja
| Test | Wynik |
|---|---|
| restart backendu | obie migracje wykonane automatycznie, health HTTP 200 |
| `alembic check` po `upgrade` | „No new upgrade operations detected” |
| ograniczenia `CHECK` w bazie po migracji | wszystkie 8 obecnych |
| kategorie systemowe | 16, w tym 1 przychodowa (Wynagrodzenie) |
| `alembic downgrade base` | została tylko tabela `alembic_version` |
| ponowny `upgrade` | 7 tabel, 16 kategorii, `alembic check` bez różnic |
| cofnięcie kategorii przy istniejącej kategorii użytkownika | systemowe usunięte, kategoria użytkownika zostaje |
| dane testowe po sprawdzeniach | usunięte: 0 użytkowników, 16 kategorii |
| `pytest` | 10 testów zaliczonych |
| `ruff check`, `ruff format --check`, lokalnie i w kontenerze | bez uwag |

### Dalej
Dzień 3: hasła Argon2, tokeny JWT i rozwiązanie problemu przykładowego klucza z `.env.example`.
