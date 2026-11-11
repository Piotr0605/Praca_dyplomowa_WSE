"""Analityka wydatków i przychodów (Pandas).

Dane z bazy trafiają do `DataFrame` jednym zapytaniem (`load_frame`), a wszystkie obliczenia to czyste
funkcje na tej ramce: łatwo je testować na ręcznie policzonych przykładach.

Zasady liczenia:
- kwoty są w groszach jako liczby całkowite, więc sumy są dokładne (bez błędów liczb zmiennoprzecinkowych);
- przelewy własne (rodzaj `own_transfer` albo systemowa kategoria „Przelewy własne”) nie są ani
  wydatkiem, ani przychodem: to przesunięcie pieniędzy między kontami użytkownika;
- kategoria liczy się po saldzie: zwrot albo oddane pieniądze w kategorii wydatku pomniejszają wydatki
  w tej kategorii. Jeśli w okresie wpłynęło do niej więcej, niż wyszło (np. zwrot za zakup z poprzedniego
  miesiąca), nadwyżka jest wpływem. Dzięki temu żadna kategoria nie ma ujemnej kwoty na wykresie;
- transakcja bez kategorii jest wydatkiem, gdy kwota jest ujemna albo to zwrot, a w przeciwnym razie
  przychodem;
- dzięki temu przychody − wydatki = suma wszystkich kwot poza przelewami własnymi;
- liczymy tylko transakcje w PLN (wielowalutowość jest poza zakresem); pozostałe są zliczane osobno.
"""

import datetime as dt
from dataclasses import dataclass
from decimal import Decimal

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Category, Transaction
from app.models.enums import TransactionKind
from app.services.categorization_service import OWN_TRANSFER_CATEGORY

CURRENCY = "PLN"
UNCATEGORIZED = "Bez kategorii"
# Średnia do porównania: do 3 pełnych miesięcy przed wybranym.
AVERAGE_MONTHS = 3

COLUMNS = [
    "date",
    "amount",
    "kind",
    "category_id",
    "category",
    "color",
    "is_income",
    "is_own_category",
    "counterparty",
    "description",
]


def to_money(grosze: int) -> Decimal:
    """Grosze (także liczba całkowita z NumPy) na złote z dwoma miejscami po przecinku."""
    return Decimal(int(grosze)).scaleb(-2)


# --- Wczytanie danych -------------------------------------------------------------------------


@dataclass(frozen=True)
class Frame:
    data: pd.DataFrame
    # Transakcje w innej walucie niż PLN, pominięte w obliczeniach.
    other_currency: int


def frame_from_rows(rows: list[dict]) -> pd.DataFrame:
    """Ramka o stałych kolumnach także dla pustej listy; kwota w groszach jako int64."""
    df = pd.DataFrame(rows, columns=COLUMNS)
    df["date"] = pd.to_datetime(df["date"])
    df["amount"] = (
        df["amount"].map(lambda a: int(Decimal(a) * 100)).astype("int64")
        if len(df)
        else df["amount"].astype("int64")
    )
    df["category_id"] = df["category_id"].astype("Int64")
    df["category"] = df["category"].fillna(UNCATEGORIZED)
    df["is_income"] = df["is_income"].fillna(False).astype(bool)
    df["is_own_category"] = df["is_own_category"].fillna(False).astype(bool)
    return df


def load_frame(
    session: Session,
    user_id: int,
    date_from: dt.date | None = None,
    date_to: dt.date | None = None,
) -> Frame:
    query = (
        select(
            Transaction.date,
            Transaction.amount,
            Transaction.currency,
            Transaction.kind,
            Transaction.category_id,
            Transaction.counterparty,
            Transaction.description,
            Category.name,
            Category.color,
            Category.is_income,
            Category.user_id,
        )
        .outerjoin(Category, Category.id == Transaction.category_id)
        .where(Transaction.user_id == user_id)
    )
    if date_from is not None:
        query = query.where(Transaction.date >= date_from)
    if date_to is not None:
        query = query.where(Transaction.date <= date_to)

    rows, other_currency = [], 0
    for row in session.execute(query):
        if row.currency != CURRENCY:
            other_currency += 1
            continue
        rows.append(
            {
                "date": row.date,
                "amount": row.amount,
                "kind": row.kind.value,
                "category_id": row.category_id,
                "category": row.name,
                "color": row.color,
                "is_income": row.is_income,
                "is_own_category": row.name == OWN_TRANSFER_CATEGORY
                and row.category_id is not None
                and row.user_id is None,
                "counterparty": row.counterparty,
                "description": row.description,
            }
        )
    return Frame(frame_from_rows(rows), other_currency)


