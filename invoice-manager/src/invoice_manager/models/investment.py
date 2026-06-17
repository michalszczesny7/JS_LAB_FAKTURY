"""Investment data model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Investment:
    name: str
    location: str | None = None
    start_date: str | None = None
    planned_end_date: str | None = None
    budget: float = 0.0
    id: int | None = None
    created_at: str | None = None
