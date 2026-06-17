"""Tests for Polish NIP validation."""

from invoice_manager.validators.nip_validator import (
    is_valid_nip,
    normalize_nip,
    validate_nip,
)


def test_valid_nip_passes_validation():
    assert is_valid_nip("8567346215") is True
    assert validate_nip("8567346215") == []


def test_invalid_nip_fails_validation():
    errors = validate_nip("8567346216")
    assert errors
    assert "sumę kontrolną" in errors[0]


def test_nip_with_spaces_and_hyphens_is_normalized():
    formatted_nip = "856-734-62 15"
    assert normalize_nip(formatted_nip) == "8567346215"
    assert is_valid_nip(formatted_nip) is True