# --- Czyste funkcje ---------------------------------------------------------------------------


def classify(df: pd.DataFrame) -> pd.Series:
    """Strona przepływu każdej transakcji: `own`, `income` albo `expense`."""
    own = (df["kind"] == TransactionKind.OWN_TRANSFER.value) | df["is_own_category"]
    uncategorized = df["category_id"].isna()
    income = df["is_income"] | (
        uncategorized
        & (df["amount"] > 0)
        & (df["kind"] != TransactionKind.REFUND.value)
    )
    flow = pd.Series("expense", index=df.index, dtype="object")
    flow[income] = "income"
    flow[own] = "own"
    return flow


def category_totals(df: pd.DataFrame) -> pd.DataFrame:
    """Saldo każdej kategorii w okresie: kolumny category_id, category, color, side, amount, count.

    `side` to `expense` albo `income`, `amount` jest zawsze dodatnie (grosze). Kategoria o saldzie
    zerowym nie występuje. Kolejność: od największej kwoty."""
    result_columns = ["category_id", "category", "color", "side", "amount", "count"]
    flow = classify(df)
    base = df[flow != "own"].assign(flow=flow[flow != "own"])
    if base.empty:
        return pd.DataFrame(columns=result_columns)
    grouped = (
        base.groupby(["flow", "category_id", "category"], dropna=False)
        .agg(net=("amount", "sum"), count=("amount", "size"), color=("color", "first"))
        .reset_index()
    )
    grouped = grouped[grouped["net"] != 0]
    grouped["side"] = grouped["net"].map(lambda n: "income" if n > 0 else "expense")
    grouped["amount"] = grouped["net"].abs().astype("int64")
    # Brak koloru jako None, a nie NaN z Pandas.
    grouped["color"] = (
        grouped["color"].astype(object).where(grouped["color"].notna(), None)
    )
    return grouped.sort_values(
        ["amount", "category"], ascending=[False, True]
    ).reset_index(drop=True)[result_columns]


@dataclass(frozen=True)
class Totals:
    income: int
    expenses: int

    @property
    def balance(self) -> int:
        return self.income - self.expenses

    @property
    def savings_rate(self) -> float | None:
        """Część przychodów, która nie została wydana; brak przychodów to brak wskaźnika."""
        return round(self.balance / self.income, 4) if self.income > 0 else None


def totals(df: pd.DataFrame) -> Totals:
    by_category = category_totals(df)
    side = by_category.groupby("side")["amount"].sum()
    return Totals(int(side.get("income", 0)), int(side.get("expense", 0)))


@dataclass(frozen=True)
class Summary:
    totals: Totals
    # Dodatnie: tyle netto przelano na własne konta (np. oszczędnościowe).
    own_transfers_net: int
    transactions: int
    uncategorized: int
    days: int
    avg_daily_expense: int


def summary(df: pd.DataFrame, date_from: dt.date, date_to: dt.date) -> Summary:
    flow = classify(df)
    result = totals(df)
    days = (date_to - date_from).days + 1
    return Summary(
        totals=result,
        own_transfers_net=-int(df.loc[flow == "own", "amount"].sum()),
        transactions=int((flow != "own").sum()),
        uncategorized=int(((flow != "own") & df["category_id"].isna()).sum()),
        days=days,
        avg_daily_expense=round(result.expenses / days) if days > 0 else 0,
    )


@dataclass(frozen=True)
class Month:
    month: str  # RRRR-MM
    totals: Totals
    complete: bool


def month_complete(month: pd.Period, first_date: dt.date, today: dt.date) -> bool:
    """Miesiąc jest pełny, jeśli dane obejmują go od pierwszego dnia i już się skończył."""
    return month.start_time.date() >= first_date and month.end_time.date() < today


