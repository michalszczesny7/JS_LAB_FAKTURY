"""Analysis and result models for tabular invoice imports."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class ImportRowAnalysis:
    row_number: int
    source: dict[str, object]
    values: dict[str, object] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    duplicate_kind: str | None = None

    @property
    def is_valid(self) -> bool:
        return not self.errors and self.duplicate_kind is None


@dataclass(slots=True)
class ImportPreview:
    headers: list[str]
    source_rows: list[dict[str, object]]
    mapping: dict[str, str | None]
    rows: list[ImportRowAnalysis] = field(default_factory=list)
    mapping_errors: list[str] = field(default_factory=list)

    @property
    def total_rows(self) -> int:
        return len(self.source_rows)

    @property
    def valid_rows(self) -> int:
        return sum(row.is_valid for row in self.rows)

    @property
    def error_rows(self) -> int:
        return sum(bool(row.errors) for row in self.rows)

    @property
    def duplicate_rows(self) -> int:
        return sum(row.duplicate_kind is not None for row in self.rows)


@dataclass(slots=True)
class ImportResult:
    total_rows: int = 0
    valid_rows: int = 0
    imported_rows: int = 0
    skipped_rows: int = 0
    error_rows: int = 0
    duplicate_rows: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    imported_invoice_ids: list[int] = field(default_factory=list)

    @property
    def is_successful(self) -> bool:
        return self.error_rows == 0
