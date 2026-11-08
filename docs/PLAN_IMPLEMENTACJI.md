# Plan implementacji — krok po kroku

**Start:** 2 listopada 2026 **Program gotowy:** 20 grudnia 2026 **Wersja 1.0:** 10 stycznia 2027 **Oddanie pracy:** do 15 stycznia 2027

Terminy są robocze: formalny termin WSE, czas procedury JSA i czas potrzebny promotorowi są jeszcze do potwierdzenia.
Mamy ok. 10 tygodni, w tym okres świąteczny, a równolegle powstaje część pisemna (sekcja 10). Dlatego:

1. **Najpierw działający szkielet od końca do końca** (baza → API → frontend), potem funkcje.
2. **Każdy tydzień kończy się działającą wersją** wypchniętą na GitHub (nawet jeśli skromną).
3. Święta (21.12–3.01) to **pomiary, poprawki i bufor** — nie planujemy tam nowych funkcji.
4. Moduł AI zaczynamy od **providera `mock`**, więc rozwój i testy nie kosztują nic i nie zależą od internetu.
5. **Badanie aplikacyjne** (hipotezy, metoda, wyniki, dyskusja) jest zaplanowane w [`BADANIA.md`](BADANIA.md) przed budową modułów;
   zadania oznaczone „(badanie)” zapewniają dane potrzebne do rzetelnego pomiaru.

---

## 0. Priorytety (MoSCoW)

| Priorytet | Zakres |
|---|---|
| **MUST** (bez tego nie ma pracy) | rejestracja/logowanie (JWT, Argon2), izolacja danych po `user_id`, import wyciągu z 1 banku (ING, PDF), ręczne dodawanie wydatków, kategoryzacja słowami kluczowymi, zapamiętywanie poprawek użytkownika, agregacje Pandas (sumy w kategoriach, zmiany m/m), dashboard z wykresami, anonimizacja regex, porady AI z agregatów, testy pytest + httpx2, Docker Compose |
| **SHOULD** | importer uniwersalny CSV z kreatorem mapowania, deduplikacja przy ponownym imporcie, podgląd importu przed zapisem, filtrowanie/wyszukiwanie transakcji, historia wygenerowanych porad, CI w GitHub Actions, przełączanie OpenAI ↔ Anthropic zmienną środowiskową |
| **COULD** | budżety miesięczne z alertem, eksport raportu (CSV/PDF), drugi parser banku, tryb ciemny, wykrywanie subskrypcji (powtarzalne płatności) |
| **WON'T** (poza zakresem) | bezpośrednie połączenie z bankiem (open banking/PSD2), aplikacja mobilna, wielowalutowość z kursami, hosting publiczny |

---

## 1. Kluczowe decyzje techniczne (do zatwierdzenia na starcie)

| Decyzja | Propozycja | Uzasadnienie |
|---|---|---|
| Bank dla parsera | **ING** (profil wbudowany) + importer uniwersalny z kreatorem mapowania | Własne dane do testów; inne banki przez profil bez pisania kodu |
| Obsługiwane formaty (decyzja 8.11) | **PDF tylko z ING** (z kontrolą sum) + **CSV z dowolnego banku** (profil lub kreator); PDF innego banku dostaje komunikat z prośbą o CSV | każdy polski bank daje eksport historii do CSV, a parser PDF to osobna, krucha praca dla każdego układu wyciągu i bez prawdziwych wyciągów nie da się go sprawdzić. MT940, XML (camt.053), OFX i XLS poza zakresem: służą głównie firmom. Na pokazie jedno zdanie zamiast listy formatów |
| Hashowanie haseł | **Argon2** (`pwdlib[argon2]` lub `argon2-cffi`) | Zwycięzca Password Hashing Competition, zalecany przez OWASP |
| JWT | `PyJWT`, access token ~60 min, nagłówek `Authorization: Bearer` | Prosty i wystarczający dla projektu; refresh token jako SHOULD |
| Sterownik DB | `psycopg` 3 + SQLAlchemy 2.0 (styl `Mapped[...]`) | Aktualny standard |
| Kwoty | `NUMERIC(12,2)` w bazie, `Decimal` w Pythonie | Nigdy `float` dla pieniędzy |
| Frontend build | **Vite** + React + TS | Szybki, standard |
| Zarządzanie stanem / zapytania | `@tanstack/react-query` + `axios`/`fetch` | Cache, odświeżanie, mniej kodu |
| Routing | `react-router` | Standard |
| Lint/format | `ruff` (Python), `oxlint` + `prettier` (TS) | Jedno narzędzie zamiast kilku w Pythonie |

---

## 2. Model danych (wersja docelowa)

