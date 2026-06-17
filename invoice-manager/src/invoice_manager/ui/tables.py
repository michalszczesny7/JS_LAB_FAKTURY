"""Preparation of invoice data for dashboard metrics and tables."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from invoice_manager.models.invoice import Invoice, InvoiceStatus, InvoiceType

INVOICE_TYPE_LABELS = {
    InvoiceType.COST: "Kosztowa",
    InvoiceType.SALES: "Sprzedażowa",
    InvoiceType.CORRECTION_COST: "Korekta kosztowa",
    InvoiceType.CORRECTION_SALES: "Korekta sprzedażowa",
}

STATUS_LABELS = {
    InvoiceStatus.DRAFT_AI: "Szkic AI",
    InvoiceStatus.DRAFT_MANUAL: "Szkic ręczny",
    InvoiceStatus.NEEDS_REVIEW: "Do weryfikacji",
    InvoiceStatus.APPROVED: "Zatwierdzona",
    InvoiceStatus.REJECTED: "Odrzucona",
    InvoiceStatus.DELETED: "Usunięta",
}

PAYMENT_STATUS_LABELS = {
    "UNPAID": "Niezapłacona",
    "PAID": "Zapłacona",
    "OVERDUE": "Po terminie",
}


def invoice_type_label(invoice_type: InvoiceType) -> str:
    return INVOICE_TYPE_LABELS[invoice_type]


def status_label(status: InvoiceStatus) -> str:
    return STATUS_LABELS[status]


def payment_status_label(status: str) -> str:
    return PAYMENT_STATUS_LABELS.get(status, status)


@dataclass(frozen=True, slots=True)
class DashboardMetrics:
    approved_count: int
    costs: float
    revenue: float
    balance: float
    unpaid_count: int
    overdue_count: int


def calculate_dashboard_metrics(
    invoices: list[Invoice],
    *,
    today: date | None = None,
) -> DashboardMetrics:
    current_date = today or date.today()
    cost_types = {InvoiceType.COST, InvoiceType.CORRECTION_COST}
    sales_types = {InvoiceType.SALES, InvoiceType.CORRECTION_SALES}
    costs = sum(item.gross_amount for item in invoices if item.invoice_type in cost_types)
    revenue = sum(
        item.gross_amount for item in invoices if item.invoice_type in sales_types
    )
    unpaid = [item for item in invoices if item.payment_status != "PAID"]
    overdue = [item for item in unpaid if _is_overdue(item, current_date)]
    return DashboardMetrics(
        approved_count=len(invoices),
        costs=costs,
        revenue=revenue,
        balance=revenue - costs,
        unpaid_count=len(unpaid),
        overdue_count=len(overdue),
    )


def prepare_invoice_rows(
    invoices: list[Invoice],
    contractor_names: dict[int, str],
    investment_names: dict[int, str],
    category_names: dict[int, str],
) -> list[dict[str, object]]:
    """Build display rows with names replacing foreign key identifiers."""

    return [
        {
            "ID": invoice.id,
            "Numer": invoice.invoice_number,
            "Data wystawienia": invoice.issue_date,
            "Termin płatności": invoice.payment_date or "-",
            "Kontrahent": contractor_names.get(invoice.contractor_id, "Nieznany"),
            "Inwestycja": investment_names.get(invoice.investment_id, "Nieznana"),
            "Kategoria": category_names.get(invoice.category_id, "Nieznana"),
            "Typ": invoice_type_label(invoice.invoice_type),
            "Status": status_label(invoice.status),
            "Płatność": payment_status_label(invoice.payment_status),
            "Netto": invoice.net_amount,
            "VAT": invoice.vat_amount,
            "Brutto": invoice.gross_amount,
        }
        for invoice in invoices
    ]


def _is_overdue(invoice: Invoice, current_date: date) -> bool:
    if not invoice.payment_date:
        return False
    try:
        return date.fromisoformat(invoice.payment_date) < current_date
    except ValueError:
        return False


def filter_invoices(
    invoices: list[Invoice],
    *,
    status: object | None = None,
    investment_id: int | None = None,
    contractor_id: int | None = None,
    category_id: int | None = None,
    invoice_type: object | None = None,
) -> list[Invoice]:
    return [
        invoice
        for invoice in invoices
        if (status is None or invoice.status is status)
        and (investment_id is None or invoice.investment_id == investment_id)
        and (contractor_id is None or invoice.contractor_id == contractor_id)
        and (category_id is None or invoice.category_id == category_id)
        and (invoice_type is None or invoice.invoice_type is invoice_type)
    ]
