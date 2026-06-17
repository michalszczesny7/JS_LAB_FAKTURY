"""Contractor data model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Contractor:
    name: str
    contractor_type: str
    nip: str | None = None
    id: int | None = None
    created_at: str | None = None
