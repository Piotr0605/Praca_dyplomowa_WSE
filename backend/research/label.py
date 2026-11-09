"""Ręczne etykietowanie transakcji (zbiór D2, docs/BADANIA.md, 3.3).

Uruchamia autor w swoim terminalu, z katalogu backend/:
    .venv/bin/python -m research.label

Transakcje są pogrupowane po kontrahencie, od największych grup. Dla każdej grupy wybierasz numer
kategorii albo dzielisz grupę i etykietujesz transakcje pojedynczo. Narzędzie celowo nie pokazuje,
co zaproponowałby system: etykiety mają być od niego niezależne. Przelewy własne (Smart Saver itp.)
rozpoznaje parser, więc nie wymagają etykiet. Postęp zapisuje się po każdej grupie w
data/private/etykiety.csv; po przerwaniu można wrócić do pracy.
"""

import sys
from collections import defaultdict
from collections.abc import Callable
from decimal import Decimal

from research.data import (
    SYSTEM_CATEGORIES,
    Item,
    group_key,
    is_own_transfer,
    load_labels,
    load_statements,
    save_labels,
)

HELP = (
    "numer = kategoria dla całej grupy · p = etykietuj pojedynczo · n = nowa kategoria · "
    "s = pomiń · w = wróć · q = zapisz i zakończ"
)


def groups_to_label(items: list[Item]) -> list[list[Item]]:
    """Grupy transakcji do etykietowania, od największych; bez przelewów własnych."""
    grouped: dict[str, list[Item]] = defaultdict(list)
    for item in items:
        if not is_own_transfer(item):
            grouped[group_key(item)].append(item)
    return sorted(grouped.values(), key=lambda g: (-len(g), group_key(g[0])))


def _show_categories(categories: list[str]) -> None:
    for number, name in enumerate(categories, start=1):
        print(f"  {number:2}. {name}")


def _describe(group: list[Item]) -> str:
    first = group[0].text
    total = sum((i.text.amount for i in group), Decimal(0))
    kinds = ", ".join(sorted({i.text.kind.value for i in group}))
    examples = list(dict.fromkeys(i.text.description[:70] for i in group))[:3]
    return (
        f"Kontrahent: {first.counterparty or '(brak)'}\n"
        f"Transakcji: {len(group)}, suma: {total} zł, rodzaje: {kinds}\n"
        f"Opisy (do 3 przykładów): {' | '.join(examples)}"
    )


def _choose(
    prompt: str, categories: list[str], ask: Callable[[str], str]
) -> str | None:
    """Zwraca nazwę kategorii albo polecenie (p, s, w, q)."""
    while True:
        answer = ask(prompt).strip().lower()
        if answer in {"p", "s", "w", "q"}:
            return answer
        if answer == "n":
            name = ask("Nazwa nowej kategorii: ").strip()
            if name:
                categories.append(name)
                print(f"Dodano kategorię {len(categories)}. {name}")
                return name
            continue
        if answer == "?":
            _show_categories(categories)
            continue
        if answer.isdigit() and 1 <= int(answer) <= len(categories):
            return categories[int(answer) - 1]
        print(HELP)


def run(
    items: list[Item],
    labels: dict[str, str],
    ask: Callable[[str], str] = input,
    save: Callable[[dict[str, str]], None] = save_labels,
) -> dict[str, str]:
    categories = list(dict.fromkeys([*SYSTEM_CATEGORIES, *labels.values()]))
    groups = groups_to_label(items)
    todo = [g for g in groups if any(i.key not in labels for i in g)]
    print(f"Grup do etykietowania: {len(todo)} z {len(groups)}. {HELP}")
    _show_categories(categories)
    index = 0
    while index < len(todo):
        group = todo[index]
        done = sum(1 for g in groups for i in g if i.key in labels)
        print(f"\n[{index + 1}/{len(todo)}] (etykiet: {done})\n{_describe(group)}")
        answer = _choose("Kategoria (? = lista): ", categories, ask)
        if answer == "q":
            break
        if answer == "w":
            index = max(0, index - 1)
            continue
        if answer == "s":
            index += 1
            continue
        if answer == "p":
            for item in group:
                print(f"  {item.text.description[:90]} | {item.text.amount} zł")
                single = _choose("  Kategoria: ", categories, ask)
                if single in {"q", "w", "p"}:
                    break
                if single != "s":
                    labels[item.key] = single
        else:
            for item in group:
                labels[item.key] = answer
        save(labels)
        index += 1
    save(labels)
    return labels


def main() -> int:
    items = load_statements()
    if not items:
        print("Brak wyciągów PDF w data/private/")
        return 1
    labels = run(items, load_labels())
    to_label = [i for i in items if not is_own_transfer(i)]
    print(
        f"\nZapisano. Etykiety: {sum(i.key in labels for i in to_label)} z {len(to_label)} "
        f"transakcji (przelewy własne: {len(items) - len(to_label)}, bez etykiet)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
