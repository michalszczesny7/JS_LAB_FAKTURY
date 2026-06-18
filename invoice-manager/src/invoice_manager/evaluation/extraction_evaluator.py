"""Compare extraction candidates against explicit reference values."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any

from invoice_manager.ai.invoice_ai_schema import AI_FIELD_NAMES
from invoice_manager.evaluation.reference_loader import ReferenceCase
from invoice_manager.services.ai_review_service import AIReviewMethod, AIReviewService

AMOUNT_FIELDS = {"net_amount", "vat_amount", "gross_amount"}
AMOUNT_TOLERANCE = 0.01


@dataclass(frozen=True, slots=True)
class FieldComparison:
    field: str
    expected: Any
    actual: Any
    status: str


@dataclass(frozen=True, slots=True)
class ExtractionResult:
    case_name: str
    requested_method: str
    used_method: str
    comparisons: tuple[FieldComparison, ...]

    @property
    def correct_count(self) -> int:
        return sum(item.status == "correct" for item in self.comparisons)

    @property
    def incorrect_count(self) -> int:
        return sum(item.status == "incorrect" for item in self.comparisons)

    @property
    def missing_count(self) -> int:
        return sum(item.status == "missing" for item in self.comparisons)

    @property
    def total_fields(self) -> int:
        return len(self.comparisons)

    @property
    def score(self) -> float:
        return self.correct_count / self.total_fields if self.total_fields else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_name": self.case_name,
            "requested_method": self.requested_method,
            "used_method": self.used_method,
            "correct_fields": self.correct_count,
            "incorrect_fields": self.incorrect_count,
            "missing_fields": self.missing_count,
            "total_fields": self.total_fields,
            "score": round(self.score, 4),
            "comparisons": [asdict(item) for item in self.comparisons],
        }


@dataclass(frozen=True, slots=True)
class ExtractionQualityReport:
    requested_method: str
    results: tuple[ExtractionResult, ...]

    @property
    def correct_count(self) -> int:
        return sum(result.correct_count for result in self.results)

    @property
    def incorrect_count(self) -> int:
        return sum(result.incorrect_count for result in self.results)

    @property
    def missing_count(self) -> int:
        return sum(result.missing_count for result in self.results)

    @property
    def total_fields(self) -> int:
        return sum(result.total_fields for result in self.results)

    @property
    def score(self) -> float:
        return self.correct_count / self.total_fields if self.total_fields else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "requested_method": self.requested_method,
            "case_count": len(self.results),
            "correct_fields": self.correct_count,
            "incorrect_fields": self.incorrect_count,
            "missing_fields": self.missing_count,
            "total_fields": self.total_fields,
            "score": round(self.score, 4),
            "results": [result.to_dict() for result in self.results],
        }


class ExtractionEvaluator:
    def __init__(self, review_service: AIReviewService | None = None) -> None:
        self.review_service = review_service or AIReviewService()

    def evaluate_case(
        self,
        case: ReferenceCase,
        method: AIReviewMethod | str = AIReviewMethod.LOCAL,
    ) -> ExtractionResult:
        extraction = self.review_service.extract(case.text, method)
        actual = _extraction_values(extraction)
        comparisons = tuple(
            _compare_field(field, case.expected[field], actual[field])
            for field in AI_FIELD_NAMES
        )
        return ExtractionResult(
            case_name=case.name,
            requested_method=extraction.requested_method.value,
            used_method=extraction.used_method.value,
            comparisons=comparisons,
        )

    def evaluate(
        self,
        cases: list[ReferenceCase],
        method: AIReviewMethod | str = AIReviewMethod.LOCAL,
    ) -> ExtractionQualityReport:
        selected = AIReviewMethod(method)
        return ExtractionQualityReport(
            requested_method=selected.value,
            results=tuple(self.evaluate_case(case, selected) for case in cases),
        )


def _extraction_values(extraction: Any) -> dict[str, Any]:
    fields = extraction.fields
    ai_result = extraction.ai_result
    return {
        "invoice_number": fields.invoice_number,
        "issue_date": fields.issue_date,
        "payment_date": fields.payment_date,
        "contractor_name": fields.contractor_name,
        "contractor_nip": fields.nip,
        "invoice_type": ai_result.invoice_type if ai_result else None,
        "category": ai_result.category if ai_result else None,
        "net_amount": fields.net_amount,
        "vat_amount": fields.vat_amount,
        "gross_amount": fields.gross_amount,
        "payment_status": ai_result.payment_status if ai_result else None,
    }


def _compare_field(field: str, expected: Any, actual: Any) -> FieldComparison:
    if actual is None and expected is not None:
        status = "missing"
    elif _values_equal(field, expected, actual):
        status = "correct"
    else:
        status = "incorrect"
    return FieldComparison(field, expected, actual, status)


def _values_equal(field: str, expected: Any, actual: Any) -> bool:
    if expected is None or actual is None:
        return expected is actual
    if field in AMOUNT_FIELDS:
        try:
            difference = abs(float(expected) - float(actual))
            return difference <= AMOUNT_TOLERANCE + 1e-9
        except (TypeError, ValueError):
            return False
    return _normalize_text(expected) == _normalize_text(actual)


def _normalize_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value).strip().casefold())
