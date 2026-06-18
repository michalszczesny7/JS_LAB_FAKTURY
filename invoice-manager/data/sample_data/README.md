# Dane demonstracyjne

Wszystkie nazwy, numery faktur, NIP-y i wartości w tym katalogu są fikcyjne i
służą wyłącznie do demonstracji oraz testów.

## Faktury referencyjne

Katalog `reference_invoices` zawiera pięć par plików:

- `invoice_NNN.txt` — tekst odpowiadający warstwie tekstowej PDF,
- `invoice_NNN.expected.json` — oczekiwane wartości 11 ocenianych pól.

Przypadki obejmują materiały budowlane, podwykonawcę, wynajem sprzętu,
sprzedaż lokalu i dokument bez terminu płatności. Celowo użyto kilku formatów
dat, kwot i NIP-ów.

## CSV do demonstracji importu

`sample_invoices.csv` zawiera 15 faktur gotowych do wczytania na stronie
Import. Przed wykonaniem importu zainicjalizuj bazę z domyślnymi kategoriami,
sprawdź automatyczne mapowanie i zaznacz tworzenie brakujących kontrahentów
oraz inwestycji.

## Ocena jakości

```bash
PYTHONPATH=src python3 scripts/evaluate_extraction.py
```

Komenda nie wymaga internetu ani klucza OpenAI. Domyślnie ocenia lokalny
ekstraktor regex i zapisuje raport do `exports/extraction_quality_report.json`.
