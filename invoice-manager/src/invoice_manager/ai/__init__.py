"""Replaceable AI-assisted invoice extraction providers."""

from invoice_manager.ai.ai_extractor import InvoiceAIExtractor
from invoice_manager.ai.invoice_ai_schema import AIInvoiceExtractionResult
from invoice_manager.ai.mock_ai_extractor import MockInvoiceAIExtractor
from invoice_manager.ai.openai_ai_extractor import OpenAIInvoiceAIExtractor

__all__ = [
    "AIInvoiceExtractionResult",
    "InvoiceAIExtractor",
    "MockInvoiceAIExtractor",
    "OpenAIInvoiceAIExtractor",
]
