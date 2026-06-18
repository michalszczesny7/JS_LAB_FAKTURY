"""Common interface implemented by invoice AI providers."""

from __future__ import annotations

from abc import ABC, abstractmethod

from invoice_manager.ai.invoice_ai_schema import AIInvoiceExtractionResult


class InvoiceAIExtractor(ABC):
    """Provider-neutral extraction contract with no persistence capability."""

    @abstractmethod
    def extract(self, text: str) -> AIInvoiceExtractionResult:
        """Extract candidate invoice fields from already-read document text."""
