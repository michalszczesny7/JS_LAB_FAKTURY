"""Offline demo extractor backed by the existing regex heuristics."""

from __future__ import annotations

from invoice_manager.ai.ai_extractor import InvoiceAIExtractor
from invoice_manager.ai.invoice_ai_schema import (
    AI_FIELD_NAMES,
    AIInvoiceExtractionResult,
)
from invoice_manager.documents.field_extractor import extract_invoice_fields


class MockInvoiceAIExtractor(InvoiceAIExtractor):
    def extract(self, text: str) -> AIInvoiceExtractionResult:
        local = extract_invoice_fields(text)
        values = {
            "invoice_number": local.invoice_number,
            "issue_date": local.issue_date,
            "payment_date": local.payment_date,
            "contractor_name": local.contractor_name,
            "contractor_nip": local.nip,
            "invoice_type": None,
            "category": None,
            "net_amount": local.net_amount,
            "vat_amount": local.vat_amount,
            "gross_amount": local.gross_amount,
            "payment_status": None,
        }
        found = sum(value is not None for value in values.values())
        confidence = round(found / len(values), 2)
        return AIInvoiceExtractionResult(
            **values,
            confidence=confidence,
            field_confidence={
                name: 0.8 if values[name] is not None else 0.0
                for name in AI_FIELD_NAMES
            },
            warnings=[
                "Użyto trybu demo/mock — wynik nie pochodzi z zewnętrznego modelu AI.",
                *local.warnings,
            ],
            raw_response=None,
        )
