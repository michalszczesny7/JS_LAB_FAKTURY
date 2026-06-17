# Invoice Manager

Invoice Manager to prosta aplikacja MVP do ręcznego zarządzania fakturami
kosztowymi i sprzedażowymi dla inwestycji. Interfejs powstał w Streamlit,
a dane są przechowywane lokalnie w bazie SQLite.

## Wymagania

- Python 3.11 lub nowszy
- pip

## Instalacja

```bash
cd /Users/macbookpro15/Documents/JS_LAB_FAKTURY/invoice-manager
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements-dev.txt
```

Plik `requirements.txt` zawiera zależności aplikacji. Plik
`requirements-dev.txt` dodaje narzędzia potrzebne do uruchamiania testów.

## Inicjalizacja bazy

```bash
PYTHONPATH=src python3 -m invoice_manager.db.init_db
```

Polecenie tworzy lokalny plik `data/invoices.db` i dodaje podstawowe kategorie.
Baza jest ignorowana przez Git.

## Uruchomienie aplikacji

```bash
PYTHONPATH=src streamlit run app.py
```

Po uruchomieniu Streamlit wyświetli lokalny adres aplikacji, zwykle
`http://localhost:8501`.

## Testy

```bash
python3 -m compileall src app.py pages
PYTHONPATH=src python3 -m pytest
```

## Obecny zakres

- ręczne dodawanie faktur,
- szybkie dodawanie kontrahentów i inwestycji,
- walidacja NIP, dat, kwot, statusów i duplikatów,
- zatwierdzanie i odrzucanie faktur,
- soft delete,
- tabela faktur z filtrami i nazwami powiązanych rekordów,
- dashboard KPI dla zatwierdzonych faktur,
- import faktur z CSV i XLSX z podglądem oraz ręcznym mapowaniem kolumn,
- walidacja importu, wykrywanie duplikatów i raport końcowy,
- opcjonalne tworzenie brakujących kontrahentów i inwestycji,
- raporty okresowe z filtrami i zestawieniami grupowymi,
- eksport aktywnego raportu do CSV oraz wieloarkuszowego XLSX,
- upload faktur PDF, ekstrakcja tekstu i ręczna weryfikacja wykrytych pól.

## Import CSV i Excel

Strona Import obsługuje pliki `.csv` oraz `.xlsx`. Po przesłaniu pliku aplikacja:

1. pokazuje pierwsze 20 wierszy,
2. proponuje mapowanie popularnych nazw kolumn,
3. pozwala poprawić mapowanie ręcznie,
4. analizuje błędy, ostrzeżenia i duplikaty,
5. zapisuje tylko poprawne, niepowielone wiersze,
6. wyświetla raport importu.

Przykładowy plik CSV rozdzielany średnikami:

```csv
nr faktury;kontrahent;inwestycja;data;termin płatności;netto;vat;brutto
FV/2026/001;Bud-Mat Sp. z o.o.;Osiedle Słoneczne;2026-06-17;2026-07-01;1000,00;230,00;1230,00
FV/2026/002;Projekt Dom S.A.;Budynek A;18.06.2026;;2500,00;575,00;3075,00
```

Rozpoznawane są między innymi nagłówki `numer`, `nr faktury`,
`invoice_number`, `kontrahent`, `contractor`, `client`, `inwestycja`,
`investment`, `project`, `data`, `issue_date`, `invoice_date`, `due_date`,
`netto`, `net_amount`, `brutto`, `gross_amount`, `vat` i `tax_amount`.

Numer faktury, kontrahent, inwestycja i data są wymagane. Należy również
zmapować kwotę netto albo brutto. Brakująca druga kwota jest wyliczana z VAT,
a pusty VAT przyjmuje wartość `0`. Kwoty ujemne są błędem, ponieważ obecny
model faktury nie dopuszcza ich do zapisu. Duplikaty w pliku i bazie są
domyślnie pomijane.

## Raporty i eksport

Strona Raporty pozwala filtrować faktury według zakresu dat, inwestycji,
kontrahenta, kategorii, typu faktury, statusu faktury i statusu płatności.
Miękko usunięte faktury są domyślnie ukryte i można je dołączyć osobną opcją.

Po ustawieniu filtrów wybierz `Odśwież raport`. Widok pokaże KPI oraz tabele:

- pełną listę faktur,
- zestawienie według inwestycji,
- zestawienie według kontrahentów,
- zestawienie miesięczne,
- zestawienie według statusu.

Przycisk `Pobierz CSV` zapisuje pełną listę faktur po aktywnych filtrach w
UTF-8, z separatorem średnikowym. Daty mają format `YYYY-MM-DD`, a kwoty są
eksportowane jako wartości liczbowe.

Przycisk `Pobierz XLSX` tworzy skoroszyt z arkuszami `Faktury`,
`Podsumowanie`, `Według inwestycji`, `Według kontrahentów`, `Miesięcznie` i
`Według statusu`. Arkusze mają filtry, zamrożone nagłówki, formatowanie dat i
kwot oraz wykres wartości brutto według statusu w podsumowaniu.

## AI Review — faktury PDF

Strona AI Review przyjmuje pliki `.pdf` do 10 MB. Na tym etapie działa w pełni
lokalnie i nie łączy się z API AI. Aplikacja sprawdza
rozszerzenie, typ MIME i nagłówek pliku, a następnie próbuje odczytać warstwę
tekstową przez `pypdf`. Bezpieczna kopia trafia do `data/uploaded_invoices`
pod sanityzowaną nazwą zawierającą fragment SHA-256, dlatego inny dokument nie
zostanie przypadkowo nadpisany.

Proste heurystyki rozpoznają numer faktury, sprzedawcę, NIP, datę wystawienia,
termin płatności, kwoty netto/VAT/brutto i walutę. Obsługiwane są daty
`YYYY-MM-DD`, `DD.MM.YYYY`, `DD/MM/YYYY` oraz polskie formaty kwot, np.
`1 230,00` i `1.230,00`.

Po odczycie użytkownik:

1. sprawdza fragment tekstu i ostrzeżenia,
2. może szybko dodać kontrahenta lub inwestycję,
3. wybiera kontrahenta, inwestycję i kategorię,
4. poprawia każde rozpoznane pole,
5. zapisuje fakturę jako `NEEDS_REVIEW` albo `APPROVED`.

Przed zapisem aplikacja sprawdza duplikat numeru faktury dla kontrahenta.
Ścieżka PDF i jego hash są zapisywane w istniejących polach `source_file` i
`file_hash` faktury.

## Znane ograniczenia

- brak uwierzytelniania i obsługi wielu użytkowników,
- lokalna baza SQLite bez migracji schematu,
- brak obsługi starego formatu XLS, OCR i AI,
- skany PDF bez warstwy tekstowej wymagają opcjonalnego OCR; interfejs OCR jest
  przygotowany, ale żaden ciężki silnik nie jest instalowany obowiązkowo,
- rozpoznawanie pól PDF opiera się na heurystykach i zawsze wymaga weryfikacji,
- brak harmonogramów i automatycznej wysyłki raportów,
- import działa na pierwszym arkuszu pliku XLSX,
- import nie jest jedną transakcją: poprawne wiersze zapisują się niezależnie,
- kwoty są obecnie przechowywane jako `float`, co nie jest docelowym
  rozwiązaniem dla rozbudowanej księgowości.

## Test ręczny

Pełna lista kroków znajduje się w [CHECKLIST.md](CHECKLIST.md).