```
users
  id (PK), email (unique, małe litery), password_hash, created_at

categories
  id (PK), user_id (FK, NULL = kategoria systemowa), name, color, icon, is_income
  UNIQUE (user_id, name), także dla kategorii systemowych

transactions
  id (PK), user_id (FK), date (operacji), booking_date (NULL), amount NUMERIC(12,2), currency,
  description, description_normalized, counterparty,
  category_id (FK, NULL = nieprzypisana), source ('pdf' | 'csv' | 'manual'),
  kind ('card' | 'blik' | 'transfer' | 'own_transfer' | 'refund' | 'cash' | 'fee' | 'other'),
  import_batch_id (FK, NULL), dedup_hash (NULL = transakcja ręczna), created_at
  UNIQUE (user_id, dedup_hash)

import_batches
  id (PK), user_id (FK), bank, filename, rows_total, rows_imported,
  rows_duplicated, created_at

category_rules                      ← „pamięć” poprawek użytkownika
  id (PK), user_id (FK, NULL = reguła systemowa), pattern,
  match_type ('contains' | 'exact_counterparty' | 'regex'),
  category_id (FK), priority, source ('system' | 'user'), created_at

bank_profiles                       ← mapowanie kolumn CSV (wbudowane + zapisane przez użytkownika)
  id (PK), user_id (FK), bank_name (UNIQUE z user_id),
  config JSONB (kodowanie, separator, mapowanie kolumn po nazwach,
  format daty, separator dziesiętny, sposób zapisu kwoty), created_at
  — profile wbudowane (np. ING) to pliki JSON w kodzie, nie wiersze tabeli

ai_advice
  id (PK), user_id (FK), period_start, period_end,
  provider, model, prompt_version, temperature, latency_ms (etap 7, badanie),
  prompt_payload JSONB (zanonimizowane agregaty!),
  response_text, tokens_in, tokens_out, created_at
```

**Usuwanie:** usunięcie użytkownika kasuje wszystkie jego dane. Usunięcie kategorii lub importu zostawia transakcje bez
powiązania, a reguły znikają razem ze swoją kategorią.

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
| GET/DELETE | `/api/imports/banks` | lista profili banków (wbudowane + użytkownika) / usunięcie własnego |
| POST | `/api/imports/detect` | auto-wykrycie formatu CSV → propozycja mapowania kolumn |
| POST | `/api/imports/preview` | wgranie PDF lub CSV → podgląd (bez zapisu); proponowane kategorie od etapu 5 |
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

Każdy etap kończy się checklistą „Definition of Done”. Zasady gałęzi opisuje sekcja 7.

### Etap 1 · Tydzień 1 (2–8 XI) — Fundament i szkielet end-to-end
- [x] `docker-compose.yml`: `db` (postgres:16, wolumen, healthcheck), `backend`, `frontend`
- [x] Backend: `pyproject.toml`/`requirements.txt`, `app/main.py`, `core/config.py` (pydantic-settings, `.env`), `core/database.py` (engine, `SessionLocal`, `get_db`)
- [x] Endpoint `GET /api/health` sprawdzający połączenie z bazą
- [x] `alembic init`, konfiguracja `env.py` pod modele i `DATABASE_URL`
- [x] Frontend: `npm create vite@latest` (react-ts), Tailwind, strona startowa wołająca `/api/health`
- [x] CORS w FastAPI dla `localhost:5173`
- [x] pytest + pierwszy test `/api/health` (`TestClient`)
- [x] GitHub Actions: `ruff` + `pytest` przy każdym pushu

**DoD:** `docker compose up --build` → frontend pokazuje „API OK, baza OK”; `/docs` (Swagger) działa.

### Etap 2 · do 8 XI — Model danych i uwierzytelnianie
- [x] Modele SQLAlchemy: `User`, `Category`, `Transaction`, `ImportBatch`, `CategoryRule`, `AIAdvice`
- [x] Pierwsza migracja Alembic + migracja z **seedem kategorii systemowych** (Jedzenie, Zakupy spożywcze, Restauracje, Transport, Paliwo, Mieszkanie, Rachunki, Subskrypcje, Rozrywka, Zdrowie, Odzież, Edukacja, Prezenty, Przelewy własne, Wynagrodzenie, Inne)
- [x] `core/security.py`: hash/verify Argon2, tworzenie i dekodowanie JWT
- [x] `api/deps.py`: `get_current_user`
- [x] Endpointy `register`, `login`, `me` + schematy Pydantic (`EmailStr`, min. długość hasła)
- [x] Testy: rejestracja, duplikat e-maila, złe hasło, dostęp bez tokenu → 401
- [x] Osobna baza testowa (np. `postgres` w CI lub transakcja z rollbackiem per test)

