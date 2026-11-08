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

---

## Tydzień 2, dzień 3: hasła, tokeny i klucz JWT (wykonano 5.11.2026)

### Co zostało zrobione
| Plik | Rola |
|---|---|
| `backend/app/core/security.py` | `hash_password`, `verify_password`, `create_access_token`, `decode_access_token` |
| `backend/app/core/jwt_key.py` | odczyt klucza albo wygenerowanie go przy pierwszym uruchomieniu |
| `backend/app/core/config.py` | ustawienia JWT z walidacją |
| `backend/app/main.py` | sprawdzenie klucza przy starcie aplikacji |
| `backend/tests/unit/test_security.py` | testy haseł, tokenów i klucza |
| `.env.example`, `docker-compose.yml`, `Dockerfile` | pusty klucz w przykładzie, wolumen `backend_data` na klucz |

Endpointów logowania jeszcze nie ma: powstaną w dniu 4.

### Dlaczego
- **Argon2id.** Zużywa czas i pamięć, więc masowe zgadywanie haseł po wycieku bazy jest kosztowne. Sól jest losowa, więc te same hasła mają różne hashe.
- **W tokenie tylko identyfikator użytkownika.** Zawartość JWT można odczytać bez klucza, więc e-mail ani inne dane osobowe nie mogą się w nim znaleźć.
- **Brak klucza w repozytorium.** Repozytorium jest publiczne, więc każdy mógłby użyć przykładowego klucza do podrobienia tokenu. Samo ostrzeżenie zostawiałoby tę możliwość otwartą.
- **Klucz generowany automatycznie, a nie obowiązkowo wpisywany.** `cp .env.example .env` ma nadal wystarczać do uruchomienia, np. u promotora.

### W jaki sposób
- **Argon2:** domyślne parametry biblioteki `argon2-cffi` (profil RFC 9106: 64 MiB pamięci, 3 iteracje, 4 wątki).
- **Weryfikacja tokenu:** jawna lista algorytmów blokuje token z `alg: none` i z innym algorytmem niż ustawiony. `exp` i `sub` są wymagane. Każdy błąd daje jeden wyjątek `InvalidTokenError`, więc później przełoży się na jeden kod odpowiedzi 401.
- **Klucz:** `secrets.token_hex(32)`, plik `/data/jwt_secret` w wolumenie Dockera z uprawnieniami 600. `O_EXCL` gwarantuje, że istniejący klucz nie zostanie nadpisany. Usunięcie wolumenu tylko wyloguje użytkowników.
- **Szybki błąd:** niepoprawny klucz zatrzymuje start aplikacji, zamiast ujawnić się przy pierwszym logowaniu.

### Problemy i rozwiązania
| Problem | Rozwiązanie |
|---|---|
| Publiczny przykładowy klucz w `.env.example` umożliwiałby podrabianie tokenów | pusta wartość i automatyczne generowanie; stary przykład odrzucany, jeśli ktoś ma go w swoim `.env` |
| Komunikat błędu Pydantic wypisywał odrzuconą wartość, więc za krótki klucz trafiłby do logów | `hide_input_in_errors=True` i test |
| Pierwsze sprawdzenia generowania klucza nie wykonały się, bo zsh nie rozdzielił zmiennej z poleceniem, a puste wyniki wyglądały jak zaliczone | powtórzenie z funkcją powłoki i sprawdzeniem kodu wyjścia |
| Logowanie mogłoby zdradzać istnienie konta przez czas odpowiedzi, a bardzo długie hasło obciążać serwer | dopisane jako zadania do dnia 4 |

### Weryfikacja
| Test | Wynik |
|---|---|
| pusty klucz, dwa osobne uruchomienia kontenera | ten sam wygenerowany klucz (porównanie skrótów, bez wypisywania klucza) |
| plik klucza | uprawnienia 600, właściciel `appuser` |
| publiczny przykład lub za krótki klucz | start zatrzymany, kod wyjścia 1, czytelny komunikat |
| nie można zapisać klucza | start aplikacji zatrzymany |
| hash | `$argon2id$v=19$m=65536,t=3,p=4` |
| 15 celowo osłabionych zabezpieczeń, m.in. brak sprawdzania podpisu, akceptowanie wygasłych tokenów, hasło bez hashowania, plik klucza dostępny dla wszystkich | 15 z 15 wykrytych przez testy; kod przywrócony |
| `pytest` | wszystkie zaliczone |
| `ruff check`, `ruff format` | bez uwag |

### Dalej
Dzień 4: endpointy `register`, `login` i `me`.

---

## Tydzień 2, dzień 4: rejestracja i logowanie (wykonano 5.11.2026)

### Co zostało zrobione
Działają endpointy `POST /api/auth/register`, `POST /api/auth/login` i `GET /api/auth/me`.

| Plik | Rola |
|---|---|
| `backend/app/schemas/user.py` | `UserCreate`, `UserRead` (bez hasła), `Token` |
| `backend/app/repositories/user_repository.py` | zapytania do tabeli `users` |
| `backend/app/services/auth_service.py` | logika rejestracji i logowania |
| `backend/app/api/deps.py` | `get_current_user`, alias `CurrentUser` |
| `backend/app/api/routes/auth.py` | endpointy |
| `backend/app/main.py` | obsługa błędów walidacji bez odrzuconej wartości |

### Dlaczego
- **Warstwy: endpoint, serwis, repozytorium.** Endpoint obsługuje HTTP, serwis reguły, a repozytorium bazę. To samo rozdzielenie posłuży w kolejnych etapach, a izolacja danych po `user_id` będzie mieć jedno miejsce.
- **Ten sam komunikat i czas przy złym haśle i nieznanym e-mailu.** Inaczej logowanie pozwalałoby sprawdzać, czy dana osoba ma konto.
- **Hasło od 12 do 128 znaków.** Bez drugiego składnika logowania długość jest główną ochroną hasła, a górna granica chroni serwer przed bardzo długimi danymi.
- **`OAuth2PasswordRequestForm` przy logowaniu.** Formularz jest wymagany przez przycisk „Authorize” w Swaggerze. Pole nazywa się `username`, ale zawiera e-mail.

