# Plan implementacji — krok po kroku

**Start:** 2 listopada 2026 **Wersja 1.0 (feature freeze):** 17 stycznia 2027 **Bufor:** 18–31 stycznia 2027

Mamy ok. 11 tygodni, w tym okres świąteczny. Dlatego:

1. **Najpierw działający szkielet od końca do końca** (baza → API → frontend), potem funkcje.
2. **Każdy tydzień kończy się działającą wersją** wypchniętą na GitHub (nawet jeśli skromną).
3. Święta (21.12–3.01) to celowo **lżejszy tydzień i bufor** — nie planujemy tam kluczowych funkcji.
4. Moduł AI zaczynamy od **providera `mock`**, więc rozwój i testy nie kosztują nic i nie zależą od internetu.

---

## 0. Priorytety (MoSCoW)

| Priorytet | Zakres |
|---|---|
| **MUST** (bez tego nie ma pracy) | rejestracja/logowanie (JWT, Argon2), izolacja danych po `user_id`, import CSV z 1 banku, ręczne dodawanie wydatków, kategoryzacja słowami kluczowymi, zapamiętywanie poprawek użytkownika, agregacje Pandas (sumy w kategoriach, zmiany m/m), dashboard z wykresami, anonimizacja regex, porady AI z agregatów, testy pytest + HTTPX, Docker Compose |
| **SHOULD** | deduplikacja przy ponownym imporcie, podgląd importu przed zapisem, filtrowanie/wyszukiwanie transakcji, historia wygenerowanych porad, CI w GitHub Actions, przełączanie OpenAI ↔ Anthropic zmienną środowiskową |
| **COULD** | budżety miesięczne z alertem, eksport raportu (CSV/PDF), drugi parser banku, tryb ciemny, wykrywanie subskrypcji (powtarzalne płatności) |
| **WON'T** (poza zakresem) | bezpośrednie połączenie z bankiem (open banking/PSD2), aplikacja mobilna, wielowalutowość z kursami, hosting publiczny |

---

## 1. Kluczowe decyzje techniczne (do zatwierdzenia na starcie)

| Decyzja | Propozycja | Uzasadnienie |
|---|---|---|
| Bank dla parsera | **do wyboru** (mBank / PKO BP / ING / Santander…) — bank, z którego masz własny wyciąg | Na własnych danych od razu przetestujesz problem „znikających pieniędzy” |
| Hashowanie haseł | **Argon2** (`pwdlib[argon2]` lub `argon2-cffi`) | Zwycięzca Password Hashing Competition, zalecany przez OWASP |
| JWT | `PyJWT`, access token ~60 min, nagłówek `Authorization: Bearer` | Prosty i wystarczający dla projektu; refresh token jako SHOULD |
| Sterownik DB | `psycopg` 3 + SQLAlchemy 2.0 (styl `Mapped[...]`) | Aktualny standard |
| Kwoty | `NUMERIC(12,2)` w bazie, `Decimal` w Pythonie | Nigdy `float` dla pieniędzy |
| Frontend build | **Vite** + React + TS | Szybki, standard |
| Zarządzanie stanem / zapytania | `@tanstack/react-query` + `axios`/`fetch` | Cache, odświeżanie, mniej kodu |
| Routing | `react-router` | Standard |
| Lint/format | `ruff` (Python), `eslint` + `prettier` (TS) | Jedno narzędzie zamiast kilku w Pythonie |

---

## 2. Model danych (wersja docelowa)

```
users
  id (PK), email (unique), password_hash, created_at

categories
  id (PK), user_id (FK, NULL = kategoria systemowa), name, color, icon, is_income

transactions
  id (PK), user_id (FK), date, amount NUMERIC(12,2), currency,
  description, description_normalized, counterparty,
  category_id (FK, NULL = nieprzypisana), source ('csv' | 'manual'),
  import_batch_id (FK, NULL), dedup_hash, created_at
  UNIQUE (user_id, dedup_hash)

import_batches
  id (PK), user_id (FK), bank, filename, rows_total, rows_imported,
  rows_duplicated, created_at

category_rules                      ← „pamięć” poprawek użytkownika
  id (PK), user_id (FK, NULL = reguła systemowa), keyword/pattern,
  match_type ('contains' | 'exact_counterparty' | 'regex'),
  category_id (FK), priority, source ('system' | 'user'), created_at

ai_advice
  id (PK), user_id (FK), period_start, period_end,
  provider, model, prompt_payload JSONB (zanonimizowane agregaty!),
  response_text, tokens_in, tokens_out, created_at
```

