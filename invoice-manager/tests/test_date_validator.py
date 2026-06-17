"""Tests for invoice date validation."""

from invoice_manager.validators.date_validator import validate_invoice_dates


def test_valid_dates_pass_validation():
    assert validate_invoice_dates("2026-06-17", "2026-07-01") == []
    assert validate_invoice_dates("2026-06-17", None) == []


def test_payment_date_before_issue_date_fails_validation():
    errors = validate_invoice_dates("2026-06-17", "2026-06-16")
    assert any("wcześniejsza" in error for error in errors)


def test_invalid_date_format_fails_validation():
    errors = validate_invoice_dates("17.06.2026", "2026-02-30")
    assert len(errors) == 2
    assert all("YYYY-MM-DD" in error for error in errors)
