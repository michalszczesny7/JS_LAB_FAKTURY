"""Tests for paired reference invoice loading."""

import json

import pytest

from invoice_manager.ai.invoice_ai_schema import AI_FIELD_NAMES
from invoice_manager.evaluation.reference_loader import (
    ReferenceLoadError,
    load_reference_cases,
)


def expected_payload() -> dict[str, object]:
    return {field: None for field in AI_FIELD_NAMES}


def test_loader_finds_text_and_expected_pairs(tmp_path):
    (tmp_path / "invoice_001.txt").write_text("Faktura nr FV/1", encoding="utf-8")
    (tmp_path / "invoice_001.expected.json").write_text(
        json.dumps(expected_payload()),
        encoding="utf-8",
    )

    cases = load_reference_cases(tmp_path)

    assert len(cases) == 1
    assert cases[0].name == "invoice_001"
    assert cases[0].expected == expected_payload()


def test_missing_expected_file_has_readable_error(tmp_path):
    (tmp_path / "invoice_001.txt").write_text("Faktura nr FV/1", encoding="utf-8")

    with pytest.raises(ReferenceLoadError, match="Brak pliku expected"):
        load_reference_cases(tmp_path)


def test_bundled_reference_dataset_contains_five_complete_cases():
    cases = load_reference_cases()

    assert len(cases) == 5
    assert all(set(case.expected) == set(AI_FIELD_NAMES) for case in cases)