**Zasada izolacji:** każde repozytorium przyjmuje `user_id` jako obowiązkowy argument; nie istnieje
metoda pobierająca transakcje „wszystkich”. Test integracyjny sprawdza, że użytkownik B dostaje 404
na zasobie użytkownika A.

---

## 3. Endpointy API (wersja docelowa)

| Metoda | Ścieżka | Opis |
|---|---|---|
| POST | `/api/auth/register` | rejestracja |
| POST | `/api/auth/login` | logowanie → JWT |
| GET | `/api/auth/me` | dane zalogowanego |
| GET/POST | `/api/transactions` | lista (filtry: daty, kategoria, szukaj, paginacja) / dodanie ręczne |
| PATCH/DELETE | `/api/transactions/{id}` | edycja (w tym zmiana kategorii → tworzy regułę) / usunięcie |
| GET/POST/PATCH/DELETE | `/api/categories` | kategorie użytkownika + systemowe |
| GET/DELETE | `/api/rules` | podgląd/usuwanie zapamiętanych reguł |
| GET | `/api/imports/banks` | lista obsługiwanych banków |
| POST | `/api/imports/preview` | wgranie CSV → podgląd + proponowane kategorie (bez zapisu) |
| POST | `/api/imports/confirm` | zapis zaimportowanych transakcji |
| GET | `/api/analytics/summary?from&to` | przychody, wydatki, saldo okresu |
| GET | `/api/analytics/by-category?from&to` | sumy i udziały % w kategoriach |
| GET | `/api/analytics/monthly?months=6` | trend miesięczny |
| GET | `/api/analytics/changes?month=` | zmiana m/m w kategoriach |
| GET | `/api/analytics/top-merchants` | najczęstsi / najdrożsi odbiorcy |
| POST | `/api/advice` | wygeneruj poradę dla okresu |
| GET | `/api/advice` | historia porad |
| GET | `/api/advice/preview-payload` | **pokaż, co zostanie wysłane do AI** (transparentność — świetne do pracy) |

---

## 4. Harmonogram tygodniowy

Każdy etap = osobna gałąź / PR, zakończony checklistą „Definition of Done”.

### Etap 1 · Tydzień 1 (2–8 XI) — Fundament i szkielet end-to-end
- [ ] `docker-compose.yml`: `db` (postgres:16, wolumen, healthcheck), `backend`, `frontend`
- [ ] Backend: `pyproject.toml`/`requirements.txt`, `app/main.py`, `core/config.py` (pydantic-settings, `.env`), `core/database.py` (engine, `SessionLocal`, `get_db`)
- [ ] Endpoint `GET /api/health` sprawdzający połączenie z bazą
- [ ] `alembic init`, konfiguracja `env.py` pod modele i `DATABASE_URL`
- [ ] Frontend: `npm create vite@latest` (react-ts), Tailwind, strona startowa wołająca `/api/health`
- [ ] CORS w FastAPI dla `localhost:5173`
- [ ] pytest + pierwszy test `/api/health` (HTTPX `AsyncClient` / `TestClient`)
- [ ] GitHub Actions: `ruff` + `pytest` przy każdym pushu

**DoD:** `docker compose up --build` → frontend pokazuje „API OK, baza OK”; `/docs` (Swagger) działa.

