# Invoice Manager AI

## Opis projektu

Invoice Manager AI to laboratoryjna aplikacja Streamlit do zarządzania
fakturami firmy budowlano-deweloperskiej. Dane są przechowywane lokalnie w
SQLite, a logika biznesowa jest oddzielona od interfejsu i repozytoriów.

AI pełni rolę pomocnika: proponuje wartości odczytane z tekstu faktury, ale nie
zapisuje ich autonomicznie. Użytkownik weryfikuje formularz, a każda faktura
przed zapisem przechodzi wspólną walidację. Dashboard finansowy uwzględnia
wyłącznie faktury zatwierdzone; moduł Raporty pozwala dodatkowo analizować i
filtrować pozostałe statusy.

## Główne funkcje

- ręczne dodawanie, zatwierdzanie, odrzucanie i soft delete faktur,
- kontrahenci, inwestycje, kategorie i statusy płatności,
- dashboard kosztów, przychodów i bilansu zatwierdzonych faktur,
- import CSV/XLSX z mapowaniem, walidacją i wykrywaniem duplikatów,
- raporty okresowe oraz eksport CSV i wieloarkuszowego XLSX,
- bezpieczny upload PDF z warstwą tekstową i SHA-256,
- lokalna ekstrakcja regex, offline demo/mock i opcjonalny adapter OpenAI,
- ręczna korekta pól przed zapisem przez `InvoiceService`,
- referencyjny zestaw faktur i raport jakości ekstrakcji.

## Technologie

- Python 3.11+
- Streamlit
- SQLite
- pypdf
- openpyxl
- OpenAI Python SDK jako opcjonalny dostawca ekstrakcji
- pytest
- Docker

## Architektura

Projekt stosuje prostą architekturę warstwową:

```text
Streamlit pages
      ↓
Services (przypadki użycia i orkiestracja)
      ↓
Validation + repositories
      ↓
SQLite

PDF → DocumentService → regex/mock/OpenAI → formularz użytkownika
                                          ↓
                               InvoiceService → ValidationService → SQLite
```

Ekstraktory AI implementują wspólny interfejs i nie mają dostępu do
repozytorium faktur. `DocumentService` odpowiada za dokument, powiązanie pliku
i hasha, natomiast `InvoiceService` pozostaje jedyną ścieżką zapisu faktury.

## Struktura katalogów

```text
app.py                         punkt startowy Streamlit
pages/                         widoki aplikacji
src/invoice_manager/
  ai/                          wymienne ekstraktory AI
  db/                          schemat i inicjalizacja SQLite
  documents/                   PDF i heurystyki pól
  evaluation/                  loader i metryki jakości
  importers/                   CSV/XLSX
  models/                      modele domenowe
  repositories/                dostęp do SQLite
  services/                    przypadki użycia
  ui/                          współdzielone komponenty Streamlit
  validators/                  reguły biznesowe
data/sample_data/              wersjonowane dane demonstracyjne
scripts/                       ewaluacja i smoke check
tests/                         testy jednostkowe i integracyjne
```

## Instalacja

```bash
git clone <adres-repozytorium>
cd invoice-manager
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
cp .env.example .env
```

Do uruchamiania testów doinstaluj zależności developerskie:

```bash
python3 -m pip install -r requirements-dev.txt
```

## Konfiguracja środowiska

Domyślna konfiguracja `.env.example`:

```env
APP_ENV=development
DATABASE_PATH=data/invoices.db

AI_PROVIDER=mock
OPENAI_API_KEY=
OPENAI_MODEL=gpt-5-mini

MAX_UPLOAD_SIZE_MB=10
```

`INVOICE_MANAGER_DB_PATH` pozostaje obsługiwanym nadpisaniem ścieżki bazy,
przydatnym między innymi w testach. Lokalny `.env` jest ignorowany przez Git.

## Inicjalizacja bazy danych

```bash
PYTHONPATH=src python3 -m invoice_manager.db.init_db
```

Polecenie tworzy `data/invoices.db` i podstawowe kategorie. Lokalna baza nie
jest wersjonowana.

## Uruchomienie aplikacji

```bash
PYTHONPATH=src streamlit run app.py
```

Aplikacja jest zwykle dostępna pod `http://localhost:8501`.

## Tryb demo/mock AI

Tryb domyślny nie wymaga internetu ani płatnego API:

```env
AI_PROVIDER=mock
OPENAI_API_KEY=
```

Mock korzysta z lokalnych heurystyk i zwraca wynik w tym samym schemacie co
zewnętrzny dostawca. Na stronie AI Review można też wybrać czysty regex.

## Konfiguracja OpenAI API

OpenAI jest opcjonalne. Aby włączyć adapter, ustaw lokalnie:

