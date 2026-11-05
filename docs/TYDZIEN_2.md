# Tydzień 2: model danych i uwierzytelnianie

Plan przewiduje ten etap na 9–15 listopada 2026. Po tygodniu 1 jesteśmy przed harmonogramem, więc numery dni
oznaczają kolejność pracy, a nie daty.

**Cel tygodnia:** w bazie są wszystkie główne tabele, a przez Swagger można się zarejestrować, zalogować
i wywołać `/api/auth/me`. Testy działają na osobnej bazie i nie dotykają danych deweloperskich.

Dlaczego teraz? Każdy kolejny etap zapisuje dane konkretnego użytkownika. Transakcje, import i porady AI potrzebują
tabel oraz `user_id` zalogowanej osoby, dlatego model danych i logowanie muszą powstać przed nimi.

---

## 1. Jak to będzie działać

```
Rejestracja: e-mail + hasło ──► walidacja ──► hash Argon2 ──► zapis w tabeli users
Logowanie:   e-mail + hasło ──► porównanie z hashem ──► token JWT (ważny 60 min)
Zapytanie:   Authorization: Bearer <token> ──► get_current_user ──► endpoint dostaje użytkownika
```

| Metoda i ścieżka | Wynik |
|---|---|
| `POST /api/auth/register` | 201 i dane użytkownika, bez hasła; 409, gdy e-mail jest zajęty; 422 przy błędnych danych |
| `POST /api/auth/login` | 200 i token; 401 przy złych danych |
| `GET /api/auth/me` | 200 i dane zalogowanego; 401 bez ważnego tokenu |

---

## 2. Technologie tygodnia 2

### Modele SQLAlchemy i relacje
- **Co to:** klasy Pythona opisujące tabele, kolumny i powiązania między nimi.
- **Jak działa:** pola `Mapped[...]` definiują typy, a `ForeignKey` łączy tabele. Alembic porównuje modele z bazą i generuje migrację.
- **Po co nam:** wymuszamy poprawność na poziomie bazy. `NUMERIC(12,2)` daje dokładne kwoty, a `UNIQUE(user_id, dedup_hash)` blokuje duplikaty.

### Argon2 (`argon2-cffi`)
- **Co to:** funkcja haszowania haseł, zwycięzca Password Hashing Competition, zalecana przez OWASP.
- **Jak działa:** celowo zużywa czas i pamięć, a każdy hash ma losową sól. Dwa identyczne hasła dają różne hashe, a masowe zgadywanie jest kosztowne.
- **Po co nam:** wyciek bazy nie ujawnia haseł. Hasła nigdy nie są zapisywane ani logowane jawnym tekstem.

### JWT (`PyJWT`)
- **Co to:** podpisany token z identyfikatorem użytkownika (`sub`) i czasem ważności (`exp`).
- **Jak działa:** serwer podpisuje token kluczem `JWT_SECRET_KEY`, a przy każdym zapytaniu sprawdza podpis i ważność. Zawartość tokenu da się odczytać, ale nie da się jej zmienić bez klucza.
- **Po co nam:** API nie musi przechowywać sesji. W tokenie nie umieszczamy e-maila ani innych danych osobowych.

### Dependency Injection (`get_current_user`)
- **Co to:** zależność FastAPI, która z tokenu ustala zalogowanego użytkownika.
- **Po co nam:** endpoint deklaruje `user: CurrentUser` i nie może zapomnieć o sprawdzeniu tokenu. To podstawa izolacji danych z etapu 3.

### Osobna baza testowa
- **Jak działa:** testy łączą się z bazą `finanse_test`, która dostaje schemat z migracji. Każdy test działa w transakcji wycofywanej na końcu.
- **Po co nam:** testy nie zmieniają danych deweloperskich i nie wpływają na siebie nawzajem, a przy okazji sprawdzają same migracje.

---

## 3. Decyzje do sprawdzenia w tym tygodniu

| Temat | Decyzja | Uzasadnienie |
|---|---|---|
| Biblioteka haseł | `argon2-cffi` zamiast `pwdlib` | dojrzała, bezpośrednie użycie Argon2; nie potrzebujemy wielu algorytmów |
| Format logowania | formularz `OAuth2PasswordRequestForm` (wymaga `python-multipart`) | działa z przyciskiem „Authorize” w Swaggerze, czego wymaga kryterium ukończenia |
| Odpowiedź przy złym logowaniu | taki sam kod i komunikat dla złego e-maila i złego hasła | nie zdradza, które konto istnieje |
| Odświeżanie tokenu | brak w tym etapie | plan traktuje je jako SHOULD; po 60 minutach trzeba się zalogować ponownie |
| Pola transakcji z analizy PDF | data operacji, data księgowania, rodzaj operacji | zob. dzień 1 |
| Tabela `bank_profiles` | migracja dopiero w etapie 4 | powstanie razem z importerem CSV, który z niej korzysta |

