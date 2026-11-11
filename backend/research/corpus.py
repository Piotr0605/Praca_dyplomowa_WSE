"""Korpus D4: sztuczne tytuły przelewów z oznaczonymi danymi osobowymi (badanie P3, docs/BADANIA.md, 3.4).

Szablony odwzorowują strukturę tytułów i nazw kontrahentów z wyciągów ING (płatność kartą, BLIK, przelew na
telefon, przelew od osoby z adresem, wolny tekst), ale wszystkie wartości są losowe. Stałe ziarno daje zawsze
ten sam korpus.

Dwie części: robocza (do rozwijania reguł anonimizacji) i testowa (do pomiaru). Pule imion, nazwisk, ulic
i miast są podzielone na dwie rozłączne połowy, więc dostrajanie reguł na części roboczej nie „uczy” ich
konkretnych osób z części testowej. Część testowa jest zapisana w repozytorium i zamrożona tagiem
`badanie-korpus` przed napisaniem anonimizatora.

Uruchomienie z katalogu backend/:
    .venv/bin/python -m research.corpus                     # zapisuje obie części w research/korpus/
    .venv/bin/python -m research.corpus --poza-slownikiem   # oraz zestaw kontrolny z imionami spoza słownika
"""

import json
import random
import sys
import unicodedata
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import ClassVar

CORPUS_DIR = Path(__file__).resolve().parent / "korpus"
SIZE = 1000
SEEDS = {"robocza": 20261111, "testowa": 20261112}
# Zestaw kontrolny: imiona spoza słownika anonimizatora (rzadkie polskie i obce). Powstał po napisaniu
# anonimizatora, więc to test obciążeniowy wykrywania z kontekstu, a nie ślepy pomiar.
OUTSIDE_SEED = 20261113
OUTSIDE_SIZE = 300
RARE_FIRST_NAMES = [
    "Bożydar", "Wieńczysław", "Gniewomir", "Jarogniew", "Przybysław", "Dobrosław", "Mścisław", "Ludomira",
    "Dobrosława", "Radosława", "Bogna", "Jagna", "Grzymisława", "Sobiesław", "Lubomir", "Kazimiera",
    "Leonarda", "Teodor", "Teodora", "Florian", "Hieronim", "Euzebiusz", "Kevin", "Jessica", "Brajan",
    "Dżesika", "Mohammed", "Ahmed", "Ngoc", "Giulia", "Pierre", "Hans", "Svetlana", "Aliaksandr",
    "Siarhei", "Zhanna", "Mehmet", "Fatima",
]  # fmt: skip

# Typy danych osobowych, które anonimizacja ma usunąć.
PII_TYPES = ("IBAN", "KARTA", "TELEFON", "EMAIL", "PESEL", "ADRES", "OSOBA")
# Fragmenty oznaczone, ale niebędące danymi osobowymi: ich zamaskowanie to błąd (nadmierne maskowanie).
NEGATIVE_TYPES = ("FIRMA", "NUMER")

# --- Pule wartości (połowa A: część robocza, połowa B: część testowa) -------------------------

