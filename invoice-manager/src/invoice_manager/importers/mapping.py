"""Automatic and manual mapping of source columns to invoice fields."""

from __future__ import annotations

import re
import unicodedata

IMPORT_FIELDS = {
    "invoice_number": "Numer faktury",
    "contractor": "Kontrahent",
    "investment": "Inwestycja",
    "issue_date": "Data faktury",
    "payment_date": "Termin płatności",
    "net_amount": "Kwota netto",
    "vat_amount": "Kwota VAT",
    "gross_amount": "Kwota brutto",
    "category": "Kategoria",
    "invoice_type": "Typ faktury",
    "status": "Status faktury",
    "payment_status": "Status płatności",
}

COLUMN_ALIASES = {
    "invoice_number": {"numer", "nr faktury", "numer faktury", "invoice number"},
    "contractor": {"kontrahent", "contractor", "client", "klient", "dostawca"},
    "investment": {"inwestycja", "investment", "project", "projekt"},
    "issue_date": {"data", "data faktury", "issue date", "invoice date"},
    "payment_date": {
        "termin platnosci",
        "termin płatności",
        "due date",
        "payment date",
    },
    "net_amount": {"netto", "kwota netto", "net amount", "net"},
    "vat_amount": {"vat", "kwota vat", "tax amount", "tax"},
    "gross_amount": {"brutto", "kwota brutto", "gross amount", "gross"},
    "category": {"kategoria", "category"},
    "invoice_type": {"typ faktury", "invoice type", "type"},
    "status": {"status", "status faktury", "invoice status"},
    "payment_status": {"status platnosci", "status płatności", "payment status"},
}

REQUIRED_MAPPED_FIELDS = ("invoice_number", "contractor", "investment", "issue_date")


def normalize_header(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(character for character in text if not unicodedata.combining(character))
    text = re.sub(r"[_\-]+", " ", text.casefold())
    return " ".join(text.split())


def suggest_column_mapping(headers: list[str]) -> dict[str, str | None]:
    normalized_headers = {normalize_header(header): header for header in headers}
    mapping: dict[str, str | None] = {}
    for field, aliases in COLUMN_ALIASES.items():
        mapping[field] = next(
            (
                normalized_headers[normalize_header(alias)]
                for alias in aliases
                if normalize_header(alias) in normalized_headers
            ),
            None,
        )
    return mapping


def validate_column_mapping(mapping: dict[str, str | None]) -> list[str]:
    errors = [
        f"Brak mapowania pola: {IMPORT_FIELDS[field]}."
        for field in REQUIRED_MAPPED_FIELDS
        if not mapping.get(field)
    ]
    if not mapping.get("net_amount") and not mapping.get("gross_amount"):
        errors.append("Zmapuj co najmniej kwotę netto albo kwotę brutto.")

    used_columns = [column for column in mapping.values() if column]
    duplicate_columns = {
        column for column in used_columns if used_columns.count(column) > 1
    }
    if duplicate_columns:
        errors.append(
            "Jedna kolumna źródłowa nie może mapować wielu pól: "
            + ", ".join(sorted(duplicate_columns))
            + "."
        )
    return errors
