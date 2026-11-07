# Tydzień 3: transakcje, kategorie i logowanie w przeglądarce

Plan przewiduje ten etap na 9–15 listopada 2026. Numery dni oznaczają kolejność pracy, a nie daty.

**Cel tygodnia:** użytkownik loguje się w przeglądarce, ręcznie dodaje wydatki i przychody, edytuje je, usuwa
i przegląda z filtrami. Każdy widzi wyłącznie własne dane.

Dlaczego teraz? Import wyciągów (etap 4) i kategoryzacja (etap 5) zapisują transakcje w tych samych tabelach i przez
te same repozytoria. Ręczne dodawanie to najprostszy sposób, żeby sprawdzić cały przepływ i izolację danych, zanim
dojdzie parser PDF.

---

## 1. API tego etapu

| Metoda i ścieżka | Wynik |
|---|---|
| `GET /api/categories` | kategorie systemowe i własne |
| `POST /api/categories` | 201; 409, gdy nazwa jest zajęta przez kategorię systemową lub własną |
| `PATCH`, `DELETE /api/categories/{id}` | tylko własne; kategoria systemowa: 403; cudza lub nieistniejąca: 404 |
| `GET /api/transactions` | lista z filtrami (daty, kategoria, brak kategorii, rodzaj, wyszukiwanie) i paginacją |
| `POST /api/transactions` | 201; transakcja ręczna (`source = manual`) |
| `GET`, `PATCH`, `DELETE /api/transactions/{id}` | tylko własne; cudza lub nieistniejąca: 404 |

**Zasada izolacji:** każda metoda repozytorium wymaga `user_id`, a cudzy zasób daje 404, a nie 403. Odpowiedź 403
zdradzałaby, że zasób o takim numerze istnieje.

---

## 2. Decyzje

| Temat | Decyzja | Uzasadnienie |
|---|---|---|
| Kategoria przypisana do transakcji | musi być systemowa albo użytkownika; inaczej 422 | baza tego nie wymusza (dziennik, tydzień 2, dzień 1) |
| Kategorie systemowe | tylko do odczytu | są wspólne dla wszystkich użytkowników |
| Nazwa własnej kategorii | nie może powtarzać nazwy systemowej ani własnej, bez względu na wielkość liter | dwie „Inne” na liście byłyby mylące |
| Edycja transakcji z importu | można zmienić tylko kategorię, rodzaj i opis; data, kwota i waluta: 409 | dane z banku są podstawą sum kontrolnych i deduplikacji |
| Kwoty w API | tekst, np. `"-12.50"` | liczba w JSON to `float` i mogłaby stracić dokładność |
| Token w przeglądarce | `sessionStorage` | przetrwa odświeżenie strony, znika po zamknięciu karty; `localStorage` trzymałby go dłużej, a sama pamięć wylogowywałaby przy każdym odświeżeniu |
| Biblioteki frontendu | `react-router`, `@tanstack/react-query` | zgodnie z decyzjami technicznymi planu |
| Strona zarządzania kategoriami | dopiero w etapie 5 | etap 3 wymaga jej tylko w API; w przeglądarce kategorie są wybierane z listy |

---

## 3. Kolejne dni

### Dzień 1: kategorie (backend)
- [x] `schemas/category.py`, `repositories/category_repository.py`, `api/routes/categories.py`
- [x] Walidacja nazwy, koloru (`#RRGGBB`) i ikony; kategorie systemowe tylko do odczytu
- [x] Testy

### Dzień 2: transakcje (backend)
- [x] `schemas/transaction.py`, `repositories/transaction_repository.py`, `services/transaction_service.py`, `api/routes/transactions.py`
- [x] Filtry, wyszukiwanie, paginacja, sortowanie od najnowszych
- [x] Sprawdzenie kategorii przy dodawaniu i edycji (odłożone z tygodnia 2)
- [x] Ograniczenia edycji transakcji z importu
- [x] Testy

### Dzień 3: izolacja danych
- [x] Testy: użytkownik B nie widzi, nie edytuje i nie usuwa danych A, nie przypisuje cudzej kategorii, nie widzi cudzych transakcji w liście ani w wyszukiwaniu
- [x] Celowe wprowadzenie błędów, żeby sprawdzić, czy testy je wykrywają

### Dzień 4: logowanie w przeglądarce
- [ ] `react-router`, `@tanstack/react-query`
- [ ] Klient API z tokenem i obsługą 401, `AuthContext`, strony logowania i rejestracji, chronione trasy

### Dzień 5: transakcje w przeglądarce
- [ ] Układ strony (menu boczne, górny pasek z kontem i wylogowaniem)
- [ ] Strona „Transakcje”: tabela, filtry, paginacja, formularz dodawania, edycja, usuwanie

### Dzień 6: sprawdzenie całości
- [ ] Przejście w przeglądarce: rejestracja, logowanie, dodanie, edycja, usunięcie, filtry, wylogowanie, odświeżenie strony
- [ ] Brak połączeń z zewnętrznymi serwerami

### Dzień 7: domknięcie
- [ ] Dziennik prac, plan, notatki o technologiach
- [ ] PR do `main` i tag

---

## 4. Definition of Done tygodnia 3
- [ ] Użytkownik loguje się w przeglądarce i ręcznie dodaje, edytuje i usuwa wydatki
- [ ] Testy izolacji: użytkownik B nie ma dostępu do danych A
- [ ] Kategoria transakcji jest zawsze systemowa albo użytkownika, a kategorii systemowych nie można zmienić
- [ ] Testy przechodzą lokalnie i w CI
- [ ] Dziennik prac, plan i notatki są aktualne
