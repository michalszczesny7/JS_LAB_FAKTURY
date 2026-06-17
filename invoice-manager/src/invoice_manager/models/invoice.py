"""Invoice model and invoice-related enumerations."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class InvoiceStatus(str, Enum):
    DRAFT_AI = "DRAFT_AI"
    DRAFT_MANUAL = "DRAFT_MANUAL"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    DELETED = "DELETED"


class InvoiceType(str, Enum):
    COST = "COST"
    SALES = "SALES"
    CORRECTION_COST = "CORRECTION_COST"
    CORRECTION_SALES = "CORRECTION_SALES"


@dataclass(slots=True)
class Invoice:
    invoice_number: str
    issue_date: str
    contractor_id: int
    invoice_type: InvoiceType
    status: InvoiceStatus
    net_amount: float
    vat_amount: float
    gross_amount: float
    payment_date: str | None = None
    investment_id: int | None = None
    category_id: int | None = None
    payment_status: str = "UNPAID"
    source_file: str | None = None
    file_hash: str | None = None
    id: int | None = None
    created_at: str | None = None
    updated_at: str | None = None
