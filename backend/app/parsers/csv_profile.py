"""Profil pliku CSV z banku: jak odczytać plik i co oznaczają jego kolumny.

Ten sam model opisuje profile wbudowane (`profiles/*.json`) i profile zapisane przez użytkownika
w kreatorze mapowania (tabela `bank_profiles`). Kolumny są wskazywane nazwą z wiersza nagłówka,
więc zmiana liczby wierszy metadanych nad tabelą nie psuje profilu.
"""

from functools import cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

PROFILES_DIR = Path(__file__).parent / "profiles"

Encoding = Literal["utf-8-sig", "cp1250", "iso-8859-2"]
Delimiter = Literal[";", ",", "\t", "|"]
DateFormat = Literal[
    "%Y-%m-%d", "%d.%m.%Y", "%d-%m-%Y", "%d/%m/%Y", "%Y.%m.%d", "%Y/%m/%d", "%m/%d/%Y"
]
ENCODINGS: tuple[Encoding, ...] = ("utf-8-sig", "cp1250", "iso-8859-2")
DELIMITERS: tuple[Delimiter, ...] = (";", ",", "\t", "|")
# Kolejność ma znaczenie przy niejednoznacznych datach: 03/04/2026 to w Polsce 3 kwietnia.
DATE_FORMATS: tuple[DateFormat, ...] = (
    "%Y-%m-%d",
    "%d.%m.%Y",
    "%d-%m-%Y",
    "%d/%m/%Y",
    "%Y.%m.%d",
    "%Y/%m/%d",
    "%m/%d/%Y",
)

ColumnName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
]


class ColumnMapping(BaseModel):
    """Nazwy kolumn z wiersza nagłówka. Powtórzona nazwa ma dopisany numer, np. „Waluta (2)”."""

    model_config = ConfigDict(extra="forbid")

    date: ColumnName
    booking_date: ColumnName | None = None
    # Kwota ze znakiem albo dwie kolumny: uznania i obciążenia.
    amount: ColumnName | None = None
    credit: ColumnName | None = None
    debit: ColumnName | None = None
    currency: ColumnName | None = None
    description: list[ColumnName] = Field(min_length=1, max_length=3)
    counterparty: ColumnName | None = None
    # Kolumna z rodzajem operacji, np. „TR.KART” albo „Płatność kartą”.
    kind: ColumnName | None = None
    # Numer operacji nadany przez bank: najpewniejszy klucz wykrywania duplikatów.
    reference: ColumnName | None = None

    @model_validator(mode="after")
    def _amount_columns(self) -> "ColumnMapping":
        split = self.credit is not None or self.debit is not None
        if self.amount is not None and split:
            raise ValueError(
                "Wskaż kolumnę kwoty albo kolumny uznań i obciążeń, nie oba naraz"
            )
        if self.amount is None and (self.credit is None or self.debit is None):
            raise ValueError(
                "Wskaż kolumnę kwoty albo obie kolumny: uznania i obciążenia"
            )
        return self

    def names(self) -> list[str]:
        """Wszystkie wskazane kolumny: muszą wystąpić w wierszu nagłówka pliku."""
        single = [
            self.date,
            self.booking_date,
            self.amount,
            self.credit,
            self.debit,
            self.currency,
            self.counterparty,
            self.kind,
            self.reference,
        ]
        return list(
            dict.fromkeys([n for n in single if n is not None] + self.description)
        )


class CsvProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bank_name: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
    ]
    encoding: Encoding
    delimiter: Delimiter
    date_format: DateFormat
    decimal_separator: Literal[",", "."]
    default_currency: str = Field("PLN", pattern=r"^[A-Z]{3}$")
    # Przedrostek klucza duplikatów z numeru operacji. Profil ING używa „ING”, tak jak parser PDF,
    # więc ta sama operacja z PDF i z CSV jest rozpoznawana jako duplikat.
    reference_namespace: str | None = Field(None, pattern=r"^[A-Za-z0-9_-]{1,20}$")
    columns: ColumnMapping


@cache
def builtin_profiles() -> dict[str, CsvProfile]:
    """Profile dostarczone z aplikacją; klucz to nazwa pliku bez rozszerzenia."""
    return {
        path.stem: CsvProfile.model_validate_json(path.read_text(encoding="utf-8"))
        for path in sorted(PROFILES_DIR.glob("*.json"))
    }
