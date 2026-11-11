"""Analityka na ręcznie policzonym przykładzie (app/services/analytics_service.py).

Przykład: wrzesień i październik pełne, listopad trwa (dziś 11.11.2026).

| data  | kwota    | rodzaj       | kategoria             | kontrahent |
|-------|----------|--------------|-----------------------|------------|
| 09-01 | +5000,00 | transfer     | Wynagrodzenie (przych)| FIRMA      |
| 09-03 |  -200,00 | card         | Zakupy spożywcze      | BIEDRONKA  |
| 09-05 | -1000,00 | own_transfer | Przelewy własne       | —          |
| 09-10 |  -100,00 | card         | Restauracje           | PIZZA      |
| 09-12 |   +30,00 | refund       | Restauracje           | PIZZA      |
| 09-20 |   -50,00 | card         | —                     | KIOSK      |
| 10-01 | +5000,00 | transfer     | Wynagrodzenie         | FIRMA      |
| 10-02 |  -300,00 | card         | Zakupy spożywcze      | BIEDRONKA  |
| 10-15 |  +200,00 | own_transfer | Przelewy własne       | —          |
| 10-20 |   +80,00 | blik         | —                     | JAN        |
| 10-21 |   -40,00 | blik         | Inne                  | ANNA       |
| 10-22 |  +100,00 | blik         | Inne                  | ANNA       |
| 11-02 |  -150,00 | card         | Zakupy spożywcze      | BIEDRONKA  |

Wrzesień: przychody 5000; wydatki 200 + (100 − 30) + 50 = 320; saldo 4680; przelano na własne 1000.
Październik: przychody 5000 + 80 (bez kategorii, wpływ) + 60 (Inne po saldzie: 100 − 40) = 5140;
wydatki 300; saldo 4840; z własnych kont wróciło 200.
Całość: przychody 10 140, wydatki 770, saldo 9370 = suma kwot poza przelewami własnymi.
"""

import datetime as dt

import pandas as pd
import pytest

from app.services import analytics_service as a

FIRMA = (16, "Wynagrodzenie", "#006300", True, False)
SPOZ = (2, "Zakupy spożywcze", "#1baf7a", False, False)
REST = (3, "Restauracje", "#e34948", False, False)
WLASNE = (14, "Przelewy własne", "#898781", False, True)
INNE = (15, "Inne", "#b4b2a9", False, False)
BRAK = (None, None, None, None, None)

DZIS = dt.date(2026, 11, 11)


def wiersz(data, kwota, rodzaj, kategoria, kontrahent):
    cid, nazwa, kolor, przychod, wlasna = kategoria
    return {
        "date": dt.date.fromisoformat(f"2026-{data}"),
        "amount": kwota,
        "kind": rodzaj,
        "category_id": cid,
        "category": nazwa,
        "color": kolor,
        "is_income": przychod,
        "is_own_category": wlasna,
        "counterparty": kontrahent,
        "description": f"opis {data}",
    }


WIERSZE = [
    wiersz("09-01", "5000.00", "transfer", FIRMA, "FIRMA"),
    wiersz("09-03", "-200.00", "card", SPOZ, "BIEDRONKA"),
    wiersz("09-05", "-1000.00", "own_transfer", WLASNE, None),
    wiersz("09-10", "-100.00", "card", REST, "PIZZA"),
    wiersz("09-12", "30.00", "refund", REST, "PIZZA"),
    wiersz("09-20", "-50.00", "card", BRAK, "KIOSK"),
    wiersz("10-01", "5000.00", "transfer", FIRMA, "FIRMA"),
    wiersz("10-02", "-300.00", "card", SPOZ, "BIEDRONKA"),
    wiersz("10-15", "200.00", "own_transfer", WLASNE, None),
    wiersz("10-20", "80.00", "blik", BRAK, "JAN"),
    wiersz("10-21", "-40.00", "blik", INNE, "ANNA"),
    wiersz("10-22", "100.00", "blik", INNE, "ANNA"),
    wiersz("11-02", "-150.00", "card", SPOZ, "BIEDRONKA"),
]


@pytest.fixture
def df() -> pd.DataFrame:
    return a.frame_from_rows(WIERSZE)


def miesiac(df: pd.DataFrame, okres: str) -> pd.DataFrame:
    return df[df["date"].dt.to_period("M") == pd.Period(okres, "M")]


def test_kwoty_w_groszach(df: pd.DataFrame) -> None:
    assert df["amount"].dtype == "int64"
    # Wszystkie kwoty razem z przelewami własnymi: 9370 − 1000 + 200.
    assert df["amount"].sum() == 857_000
    assert str(a.to_money(-5)) == "-0.05"
    assert (
        str(a.to_money(df["amount"].iloc[0])) == "5000.00"
    )  # liczba całkowita z NumPy