### W jaki sposób
- **E-mail** jest normalizowany w schemacie: bez białych znaków i małymi literami. Baza dodatkowo pilnuje tego ograniczeniem `CHECK`.
- **Duplikat** wykrywa ograniczenie `UNIQUE` przy zapisie, bez wcześniejszego `SELECT`. Sprawdzenie „czy istnieje” przed zapisem przepuściłoby dwie jednoczesne rejestracje.
- **Stały czas:** przy nieznanym e-mailu lub zbyt długim haśle liczone jest porównanie z hashem losowego hasła.
- **Hasło w kodzie** jest typu `SecretStr`, więc nie wypisze się przypadkiem w logu ani w reprezentacji obiektu.

### Problemy i rozwiązania
| Problem | Rozwiązanie |
|---|---|
| Domyślna odpowiedź 422 w FastAPI odsyła odrzuconą wartość, czyli za krótkie hasło jawnym tekstem | własna obsługa `RequestValidationError` usuwająca pola `input` i `ctx` |
| Rejestracja i tak ujawnia, że e-mail jest zajęty (409) | świadomy kompromis: aplikacja jest lokalna i nie ma potwierdzania adresu e-mail |
| Brak ograniczenia liczby prób logowania | świadomie poza zakresem: aplikacja działa lokalnie na `127.0.0.1` |

### Weryfikacja
Na działającym API, a dane testowe usunięto po sprawdzeniach. Testy automatyczne powstały w dniu 5.

| Test | Wynik |
|---|---|
| rejestracja z e-mailem z wielkimi literami | 201, e-mail małymi literami, odpowiedź bez hasła i hasha |
| ten sam e-mail innymi literami | 409 |
| za krótkie hasło, błędny e-mail | 422, odpowiedź bez odrzuconej wartości |
| złe hasło, nieznany e-mail | 401, identyczny komunikat |
| poprawne logowanie, `/me` z tokenem | 200 |
| `/me` bez tokenu, ze złym tokenem | 401 |
| hasło w bazie | hash `$argon2id$v=19$m=65536,t=3,p=4` |
| czas logowania, po 60 prób: złe hasło / nieznane konto | mediana 23,2 ms / 23,3 ms |
| `ruff check`, `ruff format` | bez uwag |

### Dalej
Dzień 5: osobna baza testowa, testy API i test zgodności schematu.

---

## Tydzień 2, dzień 5: baza testowa i testy API (wykonano 5.11.2026)

### Co zostało zrobione
| Plik | Rola |
|---|---|
| `backend/tests/conftest.py` | baza testowa i transakcja wycofywana po każdym teście |
| `backend/tests/db_helpers.py` | tworzenie i usuwanie baz testowych z blokadą przed usunięciem innej bazy |
| `backend/tests/integration/test_auth.py` | testy rejestracji, logowania, `/me` i wycieku haseł |
| `backend/tests/integration/test_schema_parity.py` | porównanie schematu z modeli i z migracji |
| `backend/alembic/env.py` | możliwość podania adresu bazy przez testy, logi aplikacji nie są wyłączane |

Łącznie jest 70 testów.

### Dlaczego
- **Osobna baza.** Testy zakładają konta i usuwają dane, więc nie mogą działać na bazie deweloperskiej, a później na prawdziwych transakcjach.
- **Wycofywana transakcja.** Testy nie wpływają na siebie nawzajem, a przebieg jest szybki: 70 testów trwa ok. 1,5 s.
- **Schemat z migracji.** Testy sprawdzają bazę w takim stanie, w jakim będzie działać u użytkownika, więc przy okazji sprawdzają migracje.
- **Test zgodności schematu.** Zamyka lukę `alembic check` opisaną w dniu 2: zmiana reguły `CHECK` w modelu bez migracji przechodziła niezauważona.

### W jaki sposób
- **Baza testowa:** na początku przebiegu powstaje od zera `<nazwa>_test` i dostaje schemat z migracji. W CI działa to tak samo, bez osobnej konfiguracji.
- **Izolacja testów:** sesja z `join_transaction_mode="create_savepoint"`, więc `commit` w kodzie aplikacji zamyka tylko punkt zapisu, a cała transakcja jest wycofywana po teście.
- **Zgodność schematu:** test buduje drugą, tymczasową bazę przez `create_all` i porównuje obie w katalogu PostgreSQL: kolumny z wartościami domyślnymi, ograniczenia (`pg_get_constraintdef`) i indeksy. Definicje zapisuje sam PostgreSQL, więc różny zapis tej samej reguły nie daje fałszywego alarmu.
- **Blokada:** funkcje usuwające odmawiają pracy na bazie bez `_test` w nazwie, co ma własny test.

### Problemy i rozwiązania
| Problem | Rozwiązanie |
|---|---|
| Celowe przepuszczenie zbyt długiego hasła do Argon2 nie zostało wykryte, bo odpowiedź nadal była 401 | nowy test sprawdzający, że takie hasło nie trafia do `verify_password` |
| Pierwsza wersja testu „`/me` bez logowania” niczego nie zmieniała: zależność nadal działała | poprawiony przypadek, faktycznie usuwający zależność; testy go wykrywają |
| `fileConfig` Alembica wyłączał istniejące loggery, więc po migracjach w testach logi aplikacji mogły zniknąć, a test braku haseł w logach przechodziłby bez sprawdzania | `disable_existing_loggers=False` |
| Funkcja pomocnicza `test_database_url` była uruchamiana przez pytest jako test | przeniesienie do `db_helpers.py` i zmiana nazwy |
| Ostrzeżenie PyJWT w CI: ustawienia dopuszczały HS512, który zaleca klucz od 64 bajtów, a walidacja przepuszczała już 32 znaki | ograniczenie `JWT_ALGORITHM` do HS256 i dłuższy klucz testowy w CI |

### Weryfikacja
| Test | Wynik |
|---|---|
| `pytest` | 70 testów zaliczonych, ok. 1,5 s, także w CI |
| 20 jednoczesnych rejestracji tego samego e-maila przez działające API | 1 × 201, 19 × 409, jedno konto w bazie, brak błędów 500 |
| znacznik w bazie deweloperskiej przed testami | zostaje; testy nie zmieniają tej bazy |

