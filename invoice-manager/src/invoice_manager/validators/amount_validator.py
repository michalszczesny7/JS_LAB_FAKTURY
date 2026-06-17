"""Validation rules for invoice amounts."""

from __future__ import annotations

import math
from numbers import Real

AMOUNT_TOLERANCE = 0.01
FLOAT_EPSILON = 1e-9


def _is_number(value: object) -> bool:
    return isinstance(value, Real) and not isinstance(value, bool) and math.isfinite(value)


def validate_amounts(
    net_amount: object,
    vat_amount: object,
    gross_amount: object,
    *,
    tolerance: float = AMOUNT_TOLERANCE,
) -> list[str]:
    """Validate non-negative amounts and their accounting relationship."""

    errors: list[str] = []
    values = {
        "Kwota netto": net_amount,
        "Kwota VAT": vat_amount,
        "Kwota brutto": gross_amount,
    }
    for label, value in values.items():
        if not _is_number(value):
            errors.append(f"{label} musi być poprawną liczbą.")

    if errors:
        return errors

    net = float(net_amount)
    vat = float(vat_amount)
    gross = float(gross_amount)

    if net < 0:
        errors.append("Kwota netto nie może być ujemna.")
    if vat < 0:
        errors.append("Kwota VAT nie może być ujemna.")
    if gross <= 0:
        errors.append("Kwota brutto musi być większa od zera.")
    if abs((net + vat) - gross) > tolerance + FLOAT_EPSILON:
        errors.append(
            "Suma kwoty netto i VAT musi być równa kwocie brutto "
            f"z tolerancją {tolerance:.2f}."
        )

    return errors