def test_przelewy_wlasne_poza_przychodami_i_wydatkami(df: pd.DataFrame) -> None:
    flow = a.classify(df)
    assert list(flow[df["kind"] == "own_transfer"]) == ["own", "own"]
    t = a.totals(df)
    assert (t.income, t.expenses, t.balance) == (1_014_000, 77_000, 937_000)
    # Saldo to suma kwot poza przelewami własnymi.
    assert t.balance == df.loc[flow != "own", "amount"].sum()


def test_kategoria_przelewow_wlasnych_bez_rodzaju_own_transfer() -> None:
    """Np. wypłata z bankomatu oznaczona ręcznie jako przelew własny."""
    df = a.frame_from_rows([wiersz("09-01", "-70.00", "cash", WLASNE, None)])
    assert a.totals(df) == a.Totals(0, 0)


def test_wrzesien(df: pd.DataFrame) -> None:
    s = a.summary(miesiac(df, "2026-09"), dt.date(2026, 9, 1), dt.date(2026, 9, 30))
    assert (s.totals.income, s.totals.expenses, s.totals.balance) == (
        500_000,
        32_000,
        468_000,
    )
    assert s.totals.savings_rate == 0.936
    assert s.own_transfers_net == 100_000
    assert (s.transactions, s.uncategorized, s.days) == (5, 1, 30)
    assert s.avg_daily_expense == round(32_000 / 30)


def test_zwrot_pomniejsza_wydatki_w_kategorii(df: pd.DataFrame) -> None:
    rows = a.category_totals(miesiac(df, "2026-09"))
    rest = rows[rows["category"] == "Restauracje"].iloc[0]
    assert (rest["side"], rest["amount"], rest["count"]) == ("expense", 7_000, 2)


def test_nadwyzka_wplywow_w_kategorii_wydatku_jest_wplywem(df: pd.DataFrame) -> None:
    rows = a.category_totals(miesiac(df, "2026-10"))
    inne = rows[rows["category"] == "Inne"].iloc[0]
    assert (inne["side"], inne["amount"]) == ("income", 6_000)
    s = a.summary(miesiac(df, "2026-10"), dt.date(2026, 10, 1), dt.date(2026, 10, 31))
    assert (s.totals.income, s.totals.expenses) == (514_000, 30_000)
    assert s.own_transfers_net == -20_000


def test_bez_kategorii_wedlug_znaku_a_zwrot_to_wydatek() -> None:
    df = a.frame_from_rows(
        [
            wiersz("09-01", "-50.00", "card", BRAK, "KIOSK"),
            wiersz("09-02", "20.00", "refund", BRAK, "KIOSK"),
            wiersz("09-03", "80.00", "blik", BRAK, "JAN"),
        ]
    )
    rows = a.category_totals(df)
    assert sorted(zip(rows["side"], rows["category"], rows["amount"], strict=True)) == [
        ("expense", a.UNCATEGORIZED, 3_000),
        ("income", a.UNCATEGORIZED, 8_000),
    ]


def test_kolejnosc_kategorii_od_najwiekszej(df: pd.DataFrame) -> None:
    rows = a.category_totals(df)
    wydatki = rows[rows["side"] == "expense"]
    assert list(wydatki["category"]) == [
        "Zakupy spożywcze",
        "Restauracje",
        a.UNCATEGORIZED,
    ]
    assert list(wydatki["amount"]) == [65_000, 7_000, 5_000]
    assert list(wydatki["color"]) == ["#1baf7a", "#e34948", None]


def test_trend_miesieczny(df: pd.DataFrame) -> None:
    months = a.monthly(df, dt.date(2026, 9, 1), DZIS, 12)
    assert [
        (m.month, m.totals.income, m.totals.expenses, m.complete) for m in months
    ] == [
        ("2026-09", 500_000, 32_000, True),
        ("2026-10", 514_000, 30_000, True),
        ("2026-11", 0, 15_000, False),
    ]
    assert [m.month for m in a.monthly(df, dt.date(2026, 9, 1), DZIS, 2)] == [
        "2026-10",
        "2026-11",
    ]


def test_miesiac_bez_transakcji_jest_w_trendzie() -> None:
    df = a.frame_from_rows(
        [
            wiersz("07-01", "-10.00", "card", SPOZ, "X"),
            wiersz("09-01", "-20.00", "card", SPOZ, "X"),
        ]
    )
    months = a.monthly(df, dt.date(2026, 7, 1), DZIS, 12)
    assert [(m.month, m.totals.expenses) for m in months] == [
        ("2026-07", 1_000),
        ("2026-08", 0),
        ("2026-09", 2_000),
    ]


@pytest.mark.parametrize(
    ("okres", "pierwszy", "pelny"),
    [
        ("2026-04", dt.date(2026, 4, 23), False),  # dane od połowy miesiąca
        ("2026-04", dt.date(2026, 4, 1), True),
        ("2026-05", dt.date(2026, 4, 23), True),
        ("2026-10", dt.date(2026, 4, 23), True),  # skończył się 31.10
        ("2026-11", dt.date(2026, 4, 23), False),  # trwa
    ],
)
def test_pelny_miesiac(okres: str, pierwszy: dt.date, pelny: bool) -> None:
    assert a.month_complete(pd.Period(okres, "M"), pierwszy, DZIS) is pelny