**Zmiany modelu bez migracji** (test zgodności schematu):

| Zmiana | Test | `alembic check` |
|---|---|---|
| reguła `CHECK` waluty | wykrywa | nie wykrywa |
| reguła `CHECK` e-maila | wykrywa | nie wykrywa |
| wartość domyślna `kind` | wykrywa | nie wykrywa |
| domyślna waluta | wykrywa | nie wykrywa |
| długość kolumny, usunięty indeks, `ondelete`, `NULLS NOT DISTINCT` | wykrywa | wykrywa |

**Celowo wprowadzone błędy w logowaniu:** m.in. hash w odpowiedzi, niesprawdzane hasło, brak stałego czasu, akceptowanie złego tokenu, logowanie hasła, odsyłanie wartości w 422. Wszystkie 16 przypadków jest wykrywanych. Pierwszy przebieg ujawnił lukę i źle przygotowany przypadek opisane wyżej. Kod został przywrócony.

### Dalej
Dzień 6: przejście całości w Swaggerze i czysty start ze świeżego klonu.

---

## Tydzień 2, dzień 6: sprawdzenie całości (wykonano 5.11.2026)

### Co zostało zrobione
Sprawdzono cały przebieg: czysty start, świeży klon z pustym kluczem JWT oraz rejestrację i logowanie w prawdziwym Swaggerze.
Kod aplikacji się nie zmienił.

### Dlaczego
- **Swagger w przeglądarce.** Kryterium ukończenia etapu mówi o Swaggerze, a testy automatyczne i `curl` nie sprawdzają okna „Authorize” ani tego, jak strona działa w przeglądarce.
- **Świeży klon z pustym kluczem.** Dotąd generowanie klucza sprawdzano tylko w kontenerze z istniejącej instalacji, a nie w scenariuszu nowej osoby.

### W jaki sposób
- **Czysty start:** `docker compose down -v`, po sprawdzeniu, że baza nie zawiera danych, potem `docker compose up --build`.
- **Świeży klon:** `git clone` gałęzi `develop`, `cp .env.example .env`, build bez cache, osobny projekt Compose; zmieniono tylko porty.
- **Swagger:** Chromium sterowany przez Playwright, użyty jednorazowo i poza repozytorium, klika te same elementy co użytkownik: „Try it out”, „Execute”, „Authorize”. Wyniki odczytano z odpowiedzi HTTP i z ekranu.

### Problemy i rozwiązania
| Problem | Rozwiązanie |
|---|---|
| `/docs` pobiera Swagger UI z `cdn.jsdelivr.net`. Bez internetu strona jest pusta, co psuje krok pokazu i narusza regułę braku zewnętrznych połączeń | zadanie w etapie 9: serwowanie Swagger UI lokalnie; adnotacja w scenariuszu pokazu. Dotyczy tylko dokumentacji API, a nie danych użytkownika |
| Skrypt pokazał 401 dla `/me` po zalogowaniu, choć treść zawierała e-mail: odczytał status sprzed odświeżenia wyniku | odczyt statusu z faktycznej odpowiedzi HTTP; wynik to 200 |

### Weryfikacja
| Test | Wynik |
|---|---|
| `down -v` + `up --build` | 3 kontenery działają, gotowe po 33 s, migracje na bieżącej wersji |
| świeży klon, build bez cache | gotowy po 49 s (obrazy bazowe były już pobrane) |
| klucz JWT w klonie | wygenerowany: 64 znaki, uprawnienia 600, właściciel `appuser` |
| `pytest` (oba przypadki) | 70 testów zaliczonych |
| Swagger: `/me` bez logowania | 401 |
| Swagger: rejestracja | 201 |
| Swagger: logowanie w oknie „Authorize” | 200 |
| Swagger: `/me` po zalogowaniu | 200, nagłówek `Bearer`, w odpowiedzi e-mail, bez hasha |
| hasło w bazie | `$argon2id$v=19$m=65536,t=3,p=4` |
| ekran stanu w klonie | „API: OK, Baza: OK” |
| `/docs` bez dostępu do zewnętrznych serwerów | 0 sekcji API, zob. problem wyżej |

Domyślne porty i pierwsze pobranie obrazów nadal nie są sprawdzone: to zadanie etapu 9.

### Dalej
Dzień 7: domknięcie etapu 2.

---

## Tydzień 2, dzień 7: domknięcie etapu 2 (wykonano 5.11.2026)

### Co zostało zrobione
- Etap 2 oznaczony w planie jako ukończony, a notatki o technologiach uzupełnione o Argon2 i JWT.
- Harmonogram przesunięty pod oddanie pracy do 15 stycznia 2027, a część pisemna dopisana do planu (sekcja 10).
- Wszystkie 6 kryteriów ukończenia tygodnia sprawdzone.

### Dlaczego
- **Zmiana harmonogramu.** Pierwotny plan kończył program 17 stycznia, czyli po docelowym terminie oddania.
- **Część pisemna w planie.** Program i tekst powstają równolegle, więc obie części muszą mieć terminy.

### W jaki sposób
- Program ma być gotowy do 20 grudnia, święta przeznaczono na pomiary i poprawki, a od 4 stycznia tylko na krytyczne błędy. Terminy są robocze do czasu potwierdzenia terminu WSE, procedury JSA i czasu promotora.
- Ustalono kolejność cięć, gdyby zabrakło czasu: funkcje COULD, importer uniwersalny CSV, drugi dostawca AI.

### Problemy i rozwiązania
| Problem | Rozwiązanie |
|---|---|
| Bufor ze stycznia zniknął, więc margines błędu jest mniejszy | bufor świąteczny, zapas 11–15 stycznia i ustalona kolejność cięć |
| Formalne terminy nie są jeszcze znane | harmonogram oznaczony jako roboczy, zadanie ich ustalenia w sekcji 10 |

