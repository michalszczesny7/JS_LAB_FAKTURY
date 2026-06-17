"""Tests for regex-based extraction from synthetic Polish invoice text."""

from invoice_manager.documents.field_extractor import extract_invoice_fields

SAMPLE_INVOICE_TEXT = """
Faktura VAT nr FV/2026/001
Sprzedawca: Test Bud Sp. z o.o.
NIP: 856-734-62-15
Data wystawienia: 17.06.2026
Termin płatności: 01/07/2026
Netto: 1.000,00 PLN
VAT: 230,00 PLN
Brutto: 1 230,00 PLN
"""


def test_extractor_detects_invoice_identity_and_contractor():
    fields = extract_invoice_fields(SAMPLE_INVOICE_TEXT)
    assert fields.invoice_number == "FV/2026/001"
    assert fields.contractor_name == "Test Bud Sp. z o.o."
    assert fields.nip == "8567346215"
    assert fields.currency == "PLN"


def test_extractor_parses_polish_dates():
    fields = extract_invoice_fields(SAMPLE_INVOICE_TEXT)
    assert fields.issue_date == "2026-06-17"
    assert fields.payment_date == "2026-07-01"


def test_extractor_parses_polish_amounts():
    fields = extract_invoice_fields(SAMPLE_INVOICE_TEXT)
    assert fields.net_amount == 1000.0
    assert fields.vat_amount == 230.0
    assert fields.gross_amount == 1230.0


def test_empty_text_returns_readable_warnings():
    fields = extract_invoice_fields("")
    assert fields.invoice_number is None
    assert fields.warnings == ["Brak tekstu do rozpoznania pól faktury."]
