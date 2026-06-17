"""Testable regex heuristics for common Polish invoice fields."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from invoice_manager.importers.parsers import parse_amount, parse_date
from invoice_manager.validators.nip_validator import validate_nip

AMOUNT_TOKEN = r"[+-]?\d(?:[\d .\u00a0]*\d)?(?:,\d{1,2})?"


@dataclass(slots=True)
class ExtractedInvoiceFields:
    invoice_number: str | None = None
    contractor_name: str | None = None
    issue_date: str | None = None
    payment_date: str | None = None
    net_amount: float | None = None
    vat_amount: float | None = None
    gross_amount: float | None = None
    nip: str | None = None
    currency: str | None = None
    warnings: list[str] = field(default_factory=list)


def extract_invoice_fields(text: str) -> ExtractedInvoiceFields:
    fields = ExtractedInvoiceFields()
    cleaned_text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not cleaned_text:
        fields.warnings.append("Brak tekstu do rozpoznania pól faktury.")
        return fields

    fields.invoice_number = _first_group(
        cleaned_text,
        r"(?im)^\s*(?:faktura(?:\s+vat)?\s*(?:nr|numer)?|numer\s+faktury)"
        r"\s*[:#]?\s*([A-Z0-9][A-Z0-9/_.-]+)\s*$",
    )
    fields.contractor_name = _first_group(
        cleaned_text,
        r"(?im)^\s*(?:sprzedawca|dostawca|wystawca|kontrahent)\s*:"
        r"\s*(?:\n\s*)?([^\n]+)$",
    )
    fields.issue_date = _extract_date(
        cleaned_text, r"data\s+(?:wystawienia|faktury)|wystawiono"
    )
    fields.payment_date = _extract_date(
        cleaned_text, r"termin\s+płatności|data\s+płatności|płatne\s+do"
    )
    fields.net_amount = _extract_amount(
        cleaned_text, r"(?:kwota\s+)?netto(?:\s+razem)?"
    )
    fields.vat_amount = _extract_amount(
        cleaned_text, r"vat(?:\s+\d{1,2}(?:[,.]\d+)?\s*%?)?(?:\s+razem)?"
    )
    fields.gross_amount = _extract_amount(
        cleaned_text,
        r"(?:kwota\s+)?brutto|razem\s+brutto|razem\s+do\s+zapłaty|do\s+zapłaty|razem",
    )

    nip = _first_group(
        cleaned_text,
        r"(?i)\bNIP\s*:?\s*([0-9][0-9\s-]{8,15}[0-9])\b",
    )
    if nip:
        normalized_nip = re.sub(r"[\s-]", "", nip)
        fields.nip = normalized_nip
        nip_errors = validate_nip(normalized_nip)
        if nip_errors:
            fields.warnings.append("Wykryty NIP wymaga ręcznej weryfikacji.")

    currency_match = re.search(r"(?i)\b(PLN|EUR|USD)\b|zł", cleaned_text)
    if currency_match:
        token = currency_match.group(0).upper()
        fields.currency = "PLN" if token == "ZŁ" else token
    if fields.currency and fields.currency != "PLN":
        fields.warnings.append(
            "Wykryto walutę inną niż PLN. Obecny model faktury nie zapisuje waluty."
        )

    if fields.gross_amount is None and None not in (
        fields.net_amount,
        fields.vat_amount,
    ):
        fields.gross_amount = fields.net_amount + fields.vat_amount
    if fields.net_amount is None and None not in (
        fields.gross_amount,
        fields.vat_amount,
    ):
        fields.net_amount = fields.gross_amount - fields.vat_amount

    required_labels = (
        (fields.invoice_number, "Nie wykryto numeru faktury."),
        (fields.issue_date, "Nie wykryto daty wystawienia."),
        (fields.gross_amount, "Nie wykryto kwoty brutto."),
    )
    for value, warning in required_labels:
        if value is None:
            fields.warnings.append(warning)
    return fields


def _first_group(text: str, pattern: str) -> str | None:
    match = re.search(pattern, text)
    return match.group(1).strip() if match else None


def _extract_date(text: str, label_pattern: str) -> str | None:
    match = re.search(
        rf"(?im)^\s*(?:{label_pattern})\s*:?\s*"
        r"(\d{4}-\d{2}-\d{2}|\d{2}[./]\d{2}[./]\d{4})\s*$",
        text,
    )
    if not match:
        return None
    try:
        return parse_date(match.group(1), required=True)
    except ValueError:
        return None


def _extract_amount(text: str, label_pattern: str) -> float | None:
    match = re.search(
        rf"(?im)^\s*(?:{label_pattern})\s*:?\s*({AMOUNT_TOKEN})"
        r"\s*(?:PLN|zł|EUR|USD)?\s*$",
        text,
    )
    if not match:
        return None
    try:
        return parse_amount(match.group(1), required=True)
    except ValueError:
        return None