FIRST_NAMES = {
    "A": [
        "Anna", "Katarzyna", "Małgorzata", "Agnieszka", "Barbara", "Ewa", "Krystyna", "Magdalena",
        "Joanna", "Aleksandra", "Monika", "Natalia", "Julia", "Karolina", "Paulina", "Weronika",
        "Piotr", "Krzysztof", "Andrzej", "Tomasz", "Paweł", "Michał", "Marcin", "Jakub", "Adam",
        "Łukasz", "Mateusz", "Bartosz", "Wojciech", "Kamil", "Grzegorz", "Dariusz", "Olena",
        "Oksana", "Iryna", "Dmytro", "Serhii", "Bożena", "Jadwiga", "Lech", "Bogumił", "Zdzisław",
    ],
    "B": [
        "Maria", "Elżbieta", "Zofia", "Teresa", "Danuta", "Dorota", "Beata", "Jolanta", "Iwona",
        "Marta", "Justyna", "Sylwia", "Patrycja", "Zuzanna", "Oliwia", "Wiktoria", "Jan", "Stanisław",
        "Marek", "Józef", "Rafał", "Robert", "Jacek", "Sebastian", "Szymon", "Filip", "Dawid",
        "Przemysław", "Hubert", "Radosław", "Mirosław", "Tetiana", "Nataliia", "Andrii", "Oleksandr",
        "Wiesława", "Gabriela", "Kornelia", "Ignacy", "Bronisław", "Wacław", "Eugeniusz",
    ],
}  # fmt: skip
# Zdrobnienia używane w nazwach kontaktów i tytułach przelewów na telefon.
DIMINUTIVES = {
    "A": ["Ania", "Kasia", "Gosia", "Aga", "Asia", "Ola", "Madzia", "Tomek", "Michał", "Kuba", "Bartek", "Wojtek", "Łukasz"],
    "B": ["Marysia", "Zosia", "Ela", "Dorotka", "Martusia", "Zuzia", "Janek", "Staś", "Marek", "Józek", "Szymek", "Filip", "Przemek"],
}  # fmt: skip
SURNAMES = {
    "A": [
        "Nowak", "Kowalski", "Wiśniewski", "Wójcik", "Kowalczyk", "Kamiński", "Lewandowski", "Zieliński",
        "Szymański", "Woźniak", "Dąbrowski", "Kozłowski", "Jankowski", "Mazur", "Kwiatkowski", "Krawczyk",
        "Piotrowski", "Grabowski", "Nowakowski", "Pawłowski", "Michalski", "Shevchenko", "Kovalenko",
        "Bondarenko", "Brzęczyszczykiewicz", "Gałązka",
    ],
    "B": [
        "Wróbel", "Adamczyk", "Dudek", "Zając", "Wieczorek", "Jabłoński", "Król", "Majewski", "Olszewski",
        "Jaworski", "Malinowski", "Pawlak", "Witkowski", "Walczak", "Stępień", "Górski", "Rutkowski",
        "Michalak", "Sikora", "Ostrowski", "Baran", "Tkachenko", "Melnyk", "Kravchenko", "Żółtowski",
        "Chrząszcz",
    ],
}  # fmt: skip
STREETS = {
    "A": ["Kwiatowa", "Lipowa", "Słoneczna", "Mickiewicza", "Długa", "Polna", "Leśna", "Ogrodowa", "Jana Pawła II", "Kościuszki", "3 Maja", "Fabryczna"],
    "B": ["Szkolna", "Krótka", "Brzozowa", "Sienkiewicza", "Zielona", "Łąkowa", "Słowackiego", "Piłsudskiego", "Wiejska", "Klonowa", "Armii Krajowej", "Kolejowa"],
}  # fmt: skip
CITIES = {
    "A": ["Warszawa", "Kraków", "Białystok", "Gdańsk", "Lublin", "Suwałki", "Łomża", "Radom"],
    "B": ["Wrocław", "Poznań", "Łódź", "Szczecin", "Katowice", "Rzeszów", "Olsztyn", "Kielce"],
}  # fmt: skip

# Firmy są wspólne: to nie dane osobowe, a ich zamaskowanie mierzy nadmierne maskowanie. Część nazw
# przypomina imiona albo nazwiska (trudne przypadki).
MERCHANTS = [
    "BIEDRONKA", "LIDL SP. Z O.O. SP.K.", "ZABKA Z1234", "ORLEN STACJA NR 123", "ROSSMANN", "CASTORAMA",
    "MCDONALDS", "KFC", "PEPCO", "HEBE", "APTEKA DR.MAX", "KWIACIARNIA ROZA", "PIEKARNIA JAN",
    "HOTEL MARIA", "STUDIO EWA", "SALON ANNA", "CUKIERNIA MARTA", "KAWIARNIA ZOFIA", "AUCHAN",
    "CARREFOUR EXPRESS", "STOKROTKA", "JMP S.A. BIEDRONKA 1234", "SPOTIFY", "NETFLIX.COM", "UBER *TRIP",
    "BOLT.EU", "ALLEGRO", "PAYPRO SA", "JAKDOJADE", "MAX PREMIUM BURGERS", "ZAKLAD FRYZJERSKI KAMIL",
]  # fmt: skip
COMPANIES = [
    "FIRMA TESTOWA SPÓŁKA Z O.O.", "PGE OBRÓT S.A.", "ORANGE POLSKA S.A.", "TAURON SPRZEDAŻ SP. Z O.O.",
    "WSPÓLNOTA MIESZKANIOWA", "ZAKŁAD UBEZPIECZEŃ SPOŁECZNYCH", "URZĄD SKARBOWY", "TECHSOFT SP. Z O.O.",
    "PRZEDSZKOLE NR 5", "SZKOŁA JĘZYKOWA LINGUA", "SPÓŁDZIELNIA MIESZKANIOWA PIAST", "KANCELARIA NOWAK I WSPÓLNICY",
]  # fmt: skip
DOMAINS = [
    "gmail.com",
    "wp.pl",
    "onet.pl",
    "interia.pl",
    "o2.pl",
    "poczta.fm",
    "outlook.com",
]
SHOPS = ["sklep.example", "allegro.pl", "zalando.pl", "empik.com", "mediaexpert.pl"]
MONTHS = ["styczeń", "luty", "marzec", "kwiecień", "maj", "czerwiec", "lipiec", "sierpień", "wrzesień", "październik", "listopad", "grudzień"]  # fmt: skip


