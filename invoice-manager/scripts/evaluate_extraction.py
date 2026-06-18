#!/usr/bin/env python3
"""Evaluate invoice extraction against the bundled fictional references."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from invoice_manager.config import PROJECT_ROOT
from invoice_manager.evaluation import (
    ExtractionEvaluator,
    ExtractionQualityReport,
    load_reference_cases,
)
from invoice_manager.services.ai_review_service import AIReviewMethod

DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "exports" / "extraction_quality_report.json"


def run_evaluation(
    *,
    method: AIReviewMethod | str = AIReviewMethod.LOCAL,
    reference_directory: str | Path | None = None,
    output_path: str | Path = DEFAULT_OUTPUT_PATH,
) -> ExtractionQualityReport:
    cases = (
        load_reference_cases(reference_directory)
        if reference_directory is not None
        else load_reference_cases()
    )
    report = ExtractionEvaluator().evaluate(cases, method)
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(report.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Oceń ekstrakcję na fikcyjnych fakturach referencyjnych."
    )
    parser.add_argument(
        "--method",
        choices=[method.value for method in AIReviewMethod],
        default=AIReviewMethod.LOCAL.value,
        help="Metoda ekstrakcji (domyślnie: local).",
    )
    parser.add_argument("--references", type=Path, help="Opcjonalny katalog danych.")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Ścieżka raportu JSON.",
    )
    args = parser.parse_args()

    report = run_evaluation(
        method=args.method,
        reference_directory=args.references,
        output_path=args.output,
    )
    for result in report.results:
        print(
            f"{result.case_name}: {result.correct_count}/{result.total_fields} "
            f"fields correct, score {result.score:.1%}"
        )
    print(f"Total score: {report.score:.1%}")
    print(f"Report: {args.output}")


if __name__ == "__main__":
    main()
