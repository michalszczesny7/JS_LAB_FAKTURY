"""Validation of fields required for every invoice."""

from __future__ import annotations

from invoice_manager.models.invoice import Invoice, InvoiceStatus, InvoiceType


def validate_required_fields(invoice: Invoice) -> list[str]:
    """Return errors for required invoice fields that are missing."""

    errors: list[str] = []
    if not isinstance(invoice.invoice_number, str) or not invoice.invoice_number.strip():
        errors.append("Numer faktury jest wymagany.")
    if not isinstance(invoice.issue_date, str) or not invoice.issue_date.strip():
        errors.append("Data wystawienia jest wymagana.")
    if not isinstance(invoice.contractor_id, int) or invoice.contractor_id <= 0:
        errors.append("Kontrahent jest wymagany.")
    if not isinstance(invoice.investment_id, int) or invoice.investment_id <= 0:
        errors.append("Inwestycja jest wymagana.")
    if not isinstance(invoice.category_id, int) or invoice.category_id <= 0:
        errors.append("Kategoria jest wymagana.")
    if not isinstance(invoice.invoice_type, InvoiceType):
        errors.append("Typ faktury jest wymagany i musi być poprawną wartością enum.")
    if not isinstance(invoice.status, InvoiceStatus):
        errors.append("Status faktury jest wymagany i musi być poprawną wartością enum.")
    if invoice.gross_amount is None:
        errors.append("Kwota brutto jest wymagana.")
    return errors
