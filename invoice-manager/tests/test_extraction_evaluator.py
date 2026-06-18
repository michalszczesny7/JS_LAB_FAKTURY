"""Tests for extraction field comparison and quality metrics."""

from pathlib import Path

from invoice_manager.ai.invoice_ai_schema import AI_FIELD_NAMES
from invoice_manager.evaluation.extraction_evaluator import ExtractionEvaluator
from invoice_manager.evaluation.reference_loader import ReferenceCase
from invoice_manager.services.ai_review_service import AIReviewMethod


def make_case(**overrides) -> ReferenceCase:
    expected = {field: None for field in AI_FIELD_NAMES}
    expected.update(
        invoice_number="FV/TEST/1",
        issue_date="2026-06-17",
        contractor_name="Testowa Firma",
        contractor_nip="5260250274",
        net_amount=100.0,
        vat_amount=23.0,
        gross_amount=123.0,
    )
    expected.update(overrides)
    return ReferenceCase(
        name="test_case",
        text=(
            "Faktura nr FV/TEST/1\n"
            "Sprzedawca: Testowa   Firma\n"
            "NIP: 526-025-02-74\n"
            "Data wystawienia: 2026-06-17\n"
            "Netto: 100,00 PLN\nVAT: 23,00 PLN\nBrutto: 123,00 PLN"
        ),
        expected=expected,
        text_path=Path("test.txt"),
        expected_path=Path("test.expected.json"),
    )


def comparison_by_field(result, field):
    return next(item for item in result.comparisons if item.field == field)


def test_evaluator_counts_correct_incorrect_and_missing_fields():
    case = make_case(issue_date="2026-06-18", invoice_type="COST")

    result = ExtractionEvaluator().evaluate_case(case, AIReviewMethod.LOCAL)

    assert comparison_by_field(result, "invoice_number").status == "correct"
    assert comparison_by_field(result, "issue_date").status == "incorrect"
    assert comparison_by_field(result, "invoice_type").status == "missing"
    assert result.correct_count + result.incorrect_count + result.missing_count == 11


def test_amount_comparison_uses_one_cent_tolerance():
    within = make_case(gross_amount=123.01)
    outside = make_case(gross_amount=123.02)
    evaluator = ExtractionEvaluator()

    within_result = evaluator.evaluate_case(within)
    outside_result = evaluator.evaluate_case(outside)

    assert comparison_by_field(within_result, "gross_amount").status == "correct"
    assert comparison_by_field(outside_result, "gross_amount").status == "incorrect"


def test_text_comparison_ignores_case_and_repeated_spaces():
    case = make_case(contractor_name="  TESTOWA FIRMA  ")

    result = ExtractionEvaluator().evaluate_case(case)

    assert comparison_by_field(result, "contractor_name").status == "correct"
