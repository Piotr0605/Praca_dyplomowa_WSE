# Tydzień 4: import wyciągów

Plan przewiduje ten etap na 16–22 listopada 2026; wykonano go 7 listopada. Ten plik spisano po wykonaniu prac:
etap zaczął się od próby biblioteki na prawdziwych wyciągach, bo od jej wyniku zależało całe podejście.

**Cel tygodnia:** użytkownik wgrywa wyciąg z ING w PDF, widzi podgląd zgodny z sumami kontrolnymi banku, zapisuje
transakcje, a ponowny import nie tworzy duplikatów.

---

## 1. Zakres i decyzje

| Temat | Decyzja | Uzasadnienie |
|---|---|---|
| Format | PDF z ING (MUST), potem importer uniwersalny CSV (SHOULD) | PDF to jedyny potwierdzony format; CSV dodany tego samego dnia na prośbę użytkownika |
| Biblioteka | `pdfplumber` | daje współrzędne znaków i linii, potrzebne do odczytu tabeli bez struktury |
| Odczyt tekstu | słowa składane ze znaków, a nie przez `extract_words` | przy dolnej krawędzi strony biblioteka dzieliła tekst na litery |
| Kontrola | import zatrzymany, jeśli liczba lub suma uznań i obciążeń albo saldo nie zgadza się z nagłówkiem wyciągu | błąd odczytu nie może trafić do bazy nawet częściowo |
| Duplikaty | numer operacji z banku (hash SHA-256), `ON CONFLICT DO NOTHING` | dwa identyczne zakupy tego samego dnia nie są duplikatem |
| Przechowywanie pliku | żadne: podgląd i zapis przyjmują plik osobno | dane bankowe nie zostają w plikach tymczasowych serwera |
| Numer karty | usuwany z opisu | nie jest potrzebny do analizy |
| Testy | sztuczny wyciąg PDF o tym samym układzie, generowany w testach | prawdziwe wyciągi nie mogą trafić do repozytorium |
| Profil CSV | kolumny wskazywane nazwą z nagłówka, nie numerem | inna liczba wierszy metadanych nad tabelą nie psuje profilu |
| Profile wbudowane | pliki JSON w kodzie, nie wiersze tabeli `bank_profiles` | mają testy i zmieniają się razem z aplikacją; tabela trzyma tylko profile użytkowników (zmiana względem modelu danych w planie) |
| Błędny wiersz CSV | zatrzymuje import z numerem wiersza | CSV nie ma sum kontrolnych, więc pominięty wiersz byłby niezauważony |
| Duplikaty CSV | numer operacji; bez niego data, kwota, opis z numerem kolejnym w pliku | profil ING ma ten sam klucz co PDF, więc PDF i CSV z tego samego okresu nie dublują się |

## 2. Wykonane zadania
- [x] Próba `pdfplumber` na prawdziwych wyciągach, wyłącznie lokalnie i bez wypisywania treści
- [x] `parsers/ing_pdf.py`: nagłówek z sumami, tabela według współrzędnych, transakcje dzielone między strony, rodzaje operacji
- [x] Kontrola sum: zgodność wszystkich 6 prawdziwych wyciągów (1113 transakcji)
- [x] `tests/fixtures/ing_statement.py`: generator sztucznego wyciągu; `tests/unit/test_ing_pdf.py`
- [x] `scripts/check_statements.py`: sprawdzenie prawdziwych wyciągów bez ujawniania treści
- [x] `services/import_service.py`, `api/routes/imports.py`: podgląd, zapis, historia importów; testy
- [x] Strona „Import wyciągu” w przeglądarce
- [x] Porządki: usunięte zbędne pliki `.gitkeep` i nieużywane wolumeny Dockera
- [x] Importer uniwersalny CSV: profil, rozpoznawanie formatu, odczyt według profilu, tabela `bank_profiles`
- [x] Endpointy `GET/DELETE /imports/banks`, `POST /imports/detect`; podgląd i zapis przyjmują PDF i CSV
- [x] Kreator mapowania kolumn i lista zapisanych profili na stronie importu
- [x] Sprawdzenie profilu ING na prawdziwym eksporcie CSV (8.11: poprawiona nazwa kolumny kwoty)
- [ ] PR do `main`

## 3. Definition of Done
- [x] Wgranie prawdziwego wyciągu daje transakcje w aplikacji (sprawdzone przez API na tymczasowym koncie)
- [x] Ponowny import nie tworzy duplikatów
- [x] Testy przechodzą lokalnie i w CI
- [x] Dziennik prac, plan i notatki są aktualne
