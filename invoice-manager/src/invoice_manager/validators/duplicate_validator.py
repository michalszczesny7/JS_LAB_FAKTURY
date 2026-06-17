"""Duplicate invoice validation backed by InvoiceRepository."""

from __future__ import annotations

from invoice_manager.models.invoice import Invoice
from invoice_manager.repositories.invoice_repository import InvoiceRepository


class DuplicateValidator:
    def __init__(self, invoice_repository: InvoiceRepository) -> None:
        self.invoice_repository = invoice_repository

    def validate(self, invoice: Invoice) -> list[str]:
        """Check invoice number and contractor, excluding the current row."""

        if not invoice.invoice_number or not invoice.contractor_id:
            return []

        duplicate = self.invoice_repository.find_duplicate(
            invoice.invoice_number,
            invoice.contractor_id,
            exclude_invoice_id=invoice.id,
        )
        if duplicate is None:
            return []
        return [
            "Faktura o tym numerze dla wybranego kontrahenta już istnieje "
            f"(id: {duplicate.id})."
        ]