def test_zmiany_wzgledem_poprzedniego_i_sredniej(df: pd.DataFrame) -> None:
    pelne = {pd.Period("2026-09", "M"), pd.Period("2026-10", "M")}
    zmiany = {c.category: c for c in a.changes(df, pd.Period("2026-11", "M"), pelne)}

    spoz = zmiany["Zakupy spożywcze"]
    # 150 wobec 300 w październiku i średniej (200 + 300) / 2 = 250.
    assert (spoz.current, spoz.previous, spoz.average) == (15_000, 30_000, 25_000)
    assert (spoz.change_previous, spoz.change_average) == (-0.5, -0.4)

    rest = zmiany["Restauracje"]
    # W listopadzie i październiku 0, we wrześniu 70 → średnia 35; przy zerowej bazie brak zmiany.
    assert (rest.current, rest.previous, rest.average) == (0, 0, 3_500)
    assert (rest.change_previous, rest.change_average) == (None, -1.0)

    assert zmiany[a.UNCATEGORIZED].average == 2_500  # (50 + 0) / 2
    assert "Inne" not in zmiany  # w październiku po stronie wpływów
    assert list(zmiany) == ["Zakupy spożywcze", "Restauracje", a.UNCATEGORIZED]


def test_zmiany_bez_pelnych_miesiecy_przed() -> None:
    df = a.frame_from_rows([wiersz("10-02", "-300.00", "card", SPOZ, "BIEDRONKA")])
    (spoz,) = a.changes(df, pd.Period("2026-10", "M"), set())
    assert (spoz.previous, spoz.average, spoz.change_previous) == (None, None, None)


def test_zmiany_srednia_tylko_z_pelnych_miesiecy(df: pd.DataFrame) -> None:
    """Wrzesień niepełny: średnia i poprzedni miesiąc dla października go pomijają."""
    (spoz, *_) = a.changes(df, pd.Period("2026-10", "M"), set())
    assert (spoz.current, spoz.previous, spoz.average) == (30_000, None, None)
    zmiany = a.changes(df, pd.Period("2026-10", "M"), {pd.Period("2026-09", "M")})
    spoz = next(c for c in zmiany if c.category == "Zakupy spożywcze")
    assert (spoz.previous, spoz.average, spoz.change_previous) == (20_000, 20_000, 0.5)


def test_najwieksi_odbiorcy(df: pd.DataFrame) -> None:
    top = a.top_counterparties(df, 10)
    # Zwrot od PIZZA i przelewy własne się nie liczą; wpływy od ANNA też nie.
    assert [(c.name, c.amount, c.count) for c in top] == [
        ("BIEDRONKA", 65_000, 3),
        ("PIZZA", 10_000, 1),
        ("KIOSK", 5_000, 1),
        ("ANNA", 4_000, 1),
    ]
    assert len(a.top_counterparties(df, 2)) == 2


def test_odbiorca_bez_kontrahenta_to_opis() -> None:
    df = a.frame_from_rows(
        [
            wiersz("09-03", "-20.00", "card", SPOZ, None)
            | {"description": "Biedronka"},
            wiersz("09-04", "-30.00", "card", SPOZ, None)
            | {"description": "Biedronka"},
        ]
    )
    assert [(c.name, c.amount, c.count) for c in a.top_counterparties(df, 5)] == [
        ("Biedronka", 5_000, 2)
    ]


def test_najwieksze_wydatki(df: pd.DataFrame) -> None:
    largest = a.largest_expenses(df, 2)
    assert [(e.date.isoformat(), e.amount, e.category) for e in largest] == [
        ("2026-10-02", 30_000, "Zakupy spożywcze"),
        ("2026-09-03", 20_000, "Zakupy spożywcze"),
    ]
    assert largest[0].counterparty == "BIEDRONKA"


def test_bez_przychodow_brak_stopy_oszczednosci() -> None:
    df = a.frame_from_rows([wiersz("09-03", "-200.00", "card", SPOZ, "X")])
    assert a.totals(df).savings_rate is None


def test_pusta_ramka() -> None:
    df = a.frame_from_rows([])
    s = a.summary(df, dt.date(2026, 9, 1), dt.date(2026, 9, 30))
    assert (s.totals.income, s.totals.expenses, s.transactions) == (0, 0, 0)
    assert a.category_totals(df).empty
    assert a.monthly(df, DZIS, DZIS, 12) == []
    assert a.changes(df, pd.Period("2026-11", "M"), set()) == []
    assert a.top_counterparties(df, 5) == []
    assert a.largest_expenses(df, 5) == []