### Weryfikacja
Kryteria ukończenia z `TYDZIEN_2.md`: rejestracja i `/me` w Swaggerze, tabele, kategorie po czystym starcie, hash Argon2 i testy na osobnej bazie, lokalnie oraz w CI. Sprawdzone w dniach 1–6.

### Dalej
Etap 3 (9–15 listopada): transakcje, kategorie i logowanie w przeglądarce.

---

## Tydzień 3, dni 1–3: kategorie, transakcje i izolacja danych w API (wykonano 7.11.2026)

### Co zostało zrobione
| Plik | Rola |
|---|---|
| `schemas/category.py`, `repositories/category_repository.py`, `services/category_service.py`, `api/routes/categories.py` | kategorie: lista, dodawanie, edycja i usuwanie własnych |
| `schemas/transaction.py`, `repositories/transaction_repository.py`, `services/transaction_service.py`, `api/routes/transactions.py` | transakcje: lista z filtrami i paginacją, dodawanie ręczne, edycja, usuwanie |
| `tests/integration/test_categories.py`, `test_transactions.py`, `test_isolation.py`, `helpers.py` | 81 nowych testów |

Rozwiązano dwie sprawy odłożone w tygodniu 2: kategoria przypisana do transakcji musi być systemowa albo użytkownika,
a kategorii systemowych nie można zmienić ani usunąć.

### Dlaczego
- **Cudzy zasób daje 404, a nie 403.** Kod 403 zdradzałby, że zasób o danym numerze istnieje i należy do kogoś innego. Odpowiedź dla cudzej i nieistniejącej transakcji jest identyczna, co sprawdza osobny test.
- **Sprawdzanie kategorii w aplikacji.** Kategoria systemowa nie ma właściciela, więc prosty klucz obcy nie wyrazi warunku „systemowa albo moja”.
- **Dane bankowe z importu są zablokowane.** Data, kwota i waluta z wyciągu są podstawą sum kontrolnych i wykrywania duplikatów (etap 4). W takiej transakcji można zmienić tylko kategorię, rodzaj i opis.
- **Kwoty jako tekst w JSON** (`"-12.50"`). Liczba w JSON to `float` i mogłaby stracić dokładność.
- **Nazwy kategorii bez powtórzeń**, także z kategoriami systemowymi i bez względu na wielkość liter: dwie „Inne” na liście byłyby mylące.

### W jaki sposób
- **Izolacja w jednym miejscu:** każda metoda repozytorium wymaga `user_id`, a zapytania budowane są od `WHERE user_id = :id`. Repozytorium nie ma metody pobierającej dane wszystkich użytkowników.
- **Wyszukiwanie:** `ILIKE` z `autoescape=True`, więc `%` i `_` w szukanym tekście są zwykłymi znakami, a nie wzorcem.
- **Częściowa edycja:** zmieniane są tylko przysłane pola (`exclude_unset`). `category_id: null` usuwa kategorię, a `null` w polu wymaganym daje 422.
- **Paginacja:** sortowanie od najnowszych (data, potem identyfikator), strona do 200 pozycji, w odpowiedzi łączna liczba wyników.
- **Jednoczesne utworzenie tej samej nazwy kategorii** wychwytuje ograniczenie `UNIQUE` w bazie, tak jak przy rejestracji.

### Problemy i rozwiązania
| Problem | Rozwiązanie |
|---|---|
| Transakcji z importu nie da się jeszcze utworzyć przez API, a reguły ich edycji trzeba przetestować | testy wstawiają taką transakcję bezpośrednio do bazy testowej |
| Część wzorców w skrypcie celowych błędów nie pasowała do kodu, bo formatter przełamał linie | dopasowanie wzorców do faktycznego kodu i ponowne uruchomienie; kod przywrócony |
| `PATCH` z `"name": null` mógłby usunąć nazwę kategorii | `null` w nazwie jest ignorowany, a w kolorze i ikonie usuwa wartość; oba zachowania mają testy |

### Weryfikacja
| Test | Wynik |
|---|---|
| `pytest` | 151 testów zaliczonych |
| 16 celowo usuniętych zabezpieczeń, m.in. lista bez filtra `user_id`, odczyt transakcji bez `user_id`, kategorie widoczne dla wszystkich, brak sprawdzenia kategorii, edytowalna kategoria systemowa, odpowiedź 403 zamiast 404, edytowalne dane bankowe, wyszukiwanie bez `autoescape`, zła paginacja | 16 z 16 wykrytych; kod przywrócony |
| `ruff check`, `ruff format` | bez uwag |

### Dalej
Dni 4–5: logowanie i transakcje w przeglądarce.

---

## Tydzień 3, dni 4–5: logowanie i transakcje w przeglądarce (wykonano 7.11.2026)

### Co zostało zrobione
| Plik | Rola |
|---|---|
| `src/api/client.ts`, `token.ts`, `endpoints.ts` | zapytania do API z tokenem, obsługa błędów i odrzuconego tokenu |
| `src/context/`, `src/hooks/useAuth.ts` | stan logowania: logowanie, rejestracja, wylogowanie, sprawdzenie tokenu po odświeżeniu |
| `src/components/RequireAuth.tsx`, `layout/AppLayout.tsx` | trasy dostępne po zalogowaniu, menu boczne i górny pasek |
| `src/pages/AuthPage.tsx` | logowanie i rejestracja |
| `src/pages/TransactionsPage.tsx`, `components/transactions/TransactionForm.tsx` | tabela, filtry, paginacja, dodawanie, edycja, usuwanie |
| `src/utils/format.ts` | formatowanie kwot i dat, odczyt kwoty wpisanej z przecinkiem |

### Dlaczego
- **Token w `sessionStorage`.** Przetrwa odświeżenie strony, a znika po zamknięciu karty. `localStorage` przechowywałby go dłużej, a zwykła zmienna wylogowywałaby przy każdym odświeżeniu.
- **Czyszczenie pamięci podręcznej przy wylogowaniu.** Dane poprzedniego użytkownika nie mogą zostać w przeglądarce dla kolejnej osoby.
- **Kwota wpisywana bez znaku, z wyborem „Wydatek” albo „Przychód”.** Znak minus łatwo pominąć, a pomyłka odwróciłaby sens operacji.
- **Odrzucony token wylogowuje z komunikatem.** Po wygaśnięciu sesji użytkownik wie, dlaczego trafił na stronę logowania.

