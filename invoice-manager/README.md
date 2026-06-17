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
- opcjonalne tworzenie brakujących kontrahentów i inwestycji.

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

## Znane ograniczenia

- brak uwierzytelniania i obsługi wielu użytkowników,
- lokalna baza SQLite bez migracji schematu,
- brak obsługi starego formatu XLS, OCR i AI,
- brak eksportu i zaawansowanych raportów,
- import działa na pierwszym arkuszu pliku XLSX,
- import nie jest jedną transakcją: poprawne wiersze zapisują się niezależnie,
- kwoty są obecnie przechowywane jako `float`, co nie jest docelowym
  rozwiązaniem dla rozbudowanej księgowości.

## Test ręczny

Pełna lista kroków znajduje się w [CHECKLIST.md](CHECKLIST.md).
