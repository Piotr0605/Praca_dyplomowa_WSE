# Parsery wyciągów bankowych

Każdy bank = jedna klasa dziedzicząca po `BaseBankParser` (`base.py`).
Parser zamienia surowy plik CSV na ujednolicony `DataFrame` o kolumnach:

| kolumna        | typ        | opis                                  |
|----------------|------------|---------------------------------------|
| `date`         | date       | data operacji                         |
| `amount`       | Decimal    | kwota (ujemna = wydatek)              |
| `currency`     | str        | np. `PLN`                             |
| `description`  | str        | opis/tytuł operacji                   |
| `counterparty` | str / None | odbiorca lub nadawca                  |

Dodanie nowego banku = nowy plik + wpis w rejestrze (`registry.py`). Reszta systemu się nie zmienia.