@dataclass(frozen=True)
class Span:
    start: int
    end: int
    type: str


@dataclass(frozen=True)
class Item:
    id: str
    template: str
    text: str
    spans: list[Span]


class Builder:
    """Składa tekst z fragmentów i zapamiętuje położenie oznaczonych fragmentów."""

    def __init__(self) -> None:
        self.parts: list[str] = []
        self.spans: list[Span] = []
        self.length = 0

    def add(self, text: str, type_: str | None = None) -> "Builder":
        if type_ is not None:
            self.spans.append(Span(self.length, self.length + len(text), type_))
        self.parts.append(text)
        self.length += len(text)
        return self

    def text(self) -> str:
        return "".join(self.parts)


def ascii_lower(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text.replace("ł", "l").replace("Ł", "L"))
    return "".join(c for c in folded if not unicodedata.combining(c)).lower()


def female(surname: str) -> str:
    for male, fem in (("ski", "ska"), ("cki", "cka"), ("dzki", "dzka")):
        if surname.endswith(male):
            return surname[: -len(male)] + fem
    return surname


class Generator:
    def __init__(self, seed: int, half: str, rare_names: bool = False) -> None:
        self.r = random.Random(seed)
        self.half = half
        self.rare_names = rare_names

    def pick(self, pool: dict[str, list[str]]) -> str:
        if self.rare_names and pool in (FIRST_NAMES, DIMINUTIVES):
            return self.r.choice(RARE_FIRST_NAMES)
        return self.r.choice(pool[self.half])

    # --- wartości ---

    def date(self) -> str:
        return f"{self.r.randint(1, 28):02d}.{self.r.randint(1, 12):02d}.2026"

    def person(self) -> str:
        first = self.pick(FIRST_NAMES)
        surname = self.pick(SURNAMES)
        if first.endswith("a") and first not in {"Kuba", "Barnaba"}:
            surname = female(surname)
        if self.r.random() < 0.1:
            surname = f"{surname}-{female(self.pick(SURNAMES)) if first.endswith('a') else self.pick(SURNAMES)}"
        name = (
            self.r.choice([f"{first} {surname}", f"{surname} {first}"])
            if self.r.random() < 0.15
            else f"{first} {surname}"
        )
        style = self.r.random()
        if style < 0.55:
            return name.upper()
        if style < 0.95:
            return name
        return name.lower()

    def nrb(self) -> str:
        bank = f"{self.r.randint(1000, 1999)}{self.r.randint(0, 9999):04d}"
        account = "".join(str(self.r.randint(0, 9)) for _ in range(16))
        check = 98 - int(bank + account + "252100") % 97
        digits = f"{check:02d}{bank}{account}"
        style = self.r.random()
        if style < 0.6:
            return " ".join([digits[:2]] + [digits[i : i + 4] for i in range(2, 26, 4)])
        if style < 0.85:
            return digits
        return "PL" + digits

    def card(self) -> str:
        if self.r.random() < 0.8:  # tak jak w wyciągach ING: zamaskowany
            return f"{self.r.randint(4000, 5599)}xx{self.r.randint(0, 9999):04d}"
        digits = [self.r.randint(0, 9) for _ in range(15)]
        total = sum(
            (d * 2 - 9 if d * 2 > 9 else d * 2) if i % 2 == 0 else d
            for i, d in enumerate(reversed(digits))
        )
        number = "".join(map(str, digits)) + str((10 - total % 10) % 10)
        return " ".join(number[i : i + 4] for i in range(0, 16, 4))

    def phone(self) -> str:
        number = f"{self.r.choice([5, 6, 7, 8])}{self.r.randint(0, 99_999_999):08d}"
        style = self.r.random()
        if style < 0.4:  # przelew na telefon w ING
            return f"+48xxxxxx{number[-3:]}"
        if style < 0.6:
            return f"+48 {number[:3]} {number[3:6]} {number[6:]}"
        if style < 0.8:
            return number
        return f"{number[:3]}-{number[3:6]}-{number[6:]}"

    def email(self) -> str:
        first = ascii_lower(self.pick(FIRST_NAMES))
        surname = ascii_lower(self.pick(SURNAMES))
        local = self.r.choice(
            [
                f"{first}.{surname}",
                f"{first[0]}{surname}",
                f"{first}{self.r.randint(1, 99)}",
            ]
        )
        return f"{local}@{self.r.choice(DOMAINS)}"

    def pesel(self) -> str:
        year = self.r.randint(1950, 2005)
        month = self.r.randint(1, 12) + (20 if year >= 2000 else 0)
        digits = f"{year % 100:02d}{month:02d}{self.r.randint(1, 28):02d}{self.r.randint(0, 9999):04d}"
        weights = (1, 3, 7, 9, 1, 3, 7, 9, 1, 3)
        check = (
            10 - sum(int(d) * w for d, w in zip(digits, weights, strict=True)) % 10
        ) % 10
        return digits + str(check)

    def street(self) -> str:
        number = str(self.r.randint(1, 150))
        if self.r.random() < 0.4:
            number += f"/{self.r.randint(1, 60)}"
        prefix = self.r.choice(["ul. ", "ul. ", "UL. ", "al. ", "os. "])
        return f"{prefix}{self.pick(STREETS)} {number}"

    def postal(self) -> str:
        return f"{self.r.randint(0, 99):02d}-{self.r.randint(0, 999):03d} {self.pick(CITIES)}"

    def reference(self) -> str:
        return "".join(str(self.r.randint(0, 9)) for _ in range(11))

    # --- szablony ---

    def card_payment(self, b: Builder) -> None:
        b.add(f"Płatność kartą {self.date()} Nr karty ").add(self.card(), "KARTA").add(
            " | "
        )
        b.add(self.r.choice(MERCHANTS), "FIRMA").add(" " + self.pick(CITIES).upper())

    def blik_payment(self, b: Builder) -> None:
        b.add(f"Płatność BLIK {self.date()} Nr transakcji ").add(
            self.reference(), "NUMER"
        )
        b.add(f" {self.r.choice(SHOPS)} | ").add("PayU", "FIRMA").add(" ")
        b.add(self.street(), "ADRES").add(" ").add(self.postal(), "ADRES")

    def phone_transfer(self, b: Builder) -> None:
        b.add("Przelew na telefon ").add(self.phone(), "TELEFON").add(" Dla ")
        b.add(
            self.r.choice([self.pick(DIMINUTIVES), self.pick(FIRST_NAMES)]), "OSOBA"
        ).add(" Od ")
        b.add(self.person(), "OSOBA")
        if self.r.random() < 0.5:
            b.add(" | ").add(self.pick(DIMINUTIVES), "OSOBA")

    def person_transfer(self, b: Builder) -> None:
        title = self.r.choice(
            ["Za obiad", "Zwrot za bilety", f"Czynsz {self.r.choice(MONTHS)}", "Przelew środków",
             "Zrzutka na prezent", "Za zakupy", "Spłata pożyczki", "Kieszonkowe", "Za korepetycje"]
        )  # fmt: skip
        b.add(title + " | ")
        if self.r.random() < 0.7:
            b.add(self.nrb(), "IBAN").add(" ")
        b.add(self.person(), "OSOBA")
        if self.r.random() < 0.7:
            b.add(" ").add(self.street(), "ADRES")
            if self.r.random() < 0.6:
                b.add(" ").add(self.postal(), "ADRES")

    def free_title(self, b: Builder) -> None:
        kind = self.r.randrange(6)
        if kind == 0:
            b.add("Prezent dla ").add(
                self.r.choice([self.pick(DIMINUTIVES), self.pick(FIRST_NAMES)]), "OSOBA"
            )
        elif kind == 1:
            b.add("Składka na prezent dla ").add(self.person(), "OSOBA")
        elif kind == 2:
            b.add("Opłata za kurs, kontakt ").add(self.email(), "EMAIL")
        elif kind == 3:
            b.add("Ubezpieczenie OC PESEL ").add(self.pesel(), "PESEL")
        elif kind == 4:
            b.add("Zwrot kaucji, tel. ").add(self.phone(), "TELEFON")
        else:
            b.add("Za obiad ").add(self.pick(DIMINUTIVES).lower(), "OSOBA")

    def company_transfer(self, b: Builder) -> None:
        title = self.r.choice(
            [f"Wynagrodzenie {self.r.randint(1, 12):02d}/2026", f"Faktura FV/{self.r.randint(1, 999)}/2026",
             f"Opłata za {self.r.choice(MONTHS)}", "Składka zdrowotna", "Podatek PIT"]
        )  # fmt: skip
        b.add(title + " | ")
        if self.r.random() < 0.6:
            b.add(self.nrb(), "IBAN").add(" ")
        b.add(self.r.choice(COMPANIES), "FIRMA")
        if self.r.random() < 0.5:
            b.add(" ").add(self.street(), "ADRES").add(" ").add(self.postal(), "ADRES")

    def own_transfer(self, b: Builder) -> None:
        b.add(
            self.r.choice(
                ["przelew Smart Saver", "Przelew własny", "Wpłata na cel Wakacje"]
            )
        )
        b.add(" | ").add(self.person(), "OSOBA")

    def no_pii(self, b: Builder) -> None:
        b.add(self.r.choice(["Opłata za prowadzenie rachunku", "Prowizja za przewalutowanie",
                             f"Wypłata z bankomatu {self.date()}", "Kapitalizacja odsetek"]))  # fmt: skip
        if self.r.random() < 0.5:
            b.add(" | ").add(self.r.choice(MERCHANTS), "FIRMA")

    TEMPLATES: ClassVar[dict] = {
        "karta": (card_payment, 25),
        "blik": (blik_payment, 10),
        "telefon": (phone_transfer, 15),
        "przelew_osoba": (person_transfer, 20),
        "wolny_tekst": (free_title, 12),
        "przelew_firma": (company_transfer, 10),
        "wlasny": (own_transfer, 4),
        "bez_danych": (no_pii, 4),
    }

    def item(self, index: int, part: str) -> Item:
        names = list(self.TEMPLATES)
        if self.rare_names:
            names = ["telefon", "przelew_osoba", "wolny_tekst", "wlasny"]
        name = self.r.choices(names, weights=[self.TEMPLATES[n][1] for n in names])[0]
        b = Builder()
        self.TEMPLATES[name][0](self, b)
        return Item(f"{part}-{index:04d}", name, b.text(), b.spans)