```env
AI_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-5-mini
```

Klucz nie może trafić do repozytorium. Brak klucza powoduje bezpieczny fallback
do demo/mock. Testy nie wykonują rzeczywistych zapytań API.

## Import CSV/Excel

Strona Import obsługuje `.csv` i `.xlsx`. Proces obejmuje podgląd danych,
automatyczne lub ręczne mapowanie kolumn, walidację, wykrywanie duplikatów i
opcjonalne tworzenie brakujących kontrahentów oraz inwestycji.

Gotowy plik demonstracyjny:

```text
data/sample_data/sample_invoices.csv
```

Zawiera 15 fikcyjnych faktur. Przed importem zainicjalizuj bazę, pozostaw
automatyczne mapowanie i zaznacz tworzenie brakujących podmiotów.

## AI Review PDF workflow

1. Użytkownik przesyła PDF do 10 MB.
2. Aplikacja sprawdza rozszerzenie, MIME, nagłówek i rozmiar.
3. `pypdf` odczytuje istniejącą warstwę tekstową.
4. Wybrany ekstraktor proponuje pola faktury.
5. Użytkownik poprawia dane w formularzu.
6. `DocumentService` dołącza `source_file` i `file_hash`.
7. `InvoiceService` uruchamia walidację i dopiero wtedy zapisuje rekord.

Analiza dokumentu nigdy nie powoduje automatycznego zapisu faktury.

## Ocena jakości ekstrakcji

Pięć fikcyjnych faktur referencyjnych zawiera oczekiwane wartości 11 pól.
Ewaluacja offline działa bez OpenAI:

```bash
PYTHONPATH=src python3 scripts/evaluate_extraction.py
```

Raport trafia do `exports/extraction_quality_report.json`. Wynik można również
obejrzeć na stronie Jakość Ekstrakcji. Wariant mock:

```bash
PYTHONPATH=src python3 scripts/evaluate_extraction.py --method mock
```

## Testy

```bash
PYTHONPATH=src python3 -m pytest
PYTHONPATH=src python3 -m compileall app.py pages src scripts
PYTHONPATH=src python3 scripts/smoke_check.py
```

## Walidacja projektu i CI

Komplet lokalnych kontroli można uruchomić jedną komendą, bez klucza OpenAI,
internetu i Docker CLI:

```bash
PYTHONPATH=src python3 scripts/validate_project.py
```

Skrypt kolejno uruchamia testy, kompilację plików Python, smoke check, ewaluację
ekstrakcji oraz `git diff --check`. Workflow GitHub Actions wykonuje te same
kontrole dla każdego `push` i `pull_request`. Osobny job CI buduje także obraz
z istniejącego Dockerfile.

## Docker / wdrożenie

Repozytorium zawiera prosty `Dockerfile` dla demonstracyjnego wdrożenia z
domyślnym mock AI:

```bash
docker build -t invoice-manager .
docker run -p 8501:8501 invoice-manager
```

Kontener nie zawiera lokalnego `.env` ani bazy. Dla trwałych danych należy
podłączyć wolumen do `/app/data`. Dockerfile jest przeznaczony do prezentacji,
nie stanowi kompletnej konfiguracji produkcyjnej.

## Dane demonstracyjne

- `data/sample_data/sample_invoices.csv` — 15 faktur do importu,
- `data/sample_data/reference_invoices/` — teksty i oczekiwane JSON-y,
- `data/sample_data/README.md` — opis scenariuszy demonstracyjnych.

Wszystkie podmioty, NIP-y, numery i kwoty są fikcyjne.

## Ograniczenia projektu

- OCR skanów nie jest częścią domyślnej wersji,
- PDF workflow najlepiej działa z dokumentami zawierającymi warstwę tekstową,
- OpenAI API jest opcjonalne, a brak klucza uruchamia demo/mock,
- aplikacja jest prototypem zarządzania i analizy faktur, nie pełnym systemem
  księgowym,
- SQLite nie ma systemu migracji ani obsługi wielu użytkowników,
- kwoty są przechowywane jako `float`,
- import wielu rekordów nie jest jedną transakcją,
- dane referencyjne są demonstracyjne i nie zastępują ewaluacji wdrożeniowej.

## Możliwe dalsze rozszerzenia

- opcjonalny OCR i referencyjne skany PDF,
- `Decimal` dla kwot oraz migracje schematu,
- uwierzytelnianie i role użytkowników,
- transakcyjny import wsadowy,
- wersjonowanie promptów i porównywanie dostawców AI,
- publikowanie obrazu Docker po pomyślnym przejściu CI,
- produkcyjna konfiguracja kontenera i trwałych wolumenów.
