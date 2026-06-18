#!/usr/bin/env python3
"""Fast offline readiness check for a portfolio/demo checkout."""

from __future__ import annotations

from invoice_manager.ai import AIInvoiceExtractionResult, MockInvoiceAIExtractor
from invoice_manager.config import (
    APP_ENV,
    MAX_PDF_SIZE_BYTES,
    PROJECT_ROOT,
    get_ai_provider,
    get_database_path,
)
from invoice_manager.evaluation import load_reference_cases
from invoice_manager.services import AIReviewService, DocumentService, InvoiceService


def main() -> None:
    sample_csv = PROJECT_ROOT / "data" / "sample_data" / "sample_invoices.csv"
    if not sample_csv.is_file():
        raise RuntimeError(f"Brak danych demonstracyjnych: {sample_csv}")

    references = load_reference_cases()
    if len(references) < 5:
        raise RuntimeError("Zestaw referencyjny powinien zawierać co najmniej 5 faktur.")

    result = MockInvoiceAIExtractor().extract(
        "Faktura nr SMOKE/1\n"
        "Data wystawienia: 2026-06-18\n"
        "Netto: 100,00 PLN\nVAT: 23,00 PLN\nBrutto: 123,00 PLN"
    )
    if not isinstance(result, AIInvoiceExtractionResult):
        raise RuntimeError("Mock AI zwrócił nieprawidłowy typ wyniku.")
    if result.invoice_number != "SMOKE/1" or result.gross_amount != 123.0:
        raise RuntimeError("Mock AI nie rozpoznał podstawowych pól faktury.")

    imported_modules = (AIReviewService, DocumentService, InvoiceService)
    print(f"Imports: OK ({len(imported_modules)} główne serwisy)")
    print(f"Config: OK (env={APP_ENV}, provider={get_ai_provider()})")
    print(f"Database path: {get_database_path()}")
    print(f"Upload limit: {MAX_PDF_SIZE_BYTES // (1024 * 1024)} MB")
    print(f"Sample data: OK ({sample_csv})")
    print(f"References: OK ({len(references)} przypadków)")
    print("Mock extraction: OK")
    print("Smoke check: OK")


if __name__ == "__main__":
    main()