### Etap 2 · Tydzień 2 (9–15 XI) — Model danych i uwierzytelnianie
- [ ] Modele SQLAlchemy: `User`, `Category`, `Transaction`, `ImportBatch`, `CategoryRule`, `AIAdvice`
- [ ] Pierwsza migracja Alembic + migracja z **seedem kategorii systemowych** (Jedzenie, Zakupy spożywcze, Restauracje, Transport, Paliwo, Mieszkanie, Rachunki, Subskrypcje, Rozrywka, Zdrowie, Odzież, Edukacja, Prezenty, Przelewy własne, Wynagrodzenie, Inne)
- [ ] `core/security.py`: hash/verify Argon2, tworzenie i dekodowanie JWT
- [ ] `api/deps.py`: `get_current_user`
- [ ] Endpointy `register`, `login`, `me` + schematy Pydantic (`EmailStr`, min. długość hasła)
- [ ] Testy: rejestracja, duplikat e-maila, złe hasło, dostęp bez tokenu → 401
- [ ] Osobna baza testowa (np. `postgres` w CI lub transakcja z rollbackiem per test)

**DoD:** przez Swagger można się zarejestrować, zalogować i wywołać `/me`; testy zielone.

### Etap 3 · Tydzień 3 (16–22 XI) — Transakcje i kategorie (CRUD) + frontend logowania
- [ ] Repozytoria `TransactionRepository`, `CategoryRepository` (zawsze z `user_id`)
- [ ] CRUD transakcji (dodanie ręczne, lista z filtrami i paginacją, edycja, usunięcie)
- [ ] CRUD kategorii użytkownika
- [ ] **Test izolacji**: użytkownik B nie widzi / nie edytuje danych A
- [ ] Frontend: `AuthContext`, strony Logowanie / Rejestracja, chronione trasy, layout (sidebar, navbar)
- [ ] Frontend: strona „Transakcje” — tabela + formularz ręcznego dodania wydatku

**DoD:** użytkownik loguje się w przeglądarce i ręcznie dodaje/edytuje wydatki.

### Etap 4 · Tydzień 4 (23–29 XI) — Import CSV (Pandas)
- [ ] Analiza formatu CSV wybranego banku (kodowanie np. `cp1250`, separator `;`, nagłówek z metadanymi, przecinek dziesiętny, format daty)
- [ ] `parsers/base.py` (`BaseBankParser`: `detect()`, `parse() -> DataFrame`), `parsers/<bank>.py`, `parsers/registry.py`
- [ ] `services/import_service.py`: czyszczenie (białe znaki, wielkie litery, usunięcie prefiksów typu „PŁATNOŚĆ KARTĄ”), normalizacja opisu, `dedup_hash` = hash(data, kwota, opis znormalizowany)
- [ ] `POST /imports/preview` i `/imports/confirm`, zapis `ImportBatch`
- [ ] Sztuczny plik `backend/tests/fixtures/<bank>_sample.csv` + testy parsera (kwoty, daty, polskie znaki, duplikaty)
- [ ] Frontend: strona „Import” — drag&drop pliku, wybór banku, tabela podglądu, przycisk „Zapisz”

**DoD:** wgrywasz swój prawdziwy wyciąg, widzisz transakcje w aplikacji; ponowny import nie dubluje danych.

### Etap 5 · Tydzień 5 (30 XI–6 XII) — Kategoryzacja i „uczenie się” z poprawek
- [ ] Słownik słów kluczowych (reguły systemowe w migracji/seedzie): `biedronka, lidl, żabka → Zakupy spożywcze`, `orlen, bp, shell → Paliwo`, `netflix, spotify → Subskrypcje`, `uber, bolt, jakdojade → Transport` itd.
- [ ] `services/categorization_service.py` — kolejność dopasowania:
  1. reguły użytkownika (`exact_counterparty` > `contains`), wg priorytetu,
  2. reguły systemowe,
  3. brak dopasowania → „Inne / do przypisania”
- [ ] Zmiana kategorii transakcji przez użytkownika ⇒ automatyczne utworzenie reguły użytkownika (+ opcja „zastosuj do podobnych transakcji wstecz”)
- [ ] Endpoint statystyki: % transakcji skategoryzowanych automatycznie (**metryka do rozdziału badawczego pracy**)
- [ ] Testy jednostkowe kategoryzacji (priorytety, wielkość liter, polskie znaki, reguła użytkownika nadpisuje systemową)
- [ ] Frontend: zmiana kategorii z poziomu tabeli (dropdown), widok „Do przypisania”, lista zapamiętanych reguł

