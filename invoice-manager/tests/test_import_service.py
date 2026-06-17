"""Tests for CSV/XLSX invoice import analysis and execution."""

from __future__ import annotations

from datetime import date

import pytest

from invoice_manager.db.init_db import initialize_database
from invoice_manager.importers.mapping import (
    suggest_column_mapping,
    validate_column_mapping,
)
from invoice_manager.importers.parsers import parse_amount, parse_date
from invoice_manager.importers.readers import ImportedTable, read_import_file
from invoice_manager.models.category import Category
from invoice_manager.models.contractor import Contractor
from invoice_manager.models.investment import Investment
from invoice_manager.models.invoice import Invoice, InvoiceStatus, InvoiceType
from invoice_manager.repositories.category_repository import CategoryRepository
from invoice_manager.repositories.contractor_repository import ContractorRepository
from invoice_manager.repositories.investment_repository import InvestmentRepository
from invoice_manager.repositories.invoice_repository import InvoiceRepository
from invoice_manager.services.import_service import ImportService
from invoice_manager.services.invoice_service import InvoiceService
from invoice_manager.services.validation_service import ValidationService

HEADERS = [
    "nr faktury",
    "kontrahent",
    "inwestycja",
    "data",
    "termin płatności",
    "netto",
    "vat",
    "brutto",
]


def row(
    number: str,
    contractor: str = "Nowy Dostawca",
    investment: str = "Nowy Projekt",
    issue_date: object = "2026-06-17",
    net: object = "100,00",
    vat: object = "23,00",
    gross: object = "123,00",
) -> dict[str, object]:
    return {
        "nr faktury": number,
        "kontrahent": contractor,
        "inwestycja": investment,
        "data": issue_date,
        "termin płatności": "2026-07-01",
        "netto": net,
        "vat": vat,
        "brutto": gross,
    }


@pytest.fixture
def import_context(tmp_path):
    database_path = tmp_path / "import.db"
    initialize_database(database_path, seed_categories=False)
    invoices = InvoiceRepository(database_path)
    contractors = ContractorRepository(database_path)
    investments = InvestmentRepository(database_path)
    categories = CategoryRepository(database_path)
    category = categories.create(Category("Materiały", "COST"))
    validation = ValidationService(invoices, contractors, investments, categories)
    invoice_service = InvoiceService(invoices, validation)
    service = ImportService(
        invoices,
        contractors,
        investments,
        categories,
        invoice_service,
    )
    return service, invoices, contractors, investments, category, invoice_service


def standard_mapping() -> dict[str, str | None]:
    return suggest_column_mapping(HEADERS)


def test_required_column_mapping_is_validated():
    mapping = standard_mapping()
    mapping["contractor"] = None
    mapping["net_amount"] = None
    mapping["gross_amount"] = None

    errors = validate_column_mapping(mapping)
    assert any("Kontrahent" in error for error in errors)
    assert any("netto albo" in error for error in errors)


def test_amount_and_date_parsers_accept_common_polish_formats():
    assert parse_amount("1 234,56 zł") == 1234.56
    assert parse_amount("1,234.56 PLN") == 1234.56
    assert parse_date("17.06.2026") == "2026-06-17"
    assert parse_date(date(2026, 6, 17)) == "2026-06-17"
    with pytest.raises(ValueError):
        parse_amount("brak")
    with pytest.raises(ValueError):
        parse_date("31.02.2026")


def test_csv_reader_and_automatic_mapping():
    content = (
        "nr faktury;kontrahent;inwestycja;data;netto;brutto\n"
        "FV/1;Firma A;Projekt A;2026-06-17;100,00;100,00\n"
    ).encode("utf-8")
    table = read_import_file(content, "faktury.csv")
    mapping = suggest_column_mapping(table.headers)

    assert len(table.rows) == 1
    assert mapping["invoice_number"] == "nr faktury"
    assert mapping["gross_amount"] == "brutto"


def test_duplicate_inside_file_is_detected(import_context):
    service, _, _, _, category, _ = import_context
    table = ImportedTable(HEADERS, [row("FV/1"), row("FV/1")])

    preview = service.analyze(
        table,
        standard_mapping(),
        default_category_id=category.id,
    )

    assert preview.valid_rows == 1
    assert preview.duplicate_rows == 1
    assert preview.rows[1].duplicate_kind == "FILE"


def test_duplicate_against_database_is_detected(import_context):
    service, _, contractors, investments, category, invoice_service = import_context
    contractor = contractors.create(Contractor("Firma A", "SUPPLIER"))
    investment = investments.create(Investment("Projekt A"))
    invoice_service.create_invoice(
        Invoice(
            invoice_number="FV/DB/1",
            issue_date="2026-06-17",
            contractor_id=contractor.id,
            investment_id=investment.id,
            category_id=category.id,
            invoice_type=InvoiceType.COST,
            status=InvoiceStatus.DRAFT_MANUAL,
            net_amount=100.0,
            vat_amount=23.0,
            gross_amount=123.0,
        )
    )
    table = ImportedTable(
        HEADERS,
        [row("FV/DB/1", contractor="Firma A", investment="Projekt A")],
    )

    preview = service.analyze(
        table,
        standard_mapping(),
        default_category_id=category.id,
    )

    assert preview.duplicate_rows == 1
    assert preview.rows[0].duplicate_kind == "DATABASE"


def test_import_report_counts_imported_errors_and_duplicates(import_context):
    service, invoices, contractors, investments, category, _ = import_context
    table = ImportedTable(
        HEADERS,
        [
            row("FV/OK/1"),
            row("FV/OK/1"),
            row("FV/BAD/1", issue_date="31.02.2026"),
            row("FV/BAD/2", net="-100", vat="0", gross="-100"),
        ],
    )
    preview = service.analyze(
        table,
        standard_mapping(),
        default_category_id=category.id,
    )
    result = service.execute(preview, create_missing_entities=True)

    assert result.total_rows == 4
    assert result.valid_rows == 1
    assert result.imported_rows == 1
    assert result.skipped_rows == 3
    assert result.error_rows == 2
    assert result.duplicate_rows == 1
    assert len(result.errors) >= 2
    assert result.warnings
    assert len(invoices.list_all()) == 1
    assert len(contractors.list_all()) == 1
    assert len(investments.list_all()) == 1
