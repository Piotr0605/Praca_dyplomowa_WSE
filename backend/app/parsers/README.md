# Import wyciągów bankowych

Aplikacja przyjmuje dwa rodzaje plików: **wyciąg PDF z ING** i **plik CSV z dowolnego banku**. Parserów PDF innych
banków celowo nie ma (decyzja w planie, sekcja 1): PDF innego banku dostaje komunikat z prośbą o eksport CSV.

Wyciągi PDF z ING obsługuje osobny parser (`ing_pdf.py`). Pliki CSV obsługują dwa poziomy:

1. **Profile** (`csv_profile.py`): opis formatu pliku: kodowanie, separator, format daty, separator dziesiętny
   i nazwy kolumn. Profile wbudowane to pliki `profiles/*.json` (np. `ing.json`), a profile użytkowników
   leżą w tabeli `bank_profiles`. Plik pasujący do profilu importuje się bez żadnych pytań.
2. **Importer uniwersalny** (`csv_detect.py`): dla nieznanego pliku zgaduje ustawienia, a użytkownik
   potwierdza je w kreatorze mapowania kolumn. Potwierdzone ustawienia zapisują się jako jego profil.

Odczyt według profilu wykonuje `csv_generic.py`. Oba parsery zwracają te same pola:

| kolumna        | typ        | opis                                  |
|----------------|------------|---------------------------------------|
| `date`         | date       | data operacji                         |
| `amount`       | Decimal    | kwota (ujemna = wydatek)              |
| `currency`     | str        | np. `PLN`                             |
| `description`  | str        | opis/tytuł operacji                   |
| `counterparty` | str / None | odbiorca lub nadawca                  |

Dalsze kroki (czyszczenie, deduplikacja, kategoryzacja) nie wiedzą, z jakiego banku pochodzi plik.

## Importer CSV

**Rozpoznawanie formatu** (`csv_detect.detect`):

| Krok | Sposób |
|---|---|
| kodowanie | UTF-8, a gdy się nie da: cp1250 albo ISO-8859-2, zależnie od tego, które daje więcej polskich liter |
| separator | `;` `,` tabulator `\|`: ten, przy którym najwięcej wierszy ma tę samą liczbę kolumn |
| wiersz nagłówka | wiersz z największą liczbą znanych nazw kolumn wśród pierwszych 50 (nad tabelą bywają metadane) |
| role kolumn | słownik nazw spotykanych w bankach, bez polskich znaków i wielkości liter; dokładna nazwa wygrywa z początkiem nazwy |
| sprawdzenie zawartości | kolumna „Data” bez dat nie jest datą; kwota musi mieć część dziesiętną, więc numer konta nie jest kwotą; „saldo”, „blokada” i „w walucie” nie są kwotą operacji |
| bez znanych nazw | data i kwota według zawartości, opis to kolumna z najdłuższymi tekstami |

**Odczyt według profilu** (`csv_generic.parse_csv`):
- Kolumny są wskazywane nazwą z nagłówka, a nie numerem, więc dodatkowy wiersz metadanych nie psuje profilu.
  Powtórzona nazwa dostaje numer: druga „Waluta” to „Waluta (2)”.
- Pomijane są wiersze bez daty (metadane, stopka) i bez kwoty (blokady kartowe); te drugie są liczone w podglądzie.
- Wiersz z datą, którego nie da się odczytać, zatrzymuje import z numerem wiersza. CSV nie ma sum kontrolnych,
  więc ciche pominięcie wiersza zostałoby niezauważone.
- Klucz duplikatów: numer operacji z banku, a bez niego data, kwota, waluta, opis i kontrahent z numerem kolejnym
  w pliku (dwie identyczne kawy tego samego dnia to dwie transakcje). Profil ING używa tego samego klucza co parser
  PDF, więc ta sama operacja z PDF i z CSV nie zostanie zapisana dwa razy.

**Profil ING** (`profiles/ing.json`) opisuje eksport historii z bankowości ING: Windows-1250, średnik, daty RRRR-MM-DD,
kolumny „Data transakcji”, „Dane kontrahenta”, „Tytuł”, „Szczegóły”, „Nr transakcji”, „Kwota transakcji (…)”.
Został przygotowany na podstawie opisu formatu i sztucznego pliku; **nie był jeszcze sprawdzony na prawdziwym
eksporcie**. Jeśli prawdziwy plik się różni, nie zostanie dopasowany do profilu i trafi do kreatora mapowania.
Sprawdzenie: `python -m scripts.check_statements` (dla plików CSV w `data/private/` porównuje kwoty i daty
z wyciągami PDF, wypisując wyłącznie liczby).

Testy: `tests/unit/test_csv_import.py`, `tests/integration/test_csv_imports.py` na plikach z `tests/fixtures/csv_samples.py`.

## Parser PDF z ING (`ing_pdf.py`)

- Słowa są składane ze znaków według współrzędnych, a nie przez `extract_words`: przy dolnej krawędzi strony znaki
  sąsiednich linii są zapisane w pliku naprzemiennie i biblioteka dzieliła wtedy daty i opisy na pojedyncze litery.
- Granice transakcji wyznaczają poziome linie tabeli; wiersz bez daty to dokończenie transakcji z poprzedniej strony.
- `validate_statement` porównuje liczbę i sumę uznań i obciążeń oraz saldo z nagłówkiem wyciągu.
- Testy: `tests/unit/test_ing_pdf.py` na sztucznym wyciągu z `tests/fixtures/ing_statement.py`.
- Prawdziwe wyciągi: `python -m scripts.check_statements` (wypisuje tylko liczby i zgodność, bez treści).

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
