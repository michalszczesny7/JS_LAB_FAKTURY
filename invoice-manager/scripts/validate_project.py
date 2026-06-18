#!/usr/bin/env python3
"""Run the complete offline validation suite for the project."""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class ValidationStep:
    name: str
    command: tuple[str, ...]


STEPS = (
    ValidationStep("Testy", (sys.executable, "-m", "pytest")),
    ValidationStep(
        "Kompilacja plików Python",
        (sys.executable, "-m", "compileall", "app.py", "pages", "src", "scripts"),
    ),
    ValidationStep("Smoke check", (sys.executable, "scripts/smoke_check.py")),
    ValidationStep(
        "Ewaluacja ekstrakcji",
        (sys.executable, "scripts/evaluate_extraction.py"),
    ),
    ValidationStep("Kontrola diff", ("git", "diff", "--check")),
)


def run_steps(steps: Sequence[ValidationStep] = STEPS) -> int:
    env = os.environ.copy()
    source_path = str(PROJECT_ROOT / "src")
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        os.pathsep.join((source_path, existing_pythonpath))
        if existing_pythonpath
        else source_path
    )
    env.setdefault("AI_PROVIDER", "mock")

    for index, step in enumerate(steps, start=1):
        print(f"\n=== [{index}/{len(steps)}] {step.name} ===", flush=True)
        result = subprocess.run(
            step.command,
            cwd=PROJECT_ROOT,
            env=env,
            check=False,
        )
        if result.returncode != 0:
            print(
                f"\nWalidacja przerwana: {step.name} "
                f"(kod {result.returncode}).",
                file=sys.stderr,
            )
            return result.returncode

    print("\n=== Walidacja projektu: OK ===")
    return 0


def main() -> int:
    return run_steps()


if __name__ == "__main__":
    raise SystemExit(main())
