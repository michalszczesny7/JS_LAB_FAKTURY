"""Load paired invoice text and expected JSON reference fixtures."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from invoice_manager.ai.invoice_ai_schema import AI_FIELD_NAMES
from invoice_manager.config import PROJECT_ROOT

DEFAULT_REFERENCE_DIRECTORY = (
    PROJECT_ROOT / "data" / "sample_data" / "reference_invoices"
)


class ReferenceLoadError(ValueError):
    """Raised when the reference dataset is incomplete or malformed."""


@dataclass(frozen=True, slots=True)
class ReferenceCase:
    name: str
    text: str
    expected: dict[str, Any]
    text_path: Path
    expected_path: Path


def load_reference_cases(
    directory: str | Path = DEFAULT_REFERENCE_DIRECTORY,
) -> list[ReferenceCase]:
    """Load sorted `.txt` and `.expected.json` invoice pairs."""

    source_directory = Path(directory)
    if not source_directory.is_dir():
        raise ReferenceLoadError(
            f"Katalog danych referencyjnych nie istnieje: {source_directory}"
        )

    cases: list[ReferenceCase] = []
    for text_path in sorted(source_directory.glob("*.txt")):
        expected_path = text_path.with_suffix(".expected.json")
        if not expected_path.is_file():
            raise ReferenceLoadError(
                f"Brak pliku expected dla {text_path.name}: {expected_path.name}"
            )
        try:
            expected = json.loads(expected_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ReferenceLoadError(
                f"Nie udało się odczytać {expected_path.name}: {error}"
            ) from error
        if not isinstance(expected, dict):
            raise ReferenceLoadError(
                f"Plik {expected_path.name} musi zawierać obiekt JSON."
            )
        missing_fields = [field for field in AI_FIELD_NAMES if field not in expected]
        if missing_fields:
            raise ReferenceLoadError(
                f"Plik {expected_path.name} nie zawiera pól: "
                + ", ".join(missing_fields)
            )
        try:
            text = text_path.read_text(encoding="utf-8")
        except OSError as error:
            raise ReferenceLoadError(
                f"Nie udało się odczytać {text_path.name}: {error}"
            ) from error
        cases.append(
            ReferenceCase(
                name=text_path.stem,
                text=text,
                expected={field: expected[field] for field in AI_FIELD_NAMES},
                text_path=text_path,
                expected_path=expected_path,
            )
        )

    if not cases:
        raise ReferenceLoadError(
            f"Nie znaleziono plików .txt w katalogu: {source_directory}"
        )
    return cases
