"""Tests for invoice amount validation."""

from invoice_manager.validators.amount_validator import validate_amounts


def test_valid_amounts_pass_validation():
    assert validate_amounts(100.0, 23.0, 123.0) == []
    assert validate_amounts(100.0, 23.0, 123.01) == []


def test_inconsistent_amounts_fail_validation():
    errors = validate_amounts(100.0, 23.0, 130.0)
    assert any("netto i VAT" in error for error in errors)


def test_negative_and_zero_amounts_fail_validation():
    errors = validate_amounts(-10.0, -2.3, 0.0)
    assert any("netto" in error for error in errors)
    assert any("VAT" in error for error in errors)
    assert any("brutto" in error for error in errors)
