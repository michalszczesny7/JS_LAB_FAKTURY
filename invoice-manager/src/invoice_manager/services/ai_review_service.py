"""Orchestrate local and AI extraction without any persistence access."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from invoice_manager.ai.ai_extractor import InvoiceAIExtractor
from invoice_manager.ai.invoice_ai_schema import AIInvoiceExtractionResult
from invoice_manager.ai.mock_ai_extractor import MockInvoiceAIExtractor
from invoice_manager.ai.openai_ai_extractor import OpenAIInvoiceAIExtractor
from invoice_manager.documents.field_extractor import (
    ExtractedInvoiceFields,
    extract_invoice_fields,
)


class AIReviewMethod(str, Enum):
    LOCAL = "local"
    MOCK = "mock"
    OPENAI = "openai"


@dataclass(slots=True)
class AIReviewExtraction:
    requested_method: AIReviewMethod
    used_method: AIReviewMethod
    fields: ExtractedInvoiceFields
    ai_result: AIInvoiceExtractionResult | None = None
    warnings: list[str] = field(default_factory=list)


class AIReviewService:
    """Prepare form candidates; deliberately has no repositories or save method."""

    def __init__(
        self,
        mock_extractor: InvoiceAIExtractor | None = None,
        openai_extractor: OpenAIInvoiceAIExtractor | None = None,
    ) -> None:
        self.mock_extractor = mock_extractor or MockInvoiceAIExtractor()
        self.openai_extractor = openai_extractor or OpenAIInvoiceAIExtractor()

    @property
    def openai_configured(self) -> bool:
        return self.openai_extractor.is_configured

    def extract(
        self,
        text: str,
        method: AIReviewMethod | str,
    ) -> AIReviewExtraction:
        selected = AIReviewMethod(method)
        if selected is AIReviewMethod.LOCAL:
            fields = extract_invoice_fields(text)
            return AIReviewExtraction(
                requested_method=selected,
                used_method=selected,
                fields=fields,
                warnings=list(fields.warnings),
            )

        used = selected
        notices: list[str] = []
        extractor: InvoiceAIExtractor = self.mock_extractor
        if selected is AIReviewMethod.OPENAI:
            if self.openai_configured:
                extractor = self.openai_extractor
            else:
                used = AIReviewMethod.MOCK
                notices.append(
                    "Brak OPENAI_API_KEY — używany jest tryb demo/mock."
                )

        ai_result = extractor.extract(text)
        fields = ai_result_to_fields(ai_result)
        return AIReviewExtraction(
            requested_method=selected,
            used_method=used,
            fields=fields,
            ai_result=ai_result,
            warnings=[*notices, *ai_result.warnings],
        )


def ai_result_to_fields(result: AIInvoiceExtractionResult) -> ExtractedInvoiceFields:
    """Map a provider-neutral result to existing AI Review form defaults."""

    return ExtractedInvoiceFields(
        invoice_number=result.invoice_number,
        contractor_name=result.contractor_name,
        issue_date=result.issue_date,
        payment_date=result.payment_date,
        net_amount=result.net_amount,
        vat_amount=result.vat_amount,
        gross_amount=result.gross_amount,
        nip=result.contractor_nip,
        warnings=list(result.warnings),
    )