### W jaki sposób
- **Kwoty:** `parseAmountInput` przyjmuje przecinek, kropkę i spacje, a wysyła do API tekst z dwoma miejscami, np. `"1234.56"`. Obliczenia wykonuje backend; przeglądarka tylko formatuje (`Intl.NumberFormat` dla `pl-PL`).
- **Transakcja z importu:** formularz blokuje datę, kwotę i kontrahenta, a do API wysyła tylko pola, które wolno zmienić.
- **Wyszukiwanie** czeka 300 ms po ostatnim znaku, zamiast wysyłać zapytanie po każdej literze.
- **Zmiana filtra** wraca do pierwszej strony wyników.

### Problemy i rozwiązania
| Problem | Rozwiązanie |
|---|---|
| Etykieta obejmująca `<select>` dodawała do nazwy pola wszystkie opcje, np. „TypWydatekPrzychód”, więc czytnik ekranu odczytywałby całą listę. Wykrył to test w przeglądarce | etykieta powiązana z polem przez `for`/`id` (`useId`) |
| Lint Reacta wymaga, żeby plik z komponentem nie eksportował innych rzeczy | kontekst, dostawca i hook `useAuth` w osobnych plikach |
| Projekt nie ma jeszcze testów frontendu, a od `parseAmountInput` zależy poprawność zapisanych kwot | jednorazowe sprawdzenie 16 przypadków; testy przeglądarkowe w dniu 6 |

### Weryfikacja
| Test | Wynik |
|---|---|
| `parseAmountInput`: m.in. `1 234,56`, `0,01`, `007,10`, `0`, `-5`, `1,234`, `12,`, 11 cyfr | 16 z 16 poprawnych |
| `npm run lint`, `format:check`, `build` z kontrolą typów | bez uwag |

### Dalej
Dzień 6: przejście całości w przeglądarce.

---

## Tydzień 3, dni 6–7: sprawdzenie całości i domknięcie etapu 3 (wykonano 7.11.2026)

### Co zostało zrobione
- Pełne przejście w przeglądarce, scenariuszem użytkownika.
- Etap 3 oznaczony w planie jako ukończony, notatki o technologiach uzupełnione o React Router, TanStack Query i izolację danych.
- Strona zarządzania kategoriami w przeglądarce dopisana do etapu 5.

### Dlaczego
- **Test w przeglądarce.** Kryterium ukończenia etapu mówi o logowaniu i dodawaniu wydatków w przeglądarce. Testy API nie sprawdzają przekierowań, formularzy, formatowania ani zachowania po odświeżeniu strony.

### W jaki sposób
Chromium sterowany przez Playwright, użyty jednorazowo i poza repozytorium. Skrypt wykonuje te same czynności co
użytkownik i odczytuje wynik z ekranu. Dane testowe usunięto po sprawdzeniu.

### Problemy i rozwiązania
| Problem | Rozwiązanie |
|---|---|
| Usterka dostępności etykiet | zob. dni 4–5 |
| Pole daty w filtrach pokazuje `mm/dd/yyyy` w testowej przeglądarce po angielsku | format ustala przeglądarka na podstawie języka; w polskiej przeglądarce `dd.mm.rrrr`. Bez zmian |

### Weryfikacja
| Test w przeglądarce | Wynik |
|---|---|
| niezalogowany wchodzi na `/transactions` | przekierowanie na `/login` |
| rejestracja | automatyczne zalogowanie, pusta lista z komunikatem |
| błędna kwota (`12,345`) | komunikat, brak zapisu |
| 3 transakcje: wydatek z kategorią, przychód, wydatek | kolejność od najnowszej, `-1234,56 zł`, `5000,00 zł`, data `03.11.2026` |
| edycja kwoty i kategorii | zapisana, widoczna w tabeli |
| szukanie `orlen`, szukanie `%`, filtr „Bez kategorii”, filtr od daty | poprawne liczby wyników |
| usunięcie | po potwierdzeniu znika |
| odświeżenie strony | nadal zalogowany |
| 25 transakcji | 20 na stronie, „Strona 1 z 2”, druga strona: 5 |
| zepsuty token | wylogowanie z komunikatem „Sesja wygasła” |
| złe hasło | komunikat „Nieprawidłowy e-mail lub hasło” |
| wylogowanie, potem „wstecz” | token usunięty, `/transactions` niedostępne |
| drugi użytkownik | 0 transakcji, nie widzi danych pierwszego |
| błędy JavaScript, połączenia | brak błędów; tylko `localhost:5173` i `localhost:8001` |
| łącznie | 26 z 26 |
| `pytest` | 151 testów zaliczonych |

### Dalej
Etap 4 (16–22 listopada): import wyciągów PDF z ING. Wracają sprawy odłożone do tego etapu: próba biblioteki na prawdziwych
wyciągach wyłącznie lokalnie i zgodność z sumami wszystkich 6 wyciągów.

---

## Tydzień 4: import wyciągów PDF z ING (wykonano 7.11.2026)

### Co zostało zrobione
| Plik | Rola |
|---|---|
| `backend/app/parsers/ing_pdf.py` | odczyt wyciągu, kontrola sum, rozpoznanie rodzaju operacji |
| `backend/app/services/import_service.py`, `api/routes/imports.py`, `schemas/imports.py` | podgląd, zapis, historia importów |
| `backend/tests/fixtures/ing_statement.py` | generator sztucznego wyciągu PDF o tym samym układzie |
| `backend/tests/unit/test_ing_pdf.py`, `tests/integration/test_imports.py` | nowe testy parsera i API importu |
| `backend/scripts/check_statements.py` | sprawdzenie prawdziwych wyciągów bez ujawniania treści |
| `frontend/src/pages/ImportPage.tsx` | strona „Import wyciągu” |

Importer uniwersalny CSV (SHOULD) nie powstał i zgodnie z kolejnością cięć przeszedł na okres świąteczny.
Plan tygodnia (`TYDZIEN_4.md`) spisano po wykonaniu prac, bo etap zaczął się od próby biblioteki, od której zależało podejście.

