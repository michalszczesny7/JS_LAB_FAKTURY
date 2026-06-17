"""Validation of invoice statuses and approval constraints."""

from __future__ import annotations

from collections.abc import Collection

from invoice_manager.models.invoice import InvoiceStatus


def validate_status(
    status: object,
    critical_errors: Collection[str] = (),
) -> list[str]:
    """Validate enum membership and prevent approval with critical errors."""

    if not isinstance(status, InvoiceStatus):
        allowed = ", ".join(item.value for item in InvoiceStatus)
        return [f"Status faktury jest nieprawidłowy. Dozwolone wartości: {allowed}."]

    if status is InvoiceStatus.APPROVED and critical_errors:
        return ["Nie można zatwierdzić faktury zawierającej błędy krytyczne."]

    return []
