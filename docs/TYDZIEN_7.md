# Tydzień 7: moduł doradczy AI

Plan przewiduje ten etap na 7–13 grudnia 2026; wykonano go 11 listopada.

**Cel:** porady oszczędnościowe z modelu językowego przy twardej zasadzie prywatności: komputer opuszczają
wyłącznie zanonimizowane agregaty, nigdy pojedyncze transakcje. Moduł od początku zbudowany pod badania P3
(anonimizacja) i P4 (jakość, zgodność liczb, koszt porad) z `BADANIA.md`.

---

## 1. Decyzje

| Temat | Decyzja | Uzasadnienie |
|---|---|---|
| Kolejność prac | najpierw korpus testowy (tag `badanie-korpus`), potem anonimizator, na końcu pomiar | część testowa zamrożona przed strojeniem reguł nie „zna” anonimizatora (badanie P3) |
| Korpus D4 | po 1000 sztucznych tytułów (robocza/testowa) z rozłącznymi pulami imion, nazwisk, ulic i miast; nazwy firm wspólne, w tym mylące („SALON ANNA”) | strojenie na części roboczej nie uczy reguł osób z części testowej; firmy mierzą nadmierne maskowanie |
| Zestaw „poza słownikiem” | 300 tytułów z 38 imionami spoza słownika anonimizatora | wszystkie imiona D4 są w słowniku, więc 100% czułości mierzyłoby tylko jego pokrycie |
| Anonimizator | czysta funkcja `anonymize(text)`: tekst ze znacznikami i lista fragmentów z typem | pomiar czułości i precyzji per typ (H3); ta sama funkcja w aplikacji i w badaniu |
| Walidacja wzorców | karta tylko z sumą Luhna albo zamaskowana („1234xx5678”), PESEL z sumą kontrolną i datą (po słowie „PESEL” zawsze) | bez tego numery transakcji BLIK (11 cyfr) i identyfikatory wpadałyby w maskę |
| Osoby | słownik ok. 400 imion + reguły kontekstu: „Dla/Od”, po numerze rachunku, przed adresem, końcówki nazwisk (-ski, -enko…), kontakt przy przelewie na telefon | imiona spoza słownika (94,2% na zestawie kontrolnym) i ochrona nazw firm (0 z 480 zamaskowanych) |
| Pakiet dla modelu | tylko agregaty z tych samych funkcji co dashboard; nazwy kategorii użytkownika przez anonimizację; stała temperatura 0,2 i wersja promptu | brak pojedynczych transakcji i kontrahentów; powtarzalność porad (P4); „Pożyczka dla Ani” → „Pożyczka dla [OSOBA]” |
| Dostawcy | `mock` / `openai` / `anthropic` przez `AI_PROVIDER`; wywołania HTTP biblioteką standardową | mock: rozwój i pokaz bez kosztów i internetu; bez nowych zależności w obrazie produkcyjnym |
| Koszty | cache porady (ten sam okres, dane, dostawca, model i wersja promptu) + dzienny limit na użytkownika (`ADVICE_DAILY_LIMIT`, domyślnie 10) | porada nie może generować kosztów przy każdym odświeżeniu strony |
| Transparentność | `GET /api/advice/preview-payload` i kopia pakietu przy każdej poradzie w `ai_advice.prompt_payload` | użytkownik widzi dokładnie, co opuszcza komputer |
| Zgodność liczb (H4a) | reguły pokrycia zapisane przed pomiarem: wartość wprost, suma/różnica, udział, procent kwoty; procent-parametr scenariusza tylko z wynikiem w tekście | skrypt `research/advice_numbers.py` + `scripts/check_advice.py`; porada `mock` przechodzi kontrolę w teście |

## 2. Wykonane zadania
- [x] Korpus D4 (`research/corpus.py`, `research/korpus/`), zamrożony tagiem `badanie-korpus`; zestaw kontrolny poza słownikiem
- [x] `app/ai/names.py`, `app/ai/anonymizer.py`; pomiar `research/anonymization.py` (zapis do `docs/badania/`)
- [x] `app/ai/prompt_builder.py`: pakiet agregatów + prompt systemowy (rola doradcy, zakaz wymyślania liczb, format odpowiedzi)
- [x] Dostawcy `mock`/`openai`/`anthropic`; obsługa błędów (brak klucza, timeout, limit dostawcy, awaria)
- [x] Migracja `porady_dane_badania`: `prompt_version`, `temperature`, `response_time_ms` w `ai_advice`
- [x] `POST /api/advice`, `GET /api/advice`, `GET /api/advice/preview-payload`; cache i dzienny limit
- [x] Skrypt zgodności liczb (H4a) i kontrola wycieków na prawdziwych pakietach (`scripts/check_payloads.py`)
- [x] Testy: 75 (anonimizacja i korpus) + 18 (porady i liczby); razem w projekcie 464

## 3. Definition of Done
- [x] API generuje sensowne rekomendacje na danych autora przez dostawcę `mock`; przycisk w przeglądarce powstanie w etapie 8
- [x] W pakietach dla modelu nie ma danych osobowych: kontrola na 8 miesiącach prawdziwych danych wykazała 0 wycieków
- [x] Testy przechodzą lokalnie; dziennik, plan i protokół badania są aktualne

## 4. Wyniki badania P3 (wstępne; szczegóły w `BADANIA.md`, rozdz. 5)
- Część testowa D4 (zamrożona przed strojeniem): czułość 100% dla wszystkich typów, precyzja 99,8%,
  nadmierne maskowanie firm 0 z 480.
- Zestaw kontrolny z imionami spoza słownika: osoby 94,2%, pozostałe typy 100%, precyzja 100%.
- Kontrola wycieków na prawdziwych pakietach: 0 z 8 miesięcy.
