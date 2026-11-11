# Badanie aplikacyjne: protokół

Praca ma charakter aplikacyjny: obok zbudowanego systemu zawiera badanie z hipotezami, metodą, wynikami i dyskusją.
Ten dokument ustala hipotezy i metodę **przed** pomiarem. Historia repozytorium pokazuje, że protokół powstał
wcześniej niż wyniki. Zmiana protokołu po rozpoczęciu pomiarów jest dopuszczalna tylko z wpisem w sekcji 7
(co, kiedy i dlaczego).

Stan: wersja z 8.11.2026 przyjęta przez autora. Konsultacja z promotorem nie jest na razie możliwa; jeśli dojdzie
do skutku przed pomiarem, ewentualne zmiany trafią do sekcji 7.

---

## 1. Problem i pytania badawcze

System ma automatycznie porządkować wydatki z wyciągów bankowych i dawać porady oparte na modelu językowym,
nie wysyłając poza komputer danych osobowych. Z tego wynikają cztery pytania:

| | Pytanie | Moduł |
|---|---|---|
| P1 | Czy import odtwarza transakcje z wyciągu bez strat i przekłamań? | import (etap 4) |
| P2 | Czy zapamiętywanie poprawek użytkownika zwiększa trafność automatycznej kategoryzacji i zmniejsza nakład ręcznej pracy? | kategoryzacja (etap 5) |
| P3 | Czy anonimizacja usuwa dane osobowe z tekstów, które mogłyby trafić do modelu językowego? | anonimizacja (etap 7) |
| P4 | Czy porady wygenerowane wyłącznie z zanonimizowanych agregatów są zgodne z danymi i przydatne, oraz ile kosztują? | moduł AI (etapy 7–8) |

P2 jest badaniem głównym: dotyczy własnego rozwiązania pracy (uczenie się z poprawek), ma wariant porównawczy
i daje się sprawdzić testem statystycznym. P1, P3 i P4 weryfikują założenia bezpieczeństwa i jakości.

## 2. Hipotezy

Progi ustalono przed pomiarem.

| | Hipoteza | Kryterium przyjęcia |
|---|---|---|
| H1 | Import odtwarza wszystkie transakcje wyciągu. | 100% wyciągów zgodnych z sumami kontrolnymi banku (liczba i suma uznań i obciążeń, saldo); 0 duplikatów przy ponownym imporcie |
| H2a | Kategoryzacja z regułami z poprawek (wariant B) jest trafniejsza niż sama kategoryzacja słownikowa (wariant A). | B > A na miesiącach testowych, test McNemara, p < 0,05 |
| H2b | Nakład pracy użytkownika maleje z czasem. | liczba poprawek na 100 transakcji w miesiącu 6 co najmniej o połowę mniejsza niż w miesiącu 2 |
| H2c | Kategoryzacja jest użyteczna w praktyce. | trafność wariantu B na miesiącach testowych ≥ 85% |
| H3 | Anonimizacja usuwa dane osobowe z tytułów i nazw kontrahentów. | czułość ≥ 99% dla danych o stałym formacie (IBAN, karta, telefon, e-mail, PESEL) i ≥ 90% dla imion i nazwisk; precyzja ≥ 90%; 0 danych osobowych w danych wysyłanych do modelu |
| H4a | Porady nie zawierają liczb niezgodnych z wysłanymi agregatami. | ≤ 5% liczb w poradach bez pokrycia w danych wejściowych |
| H4b | Porady są przydatne. | średnia ocena ≥ 4 w skali 1–5 w kryteriach z sekcji 3.4 |
| H4c | Koszt i czas są akceptowalne dla użytku osobistego. | koszt porady < 0,10 zł; mediana czasu odpowiedzi < 20 s |

Porównanie dwóch dostawców (OpenAI i Anthropic) nie ma hipotezy kierunkowej: hipoteza zerowa mówi o braku
różnicy w ocenach (test Wilcoxona dla par, p < 0,05).

## 3. Metoda

### 3.1. Dane

