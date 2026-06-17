"""Tests for periodic reports and filtered exports."""

from __future__ import annotations

from datetime import date
from io import BytesIO

import pytest

from invoice_manager.db.init_db import initialize_database
from invoice_manager.exporters import export_report_csv, export_report_xlsx
from invoice_manager.models.category import Category
from invoice_manager.models.contractor import Contractor
from invoice_manager.models.investment import Investment
from invoice_manager.models.invoice import Invoice, InvoiceStatus, InvoiceType
from invoice_manager.repositories.category_repository import CategoryRepository
from invoice_manager.repositories.contractor_repository import ContractorRepository
from invoice_manager.repositories.investment_repository import InvestmentRepository
from invoice_manager.repositories.invoice_repository import InvoiceRepository
from invoice_manager.services.lookup_service import LookupService
from invoice_manager.services.report_service import ReportFilters, ReportService


@pytest.fixture
def report_context(tmp_path):
    database_path = tmp_path / "reports.db"
    initialize_database(database_path, seed_categories=False)
    invoices = InvoiceRepository(database_path)
    contractors = ContractorRepository(database_path)
    investments = InvestmentRepository(database_path)
    categories = CategoryRepository(database_path)

    contractor_a = contractors.create(Contractor("Firma A", "SUPPLIER"))
    contractor_b = contractors.create(Contractor("Firma B", "SUPPLIER"))
    investment_a = investments.create(Investment("Projekt A"))
    investment_b = investments.create(Investment("Projekt B"))
    category = categories.create(Category("Materiały", "COST"))

    def add_invoice(
        number: str,
        issue_date: str,
        contractor_id: int,
        investment_id: int,
        status: InvoiceStatus,
        net: float,
    ) -> Invoice:
        vat = net * 0.23
        return invoices.create(
            Invoice(
                invoice_number=number,
                issue_date=issue_date,
                payment_date=issue_date,
                contractor_id=contractor_id,
                investment_id=investment_id,
                category_id=category.id,
                invoice_type=InvoiceType.COST,
                status=status,
                net_amount=net,
                vat_amount=vat,
                gross_amount=net + vat,
                payment_status="PAID" if status is InvoiceStatus.APPROVED else "UNPAID",
            )
        )

    add_invoice(
        "FV/1", "2026-01-15", contractor_a.id, investment_a.id, InvoiceStatus.APPROVED, 100.0
    )
    add_invoice(
        "FV/2", "2026-02-10", contractor_b.id, investment_b.id, InvoiceStatus.REJECTED, 200.0
    )
    add_invoice(
        "FV/3", "2026-02-20", contractor_a.id, investment_b.id, InvoiceStatus.DELETED, 50.0
    )

    lookup = LookupService(contractors, investments, categories)
    service = ReportService(invoices, lookup)
    return service, contractor_a, contractor_b, investment_a, investment_b


def test_report_filters_by_date_range(report_context):
    service, *_ = report_context
    report = service.generate(
        ReportFilters(
            date_from=date(2026, 2, 1),
            date_to=date(2026, 2, 28),
            include_deleted=True,
        )
    )
    assert [row.invoice_number for row in report.invoices] == ["FV/3", "FV/2"]


def test_report_filters_by_contractor(report_context):
    service, contractor_a, *_ = report_context
    report = service.generate(
        ReportFilters(contractor_id=contractor_a.id, include_deleted=True)
    )
    assert {row.invoice_number for row in report.invoices} == {"FV/1", "FV/3"}


def test_report_filters_by_investment(report_context):
    service, _, _, investment_a, _ = report_context
    report = service.generate(ReportFilters(investment_id=investment_a.id))
    assert [row.invoice_number for row in report.invoices] == ["FV/1"]


def test_report_kpis_hide_deleted_by_default(report_context):
    service, *_ = report_context
    report = service.generate()

    assert report.kpis.invoice_count == 2
    assert report.kpis.net_total == pytest.approx(300.0)
    assert report.kpis.vat_total == pytest.approx(69.0)
    assert report.kpis.gross_total == pytest.approx(369.0)
    assert report.kpis.approved_count == 1
    assert report.kpis.rejected_count == 1
    assert report.kpis.deleted_count == 0


def test_monthly_summary(report_context):
    service, *_ = report_context
    report = service.generate(ReportFilters(include_deleted=True))
    assert [(row.name, row.invoice_count) for row in report.monthly] == [
        ("2026-01", 1),
        ("2026-02", 2),
    ]


def test_csv_export_uses_active_filters(report_context):
    service, _, contractor_b, *_ = report_context
    report = service.generate(ReportFilters(contractor_id=contractor_b.id))
    content = export_report_csv(report).decode("utf-8-sig")

    assert "Numer faktury;Data wystawienia" in content
    assert "FV/2" in content
    assert "FV/1" not in content
    assert "Firma B" in content


def test_xlsx_export_contains_all_sheets_and_numeric_amounts(report_context):
    openpyxl = pytest.importorskip("openpyxl")
    service, _, contractor_b, *_ = report_context
    report = service.generate(ReportFilters(contractor_id=contractor_b.id))
    workbook = openpyxl.load_workbook(BytesIO(export_report_xlsx(report)))

    assert workbook.sheetnames == [
        "Faktury",
        "Podsumowanie",
        "Według inwestycji",
        "Według kontrahentów",
        "Miesięcznie",
        "Według statusu",
    ]
    invoices_sheet = workbook["Faktury"]
    assert invoices_sheet["B2"].value == "FV/2"
    assert invoices_sheet["C2"].is_date
    assert isinstance(invoices_sheet["K2"].value, (int, float))
    assert invoices_sheet.freeze_panes == "A2"
    assert len(workbook["Podsumowanie"]._charts) == 1
