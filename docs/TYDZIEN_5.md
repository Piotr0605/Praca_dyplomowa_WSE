# Tydzień 5: kategoryzacja i uczenie się z poprawek

Plan przewiduje ten etap na 23–29 listopada 2026; wykonano go 9 listopada, na prośbę użytkownika w całości.

**Cel:** transakcje dostają kategorię automatycznie (słownik), a poprawka użytkownika zostaje zapamiętana jako
reguła, która działa przy kolejnych transakcjach od tego samego kontrahenta, także z następnego importu. Moduł jest
zbudowany tak, żeby badanie H2 z `BADANIA.md` mierzyło dokładnie to, co robi aplikacja.

---

## 1. Decyzje

| Temat | Decyzja | Uzasadnienie |
|---|---|---|
| Silnik | czysta funkcja `categorize` w `app/categorization/engine.py` | ta sama logika w aplikacji i w symulacji badania |
| Słownik | plik `system_rules.json` (199 wzorców, 13 kategorii), zamiast reguł systemowych w tabeli | wersja w git, testy, tag `badanie-slownik`; tak jak profile banków |
| Budowa słownika | wyłącznie ogólna wiedza o sieciach w Polsce, bez wglądu w dane autora | brak przecieku danych testowych do słownika (badanie H2) |
| Dopasowanie | całe słowa, bez wielkości liter i polskich znaków; dłuższy wzorzec przed krótszym | „bp” nie pasuje do „ABPX”, „uber eats” wygrywa z „uber” |
| Kolejność | przelew własny → reguły użytkownika (dokładny kontrahent przed fragmentem) → słownik → do przypisania | decyzja użytkownika ważniejsza od słownika |
| Reguła z poprawki | dokładna nazwa kontrahenta; bez kontrahenta reguła nie powstaje | sam opis („Płatność kartą 01.10”) przypisałby kategorię niepodobnym transakcjom |
| Kolejna poprawka | zmienia istniejącą regułę zamiast tworzyć drugą | ostatnia decyzja użytkownika obowiązuje |
| Zapis formularza bez zmiany kategorii | nie jest poprawką | inaczej każda edycja opisu tworzyłaby regułę |
| Przeliczanie wstecz | tylko kategorie nadane przez reguły; decyzje ręczne (także usunięcie kategorii) nietknięte | system nie może cofać wyborów użytkownika |
| Pole `categorized_by` | `system_rule`, `user_rule`, `manual` | statystyka skuteczności w realnym użyciu (H2) |
| Kategorie Twoich 1171 transakcji | nieprzypisane do czasu etykietowania | etykiety mają być niezależne od propozycji systemu |

## 2. Wykonane zadania
- [x] Silnik kategoryzacji i słownik; migracja `categorized_by`, `category_rule_id`
- [x] Kategoryzacja przy imporcie i przy ręcznym dodaniu bez kategorii
- [x] Reguła z poprawki, „zastosuj do podobnych”, przypisanie transakcjom bez kategorii
- [x] API: `POST /categorization/apply`, `GET /categorization/stats`, `GET/DELETE /rules`
- [x] Strona „Kategorie”: własne kategorie, zapamiętane reguły, kategorie systemowe
- [x] Transakcje: wybór kategorii w tabeli, pasek skuteczności, „Do przypisania”, źródło kategorii
- [x] Narzędzia badania: `research.label`, `research.simulate`; tag `badanie-slownik`
- [x] Backend przeładowuje się także po zmianie plików JSON (profile banków, słownik)
- [ ] Etykietowanie 632 transakcji przez autora (`python -m research.label`)

## 3. Definition of Done
- [x] Po poprawieniu kategorii jednej transakcji kolejne transakcje od tego kontrahenta, także z następnego importu, dostają tę kategorię
- [x] Testy przechodzą lokalnie i w CI; test w przeglądarce 20 z 20
- [x] Dziennik prac, plan i protokół badania są aktualne