**DoD:** przez Swagger można się zarejestrować, zalogować i wywołać `/me`; testy zielone.

### Etap 3 · 9–15 XI — Transakcje i kategorie (CRUD) + frontend logowania
- [x] Repozytoria `TransactionRepository`, `CategoryRepository` (zawsze z `user_id`)
- [x] CRUD transakcji (dodanie ręczne, lista z filtrami i paginacją, edycja, usunięcie)
- [x] CRUD kategorii użytkownika
- [x] **Test izolacji**: użytkownik B nie widzi / nie edytuje danych A
- [x] Przypisanie kategorii do transakcji i reguły: kategoria musi być systemowa albo należeć do tego samego użytkownika, bo baza tego nie wymusza; test z cudzą kategorią (zob. dziennik, tydzień 2, dzień 1)
- [x] Użytkownik nie może edytować ani usuwać kategorii systemowych
- [x] Frontend: `AuthContext`, strony Logowanie / Rejestracja, chronione trasy, layout (sidebar, navbar)
- [x] Frontend: strona „Transakcje” — tabela + formularz ręcznego dodania wydatku

**DoD:** użytkownik loguje się w przeglądarce i ręcznie dodaje/edytuje wydatki.

### Etap 4 · 16–22 XI — Import wyciągów: ING PDF + importer uniwersalny CSV

**Najpierw parser PDF ING (MUST).** Wyciągi pobierane z ING są w PDF, a zapisane w nim salda i sumy pozwalają
sprawdzić każdy import. Format opisuje `backend/app/parsers/README.md`. Importer CSV powstaje po nim (SHOULD); jeśli
zabraknie czasu, wypada z zakresu albo przechodzi na święta, po pomiarach. Jeśli ING udostępnia też eksport CSV, dostanie zwykły profil `ing.json`.

Dla plików CSV podejście dwupoziomowe. W pełni automatyczny parser „dla wszystkich banków” nie istnieje, bo banki różnią się
kodowaniem, separatorem, liczbą wierszy metadanych nad tabelą, nazwami kolumn, formatem dat, znakiem kwoty
(jedna kolumna ze znakiem albo osobne „Uznania”/„Obciążenia”) i blokadami kartowymi. Da się jednak zrobić importer
uniwersalny, który sam zgaduje większość ustawień, a resztę dopytuje użytkownika:

1. **Profil ING** (dedykowany, dokładnie przetestowany na prawdziwym pliku): pewny import bez pytań.
2. **Importer uniwersalny** dla każdego innego banku:
   - wykrycie kodowania (próba `utf-8-sig` → `cp1250` → `iso-8859-2`),
   - wykrycie separatora (`csv.Sniffer` na próbce: `;` `,` `\t`),
   - znalezienie wiersza nagłówka (pierwszy wiersz zawierający słowa typu „data”, „kwota”, „tytuł”, „opis”),
   - zgadywanie roli kolumn po nazwach (słownik synonimów) i po zawartości (czy wartości parsują się jako data / kwota),
   - **kreator mapowania w UI**: użytkownik potwierdza lub poprawia, która kolumna to data, kwota, opis, kontrahent,
   - zapisanie mapowania jako **profil banku** użytkownika (tabela `bank_profiles`, JSON z ustawieniami), więc kolejny
     import z tego banku jest już automatyczny.
3. Profile wbudowane (ING i ewentualne kolejne) to te same pliki konfiguracyjne co profile użytkownika, tylko dostarczone z aplikacją.
   Dodanie banku = nowy profil JSON, bez pisania kodu.

**Parser PDF ING**
- [x] Sprawdzenie `pdfplumber` na prawdziwych wyciągach, lokalnie, z raportem bez danych osobowych; wybór biblioteki
- [x] `parsers/ing_pdf.py`: odczyt wierszy według współrzędnych kolumn, łączenie transakcji dzielonych między strony, wynik jako lista transakcji (`ParsedTransaction`); wspólny format z importerem CSV ustalimy razem z nim
- [x] Walidacja importu: liczba i suma uznań oraz obciążeń, saldo początkowe + uznania − obciążenia = saldo końcowe; niezgodność zatrzymuje zapis i pokazuje błąd
- [x] Rozpoznanie rodzajów operacji (karta, BLIK, przelew, Smart Saver, przelew własny, zwrot, wpłata i wypłata gotówki, prowizja)
- [x] Skrypt tworzący sztuczny PDF o tym samym układzie (`backend/tests/fixtures/`) + testy: podział między strony, kwoty z separatorem tysięcy, waluta obca, zwrot, duplikaty, celowo niezgodna suma
- [x] Porównanie z prawdziwymi wyciągami (lokalnie): liczby i sumy zgodne z nagłówkiem wszystkich 6 plików

