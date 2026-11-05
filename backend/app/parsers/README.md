# Import wyciągów bankowych

Wyciągi PDF z ING obsługuje osobny parser (`ing_pdf.py`, etap 4). Pliki CSV obsługują dwa poziomy:

1. **Profile banków** (`profiles/*.json`): pełny opis formatu pliku, np. `ing.json`.
   Plik pasujący do profilu importuje się bez żadnych pytań.
2. **Importer uniwersalny** (`detector.py` + `generic.py`): dla nieznanego pliku zgaduje kodowanie,
   separator, wiersz nagłówka i role kolumn, a użytkownik potwierdza mapowanie w UI.
   Potwierdzone mapowanie zapisuje się jako profil użytkownika (tabela `bank_profiles`).

Każda ścieżka kończy się tym samym ujednoliconym `DataFrame`:

| kolumna        | typ        | opis                                  |
|----------------|------------|---------------------------------------|
| `date`         | date       | data operacji                         |
| `amount`       | Decimal    | kwota (ujemna = wydatek)              |
| `currency`     | str        | np. `PLN`                             |
| `description`  | str        | opis/tytuł operacji                   |
| `counterparty` | str / None | odbiorca lub nadawca                  |

Dalsze kroki (czyszczenie, deduplikacja, kategoryzacja) nie wiedzą, z jakiego banku pochodzi plik.

## Format wyciągu PDF z ING

Na podstawie 6 miesięcznych wyciągów (konto osobiste, 2026). Prawdziwe pliki leżą tylko w `data/private/`.

**Nagłówek:** numer i okres wyciągu, saldo początkowe i końcowe, suma i liczba uznań, suma i liczba obciążeń,
kwota zablokowana, saldo dostępne. We wszystkich 6 wyciągach saldo początkowe + uznania − obciążenia = saldo końcowe,
a saldo końcowe równa się początkowemu z następnego wyciągu.

**Kolumny tabeli:** data księgowania i data transakcji, dane kontrahenta, tytuł, szczegóły i numer transakcji, kwota.

| Cecha | Konsekwencja |
|---|---|
| Transakcja może zaczynać się na jednej stronie, a kończyć na następnej | łączenie wierszy między stronami |
| Kwota i numer transakcji mogą leżeć w tej samej lub w różnych liniach; tekst bywa łamany w środku wyrazu | odczyt według współrzędnych, a nie kolejnych linii |
| Kwota ma format `-1 403,86 PLN` | spacja jako separator tysięcy, przecinek dziesiętny, znak minus |
| Numer transakcji ma 18 cyfr | klucz deduplikacji |
| Płatność kartą ma w tytule własną datę, wcześniejszą od księgowania | do analizy data z tytułu; daty w kolumnach też mogą się różnić |
| Automatyczne przelewy Smart Saver po płatnościach, przelewy własne, wpłaty na cel | przelewy własne, poza wydatkami |
| Płatność w walucie obcej: kwota w PLN, waluta w tytule, prowizja jako osobna pozycja | kwota księgowana w PLN; prowizja jako koszt |
| Zwroty, wpłaty i wypłaty gotówki | osobne rodzaje operacji |
| Brak nazwy kontrahenta w części płatności lub tylko adres | `counterparty` może być puste |
| Tytuły zawierają nazwiska, numery telefonów i dowolny tekst | dane osobowe: nie mogą trafić do modułu AI |