| Zbiór | Zawartość | Gdzie jest | Do czego |
|---|---|---|---|
| D1 | 6 miesięcznych wyciągów PDF autora z ING (1113 transakcji) | `data/private/`, poza repozytorium | P1, P2, P4 |
| D2 | etykiety kategorii dla D1 nadane ręcznie przez autora | `data/private/`, poza repozytorium | P2 |
| D3 | sztuczne wyciągi i pliki CSV generowane w testach | `backend/tests/fixtures/` | P1 |
| D4 | sztuczny korpus tytułów przelewów z oznaczonymi danymi osobowymi, podzielony na część roboczą i testową | repozytorium | P3 |
| D5 | sztuczne profile finansowe (kilka „osób” z 6 miesiącami transakcji) | repozytorium | P4 |

Dane z D1 i D2 nie opuszczają komputera. Skrypty badawcze wypisują i zapisują wyłącznie wyniki zbiorcze.
W pracy pojawiają się tylko liczby zbiorcze, bez opisów transakcji.

### 3.2. P1: import

- Wszystkie wyciągi z D1 przez parser PDF: zgodność z sumami kontrolnymi, unikalność numerów operacji, ponowny import.
- Te same dane przez importer CSV (zamiana w pamięci) i, jeśli będzie dostępny, prawdziwy eksport CSV z ING.
- Detektor formatu CSV na plikach z D3: ile ról kolumn rozpoznał poprawnie bez udziału użytkownika.
- Część wyników już jest (sekcja 5): pomiar powtarza się na wersji końcowej.

### 3.3. P2: kategoryzacja (badanie główne)

**Etykiety (D2).** Autor przypisuje kategorię każdej transakcji z D1 w osobnym narzędziu, a nie przez kategoryzację
systemu. Narzędzie grupuje transakcje po kontrahencie, a pojedyncze wyjątki można poprawić. Etykiety powstają
przed uruchomieniem pomiaru.

**Słownik i podział.** Słownik reguł systemowych zbudowano z ogólnej wiedzy o popularnych sieciach handlowych
i usługach w Polsce, bez wglądu w dane autora, i zamrożono tagiem `badanie-slownik` przed etykietowaniem. Nie jest
strojony na żadnej części D1, więc nie ma ryzyka, że „zna” dane testowe. Miesiące 1–3 służą wariantowi B do nauki
z poprawek, a miesiące 4–6 są częścią testową do porównania wariantów (H2a, H2c).

**Przelewy własne** (Smart Saver, przelew własny, wpłata na cel) rozpoznaje parser, a nie kategoryzacja, więc nie
wymagają etykiet i nie wchodzą do miar. W D1 jest ich 481, do etykietowania zostaje 632 transakcji.

**Narzędzia** (`backend/research/`, uruchamiane z katalogu `backend/`):
- `python -m research.label`: etykietowanie w terminalu, grupy po kontrahencie od największych, bez podpowiedzi
  systemu; postęp zapisywany po każdej grupie w `data/private/etykiety.csv`, można przerwać i wrócić;
- `python -m research.simulate [--zapisz]`: symulacja wariantów A i B na tym samym silniku co aplikacja
  (`app/categorization/engine.py`), wyniki zbiorcze, z `--zapisz` także w `docs/badania/h2_kategoryzacja.json`.

**Symulacja.** Skrypt odtwarza 6 miesięcy w kolejności dat:
- wariant A: tylko reguły systemowe;
- wariant B: reguły systemowe i reguły użytkownika. Każda błędna kategoria jest „poprawiana” zgodnie z etykietą
  i tworzy regułę dokładnie tak jak w aplikacji. Transakcje miesiąca *m* są kategoryzowane regułami powstałymi
  z poprawek do miesiąca *m−1* włącznie.

**Miary (dla każdego miesiąca i wariantu):**
- trafność: odsetek transakcji z kategorią zgodną z etykietą;
- pokrycie: odsetek transakcji, którym system w ogóle przypisał kategorię;
- precyzja przypisań: trafność liczona tylko wśród przypisanych;
- nakład pracy: liczba poprawek na 100 transakcji.

Przelewy własne są liczone osobno, bo rozpoznaje je parser, a nie kategoryzacja.

**Analiza.** Test McNemara dla par przewidywań A i B na tych samych transakcjach z miesięcy 4–6. Proporcje
podawane są z 95-procentowym przedziałem ufności Wilsona. Do tego krzywa uczenia: trafność i liczba poprawek
w kolejnych miesiącach.