**DoD:** po poprawieniu kategorii jednej transakcji kolejne podobne transakcje (także z następnego importu) trafiają do właściwej kategorii.

### Etap 6 · Tydzień 6 (7–13 XII) — Analityka (Pandas) i dashboard
- [ ] `services/analytics_service.py` (czyste funkcje na `DataFrame` → łatwe testy):
  - podsumowanie okresu (przychody, wydatki, saldo, stopa oszczędności),
  - sumy i udziały w kategoriach,
  - trend miesięczny,
  - zmiana m/m i względem średniej z 3 mies. per kategoria,
  - top odbiorcy, średni wydatek dzienny, największe pojedyncze wydatki,
  - (COULD) wykrywanie powtarzalnych płatności = subskrypcje
- [ ] Endpointy `/analytics/*` + schematy odpowiedzi
- [ ] Testy z ręcznie policzonymi oczekiwanymi wynikami
- [ ] Frontend „Dashboard”: karty (saldo, wydatki, przychody, stopa oszczędności), wykres kołowy/donut kategorii, słupkowy trend miesięczny, tabela zmian m/m, wybór okresu

**DoD:** dashboard pokazuje realny obraz Twoich wydatków; liczby zgadzają się z testami.

### Etap 7 · Tydzień 7 (14–20 XII) — Moduł doradczy AI
- [ ] `ai/anonymizer.py` (regex): numery kont/IBAN (`PL\d{26}`, 26 cyfr), numery kart, PESEL, telefony, e-maile, kody pocztowe/adresy, imiona i nazwiska (słownik polskich imion + heurystyka „Imię Nazwisko” wielkimi literami w przelewach)
- [ ] Testy anonimizacji — **dużo przypadków**, to mocny punkt pracy
- [ ] `ai/prompt_builder.py`: tylko agregaty (sumy w kategoriach, zmiany %, top kategorie, stopa oszczędności) → JSON; **bez pojedynczych transakcji**; prompt systemowy z rolą doradcy, zakazem wymyślania liczb i wymaganym formatem odpowiedzi (np. 3–5 rekomendacji z uzasadnieniem i szacowaną kwotą oszczędności)
- [ ] `ai/providers/base.py` (interfejs `generate_advice(payload) -> AdviceResult`), `openai.py`, `anthropic.py`, `mock.py`; wybór przez `AI_PROVIDER`
- [ ] Obsługa błędów (timeout, brak klucza, limit) + zapis do `ai_advice` (tokeny ⇒ koszt)
- [ ] Ograniczenie kosztów: cache porady dla tego samego okresu i niezmienionych danych, limit zapytań/dzień na użytkownika
- [ ] `GET /advice/preview-payload` — użytkownik widzi dokładnie, co wychodzi do API
- [ ] Testy endpointu z providerem `mock`

**DoD:** przycisk „Wygeneruj porady” zwraca sensowne rekomendacje na Twoich danych; w logach/bazie nie ma żadnych danych osobowych.

### Etap 8 · Tydzień 8–9 (21 XII–3 I) — Święta: frontend porad + bufor
- [ ] Strona „Porady AI”: wybór okresu, podgląd wysyłanych danych, wynik (karty rekomendacji), historia porad
- [ ] Nadrabianie zaległości z etapów 1–7
- [ ] (COULD) budżety miesięczne

**DoD:** wszystkie funkcje MUST działają w przeglądarce.

### Etap 9 · Tydzień 10 (4–10 I) — Jakość, testy, uruchamianie jednym poleceniem
- [ ] Pokrycie testami (`pytest-cov`) — cel ≥ 70% dla `services/`, `parsers/`, `ai/`
- [ ] Obsługa błędów i stanów pustych w UI (brak danych, błędny plik, błąd AI), walidacja formularzy
- [ ] Responsywność, spójny wygląd
- [ ] Docker Compose: produkcyjny build frontendu (nginx), automatyczne `alembic upgrade head` przy starcie backendu
- [ ] Skrypt danych demo (użytkownik demo + sztuczne transakcje z 6 miesięcy)
- [ ] README: instalacja, uruchomienie, zrzuty ekranu