### Dlaczego
- **Kontrola sum przed zapisem.** Wyciąg zawiera liczbę i sumę uznań i obciążeń oraz salda. Ich porównanie z odczytem to obiektywna miara poprawności parsera, a niezgodny import nie trafia do bazy nawet częściowo.
- **Numer operacji jako klucz duplikatów.** Hash daty, kwoty i opisu uznałby dwa identyczne zakupy tego samego dnia za duplikat.
- **Brak przechowywania pliku.** Podgląd i zapis przyjmują plik osobno, więc dane bankowe nie zostają w plikach tymczasowych serwera.
- **Prywatność w trakcie pracy.** Parser był rozwijany na prawdziwych wyciągach, ale narzędzia diagnostyczne wypisywały wyłącznie liczby, zgodność sum i „kształt” tekstu (litery zamienione na `a`, cyfry na `9`), bez treści transakcji.

### W jaki sposób
- **Kolumny:** granice wyznaczają słowa nagłówka tabeli leżące w jednej linii ze słowem „kontrahenta”.
- **Wiersze:** granice transakcji wyznaczają poziome linie tabeli dłuższe niż 400 pkt. Wiersz bez daty na początku strony to dokończenie transakcji z poprzedniej strony.
- **Tekst:** słowa są składane ze znaków (grupowanie po współrzędnej y, podział według odstępu między znakami).
- **Data:** do analizy służy data z tytułu („Płatność kartą 29.09.2026”), a data księgowania jest zapisywana osobno.
- **Rodzaj operacji:** z tytułu i kodu z kolumny „Szczegóły” (`TR.KART`, `P.BLIK`, `PRZELEW`…); Smart Saver, przelew własny i wpłata na cel to przelewy własne.
- **Zapis:** `INSERT … ON CONFLICT (user_id, dedup_hash) DO NOTHING RETURNING id`, więc duplikaty pomija baza, także przy dwóch jednoczesnych importach.
- **Przeglądarka:** strona wysyła plik do podglądu, pokazuje sumy z wyciągu obok sum odczytanych, a po „Zapisz” wysyła ten sam plik ponownie do zapisu. Historia importów jest pod formularzem.

### Problemy i rozwiązania
| Problem | Rozwiązanie |
|---|---|
| W nagłówku leżą w jednym wierszu „Saldo końcowe” i „Saldo dostępne”; słownik po (nazwa, wysokość) gubił jedną etykietę, a kontrola salda nie przechodziła w żadnym wyciągu | lista etykiet i wybór etykiety z pierwszej kolumny |
| W 4 z 6 wyciągów brakowało 1–2 obciążeń. Diagnoza (same liczby): każda strona miała tyle dat, ile wierszy, ale jedna kwota nie trafiała do żadnej transakcji. Przyczyna: przy dolnej krawędzi strony znaki dwóch linii są zapisane w pliku naprzemiennie, a `extract_words` dzielił daty na fragmenty; wiersz bez rozpoznanej daty był dołączany do poprzedniego | słowa składane bezpośrednio ze znaków według współrzędnych; potem zgodność 6 z 6 |
| Opisy z dołu strony były rozbite na litery, a rodzaj operacji „inny” | ta sama zmiana dla wszystkich kolumn; 0 z 1113 opisów rozbitych |
| Sztuczny wyciąg ujawnił, że parser szukał słowa „Dane” w całym dokumencie (na str. 1 jest też „Dane posiadacza”); w prawdziwych plikach działało przypadkiem | słowa nagłówka muszą leżeć w linii ze słowem „kontrahenta” |
| Kilka dokończeń z kolejnych stron dostawało to samo przesunięcie w pionie, co mieszałoby ich linie | rosnące przesunięcie przy każdym scaleniu |
| Wbudowana czcionka ReportLab nie ma polskich znaków, a parser rozpoznaje m.in. „Płatność kartą” | czcionka DejaVu (`fonts-dejavu-core`) tylko w obrazie deweloperskim i w CI |
| Generator sztucznego wyciągu nie zawijał tekstu, przez co nachodził na sąsiednie kolumny (prawdziwy wyciąg zawija) | zawijanie do szerokości kolumny i mniejszy, dwuliniowy nagłówek tabeli |
| Skrypt kontrolny uruchamiany poza kontenerem nie miał `DATABASE_URL`, bo import `app.models` wczytuje ustawienia | adres zastępczy w poleceniu; parser sam nie łączy się z bazą |
| Pierwszy test w przeglądarce nie wystartował, bo przeglądarka testowa nie zdążyła się pobrać | osobna instalacja przeglądarki przed testem |

### Weryfikacja
| Test | Wynik |
|---|---|
| 6 prawdziwych wyciągów, parser | 1113 transakcji, zgodność z sumami 6 z 6, 1113 unikalnych numerów operacji |
| 6 prawdziwych wyciągów przez API (tymczasowe konto, usunięte po teście) | 1113 zapisanych; ponowny import: 0 nowych, 1113 duplikatów |
| suma zaimportowanych kwot | 321,52 zł = saldo końcowe ostatniego wyciągu − saldo początkowe pierwszego |
| sztuczny wyciąg | 3 strony, transakcja dzielona między strony, 25 z 25 transakcji, zgodność z sumami |
| celowo zepsute sumy (liczba i suma uznań, obciążeń, saldo) i brak jednej transakcji | wykryte |
| plik niebędący wyciągiem, za duży (> 5 MB), uszkodzony PDF | 422 / 413, nic nie zapisano |
| inny użytkownik importuje ten sam plik | zapisuje własne transakcje; duplikaty liczone osobno dla każdego |
| przeglądarka: zły plik, zepsute sumy, podgląd, zapis, historia, edycja zaimportowanej transakcji, ponowny import | 15 z 15; połączenia tylko z `localhost` |
| `pytest` | 205 testów zaliczonych |