### 3.4. P3: anonimizacja

- **Korpus D4** (`backend/research/corpus.py`, pliki w `backend/research/korpus/`): tytuły przelewów budowane z szablonów
  o strukturze prawdziwych tytułów (płatność kartą, BLIK, przelew na telefon, przelew z imieniem i nazwiskiem, adres,
  wolny tekst, przelew do firmy), z oznaczonymi fragmentami danych osobowych (IBAN, KARTA, TELEFON, EMAIL, PESEL, ADRES,
  OSOBA) oraz fragmentów, które nie są danymi osobowymi (FIRMA, NUMER transakcji). Po 1000 tytułów w części roboczej
  i testowej, stałe ziarno. Pule imion, nazwisk, ulic i miast są podzielone na dwie rozłączne połowy: część robocza
  losuje z jednej, testowa z drugiej, więc strojenie reguł na części roboczej nie uczy ich osób z części testowej.
  Nazwy firm są wspólne, w tym trudne przypadki przypominające imiona („KWIACIARNIA ROZA”, „SALON ANNA”). Część testowa
  została zamrożona tagiem `badanie-korpus` przed napisaniem anonimizatora; reguły rozwija się na części roboczej.
- **Dopasowanie:** fragment danych osobowych jest wykryty, gdy zamaskowane fragmenty pokrywają wszystkie jego znaki
  (typ nie musi się zgadzać: liczy się, czy dane opuszczą komputer). Precyzja: odsetek zamaskowanych fragmentów, które
  nachodzą na fragment danych osobowych. Nadmierne maskowanie: odsetek fragmentów FIRMA i NUMER, które zostały choć
  częściowo zamaskowane. Imiona i nazwiska raportujemy też osobno dla osób spoza słownika imion anonimizatora.
- **Miary:** czułość, precyzja i F1 dla każdego typu danych osobowych, liczone na poziomie fragmentów. Do tego odsetek
  nazw firm zamaskowanych niepotrzebnie, bo nadmierne maskowanie psuje porady.
- **Kontrola na prawdziwych danych:** dla każdego miesiąca D1 powstaje dokładnie ten pakiet danych, który poszedłby do
  modelu. Automatyczne sprawdzenie szuka w nim wzorców danych osobowych i fragmentów nazw kontrahentów będących
  osobami; autor przegląda pakiety sam. Wynik to liczba wycieków (oczekiwana: 0).

### 3.5. P4: porady AI

- **Wejście:** pakiety agregatów z 6 miesięcy D1 i z profili D5.
- **Przebieg:** każdy pakiet do obu dostawców, po 3 powtórzenia. Stała wersja promptu i modelu oraz stała temperatura,
  wszystko zapisane przy każdej poradzie.
- **Zgodność liczb (H4a):** skrypt wyciąga z porady liczby (kwoty, procenty) i sprawdza, czy wynikają z pakietu wejściowego
  (wartość wprost albo prosta różnica lub udział). Przypadki niejednoznaczne rozstrzyga ręczny przegląd, a zasady
  przeglądu są zapisane przed pomiarem.
- **Ocena przydatności (H4b):** porady eksportowane w losowej kolejności, bez nazwy dostawcy i bez numeru powtórzenia.
  Ocenia je autor w skali 1–5 w czterech kryteriach: zgodność z danymi, konkretność, wykonalność, zrozumiałość.
  Klucz (która porada od którego dostawcy) jest w osobnym pliku, otwieranym dopiero po zakończeniu oceny.
- **Koszt i czas (H4c):** tokeny wejścia i wyjścia z odpowiedzi API, przeliczone według cennika z datą pobrania;
  czas od wysłania do odpowiedzi. Podajemy medianę, 95. percentyl i średnią.

### 3.6. Badania dodatkowe (COULD, jeśli starczy czasu)

- Wydajność: czas importu wyciągu i odpowiedzi analityki dla 10 tys. i 100 tys. sztucznych transakcji.
- Użyteczności z udziałem innych osób (np. kwestionariusz SUS) nie planujemy: brak uczestników.