**Importer uniwersalny CSV** (SHOULD; wykonany 7.11 na prośbę użytkownika)
- [ ] Analiza prawdziwego eksportu CSV z ING (czeka na plik; profil przygotowany na podstawie opisu formatu) (kodowanie, separator, wiersze metadanych, kolumny, format daty i kwot, blokady)
- [x] `parsers/csv_profile.py` (model profilu: kodowanie, separator, wiersz nagłówka, mapowanie kolumn, format daty, separator dziesiętny, sposób wyznaczania znaku kwoty)
- [x] `parsers/csv_detect.py` (auto-wykrywanie: kodowanie, separator, nagłówek, role kolumn) + `parsers/csv_generic.py` (odczyt według profilu, te same pola co parser PDF)
- [x] `parsers/profiles/ing.json` + testy na sztucznym pliku w formacie ING
- [x] tabela `bank_profiles` (migracja), endpoint `POST /imports/detect` (zwraca propozycję mapowania)
- [x] Frontend: krok „Mapowanie kolumn” pokazywany tylko wtedy, gdy plik nie pasuje do żadnego profilu
- [x] `services/import_service.py`: czyszczenie (białe znaki, wielkie litery, usunięcie prefiksów typu „PŁATNOŚĆ KARTĄ”), normalizacja opisu, `dedup_hash` = hash numeru transakcji z banku, a gdy go brak: hash(data, kwota, opis znormalizowany)
- [x] `POST /imports/preview` i `/imports/confirm`, zapis `ImportBatch`
- [x] Sztuczne pliki CSV (`backend/tests/fixtures/csv_samples.py`) + testy parsera (kwoty, daty, polskie znaki, duplikaty)
- [x] Frontend: strona „Import” — wybór pliku PDF, tabela podglądu, przycisk „Zapisz” i CSV; bank rozpoznawany po profilu zamiast ręcznego wyboru

**DoD:** wgrywasz swój prawdziwy wyciąg, widzisz transakcje w aplikacji; ponowny import nie dubluje danych.

### Etap 5 · 23–29 XI — Kategoryzacja i „uczenie się” z poprawek
- [ ] Strona „Kategorie” w przeglądarce: dodawanie, zmiana nazwy i koloru, usuwanie własnych (API gotowe w etapie 3)
- [ ] Przelewy własne (Smart Saver, „Przelew własny”, „Wpłata na cel”) trafiają do kategorii „Przelewy własne” i nie liczą się jako wydatki ani przychody
- [ ] Słownik słów kluczowych (reguły systemowe w migracji/seedzie): `biedronka, lidl, żabka → Zakupy spożywcze`, `orlen, bp, shell → Paliwo`, `netflix, spotify → Subskrypcje`, `uber, bolt, jakdojade → Transport` itd.
- [ ] `services/categorization_service.py` — kolejność dopasowania:
  1. reguły użytkownika (`exact_counterparty` > `contains`), wg priorytetu,
  2. reguły systemowe,
  3. brak dopasowania → „Inne / do przypisania”
- [ ] Zmiana kategorii transakcji przez użytkownika ⇒ automatyczne utworzenie reguły użytkownika (+ opcja „zastosuj do podobnych transakcji wstecz”)
- [ ] Endpoint statystyki: % transakcji skategoryzowanych automatycznie (**metryka do rozdziału badawczego pracy**)
- [ ] (badanie) Kategoryzacja jako czysta funkcja (transakcja + reguły → kategoria + dopasowana reguła), tworzenie reguły z poprawki jako osobna funkcja: tej samej logiki używa aplikacja i symulacja
- [ ] (badanie) Pole `transactions.categorized_by` (`system_rule` / `user_rule` / `manual`) i identyfikator dopasowanej reguły (migracja)
- [ ] (badanie) Słownik reguł systemowych w wersjonowanym pliku, strojony tylko na miesiącach 1–3; tag `badanie-slownik` przed pomiarem
- [ ] (badanie) `backend/research/`: narzędzie do ręcznego etykietowania transakcji (grupowanie po kontrahencie, wynik w `data/private/`) i skrypt symulacji 6 miesięcy, wariant A (słownik) i B (słownik + poprawki), wyniki tylko zbiorcze
- [ ] (badanie) Etykietowanie 1113 transakcji przez autora, przed pomiarem (ok. 1–2 godz.)
- [ ] Testy jednostkowe kategoryzacji (priorytety, wielkość liter, polskie znaki, reguła użytkownika nadpisuje systemową)
- [ ] Frontend: zmiana kategorii z poziomu tabeli (dropdown), widok „Do przypisania”, lista zapamiętanych reguł

