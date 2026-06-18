# Checklista projektu Invoice Manager AI

## Wymagania laboratoryjne

- [x] Python 3.11+ jako język aplikacji.
- [x] Interfejs webowy w Streamlit.
- [x] Separacja modeli, repozytoriów, serwisów, walidacji i UI.
- [x] Testy jednostkowe oraz integracyjne.
- [x] Dokumentacja instalacji, konfiguracji i uruchomienia.
- [x] Repozytorium Git bez lokalnej bazy i artefaktów wykonania.
- [x] Narzędzie wdrożeniowe: Dockerfile i `.dockerignore`.

## Funkcje MVP

- [x] Inicjalizacja lokalnej bazy SQLite.
- [x] Dodawanie kontrahentów i inwestycji.
- [x] Ręczne dodawanie faktur kosztowych i sprzedażowych.
- [x] Lista, filtrowanie i czytelne nazwy powiązanych rekordów.
- [x] Zatwierdzanie, odrzucanie i soft delete faktur.
- [x] Dashboard zatwierdzonych faktur.
- [x] Statusy faktur i płatności.

## Walidacje

- [x] Wymagane pola faktury.
- [x] NIP kontrahenta.
- [x] Daty wystawienia i płatności.
- [x] Kwoty netto, VAT i brutto.
- [x] Status faktury.
- [x] Istnienie kontrahenta, inwestycji i kategorii.
- [x] Duplikat numeru faktury dla kontrahenta.
- [x] Czytelne komunikaty błędów w Streamlit.

## AI Review

- [x] Upload i walidacja PDF z warstwą tekstową.
- [x] Sanityzowana nazwa, SHA-256 i brak nadpisywania dokumentów.
- [x] Lokalny ekstraktor regex.
- [x] Offline demo/mock bez klucza API.
- [x] Opcjonalny adapter OpenAI ze Structured Outputs.
- [x] Fallback mock przy braku `OPENAI_API_KEY`.
- [x] Ręczna korekta wszystkich pól przed zapisem.
- [x] Brak automatycznego zapisu po analizie.
- [x] Zapis wyłącznie przez `DocumentService` i `InvoiceService`.

## Import/Eksport

- [x] Import CSV i XLSX.
- [x] Automatyczne oraz ręczne mapowanie kolumn.
- [x] Podgląd, walidacja i wykrywanie duplikatów.
- [x] Opcjonalne tworzenie brakujących podmiotów.
- [x] Raport importu.
- [x] Raporty z filtrami i zestawieniami grupowymi.
- [x] Eksport CSV oraz wieloarkuszowego XLSX.
- [x] Wersjonowany plik demo z 15 fakturami.

## Testy

- [x] Walidatory i serwisy biznesowe.
- [x] Repozytorium SQLite.
- [x] Import i eksport.
- [x] PDF, ekstraktory AI i fallback bez sieci.
- [x] Loader faktur referencyjnych i metryki jakości.
- [x] CLI ewaluacji ekstrakcji.
- [x] Smoke test punktów wejścia Streamlit.
- [x] Offline `scripts/smoke_check.py`.

## Dokumentacja

- [x] README o strukturze portfolio/GitHub.
- [x] Instalacja i konfiguracja `.env`.
- [x] Tryb mock i opcjonalne OpenAI.
- [x] Opis architektury warstwowej.
- [x] Instrukcja importu danych demonstracyjnych.
- [x] Instrukcja testów i ewaluacji.
- [x] Ograniczenia oraz dalsze rozszerzenia.

## Wdrożenie

- [x] Dockerfile z Pythonem 3.12 i portem 8501.
- [x] `.dockerignore` bez sekretów, bazy i artefaktów.
- [x] Domyślny tryb mock w kontenerze.
- [ ] Wykonać opcjonalny build obrazu w środowisku z Dockerem.
- [x] CI uruchamiające kontrole jakości na push i pull request.

## CI i jakość repozytorium

- [x] Git ignoruje lokalne bazy, uploady, eksporty, cache, logi i sekrety.
- [x] Testy można uruchomić lokalnie jedną komendą walidacyjną.
- [x] Smoke check działa offline w trybie mock.
- [x] Ewaluacja ekstrakcji korzysta z wersjonowanych danych referencyjnych.
- [x] GitHub Actions uruchamia pełny zestaw kontroli jakości.
- [x] Osobny job CI sprawdza build obrazu Docker.

## Do zrobienia opcjonalnie

- [ ] OCR dla skanów PDF.
- [ ] `Decimal` zamiast `float` dla kwot.
- [ ] Migracje bazy danych.
- [ ] Uwierzytelnianie i role użytkowników.
- [ ] Transakcyjny import wsadowy.
- [ ] Wersjonowanie promptów i porównanie dostawców AI.
- [ ] Produkcyjne wdrożenie z trwałym wolumenem i monitoringiem.

## Test prezentacyjny

- [ ] Zainstaluj zależności i skopiuj `.env.example` do `.env`.
- [ ] Zainicjalizuj bazę i uruchom Streamlit.
- [ ] Zaimportuj `data/sample_data/sample_invoices.csv`.
- [ ] Pokaż Dashboard, Faktury, Raporty i eksport XLSX.
- [ ] Przeanalizuj PDF lokalnie oraz w trybie mock.
- [ ] Uruchom stronę Jakość Ekstrakcji.
- [ ] Uruchom testy, ewaluację i `scripts/smoke_check.py`.