## 4. Co moduły muszą zapewnić, żeby pomiar był rzetelny

| Wymaganie | Etap | Po co |
|---|---|---|
| Kategoryzacja jako czysta funkcja: transakcja i reguły na wejściu, kategoria i dopasowana reguła na wyjściu; tworzenie reguły z poprawki jako osobna funkcja | 5 | ta sama logika w aplikacji i w symulacji P2 |
| Pole `transactions.categorized_by` (`system_rule`, `user_rule`, `manual`, brak) i identyfikator dopasowanej reguły | 5 | pokrycie i nakład pracy w realnym użyciu, nie tylko w symulacji |
| Narzędzie do etykietowania D2 i skrypt symulacji P2 (`backend/research/`) | 5 | etykiety niezależne od systemu |
| Słownik reguł systemowych w wersjonowanym pliku; tag `badanie-slownik` przed pomiarem | 5 | rozdzielenie strojenia od testu |
| Anonimizator jako czysta funkcja zwracająca też listę zamaskowanych fragmentów z typem | 7 | czułość i precyzja per typ |
| Generator korpusu D4 z podziałem na część roboczą i testową | 7 | rozdzielenie strojenia od testu |
| `ai_advice`: wersja promptu, temperatura, czas odpowiedzi w ms (obok dostawcy, modelu i tokenów) | 7 | H4c i powtarzalność |
| Skrypt sprawdzający zgodność liczb porady z pakietem wejściowym | 7 | H4a |
| Eksport porad do ślepej oceny (losowa kolejność, ukryty klucz) | 8 | H4b |
| Profile D5 razem z danymi demo | 9 | P4 na danych, które można pokazać |
| Jedno polecenie uruchamiające wszystkie pomiary i zapisujące wyniki zbiorcze do `docs/badania/` | 10 | powtarzalność |

## 5. Wyniki

Wypełniane w etapie 10 na wersji końcowej. Wyniki wcześniejsze są wstępne.

**P1 (wstępnie, 7–8.11.2026):** 6 z 6 wyciągów zgodnych z sumami kontrolnymi, 1113 transakcji, 1113 unikalnych
numerów operacji. Ponowny import: 0 nowych i 1113 duplikatów. Suma zaimportowanych kwot równa saldu końcowemu
ostatniego wyciągu minus saldo początkowe pierwszego. Te same dane przez importer CSV: 1113 z 1113, bez różnic
w polach, te same klucze duplikatów; detektor rozpoznał 8 z 8 ról kolumn. Prawdziwy eksport CSV z ING (8.11.2026, 6 miesięcy): po poprawieniu nazwy kolumny kwoty
669 transakcji i 20 pominiętych blokad. 612 transakcji ma ten sam klucz co w wyciągach PDF, a ich kwoty są zgodne
w 100%; 8 dat różni się o 1–2 dni. Różnice w zakresie danych są wyjaśnione: eksport CSV nie zawiera 432 automatycznych
przelewów Smart Saver, a 6 transakcji zaksięgowano po ostatnim wyciągu PDF.

**P2 (informacja wstępna, 9.11.2026, bez etykiet):** słownik w wersji `2026-11-09` przypisuje kategorię 234 z 632
transakcji D1 poza przelewami własnymi (37%). To pokrycie, a nie trafność: trafność wymaga etykiet.

**P2 (wstępnie, 9.11.2026, po etykietowaniu):** etykiety ma 632 z 632 transakcji, słownik w wersji `2026-11-09`,
wyniki zbiorcze w `docs/badania/h2_kategoryzacja.json`.

| Miesiąc | n | A: trafność | A: pokrycie | B: trafność | B: pokrycie | B: poprawek/100 |
|---|---|---|---|---|---|---|
| 1 | 92 | 34,8% | 37,0% | 34,8% | 37,0% | 65,2 |
| 2 | 95 | 24,2% | 24,2% | 72,6% | 72,6% | 27,4 |
| 3 | 98 | 30,6% | 32,7% | 65,3% | 67,3% | 34,7 |
| 4 | 131 | 37,4% | 41,2% | 77,1% | 78,6% | 22,9 |
| 5 | 95 | 40,0% | 44,2% | 87,4% | 87,4% | 12,6 |
| 6 | 121 | 38,0% | 40,5% | 85,1% | 85,1% | 14,9 |