**DoD:** po poprawieniu kategorii jednej transakcji kolejne podobne transakcje (także z następnego importu) trafiają do właściwej kategorii.

### Etap 6 · 30 XI–6 XII — Analityka (Pandas) i dashboard
- [ ] `services/analytics_service.py` (czyste funkcje na `DataFrame` → łatwe testy):
  - podsumowanie okresu (przychody, wydatki, saldo, stopa oszczędności),
  - sumy i udziały w kategoriach,
  - trend miesięczny,
  - zmiana m/m i względem średniej z 3 mies. per kategoria,
  - top odbiorcy, średni wydatek dzienny, największe pojedyncze wydatki,
  - (COULD) wykrywanie powtarzalnych płatności = subskrypcje
- [ ] Endpointy `/analytics/*` + schematy odpowiedzi
- [ ] Testy z ręcznie policzonymi oczekiwanymi wynikami
- [ ] Przelewy własne (`kind = own_transfer`) poza wydatkami i przychodami; zwroty pomniejszają wydatki; test na danych ze Smart Saver
- [ ] Kolory kategorii systemowych (`color`, `icon` są na razie puste) dobrane pod wykresy
- [ ] Frontend „Dashboard”: karty (saldo, wydatki, przychody, stopa oszczędności), wykres kołowy/donut kategorii, słupkowy trend miesięczny, tabela zmian m/m, wybór okresu

**DoD:** dashboard pokazuje realny obraz Twoich wydatków; liczby zgadzają się z testami.

### Etap 7 · 7–13 XII — Moduł doradczy AI
- [ ] `ai/anonymizer.py` (regex): numery kont/IBAN (`PL\d{26}`, 26 cyfr), numery kart, PESEL, telefony, e-maile, kody pocztowe/adresy, imiona i nazwiska (słownik polskich imion + heurystyka „Imię Nazwisko” wielkimi literami w przelewach)
- [ ] (badanie) Anonimizator jako czysta funkcja zwracająca też listę zamaskowanych fragmentów z typem
- [ ] (badanie) Generator sztucznego korpusu tytułów z oznaczonymi danymi osobowymi (stałe ziarno), część robocza i testowa; testową zamrozić przed strojeniem reguł
- [ ] Testy anonimizacji — **dużo przypadków**, to mocny punkt pracy; także dane z tytułów przelewów: imiona i nazwiska, nazwy kontaktów, telefony częściowo zamaskowane, dowolny tekst. Tylko sztuczne przypadki w repozytorium
- [ ] `ai/prompt_builder.py`: tylko agregaty (sumy w kategoriach, zmiany %, top kategorie, stopa oszczędności) → JSON; **bez pojedynczych transakcji**; prompt systemowy z rolą doradcy, zakazem wymyślania liczb i wymaganym formatem odpowiedzi (np. 3–5 rekomendacji z uzasadnieniem i szacowaną kwotą oszczędności)
- [ ] `ai/providers/base.py` (interfejs `generate_advice(payload) -> AdviceResult`), `openai.py`, `anthropic.py`, `mock.py`; wybór przez `AI_PROVIDER`
- [ ] Obsługa błędów (timeout, brak klucza, limit) + zapis do `ai_advice` (tokeny ⇒ koszt)
- [ ] (badanie) `ai_advice`: wersja promptu, temperatura, czas odpowiedzi w ms (migracja); stała temperatura i wersja promptu
- [ ] (badanie) Skrypt zgodności liczb: czy kwoty i procenty z porady wynikają z wysłanego pakietu agregatów
- [ ] Ograniczenie kosztów: cache porady dla tego samego okresu i niezmienionych danych, limit zapytań/dzień na użytkownika
- [ ] `GET /advice/preview-payload` — użytkownik widzi dokładnie, co wychodzi do API
- [ ] Testy endpointu z providerem `mock`

**DoD:** przycisk „Wygeneruj porady” zwraca sensowne rekomendacje na Twoich danych; w logach/bazie nie ma żadnych danych osobowych.

### Etap 8 · 14–20 XII — Frontend porad
- [ ] Strona „Porady AI”: wybór okresu, podgląd wysyłanych danych, wynik (karty rekomendacji), historia porad
- [ ] (COULD) budżety miesięczne
- [ ] (badanie) Eksport porad do ślepej oceny: losowa kolejność, bez nazwy dostawcy, klucz w osobnym pliku

**DoD:** wszystkie funkcje MUST działają w przeglądarce.

