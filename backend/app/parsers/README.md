# Import wyciągów bankowych

Dwa poziomy:

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
