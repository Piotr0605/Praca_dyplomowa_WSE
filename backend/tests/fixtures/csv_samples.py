"""Sztuczne pliki CSV w formatach banków, na zmyślonych danych.

`make_ing_csv` odtwarza układ eksportu historii z ING: kodowanie Windows-1250, średnik, kilkanaście wierszy
metadanych nad tabelą, powtórzona kolumna „Waluta”, blokady kartowe bez kwoty transakcji i stopka.
`make_other_bank_csv` to inny bank: UTF-8, przecinek, osobne kolumny uznań i obciążeń, kropka dziesiętna.

Uruchomienie: `python -m tests.fixtures.csv_samples katalog/` zapisuje oba pliki do pokazu.
"""

import sys
from pathlib import Path

ING_HEADER = [
    "Data transakcji",
    "Data księgowania",
    "Dane kontrahenta",
    "Tytuł",
    "Nr rachunku",
    "Nazwa banku",
    "Szczegóły",
    "Nr transakcji",
    "Kwota transakcji (płatności, obciążenia, uznania)",
    "Waluta",
    "Kwota blokady/zwolnienie blokady",
    "Waluta",
    "Kwota płatności w walucie",
    "Waluta",
    "Konto",
    "Saldo po transakcji",
    "Waluta",
]

# (data, księgowanie, kontrahent, tytuł, szczegóły, numer, kwota, blokada)
ING_ROWS = [
    (
        "2026-10-01",
        "2026-10-02",
        "SKLEP TESTOWY WARSZAWA",
        "Płatność kartą 01.10.2026 Nr karty 1234xx5678",
        "TR.KART",
        "'202610020000000001'",
        "-45,99",
        "",
    ),
    (
        "2026-10-01",
        "2026-10-02",
        "JAN TESTOWY",
        "przelew Smart Saver",
        "",
        "'202610020000000002'",
        "-4,60",
        "",
    ),
    (
        "2026-10-02",
        "2026-10-02",
        "PayU ul. Testowa 2 Poznań",
        "Płatność BLIK 02.10.2026",
        "TR.BLIK",
        "'202610020000000003'",
        "-1 403,86",
        "",
    ),
    (
        "2026-10-05",
        "2026-10-05",
        "FIRMA PRZYKŁADOWA SP. Z O.O.",
        "Wynagrodzenie za wrzesień",
        "PRZELEW",
        "'202610050000000004'",
        "5 200,00",
        "",
    ),
    (
        "2026-10-06",
        "2026-10-06",
        "SKLEP TESTOWY WARSZAWA",
        "Zwrot płatności kartą 06.10.2026",
        "TR.KART",
        "'202610060000000005'",
        "19,99",
        "",
    ),
    (
        "2026-10-07",
        "2026-10-07",
        "BANKOMAT TESTOWY",
        "Wypłata gotówki BLIK 07.10.2026",
        "P.BLIK",
        "'202610070000000006'",
        "-200,00",
        "",
    ),
    (
        "2026-10-08",
        "",
        "KAWIARNIA ŻÓŁTA ŁÓDŹ",
        "Płatność kartą 08.10.2026",
        "TR.KART",
        "",
        "",
        "-12,50",
    ),
    (
        "2026-10-09",
        "2026-10-09",
        "",
        "Prowizja za przewalutowanie",
        "",
        "'202610090000000007'",
        "-0,37",
        "",
    ),
]


def make_ing_csv(rows: list[tuple[str, ...]] | None = None) -> bytes:
    rows = ING_ROWS if rows is None else rows
    lines = [
        '"Lista transakcji"',
        '"Dokument nr 0123456/2026"',
        '"Wygenerowany dnia:";"2026-10-31"',
        "",
        '"Dane Użytkownika:"',
        '"JAN TESTOWY"',
        '"UL. PRZYKŁADOWA 1, 00-001 WARSZAWA"',
        "",
        '"Wybrane rachunki:"',
        '"Konto Direct";"11 2222 3333 4444 5555 6666 7777";"PLN"',
        "",
        '"Zakres dat zleceń:";"2026-10-01";"2026-10-31"',
        '"Kwota:";"Wszystkie"',
        '"Rodzaj transakcji:";"Wszystkie"',
        "",
        "Rodzaj transakcji:;Wszystkie",
        "",
        ";".join(f'"{h}"' for h in ING_HEADER) + ";;",
    ]
    for date, booking, party, title, code, ref, amount, hold in rows:
        cells = [
            date, booking, party, title, "11 2222 3333 4444 5555 6666 7777", "ING Bank Śląski",
            code, ref, amount, "PLN" if amount else "", hold, "PLN" if hold else "", "", "",
            "Konto Direct", "1 000,00", "PLN",
        ]  # fmt: skip
        lines.append(";".join(cells) + ";;")
    lines += [
        "",
        '"Dokument ma charakter informacyjny, nie stanowi dowodu księgowego"',
        ';;;;;;;;"Saldo końcowe";"1 000,00";"PLN"',
    ]
    return ("\r\n".join(lines) + "\r\n").encode("cp1250")


OTHER_HEADER = ["Data operacji", "Opis", "Odbiorca/Nadawca", "Uznania", "Obciążenia", "Waluta"]  # fmt: skip
OTHER_ROWS = [
    ("03/10/2026", "Zakupy spożywcze", "Market Testowy", "", "123.45", "PLN"),
    ("03/10/2026", "Zakupy spożywcze", "Market Testowy", "", "123.45", "PLN"),
    ("15/10/2026", "Zwrot za bilety, część 1", "Jan Testowy", "1,250.00", "", "PLN"),
    ("20/10/2026", "Opłata za kartę", "", "", "7.00", "EUR"),
]


def make_other_bank_csv(rows: list[tuple[str, ...]] | None = None) -> bytes:
    rows = OTHER_ROWS if rows is None else rows

    def quote(cell: str) -> str:
        return f'"{cell}"' if "," in cell else cell

    lines = [",".join(OTHER_HEADER)]
    lines += [",".join(quote(cell) for cell in row) for row in rows]
    return ("\n".join(lines) + "\n").encode("utf-8-sig")


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    out.mkdir(parents=True, exist_ok=True)
    (out / "ing_przyklad.csv").write_bytes(make_ing_csv())
    (out / "inny_bank_przyklad.csv").write_bytes(make_other_bank_csv())
    print(f"Zapisano pliki CSV w {out}")