def generate(part: str, size: int = SIZE) -> list[Item]:
    generator = Generator(SEEDS[part], "A" if part == "robocza" else "B")
    return [generator.item(i, part) for i in range(size)]


def generate_outside(size: int = OUTSIDE_SIZE) -> list[Item]:
    generator = Generator(OUTSIDE_SEED, "B", rare_names=True)
    return [generator.item(i, "poza_slownikiem") for i in range(size)]


def path(part: str) -> Path:
    return CORPUS_DIR / f"{part}.jsonl"


def load(part: str) -> list[Item]:
    items = []
    for line in path(part).read_text(encoding="utf-8").splitlines():
        data = json.loads(line)
        items.append(
            Item(
                data["id"],
                data["template"],
                data["text"],
                [Span(**s) for s in data["spans"]],
            )
        )
    return items


def save(part: str, items: list[Item]) -> Path:
    CORPUS_DIR.mkdir(exist_ok=True)
    target = path(part)
    target.write_text(
        "".join(json.dumps(asdict(i), ensure_ascii=False) + "\n" for i in items),
        encoding="utf-8",
    )
    return target


def main(argv: list[str]) -> int:
    for part in SEEDS:
        items = generate(part)
        counts: dict[str, int] = {}
        for item in items:
            for span in item.spans:
                counts[span.type] = counts.get(span.type, 0) + 1
        print(
            f"{save(part, items)}: {len(items)} tytułów, fragmenty: {dict(sorted(counts.items()))}"
        )
    if "--poza-slownikiem" in argv:
        print(f"{save('poza_slownikiem', generate_outside())}: {OUTSIDE_SIZE} tytułów")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
