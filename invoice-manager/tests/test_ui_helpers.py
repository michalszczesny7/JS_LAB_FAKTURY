"""Tests for dashboard and invoice table preparation."""

from datetime import date

from invoice_manager.models.invoice import Invoice, InvoiceStatus, InvoiceType
from invoice_manager.ui.forms import calculate_gross_amount
from invoice_manager.ui.tables import (
    calculate_dashboard_metrics,
    filter_invoices,
    prepare_invoice_rows,
)


def test_gross_amount_is_net_plus_vat_rounded_to_currency_precision():
    assert calculate_gross_amount(100.0, 23.0) == 123.0
    assert calculate_gross_amount(10.005, 2.004) == 12.01


def make_invoice(
    invoice_id: int,
    invoice_type: InvoiceType,
    gross_amount: float,
    *,
    payment_status: str = "UNPAID",
    payment_date: str | None = "2026-06-10",
) -> Invoice:
    return Invoice(
        id=invoice_id,
        invoice_number=f"FV/{invoice_id}",
        issue_date="2026-06-01",
        payment_date=payment_date,
        contractor_id=1,
        investment_id=2,
        category_id=3,
        invoice_type=invoice_type,
        status=InvoiceStatus.APPROVED,
        net_amount=gross_amount,
        vat_amount=0.0,
        gross_amount=gross_amount,
        payment_status=payment_status,
    )


def test_dashboard_metrics_separate_costs_and_revenue():
    invoices = [
        make_invoice(1, InvoiceType.COST, 100.0),
        make_invoice(2, InvoiceType.SALES, 250.0, payment_status="PAID"),
    ]
    metrics = calculate_dashboard_metrics(invoices, today=date(2026, 6, 17))

    assert metrics.approved_count == 2
    assert metrics.costs == 100.0
    assert metrics.revenue == 250.0
    assert metrics.balance == 150.0
    assert metrics.unpaid_count == 1
    assert metrics.overdue_count == 1


def test_table_rows_replace_foreign_keys_with_names():
    invoice = make_invoice(1, InvoiceType.COST, 100.0)
    rows = prepare_invoice_rows(
        [invoice],
        contractor_names={1: "Kontrahent A"},
        investment_names={2: "Inwestycja A"},
        category_names={3: "Materiały"},
    )

    assert rows[0]["Kontrahent"] == "Kontrahent A"
    assert rows[0]["Inwestycja"] == "Inwestycja A"
    assert rows[0]["Kategoria"] == "Materiały"


def test_invoice_filters_can_be_combined():
    matching = make_invoice(1, InvoiceType.COST, 100.0)
    other = make_invoice(2, InvoiceType.SALES, 250.0)

    filtered = filter_invoices(
        [matching, other],
        status=InvoiceStatus.APPROVED,
        investment_id=2,
        contractor_id=1,
        category_id=3,
        invoice_type=InvoiceType.COST,
    )

    assert filtered == [matching]