**DoD:** na czystym komputerze `git clone` + `cp .env.example .env` + `docker compose up --build` = działająca aplikacja z danymi demo.

### Etap 10 · Tydzień 11 (11–17 I) — Stabilizacja i materiały do pracy → **v1.0**
- [ ] Testy manualne całych scenariuszy, poprawki błędów
- [ ] Diagramy do pracy (`docs/diagramy/`): architektura warstwowa, ERD bazy, diagram sekwencji „import CSV”, diagram sekwencji „generowanie porady AI” (z krokiem anonimizacji)
- [ ] Zrzuty ekranu (`docs/zrzuty/`)
- [ ] Pomiary do rozdziału badawczego: skuteczność kategoryzacji przed/po poprawkach, skuteczność anonimizacji, koszt i czas zapytania AI, porównanie OpenAI vs Anthropic na tych samych agregatach
- [ ] Tag `v1.0.0` na GitHubie

### Bufor · 18–31 I
Rezerwa na nieprzewidziane problemy i uwagi promotora. **Nie planujemy tu nowych funkcji.**

---

## 5. Przepływ danych w module AI (do rozdziału o architekturze)

```
Transakcje (DB) ──► Pandas: agregacja ──► Anonimizacja (regex) ──► Prompt builder ──► API LLM
                    (sumy, zmiany %)       (usunięcie PII z nazw     (JSON z agregatami   (OpenAI /
                                            odbiorców, jeśli trafią)  + instrukcja)        Anthropic)
                                                                                              │
UI „Porady AI” ◄── zapis w ai_advice (payload + odpowiedź + tokeny) ◄──────────────────────────┘
```

Model **nigdy** nie dostaje: pojedynczych transakcji, numerów kont, imion i nazwisk, e-maila użytkownika.

---

## 6. Ryzyka i jak je ograniczamy

| Ryzyko | Skutek | Zapobieganie |
|---|---|---|
| Nietypowy format CSV banku (kodowanie, metadane w nagłówku) | opóźnienie etapu 4 | Analiza pliku już w tygodniu 1; testy na sztucznym pliku |
| Koszty / dostępność API AI | brak porad podczas prezentacji | provider `mock`, cache porad, zapisane przykładowe odpowiedzi |
| Wycieki danych osobowych do AI | zarzut na obronie | tylko agregaty + anonimizacja + testy + endpoint podglądu payloadu |
| Pomieszanie danych użytkowników | poważny błąd bezpieczeństwa | `user_id` obowiązkowy w repozytoriach + testy izolacji |
| Święta / sesja / praca | poślizg | bufor 21.12–3.01 oraz 18–31.01, priorytety MoSCoW |
| Za duży zakres | niedokończona aplikacja | najpierw MUST, funkcje COULD tylko gdy MUST są gotowe |

---

## 7. Zasady pracy z repozytorium

- Gałąź `main` = zawsze działająca wersja. Praca na gałęziach `etap-N-nazwa`, scalanie przez Pull Request.
- Konwencja commitów: `feat:`, `fix:`, `test:`, `docs:`, `refactor:`, `chore:` (np. `feat(import): parser CSV dla mBanku`).
- Każdy etap kończy się wpisem w sekcji „Postęp” poniżej (przydatne przy pisaniu pracy).
- Sekrety tylko w `.env`; prawdziwe wyciągi tylko w `data/private/` (ignorowane przez Git).

## 8. Postęp

| Etap | Status | Data zakończenia | Uwagi |
|---|---|---|---|
| 0. Struktura repo + plan | ✅ | 2026-11-02 | |
| 1. Fundament | ⏳ | | |
| 2. Model danych + auth | ⏳ | | |
| 3. CRUD + frontend logowania | ⏳ | | |
| 4. Import CSV | ⏳ | | |
| 5. Kategoryzacja | ⏳ | | |
| 6. Analityka + dashboard | ⏳ | | |
| 7. Moduł AI | ⏳ | | |
| 8. Frontend porad + bufor | ⏳ | | |
| 9. Jakość + Docker | ⏳ | | |
| 10. Stabilizacja → v1.0 | ⏳ | | |
