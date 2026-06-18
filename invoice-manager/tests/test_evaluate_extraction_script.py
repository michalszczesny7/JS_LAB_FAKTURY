"""Offline integration test for the extraction evaluation CLI."""

import json
import os
import subprocess
import sys
from pathlib import Path

from invoice_manager.importers.mapping import suggest_column_mapping
from invoice_manager.importers.readers import read_import_file


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "evaluate_extraction.py"


def test_cli_writes_json_report_without_openai(tmp_path):
    output_path = tmp_path / "extraction-report.json"
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(PROJECT_ROOT / "src")
    environment.pop("OPENAI_API_KEY", None)

    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--method",
            "local",
            "--output",
            str(output_path),
        ],
        cwd=PROJECT_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=True,
    )

    report = json.loads(output_path.read_text(encoding="utf-8"))
    assert report["case_count"] == 5
    assert report["total_fields"] == 55
    assert "Total score:" in completed.stdout


def test_sample_csv_is_ready_for_automatic_import_mapping():
    sample_path = PROJECT_ROOT / "data" / "sample_data" / "sample_invoices.csv"
    table = read_import_file(sample_path.read_bytes(), sample_path.name)
    mapping = suggest_column_mapping(table.headers)

    assert len(table.rows) == 15
    assert all(mapping.values())