### Etap 9 · 14–20 XII — Jakość, testy, uruchamianie jednym poleceniem
- [ ] Pokrycie testami (`pytest-cov`) — cel ≥ 70% dla `services/`, `parsers/`, `ai/`
- [ ] Obsługa błędów i stanów pustych w UI (brak danych, błędny plik, błąd AI), walidacja formularzy
- [ ] Responsywność, spójny wygląd
- [ ] Docker Compose: produkcyjny build frontendu (nginx, wspólny adres dla API, bez `VITE_API_URL`), bez `--reload`, bez podmontowanego kodu i narzędzi deweloperskich w obrazie; `alembic upgrade head` przy starcie już działa
- [ ] Swagger UI serwowany lokalnie: `/docs` pobiera teraz pliki z `cdn.jsdelivr.net` i bez internetu jest pusta (sprawdzone w tygodniu 2)
- [ ] Sprawdzenie reguły prywatności: strona, `/docs` i backend nie łączą się z zewnętrznymi serwerami poza `ai/providers/`
- [ ] Skrypt danych demo (użytkownik demo + sztuczne transakcje z 6 miesięcy)
- [ ] (badanie) Kilka sztucznych profili finansowych do porównania porad AI (zbiór D5 w `BADANIA.md`)
- [ ] README: instalacja, uruchomienie, zrzuty ekranu

- [ ] Test na komputerze bez pobranych obrazów i z domyślnymi portami, z pomiarem czasu pierwszego uruchomienia (w tygodniu 1 nie zostało to sprawdzone)

**DoD:** na czystym komputerze `git clone` + `cp .env.example .env` + `docker compose up --build` = działająca aplikacja z danymi demo.

### Etap 10 · 21 XII–10 I — Stabilizacja, pomiary i materiały do pracy → **v1.0**
- [ ] Testy manualne całych scenariuszy, poprawki błędów
- [ ] Diagramy do pracy (`docs/diagramy/`): architektura warstwowa, ERD bazy (aktualizacja), diagram sekwencji „import wyciągu”, diagram sekwencji „generowanie porady AI” (z krokiem anonimizacji)
- [ ] Eksport diagramów do PNG lub SVG do pracy (`mermaid-cli` w przypiętej wersji, wymaga zgody na pobranie pakietu)
- [ ] Zrzuty ekranu (`docs/zrzuty/`)
- [ ] Pomiary według protokołu [`BADANIA.md`](BADANIA.md) (H1–H4) jednym poleceniem na wersji końcowej; wyniki zbiorcze w `docs/badania/`, sekcje 5–7 protokołu uzupełnione
- [ ] Ślepa ocena porad przez autora (bez nazwy dostawcy, klucz otwierany po ocenie)
- [ ] Zapytać promotora, czy repozytorium może być publiczne przed obroną i kontrolą JSA; sprawdzić, czy uczelnia wymaga opisania użycia AI w pracy
- [ ] Tag `v1.0.0` na GitHubie

### Oddanie · 11–15 I
Kontrola JSA, wydruk i złożenie pracy. **Żadnych nowych funkcji:** od 4 stycznia program dostaje tylko poprawki krytycznych błędów.

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
| Nietypowy format wyciągu lub zmiana układu PDF przez bank | opóźnienie etapu 4, błędne kwoty | Analiza formatu już w tygodniu 1; testy na sztucznym pliku; sumy kontrolne zatrzymują błędny import |
| Koszty / dostępność API AI | brak porad podczas prezentacji | provider `mock`, cache porad, zapisane przykładowe odpowiedzi |
| Wycieki danych osobowych do AI | zarzut na obronie | tylko agregaty + anonimizacja + testy + endpoint podglądu payloadu |
| Pomieszanie danych użytkowników | poważny błąd bezpieczeństwa | `user_id` obowiązkowy w repozytoriach + testy izolacji |
| Święta / sesja / praca | poślizg | bufor świąteczny 21.12–3.01 i zapas przed 15.01, priorytety MoSCoW |
| Za duży zakres | niedokończona aplikacja lub praca | najpierw MUST; wycinanie w kolejności: funkcje COULD, importer uniwersalny CSV, drugi dostawca AI (wtedy też zmiana celu we wstępie) |

---

## 7. Zasady pracy z repozytorium

- Gałąź `main` = zawsze działająca, sprawdzona wersja. Bezpośrednio na `main` nic się nie commituje.
- Gałąź `develop` = bieżąca praca. Każdy dzień kończy się commitem (lub kilkoma) na `develop`.
- Gdy dzień lub etap jest ukończony i zweryfikowany, `develop` jest scalana do `main` przez Pull Request,
  a stan oznaczany tagiem z adnotacją (np. `tydzien-1-dzien-3`). Tagi pozwalają w pracy dyplomowej
  odwołać się do konkretnego stanu kodu.
