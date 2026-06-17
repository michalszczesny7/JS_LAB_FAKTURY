"""Integration tests for aggregated invoice validation."""

from dataclasses import replace

import pytest

from invoice_manager.db.init_db import initialize_database
from invoice_manager.models.category import Category
from invoice_manager.models.contractor import Contractor
from invoice_manager.models.investment import Investment
from invoice_manager.models.invoice import Invoice, InvoiceStatus, InvoiceType
from invoice_manager.repositories.category_repository import CategoryRepository
from invoice_manager.repositories.contractor_repository import ContractorRepository
from invoice_manager.repositories.investment_repository import InvestmentRepository
from invoice_manager.repositories.invoice_repository import InvoiceRepository
from invoice_manager.services.validation_service import ValidationService


@pytest.fixture
def validation_context(tmp_path):
    database_path = tmp_path / "validation.db"
    initialize_database(database_path, seed_categories=False)

    invoice_repository = InvoiceRepository(database_path)
    contractor_repository = ContractorRepository(database_path)
    investment_repository = InvestmentRepository(database_path)
    category_repository = CategoryRepository(database_path)

    contractor = contractor_repository.create(
        Contractor("Dobra Firma", "SUPPLIER", nip="8567346215")
    )
    investment = investment_repository.create(Investment("Inwestycja testowa"))
    category = category_repository.create(Category("Testowa", "COST"))

    service = ValidationService(
        invoice_repository,
        contractor_repository,
        investment_repository,
        category_repository,
    )
    invoice = Invoice(
        invoice_number="FV/VAL/001",
        issue_date="2026-06-17",
        payment_date="2026-07-01",
        contractor_id=contractor.id,
        investment_id=investment.id,
        category_id=category.id,
        invoice_type=InvoiceType.COST,
        status=InvoiceStatus.DRAFT_MANUAL,
        net_amount=100.0,
        vat_amount=23.0,
        gross_amount=123.0,
    )
    return service, invoice, invoice_repository


def test_valid_invoice_passes_aggregated_validation(validation_context):
    service, invoice, _ = validation_context
    result = service.validate_invoice(invoice)
    assert result.is_valid is True
    assert result.errors == []
    assert result.warnings == []


def test_missing_required_fields_fail_validation(validation_context):
    service, invoice, _ = validation_context
    invalid = replace(
        invoice,
        invoice_number="",
        issue_date="",
        investment_id=None,
        category_id=None,
        gross_amount=None,
    )
    result = service.validate_invoice(invalid)
    assert result.is_valid is False
    assert any("Numer faktury" in error for error in result.errors)
    assert any("Inwestycja" in error for error in result.errors)
    assert any("Kategoria" in error for error in result.errors)
    assert any("Kwota brutto" in error for error in result.errors)


def test_duplicate_invoice_fails_but_current_invoice_is_excluded(validation_context):
    service, invoice, repository = validation_context
    saved = repository.create(invoice)

    duplicate_result = service.validate_invoice(replace(invoice, id=None))
    assert duplicate_result.is_valid is False
    assert any("już istnieje" in error for error in duplicate_result.errors)

    update_result = service.validate_invoice(saved)
    assert update_result.is_valid is True