### Porządki w projekcie
Na prośbę o usunięcie zbędnych plików:
- **Repozytorium:** usunięto 5 plików `.gitkeep` z katalogów, które mają już zawartość. Zostały 2 zalążki pustych katalogów na kolejne etapy (`parsers/profiles/`, `components/charts/`).
- **Docker:** usunięto 4 nieużywane wolumeny (stare kopie `node_modules` po 116 MB) i obraz pomocniczy `alpine`.
- **Lokalnie:** usunięto katalog `frontend/dist`, czyli wynik budowania odtwarzany przy każdym buildzie.

### Dalej
Etap 5 (23–29 listopada): kategoryzacja i zapamiętywanie poprawek, strona „Kategorie”.

---

## Tydzień 4, dodatkowo: importer uniwersalny CSV (wykonano 7.11.2026)

Importer CSV był w planie oznaczony jako SHOULD i po domknięciu części PDF został przeniesiony na okres świąteczny.
Użytkownik poprosił o wykonanie go od razu, więc wrócił do etapu 4.

### Co zostało zrobione
| Plik | Rola |
|---|---|
| `backend/app/parsers/csv_profile.py`, `profiles/ing.json` | model profilu pliku CSV i wbudowany profil ING |
| `backend/app/parsers/csv_detect.py` | rozpoznanie formatu nieznanego pliku: kodowanie, separator, nagłówek, role kolumn, format daty |
| `backend/app/parsers/csv_generic.py` | odczyt pliku według profilu |
| `backend/app/parsers/common.py` | elementy wspólne z parserem PDF (normalizacja opisu, usuwanie numeru karty) |
| `backend/app/models/bank_profile.py`, migracja `profile_bankow` | tabela profili zapisanych przez użytkowników |
| `backend/app/services/import_service.py`, `api/routes/imports.py` | podgląd i zapis dla PDF i CSV, endpointy `banks` i `detect` |
| `frontend/src/components/imports/ColumnMapping.tsx`, `pages/ImportPage.tsx` | kreator mapowania kolumn i lista profili |
| `backend/tests/fixtures/csv_samples.py`, `tests/unit/test_csv_import.py`, `tests/integration/test_csv_imports.py` | sztuczne pliki CSV i 72 testy |
| `backend/scripts/check_statements.py` | sprawdzenie plików CSV z `data/private/` i porównanie z wyciągami PDF |

### Dlaczego
- **Dwa poziomy.** Parser „dla wszystkich banków” nie istnieje: banki różnią się kodowaniem, separatorem, metadanymi nad tabelą, nazwami kolumn, formatem daty i zapisem kwoty. Detektor zgaduje te ustawienia, a użytkownik potwierdza je raz; potem plik z tego banku jest rozpoznawany automatycznie.
- **Kolumny po nazwach.** Profil wskazuje kolumnę nazwą z nagłówka, a nie numerem, więc zmiana liczby wierszy metadanych nad tabelą (np. inny zakres dat w eksporcie) nie psuje profilu.
- **Profile wbudowane jako pliki JSON.** Plan przewidywał je jako wiersze tabeli `bank_profiles` z pustym `user_id`. Plik w kodzie ma testy i zmienia się razem z aplikacją, bez migracji danych, a tabela trzyma tylko profile użytkowników (`user_id` obowiązkowy). Plan zaktualizowano.
- **Błędny wiersz zatrzymuje import.** Wyciąg PDF chronią sumy kontrolne, plik CSV nie ma niczego podobnego. Dlatego wiersz z datą, którego nie da się odczytać, zatrzymuje import z numerem wiersza, zamiast zostać po cichu pominięty. Pomijane są tylko wiersze bez daty (metadane, stopka) i bez kwoty (blokady kartowe), a te drugie są pokazywane w podglądzie.
- **Wspólny klucz duplikatów z PDF.** Profil ING buduje klucz z numeru operacji tak samo jak parser PDF, więc import wyciągu PDF i pliku CSV z tego samego okresu nie dubluje transakcji.

### W jaki sposób
- **Kodowanie:** UTF-8, a gdy plik nie jest poprawnym UTF-8: cp1250 albo ISO-8859-2. Oba odczytają każdy bajt, więc rozstrzyga liczba polskich liter (te kodowania różnią się m.in. kodami „ą”, „ś”, „ź”).
- **Separator:** ten, przy którym najwięcej wierszy ma tę samą liczbę kolumn.
- **Nagłówek:** wiersz z największą liczbą znanych nazw kolumn wśród pierwszych 50.
- **Role kolumn:** słownik nazw (bez polskich znaków i wielkości liter), dokładna nazwa wygrywa z początkiem nazwy. Potem sprawdzenie zawartości wyłącznie w wierszach z poprawną datą: kolumna „Data” bez dat nie jest datą, kwota musi mieć część dziesiętną.
- **Bez numeru operacji:** klucz duplikatów to data, kwota, waluta, opis i kontrahent z numerem kolejnym wystąpienia w pliku. Dwie identyczne kawy tego samego dnia to dwie transakcje, a ponowny import tego samego pliku daje te same klucze.
- **Przeglądarka:** plik PDF trafia od razu do podglądu. Plik CSV najpierw do `detect`: rozpoznany profil prowadzi do podglądu bez pytań, a nieznany plik otwiera kreator. Kreator pokazuje 5 przykładowych wierszy z oznaczeniem ról kolumn, a zmiana kodowania lub separatora ponawia rozpoznanie. Profil jest zapisywany dopiero przy zatwierdzeniu importu, czyli gdy plik dał się według niego odczytać.

