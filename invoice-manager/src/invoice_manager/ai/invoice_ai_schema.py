"""Provider-neutral structure returned by invoice AI extractors."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

AI_FIELD_NAMES = (
    "invoice_number",
    "issue_date",
    "payment_date",
    "contractor_name",
    "contractor_nip",
    "invoice_type",
    "category",
    "net_amount",
    "vat_amount",
    "gross_amount",
    "payment_status",
)


@dataclass(slots=True)
class AIInvoiceExtractionResult:
    invoice_number: str | None = None
    issue_date: str | None = None
    payment_date: str | None = None
    contractor_name: str | None = None
    contractor_nip: str | None = None
    invoice_type: str | None = None
    category: str | None = None
    net_amount: float | None = None
    vat_amount: float | None = None
    gross_amount: float | None = None
    payment_status: str | None = None
    confidence: float | None = None
    field_confidence: dict[str, float] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    raw_response: str | None = None

    @classmethod
    def from_mapping(
        cls,
        payload: dict[str, Any],
        *,
        raw_response: str | None = None,
    ) -> "AIInvoiceExtractionResult":
        """Build a tolerant application result from provider JSON."""

        warnings = _string_list(payload.get("warnings"))
        confidence = _confidence(payload.get("confidence"))
        if payload.get("confidence") is not None and confidence is None:
            warnings.append("AI zwróciło nieprawidłową wartość confidence.")

        field_confidence: dict[str, float] = {}
        source_confidence = payload.get("field_confidence")
        if isinstance(source_confidence, dict):
            for name in AI_FIELD_NAMES:
                value = _confidence(source_confidence.get(name))
                if value is not None:
                    field_confidence[name] = value

        return cls(
            invoice_number=_text(payload.get("invoice_number")),
            issue_date=_text(payload.get("issue_date")),
            payment_date=_text(payload.get("payment_date")),
            contractor_name=_text(payload.get("contractor_name")),
            contractor_nip=_text(payload.get("contractor_nip")),
            invoice_type=_text(payload.get("invoice_type")),
            category=_text(payload.get("category")),
            net_amount=_number(payload.get("net_amount")),
            vat_amount=_number(payload.get("vat_amount")),
            gross_amount=_number(payload.get("gross_amount")),
            payment_status=_text(payload.get("payment_status")),
            confidence=confidence,
            field_confidence=field_confidence,
            warnings=warnings,
            raw_response=raw_response,
        )


def _text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return value.strip() or None


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _confidence(value: Any) -> float | None:
    number = _number(value)
    return number if number is not None and 0.0 <= number <= 1.0 else None


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def invoice_extraction_json_schema() -> dict[str, Any]:
    """Return the strict JSON Schema supplied to Structured Outputs."""

    nullable_string = {"type": ["string", "null"]}
    nullable_number = {"type": ["number", "null"]}
    confidence_properties = {
        name: {"type": ["number", "null"], "minimum": 0, "maximum": 1}
        for name in AI_FIELD_NAMES
    }
    properties: dict[str, Any] = {
        "invoice_number": nullable_string,
        "issue_date": nullable_string,
        "payment_date": nullable_string,
        "contractor_name": nullable_string,
        "contractor_nip": nullable_string,
        "invoice_type": {
            "type": ["string", "null"],
            "enum": [
                "COST",
                "SALES",
                "CORRECTION_COST",
                "CORRECTION_SALES",
                None,
            ],
        },
        "category": nullable_string,
        "net_amount": nullable_number,
        "vat_amount": nullable_number,
        "gross_amount": nullable_number,
        "payment_status": {
            "type": ["string", "null"],
            "enum": ["UNPAID", "PAID", "OVERDUE", None],
        },
        "confidence": {
            "type": ["number", "null"],
            "minimum": 0,
            "maximum": 1,
        },
        "field_confidence": {
            "type": "object",
            "properties": confidence_properties,
            "required": list(AI_FIELD_NAMES),
            "additionalProperties": False,
        },
        "warnings": {"type": "array", "items": {"type": "string"}},
    }
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }
