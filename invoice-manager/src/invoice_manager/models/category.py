"""Invoice category data model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Category:
    name: str
    category_type: str
    id: int | None = None
    created_at: str | None = None
