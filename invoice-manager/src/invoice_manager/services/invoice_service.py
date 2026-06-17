"""Invoice use cases with validation and persistence boundaries."""

from __future__ import annotations

from dataclasses import replace

from invoice_manager.models.invoice import Invoice, InvoiceStatus
from invoice_manager.repositories.invoice_repository import InvoiceRepository
from invoice_manager.services.validation_service import (
    ValidationResult,
    ValidationService,
)


class InvoiceValidationError(ValueError):
    """Raised when an invoice cannot be persisted due to validation errors."""

    def __init__(self, result: ValidationResult) -> None:
        self.result = result
        super().__init__("; ".join(result.errors))


class InvoiceService:
    def __init__(
        self,
        invoice_repository: InvoiceRepository,
        validation_service: ValidationService | None = None,
    ) -> None:
        self.invoice_repository = invoice_repository
        self.validation_service = validation_service or ValidationService(
            invoice_repository
        )

    def create_invoice(self, invoice: Invoice, approve: bool = False) -> Invoice:
        candidate = (
            replace(invoice, status=InvoiceStatus.APPROVED) if approve else invoice
        )
        self._ensure_valid(candidate)
        return self.invoice_repository.create(candidate)

    def update_invoice(self, invoice: Invoice) -> Invoice:
        if invoice.id is None:
            raise ValueError("Invoice id is required for update.")
        if self.invoice_repository.get_by_id(invoice.id) is None:
            raise LookupError(f"Invoice {invoice.id} does not exist.")
        self._ensure_valid(invoice)
        return self.invoice_repository.update(invoice)

    def approve_invoice(self, invoice_id: int) -> Invoice:
        invoice = self._get_invoice(invoice_id)
        approved = replace(invoice, status=InvoiceStatus.APPROVED)
        self._ensure_valid(approved)
        return self.invoice_repository.update(approved)

    def reject_invoice(self, invoice_id: int) -> Invoice:
        invoice = self._get_invoice(invoice_id)
        rejected = replace(invoice, status=InvoiceStatus.REJECTED)
        return self.invoice_repository.update(rejected)

    def soft_delete_invoice(self, invoice_id: int) -> bool:
        if self.invoice_repository.get_by_id(invoice_id) is None:
            raise LookupError(f"Invoice {invoice_id} does not exist.")
        return self.invoice_repository.soft_delete(invoice_id)

    def list_approved_invoices(self) -> list[Invoice]:
        return self.invoice_repository.find_by_status(InvoiceStatus.APPROVED)

    def list_invoices_by_status(self, status: InvoiceStatus) -> list[Invoice]:
        return self.invoice_repository.find_by_status(
            status,
            include_deleted=status is InvoiceStatus.DELETED,
        )

    def _ensure_valid(self, invoice: Invoice) -> None:
        result = self.validation_service.validate_invoice(invoice)
        if not result.is_valid:
            raise InvoiceValidationError(result)

    def _get_invoice(self, invoice_id: int) -> Invoice:
        invoice = self.invoice_repository.get_by_id(invoice_id)
        if invoice is None:
            raise LookupError(f"Invoice {invoice_id} does not exist.")
        return invoice
