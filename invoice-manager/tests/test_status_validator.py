"""Tests for invoice status validation."""

from invoice_manager.models.invoice import InvoiceStatus
from invoice_manager.validators.status_validator import validate_status


def test_all_invoice_enum_statuses_are_allowed_without_errors():
    for status in InvoiceStatus:
        assert validate_status(status) == []


def test_unknown_status_fails_validation():
    errors = validate_status("UNKNOWN")
    assert any("nieprawidłowy" in error for error in errors)


def test_approved_status_is_blocked_when_critical_errors_exist():
    errors = validate_status(InvoiceStatus.APPROVED, ["Błąd kwoty."])
    assert any("Nie można zatwierdzić" in error for error in errors)
