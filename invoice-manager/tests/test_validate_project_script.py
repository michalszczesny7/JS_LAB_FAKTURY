from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "validate_project.py"


def test_validate_project_script_can_be_imported_and_has_main() -> None:
    spec = importlib.util.spec_from_file_location("validate_project", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    assert callable(module.main)
    assert len(module.STEPS) == 5
