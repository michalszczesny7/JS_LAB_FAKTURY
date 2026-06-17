"""Validation of Polish tax identification numbers (NIP)."""

from __future__ import annotations

NIP_WEIGHTS = (6, 5, 7, 2, 3, 4, 5, 6, 7)


def normalize_nip(nip: str) -> str:
    """Remove separators accepted in user-entered NIP values."""

    return nip.replace("-", "").replace(" ", "")


def validate_nip(nip: str | None) -> list[str]:
    """Return validation errors for a Polish NIP number."""

    if nip is None or not nip.strip():
        return ["NIP jest wymagany."]

    normalized = normalize_nip(nip)
    if len(normalized) != 10 or not normalized.isdigit():
        return ["NIP po usunięciu spacji i myślników musi zawierać 10 cyfr."]

    digits = [int(character) for character in normalized]
    checksum = sum(
        digit * weight for digit, weight in zip(digits[:9], NIP_WEIGHTS, strict=True)
    ) % 11
    if checksum == 10 or checksum != digits[9]:
        return ["NIP ma nieprawidłową sumę kontrolną."]

    return []


def is_valid_nip(nip: str | None) -> bool:
    """Return True when the NIP has a valid format and checksum."""

    return not validate_nip(nip)
