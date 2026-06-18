"""Tests for provider selection and mapping into the review form."""

from invoice_manager.ai.invoice_ai_schema import AIInvoiceExtractionResult
from invoice_manager.ai.openai_ai_extractor import OpenAIInvoiceAIExtractor
from invoice_manager.services.ai_review_service import (
    AIReviewMethod,
    AIReviewService,
    ai_result_to_fields,
)


class StaticExtractor:
    def __init__(self, result: AIInvoiceExtractionResult):
        self.result = result

    def extract(self, _text: str) -> AIInvoiceExtractionResult:
        return self.result


def test_ai_result_can_fill_existing_review_fields():
    result = AIInvoiceExtractionResult(
        invoice_number="FV/FORM/1",
        contractor_name="Bud Test",
        contractor_nip="5260250274",
        issue_date="2026-06-17",
        net_amount=100.0,
        vat_amount=23.0,
        gross_amount=123.0,
    )

    fields = ai_result_to_fields(result)

    assert fields.invoice_number == "FV/FORM/1"
    assert fields.nip == "5260250274"
    assert fields.gross_amount == 123.0


def test_openai_selection_falls_back_to_mock_without_key():
    demo_result = AIInvoiceExtractionResult(invoice_number="FV/DEMO/1")
    service = AIReviewService(
        mock_extractor=StaticExtractor(demo_result),
        openai_extractor=OpenAIInvoiceAIExtractor(api_key=""),
    )

    extraction = service.extract("Faktura nr FV/DEMO/1", AIReviewMethod.OPENAI)

    assert extraction.requested_method is AIReviewMethod.OPENAI
    assert extraction.used_method is AIReviewMethod.MOCK
    assert extraction.fields.invoice_number == "FV/DEMO/1"
    assert any("OPENAI_API_KEY" in warning for warning in extraction.warnings)


def test_local_pdf_extraction_remains_available_and_service_cannot_save():
    service = AIReviewService(openai_extractor=OpenAIInvoiceAIExtractor(api_key=""))

    extraction = service.extract(
        "Faktura nr FV/LOCAL/1\nData wystawienia: 2026-06-17\nBrutto: 123,00 PLN",
        AIReviewMethod.LOCAL,
    )

    assert extraction.fields.invoice_number == "FV/LOCAL/1"
    assert extraction.fields.gross_amount == 123.0
    assert not hasattr(service, "save")
    assert not hasattr(service, "invoice_repository")
