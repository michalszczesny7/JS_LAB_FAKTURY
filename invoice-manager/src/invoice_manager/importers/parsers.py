"""Normalization and parsing helpers for imported invoice values."""

from __future__ import annotations

import math
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

WHITESPACE_PATTERN = re.compile(r"\s+")


def normalize_name(value: object) -> str:
    """Collapse whitespace while preserving the original letter case."""

    return WHITESPACE_PATTERN.sub(" ", str(value or "").strip())


def normalize_name_key(value: object) -> str:
    return normalize_name(value).casefold()


def normalize_invoice_number(value: object) -> str:
    return normalize_name(value).upper()


def parse_date(value: object, *, required: bool = False) -> str | None:
    """Parse common spreadsheet date representations into YYYY-MM-DD."""

    if value is None or (isinstance(value, str) and not value.strip()):
        if required:
            raise ValueError("Wartość daty jest wymagana.")
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()

    text = str(value).strip()
    for date_format in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, date_format).date().isoformat()
        except ValueError:
            continue
    raise ValueError(f"Nieprawidłowa data: {text}. Oczekiwany format YYYY-MM-DD.")


def parse_amount(value: object, *, required: bool = False) -> float | None:
    """Parse a Polish or international decimal amount into float."""

    if value is None or (isinstance(value, str) and not value.strip()):
        if required:
            raise ValueError("Wartość kwoty jest wymagana.")
        return None
    if isinstance(value, bool):
        raise ValueError("Nieprawidłowa kwota.")
    if isinstance(value, (int, float, Decimal)):
        amount = float(value)
        if not math.isfinite(amount):
            raise ValueError("Kwota musi być liczbą skończoną.")
        return amount

    text = str(value).strip().lower()
    text = text.replace("pln", "").replace("zł", "")
    text = text.replace("\u00a0", "").replace(" ", "")
    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        text = text.replace(",", ".")

    try:
        amount = float(Decimal(text))
    except (InvalidOperation, ValueError):
        raise ValueError(f"Nieprawidłowa kwota: {value}.") from None
    if not math.isfinite(amount):
        raise ValueError("Kwota musi być liczbą skończoną.")
    return amount