- `main` jest chroniona na GitHubie: zmiana tylko przez Pull Request, także dla właściciela repozytorium;
  zablokowane wymuszone nadpisanie historii (force push) i usunięcie gałęzi. Scalenie wymaga zielonych testów
  w GitHub Actions (joby `backend` i `frontend`).
- Konwencja commitów: `feat:`, `fix:`, `test:`, `docs:`, `refactor:`, `chore:` (np. `feat(import): parser CSV dla mBanku`).
- Każdy etap kończy się wpisem w sekcji „Postęp” poniżej (przydatne przy pisaniu pracy).
- Sekrety tylko w `.env`; prawdziwe wyciągi tylko w `data/private/` (ignorowane przez Git).

## 8. Postęp

| Etap | Status | Data zakończenia | Uwagi |
|---|---|---|---|
| 0. Struktura repo + plan | ✅ | 2026-11-02 | |
| 1. Fundament | ✅ | 2026-11-04 | format wyciągu opisany, pliki w `data/private/` |
| 2. Model danych + auth | ✅ | 2026-11-05 | |
| 3. CRUD + frontend logowania | ✅ | 2026-11-07 | |
| 4. Import wyciągów | ✅ | 2026-11-07 | PDF z ING i importer uniwersalny CSV z kreatorem mapowania; profil ING CSV czeka na prawdziwy plik |
| 5. Kategoryzacja | ⏳ | | |
| 6. Analityka + dashboard | ⏳ | | |
| 7. Moduł AI | ⏳ | | |
| 8. Frontend porad | ⏳ | | |
| 9. Jakość + Docker | ⏳ | | |
| 10. Stabilizacja → v1.0 | ⏳ | | |

---

## 9. Prezentacja i obrona

### Gdzie działa aplikacja i jakie dane opuszczają komputer
„Aplikacja webowa” oznacza tu **technologię** (interfejs w przeglądarce, komunikacja HTTP między frontendem
a backendem), a nie hosting w internecie. Cały system (przeglądarka, frontend, backend, baza) działa na jednym
komputerze, a ruch między warstwami idzie przez `localhost` (interfejs pętli zwrotnej) i nie wychodzi do sieci.
Porty kontenerów są wystawione tylko na `127.0.0.1`, więc aplikacji nie widać nawet z sieci lokalnej.

| Dane | Gdzie trafiają |
|---|---|
| Wyciągi CSV, transakcje, konto użytkownika | tylko lokalna baza PostgreSQL (wolumen Dockera) |
| Porady AI z providerem `mock` | nic nie opuszcza komputera |
| Porady AI z OpenAI / Anthropic | **wyłącznie** zanonimizowane agregaty (sumy kategorii, zmiany %), tylko po kliknięciu „Wygeneruj porady”; użytkownik widzi wcześniej podgląd wysyłanego JSON-a |

Warunki, których pilnujemy w kodzie, żeby to twierdzenie było prawdziwe:
- frontend nie ładuje niczego z zewnętrznych serwerów (czcionki, ikony, biblioteki z CDN, analityka): wszystko jest w paczce budowanej przez Vite,
- jedynym miejscem w backendzie, które łączy się z internetem, jest `ai/providers/` (łatwe do wskazania i przetestowania),
- logi nie zawierają treści transakcji.

Na obronie warto to sformułować precyzyjnie: *„dane finansowe są przechowywane i przetwarzane lokalnie;
poza urządzenie, i to tylko na żądanie użytkownika, trafiają wyłącznie zanonimizowane agregaty”*.
Architektura pozwala też wdrożyć system na własnym serwerze (np. domowym lub firmowym), ale wtedy dane są
na tym serwerze. To kierunek rozwoju, a nie zakres pracy.

### Uruchomienie na pokazie
1. **Dzień przed:** `git pull`, `docker compose up --build` przy dostępie do internetu (pobranie obrazów),
   wczytanie danych demo, przejście całego scenariusza raz na próbę.
2. **Przed wejściem na salę:** wyłączyć inne projekty Dockera zajmujące porty (np. finshield-api),
   uruchomić `docker compose up`, otworzyć w przeglądarce kartę aplikacji i kartę `localhost:8000/docs`
   (`/docs` działa bez internetu dopiero po zadaniu z etapu 9).
3. **AI:** jeśli jest internet i ważny klucz API, `AI_PROVIDER=openai` lub `anthropic`; jeśli nie, `mock`
   albo zapisane wcześniej porady z historii.