def monthly(
    df: pd.DataFrame, first_date: dt.date, today: dt.date, months: int
) -> list[Month]:
    """Ostatnie `months` miesięcy z danymi, także te bez transakcji pomiędzy nimi."""
    if df.empty:
        return []
    periods = df["date"].dt.to_period("M")
    full_range = pd.period_range(periods.min(), periods.max(), freq="M")[-months:]
    return [
        Month(
            month=str(period),
            totals=totals(df[periods == period]),
            complete=month_complete(period, first_date, today),
        )
        for period in full_range
    ]


@dataclass(frozen=True)
class CategoryChange:
    category_id: int | None
    category: str
    color: str | None
    current: int
    previous: int | None
    average: int | None

    @property
    def change_previous(self) -> float | None:
        return _change(self.current, self.previous)

    @property
    def change_average(self) -> float | None:
        return _change(self.current, self.average)


def _change(current: int, base: int | None) -> float | None:
    """Zmiana względna; przy bazie zero lub jej braku nie ma sensu, więc None."""
    if not base:
        return None
    return round((current - base) / base, 4)


def changes(
    df: pd.DataFrame, month: pd.Period, complete_months: set[pd.Period]
) -> list[CategoryChange]:
    """Wydatki w kategoriach w wybranym miesiącu na tle poprzedniego i średniej z do 3 pełnych
    miesięcy przed nim. Niepełne miesiące nie są punktem odniesienia: zaniżyłyby porównanie."""
    if df.empty:
        return []
    periods = df["date"].dt.to_period("M")

    def expenses(period: pd.Period) -> dict[tuple, tuple[int, str | None]]:
        rows = category_totals(df[periods == period])
        rows = rows[rows["side"] == "expense"]
        return {
            (optional_id(r.category_id), r.category): (int(r.amount), r.color)
            for r in rows.itertuples()
        }

    current = expenses(month)
    previous = expenses(month - 1) if month - 1 in complete_months else None
    history = [
        expenses(month - k)
        for k in range(1, AVERAGE_MONTHS + 1)
        if month - k in complete_months
    ]
    keys = set(current) | set(previous or {}) | {k for h in history for k in h}
    colors = {
        k: v[1]
        for source in [current, previous or {}, *history]
        for k, v in source.items()
    }

    result = [
        CategoryChange(
            category_id=key[0],
            category=key[1],
            color=colors.get(key),
            current=current.get(key, (0, None))[0],
            previous=(previous or {}).get(key, (0, None))[0]
            if previous is not None
            else None,
            average=(
                round(sum(h.get(key, (0, None))[0] for h in history) / len(history))
                if history
                else None
            ),
        )
        for key in keys
    ]
    return sorted(result, key=lambda c: (-c.current, -(c.average or 0), c.category))


def optional_id(value) -> int | None:
    return None if pd.isna(value) else int(value)


@dataclass(frozen=True)
class Counterparty:
    name: str
    amount: int
    count: int


def top_counterparties(df: pd.DataFrame, limit: int) -> list[Counterparty]:
    """Odbiorcy, którym zapłacono najwięcej (suma wydatków, bez zwrotów i przelewów własnych).
    Bez kontrahenta (np. transakcja dodana ręcznie) grupą jest opis."""
    spent = df[(classify(df) == "expense") & (df["amount"] < 0)]
    if spent.empty:
        return []
    grouped = (
        spent.assign(name=spent["counterparty"].fillna(spent["description"]))
        .groupby("name")
        .agg(amount=("amount", "sum"), count=("amount", "size"))
        .reset_index()
    )
    grouped["amount"] = -grouped["amount"]
    grouped = grouped.sort_values(["amount", "name"], ascending=[False, True]).head(
        limit
    )
    return [
        Counterparty(r.name, int(r.amount), int(r.count)) for r in grouped.itertuples()
    ]


@dataclass(frozen=True)
class Expense:
    date: dt.date
    amount: int
    counterparty: str | None
    description: str
    category: str


def largest_expenses(df: pd.DataFrame, limit: int) -> list[Expense]:
    spent = df[(classify(df) == "expense") & (df["amount"] < 0)]
    rows = spent.sort_values(["amount", "date"], ascending=[True, False]).head(limit)
    return [
        Expense(
            date=r.date.date(),
            amount=-int(r.amount),
            counterparty=None if pd.isna(r.counterparty) else r.counterparty,
            description=r.description,
            category=r.category,
        )
        for r in rows.itertuples()
    ]