Miesiące testowe 4–6 (n = 347):
- **H2a: potwierdzona.** Trafność A 38,3% (95% CI Wilsona 33,4–43,5%), B 82,7% (78,4–86,3%). Pary niezgodne:
  154 transakcje dobrze tylko w B, 0 dobrze tylko w A; dokładny test McNemara p < 0,001.
- **H2b: niespełniona.** Poprawek na 100 transakcji: 27,4 w miesiącu 2 i 14,9 w miesiącu 6, czyli spadek o 46%
  przy progu 50% (miesiąc 6 wymagałby co najwyżej 13,7). Nakład pracy wyraźnie maleje, ale nie tak mocno, jak
  zakładano.
- **H2c: niespełniona.** Trafność B 82,7% przy progu 85%. Próg mieści się w przedziale ufności (78,4–86,3%),
  więc wynik jest niejednoznaczny, a nie wyraźnie zły.

Struktura błędów wariantu B w miesiącach testowych (60 z 347): tylko 2 to zła kategoria, a 58 to brak kategorii.
Z tych 58 transakcji 50 pochodzi od kontrahentów, którzy pojawili się pierwszy raz, a 8 od już widzianych. Precyzja
przypisań B wynosi 98–100%. System prawie się nie myli, gdy przypisuje kategorię; ogranicza go to, że nowego
kontrahenta nie zna ani słownik, ani reguły z poprawek. Wniosek do dyskusji: dalszy wzrost trafności zależy od
pokrycia słownika, a nie od uczenia się z poprawek. Progów hipotez nie zmieniono po pomiarze.

P3–P4: brak (moduły jeszcze nie istnieją).

## 6. Ograniczenia (do dyskusji)

- **Dane jednej osoby z jednego banku przez 6 miesięcy.** Wyniki P2 opisują ten przypadek i nie uogólniają się
  na wszystkich użytkowników. To ograniczenie trzeba nazwać wprost.
- **Etykiety nadaje autor systemu.** Ograniczają to: narzędzie etykietowania niezależne od kategoryzacji, etykiety
  przed pomiarem i podział na część roboczą i testową.
- **H2b porównuje dwa pojedyncze miesiące.** Liczba poprawek w jednym miesiącu zależy od tego, ilu nowych kontrahentów
  w nim się pojawiło (miesiąc 5: 12,6, miesiąc 6: 14,9), więc wynik jest wrażliwy na losowe wahania.
- **Korpus anonimizacji jest sztuczny.** Szablony odwzorowują strukturę prawdziwych tytułów, ale nie ich różnorodność.
  Uzupełnia go kontrola wycieków na prawdziwych danych.
- **Przydatność porad ocenia jedna osoba, autor systemu.** Ocena jest subiektywna; ograniczają to ślepa ocena (bez nazwy
  dostawcy), kryteria ustalone z góry i obiektywna miara zgodności liczb (H4a), która nie zależy od oceniającego.
  Ślepota jest częściowa: styl odpowiedzi może zdradzać model, mimo usunięcia nazw dostawcy i zdań, w których
  model się przedstawia.
- **Modele językowe się zmieniają.** Wyniki P4 dotyczą konkretnych wersji modeli i daty pomiaru.

## 7. Zmiany protokołu

| Data | Zmiana | Powód |
|---|---|---|
| 8.11.2026 | pierwsza wersja | — |
| 8.11.2026 | ocena porad tylko przez autora; bez badania SUS; bez konsultacji z promotorem | brak innych oceniających i uczestników; promotor na razie niedostępny |
| 9.11.2026 | słownik niestrojony na D1 (zamiast strojenia na miesiącach 1–3); przelewy własne bez etykiet | słownik powstał bez wglądu w dane autora, co usuwa ryzyko przecieku danych testowych; przelewy własne rozpoznaje parser |
| 11.11.2026 | korpus D4: pule imion, nazwisk, ulic i miast rozdzielone między część roboczą i testową; ustalona definicja dopasowania | ograniczenie przecieku: autor pisze i generator, i anonimizator, więc rozłączne pule zastępują niezależnego autora korpusu |
