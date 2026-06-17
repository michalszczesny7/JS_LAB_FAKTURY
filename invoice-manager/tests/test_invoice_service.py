"""Integration tests for invoice business workflows."""

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
from invoice_manager.services.invoice_service import (
    InvoiceService,
    InvoiceValidationError,
)
from invoice_manager.services.validation_service import ValidationService


@pytest.fixture
def invoice_context(tmp_path):
    database_path = tmp_path / "service.db"
    initialize_database(database_path, seed_categories=False)

    invoices = InvoiceRepository(database_path)
    contractors = ContractorRepository(database_path)
    investments = InvestmentRepository(database_path)
    categories = CategoryRepository(database_path)

    contractor = contractors.create(
        Contractor("Serwis Testowy", "SUPPLIER", nip="8567346215")
    )
    investment = investments.create(Investment("Budynek A"))
    category = categories.create(Category("Materiały", "COST"))
    validation = ValidationService(invoices, contractors, investments, categories)
    service = InvoiceService(invoices, validation)

    invoice = Invoice(
        invoice_number="FV/SVC/001",
        issue_date="2026-06-17",
        payment_date="2026-07-01",
        contractor_id=contractor.id,
        investment_id=investment.id,
        category_id=category.id,
        invoice_type=InvoiceType.COST,
        status=InvoiceStatus.DRAFT_MANUAL,
        net_amount=200.0,
        vat_amount=46.0,
        gross_amount=246.0,
    )
    return service, invoices, invoice


def test_service_creates_draft_invoice(invoice_context):
    service, _, invoice = invoice_context
    created = service.create_invoice(invoice)
    assert created.id is not None
    assert created.status is InvoiceStatus.DRAFT_MANUAL


def test_service_approves_valid_invoice(invoice_context):
    service, _, invoice = invoice_context
    created = service.create_invoice(invoice)
    approved = service.approve_invoice(created.id)
    assert approved.status is InvoiceStatus.APPROVED
    assert service.list_approved_invoices() == [approved]


def test_service_does_not_approve_invalid_invoice(invoice_context):
    service, repository, invoice = invoice_context
    invalid = replace(invoice, gross_amount=999.0)
    saved = repository.create(invalid)

    with pytest.raises(InvoiceValidationError) as error:
        service.approve_invoice(saved.id)

    assert any("netto i VAT" in message for message in error.value.result.errors)
    unchanged = repository.get_by_id(saved.id)
    assert unchanged is not None
    assert unchanged.status is InvoiceStatus.DRAFT_MANUAL


def test_soft_delete_changes_invoice_status(invoice_context):
    service, repository, invoice = invoice_context
    created = service.create_invoice(invoice)
    assert service.soft_delete_invoice(created.id) is True

    deleted = repository.get_by_id(created.id)
    assert deleted is not None
    assert deleted.status is InvoiceStatus.DELETED
    assert service.list_invoices_by_status(InvoiceStatus.DELETED) == [deleted]
