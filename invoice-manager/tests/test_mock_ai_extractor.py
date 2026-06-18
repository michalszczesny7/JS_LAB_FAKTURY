"""Tests for the offline AI demo adapter."""

from invoice_manager.ai.invoice_ai_schema import AIInvoiceExtractionResult
from invoice_manager.ai.mock_ai_extractor import MockInvoiceAIExtractor


def test_mock_extractor_works_without_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    result = MockInvoiceAIExtractor().extract(
        """Faktura VAT nr FV/AI/1
Sprzedawca: Test Bud Sp. z o.o.
Data wystawienia: 2026-06-17
Netto: 100,00 PLN
VAT: 23,00 PLN
Brutto: 123,00 PLN"""
    )

    assert isinstance(result, AIInvoiceExtractionResult)
    assert result.invoice_number == "FV/AI/1"
    assert result.gross_amount == 123.0
    assert result.confidence is not None
    assert result.field_confidence["invoice_number"] == 0.8
    assert any("demo/mock" in warning for warning in result.warnings)
