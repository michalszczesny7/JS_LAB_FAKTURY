"""Integration check for the offline portfolio smoke script."""

import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_smoke_check_script_runs_without_api_key():
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(PROJECT_ROOT / "src")
    environment.pop("OPENAI_API_KEY", None)

    completed = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "smoke_check.py")],
        cwd=PROJECT_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=True,
    )

    assert "Smoke check: OK" in completed.stdout
    assert "References: OK (5 przypadków)" in completed.stdout