**Klucz JWT (rozwiązane w dniu 3):** `.env.example` zawiera pusty `JWT_SECRET_KEY`. Backend generuje losowy klucz przy pierwszym
uruchomieniu i zapisuje go w wolumenie Dockera, a dawny przykładowy klucz zatrzymuje start.

---

## 4. Kolejne dni

### Dzień 1: modele
- [x] `backend/app/models/`: `User`, `Category`, `Transaction`, `ImportBatch`, `CategoryRule`, `AIAdvice`
- [x] W `Transaction` dodatkowo: `booking_date` obok daty operacji oraz `kind` (rodzaj: karta, BLIK, przelew, przelew własny, zwrot, gotówka, prowizja, inne), wynikające z analizy wyciągów ING
- [x] Ograniczenia i indeksy: `UNIQUE(user_id, dedup_hash)`, unikalny e-mail, indeks `(user_id, date)` pod filtrowanie
- [x] Decyzje `ondelete`: co się dzieje z transakcjami po usunięciu użytkownika lub kategorii
- [x] Model danych w `PLAN_IMPLEMENTACJI.md` zgodny z kodem

### Dzień 2: migracje i kategorie
- [x] Pierwsza migracja autogenerate, przeczytana przed commitem
- [x] Migracja z kategoriami systemowymi (16 kategorii z planu)
- [x] Sprawdzenie: `upgrade`, `alembic check`, `downgrade`, ponowny `upgrade`
- [x] Diagram ERD do pracy (`docs/diagramy/`)

### Dzień 3: bezpieczeństwo
- [x] Zależności: `argon2-cffi`, `PyJWT`, `email-validator`, `python-multipart`
- [x] `core/security.py`: `hash_password`, `verify_password`, `create_access_token`, `decode_access_token`
- [x] `JWT_SECRET_KEY` w `Settings`: minimalna długość, odrzucenie publicznego przykładu, automatyczne generowanie
- [x] Testy jednostkowe: poprawne i złe hasło, różne hashe tego samego hasła, token wygasły, podrobiony, z innym kluczem

### Dzień 4: endpointy
- [ ] `schemas/user.py`: `UserCreate` (`EmailStr`, minimalna długość hasła), `UserRead` (bez hasła), `Token`
- [ ] `repositories/user_repository.py`, `api/routes/auth.py`: `register`, `login`, `me`
- [ ] `api/deps.py`: `get_current_user` i alias `CurrentUser`
- [ ] E-mail normalizowany (małe litery), a duplikat obsłużony także przy jednoczesnej rejestracji (`IntegrityError` → 409)
- [ ] Czas logowania nie zdradza, czy konto istnieje: przy nieznanym e-mailu też liczony jest hash Argon2
- [ ] Limit długości hasła (minimum i maksimum), żeby bardzo długie hasła nie obciążały serwera

### Dzień 5: baza testowa i testy API
- [ ] `conftest.py`: tworzenie bazy `finanse_test`, migracje, transakcja wycofywana po każdym teście
- [ ] CI: testy na tej samej konfiguracji
- [ ] Testy: rejestracja, duplikat e-maila, wielkość liter w e-mailu, za krótkie hasło, złe hasło, nieistniejący e-mail, `/me` z tokenem i bez, token wygasły
- [ ] Test: odpowiedzi API i logi nie zawierają hasła ani hasha
- [ ] Test zgodności schematu: te same modele tworzą bazę przez `create_all` i przez migracje, a test porównuje obie na podstawie katalogu PostgreSQL (ograniczenia `CHECK`, wartości domyślne, indeksy). Zamyka lukę `alembic check`
- [ ] Celowe wprowadzenie błędów, żeby sprawdzić, czy testy je wykrywają

### Dzień 6: sprawdzenie w całości
- [ ] Ręczny przebieg w Swaggerze: rejestracja, „Authorize”, `/me`
- [ ] Czysty start: `docker compose down -v && docker compose up --build`
- [ ] Sprawdzenie w bazie, że hasło jest hashem Argon2

### Dzień 7: domknięcie
- [ ] Wpisy w dzienniku prac, odhaczony postęp w planie
- [ ] Uzupełnienie notatek o technologiach (Argon2, JWT)
- [ ] PR do `main` i tag

---

## 5. Definition of Done tygodnia 2
- [ ] Przez Swagger można się zarejestrować, zalogować i wywołać `/api/auth/me`
- [ ] Wszystkie tabele z sekcji 2 planu istnieją, z wyjątkiem `bank_profiles` (etap 4)
- [ ] Baza zawiera kategorie systemowe po czystym starcie
- [ ] Hasła są zapisane wyłącznie jako hash Argon2
- [ ] Testy przechodzą lokalnie i w GitHub Actions na osobnej bazie
- [ ] Dziennik prac i plan są aktualne
