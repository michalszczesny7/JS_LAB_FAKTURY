"""Validation rules for ISO invoice dates."""

from __future__ import annotations

import re
from datetime import date

ISO_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _parse_iso_date(value: object, field_name: str) -> tuple[date | None, str | None]:
    if not isinstance(value, str) or not ISO_DATE_PATTERN.fullmatch(value):
        return None, f"{field_name} musi mieć format YYYY-MM-DD."
    try:
        return date.fromisoformat(value), None
    except ValueError:
        return None, f"{field_name} nie jest prawidłową datą w formacie YYYY-MM-DD."


def validate_invoice_dates(
    issue_date: object,
    payment_date: object | None,
) -> list[str]:
    """Validate issue date and optional payment date."""

    if issue_date is None or issue_date == "":
        return ["Data wystawienia jest wymagana."]

    errors: list[str] = []
    parsed_issue_date, issue_error = _parse_iso_date(issue_date, "Data wystawienia")
    if issue_error:
        errors.append(issue_error)

    if payment_date is None or payment_date == "":
        return errors

    parsed_payment_date, payment_error = _parse_iso_date(
        payment_date, "Data płatności"
    )
    if payment_error:
        errors.append(payment_error)
    elif parsed_issue_date is not None and parsed_payment_date < parsed_issue_date:
        errors.append("Data płatności nie może być wcześniejsza niż data wystawienia.")

    return errors
