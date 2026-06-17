"""Result model reserved for future data import services."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class ImportResult:
    total_rows: int = 0
    imported_rows: int = 0
    skipped_rows: int = 0
    error_rows: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def is_successful(self) -> bool:
        return self.error_rows == 0