4. **Plan B:** nagranie ekranu całego scenariusza i zrzuty ekranu (`docs/zrzuty/`) na pendrive i w chmurze.

### Scenariusz pokazu (ok. 10 minut)
| # | Krok | Co pokazuje (argument dla komisji) | Czas |
|---|---|---|---|
| 1 | Logowanie użytkownika demo | uwierzytelnianie JWT, hasła hashowane Argon2 | 0:30 |
| 2 | Import wyciągu PDF w formacie ING (sztucznego, bez prawdziwych danych) | odczyt PDF, zgodność z sumami kontrolnymi wyciągu, podsumowanie importu | 1:30 |
| 3 | Ponowny import tego samego pliku | deduplikacja (numer transakcji, `dedup_hash` + ograniczenie `UNIQUE`): 0 nowych transakcji | 0:30 |
| 4 | Import pliku z innego banku przez importer uniwersalny | mapowanie kolumn, zapis profilu, uniwersalność rozwiązania | 1:30 |
| 5 | Lista transakcji z automatycznymi kategoriami, ręczna poprawka jednej | kategoryzacja słownikowa i reguła zapamiętana z poprawki | 1:30 |
| 6 | Dashboard: wydatki wg kategorii, trend miesięczny | analityka w Pandas, wizualizacja | 1:30 |
| 7 | Porady AI: najpierw podgląd wysyłanych danych, potem generowanie | anonimizacja, brak danych osobowych w zapytaniu, wymienny provider | 2:00 |
| 8 | (opcjonalnie) `localhost:8000/docs` i zielony przebieg GitHub Actions | dokumentacja API, testy automatyczne, pokrycie | 0:30 |

### Pytania, których można się spodziewać
- *Skąd pewność, że do AI nie trafiają dane osobowe?* → podgląd payloadu w UI, testy anonimizacji, tabela `ai_advice` z zapisem wysłanego JSON-a.
- *Co, jeśli bank zmieni format pliku?* → importer uniwersalny z profilami mapowania.
- *Czy użytkownik A zobaczy dane użytkownika B?* → `user_id` w każdym zapytaniu repozytorium + test izolacji.
- *Dlaczego lokalnie, a nie w chmurze?* → prywatność danych finansowych, zerowy koszt, działanie bez internetu (z `mock`).

---

## 10. Część pisemna

Część pisemna powstaje równolegle z programem. Układ rozdziałów to propozycja do konsultacji z promotorem, a dokładne
wymagania formalne trzeba sprawdzić w wytycznych WSE.

| Część | Szkic gotowy do | Materiał źródłowy |
|---|---|---|
| Konspekt i układ rozdziałów, rozmowa z promotorem, gdy będzie możliwa | 8 XI | ten plan, `BADANIA.md` |
| 1. Podstawy teoretyczne: finanse osobiste, modele językowe | 29 XI | literatura |
| 2. Przegląd rozwiązań i analiza wymagań | 6 XII | istniejące aplikacje, sekcja 0 |
| 3. Wykorzystane technologie | 13 XII | `NOTATKI_TECHNOLOGIE.md` |
| 4. Architektura i model danych | 13 XII | `diagramy/`, sekcje 2, 3 i 5 |
| 5. Implementacja: import, kategoryzacja, analityka, anonimizacja, moduł AI | 20 XII | `DZIENNIK_PRAC.md` |
| 6. Badanie aplikacyjne: hipotezy, metoda, wyniki, dyskusja | metoda 20 XII, wyniki 3 I | `BADANIA.md`, pomiary z etapu 10 |
| Zakończenie, wstęp, streszczenie, bibliografia | 3 I | gotowy tekst |

- [ ] Stała pozycja w tygodniu: 1–2 godziny na literaturę; pozycje zapisywane od razu z pełnym opisem bibliograficznym
- [ ] Po ukończeniu każdego modułu krótki szkic jego opisu, póki decyzje są świeże
- [ ] Ustalić terminy: formalny termin WSE, procedura JSA, czas czytania przez promotora; po ich poznaniu poprawić harmonogram
- [ ] Sprawdzić zasady WSE dotyczące użycia i deklarowania AI
- [ ] Całość u promotora najpóźniej około 3 I; wcześniejsze rozdziały wysyłane na bieżąco
- [ ] 4–10 I: poprawki promotora, formatowanie, spis treści i rysunków
- [ ] 11–15 I: kontrola JSA, wydruk, złożenie

Dziennik prac to materiał źródłowy, a nie gotowy tekst: wymaga przepisania językiem akademickim i odwołań do literatury.
Wstęp i zakończenie muszą na końcu zgadzać się z tym, co faktycznie powstało.