### Problemy i rozwiązania
| Problem | Rozwiązanie |
|---|---|
| W sztucznym pliku ING detektor uznał za kwotę kolumnę „Nr rachunku”. Stopka pod tabelą („Saldo końcowe”) nie przechodziła sprawdzenia kwoty, więc właściwa kolumna odpadała, a numer konta po usunięciu spacji wyglądał jak liczba | sprawdzanie zawartości tylko w wierszach z poprawną datą; kwota musi mieć część dziesiętną w co najmniej połowie wierszy |
| „Opłata za kartę” rozpoznana jako płatność kartą | słowa kluczowe opłat sprawdzane przed słowem „kart” |
| Test wykrył, że tekst „abc” w kolumnie kwoty był traktowany jak kod waluty, czyli pusta kwota: wiersz zostałby po cichu pominięty jako blokada | waluta usuwana tylko wtedy, gdy stoi po liczbie |
| Separator dziesiętny w kwocie „1,250.00” był zgadywany błędnie (obie metody liczenia dawały remis) | separatorem jest ostatni znak „,” lub „.” przed jedną lub dwiema cyframi na końcu kwoty |
| Test w przeglądarce: po zapisaniu importu ponowny wybór tego samego pliku nic nie robił, bo pole pliku dalej go pokazywało, a przeglądarka nie zgłasza zmiany przy wyborze tego samego pliku | pole pliku jest czyszczone razem ze stanem strony |
| Celowe błędy w kodzie: zmiana wykluczenia „saldo”/„blokada” z kandydatów na kwotę nie była wykryta, bo w pliku ING właściwa kolumna wygrywała i bez niej | test z kolumnami „Kwota blokady”, „Saldo po operacji” i „Kwota (PLN)” |

### Weryfikacja
| Test | Wynik |
|---|---|
| `pytest` | 277 testów zaliczonych (72 nowe dla CSV) |
| celowe błędy: licznik identycznych wierszy, znak obciążeń, wykluczenie salda, pomijanie stopki, zapis profilu tylko na życzenie, izolacja listy i usuwania profili, waluta po liczbie | 8 z 8 wykrytych |
| migracja: `upgrade`, `alembic check`, `downgrade`, `upgrade` | bez błędów |
| przeglądarka: CSV z ING bez kreatora, ponowny import, plik innego banku przez kreator, zły format daty, zapamiętany profil, nieznane nazwy kolumn, zmiana separatora, usunięcie profilu, PDF nadal z kontrolą sum | 26 z 26; połączenia tylko z `localhost` |
| prawdziwe dane | brak: nie ma jeszcze prawdziwego eksportu CSV z ING. Profil ING powstał na podstawie opisu formatu; jeśli prawdziwy plik się różni, trafi do kreatora |

Zrzut kreatora na sztucznych danych: `docs/zrzuty/tydzien4_kreator_csv.png`.

**Uzupełnienie 8.11.2026: prawdziwe dane przez importer CSV.** Prawdziwego eksportu CSV z ING jeszcze nie ma, więc
transakcje z 6 wyciągów PDF zamieniono w pamięci (bez zapisu na dysk) na plik w formacie profilu ING i odczytano
importerem CSV. Wynik: 1113 z 1113 transakcji, te same klucze duplikatów co z PDF (import CSV po PDF dałby same
duplikaty), ta sama suma kwot, zero różnic w datach, kwotach, opisach i kontrahentach. Po drodze sprawdzone zostały
polskie znaki w Windows-1250, cudzysłowy w 5 tytułach i kwoty z separatorem tysięcy. Detektor bez profilu rozpoznał
wszystkie 8 ról kolumn. Ograniczenie: format pliku pochodzi z założeń profilu, a rodzaj operacji odtworzono z wyniku
parsera PDF, więc test nie potwierdza, że prawdziwy eksport ING ma takie nazwy kolumn i kodowanie. To nadal wymaga
prawdziwego pliku.

---

## 8.11.2026: protokół badania aplikacyjnego

### Co zostało zrobione
Powstał `docs/BADANIA.md`: pytania badawcze P1–P4, hipotezy H1–H4 z progami przyjęcia, dane, metoda, miary, testy
statystyczne, ograniczenia i rejestr zmian protokołu. Zadania wynikające z protokołu (oznaczone „(badanie)”) trafiły
do etapów 5, 7, 8, 9 i 10 planu, a rozdział 6 pracy nazywa się teraz „Badanie aplikacyjne: hipotezy, metoda, wyniki,
dyskusja”.

### Dlaczego
Zarządzenie dla IS wymaga pracy z badaniem aplikacyjnym albo eksperymentem (hipoteza, metoda, wyniki, dyskusja).
Plan miał tylko ogólne „pomiary w etapie 10”. Rzetelność pomiaru zależy jednak od budowy modułów:
- symulacja kategoryzacji musi używać tej samej logiki co aplikacja;
- słownik reguł nie może być strojony na danych testowych;
- porada AI musi zapisywać wersję promptu i czas odpowiedzi.

Dlatego metodę ustalono przed budową modułów, a nie po. Data commita protokołu pokazuje, że hipotezy powstały
przed wynikami.

### W jaki sposób
- **Badanie główne (P2):** porównanie kategoryzacji samym słownikiem (A) i słownikiem z regułami z poprawek (B). Symulacja odtwarza 6 miesięcy prawdziwych transakcji w kolejności dat. Etykiety autor nadaje osobnym narzędziem, a nie przez kategoryzację systemu. Miesiące 1–3 służą do strojenia, 4–6 do testu. Test McNemara dla par przewidywań.
- **Anonimizacja (P3):** sztuczny korpus z oznaczonymi danymi osobowymi, z częścią testową zamrożoną przed strojeniem reguł, oraz kontrola wycieków w pakietach z prawdziwych danych.
- **Porady (P4):** obiektywna zgodność liczb z danymi wejściowymi, ślepa ocena przydatności i koszt.
- **Import (P1):** wyniki z 7–8.11 wpisane jako wstępne.

### Problemy i rozwiązania
| Problem | Rozwiązanie |
|---|---|
| Etykiety kategorii nadaje autor systemu, co grozi stronniczością | osobne narzędzie etykietowania, etykiety przed pomiarem, podział na część roboczą i testową; ograniczenie opisane w dyskusji |
| Prawdziwych tytułów przelewów nie można oznaczyć w repozytorium | sztuczny korpus o strukturze prawdziwych tytułów oraz kontrola wycieków na prawdziwych danych, z wynikami tylko zbiorczymi |
| Dane jednej osoby nie pozwalają na uogólnienie | nazwane wprost w ograniczeniach; wyniki opisują przypadek |

### Dalej
Konsultacja protokołu z promotorem: zakres, progi hipotez, testy statystyczne, ewentualne badanie SUS.
