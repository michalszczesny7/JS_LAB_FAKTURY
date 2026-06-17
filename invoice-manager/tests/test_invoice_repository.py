"""Integration tests for the SQLite invoice repository."""

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


@pytest.fixture
def database_path(tmp_path):
    path = tmp_path / "test_invoices.db"
    initialize_database(path, seed_categories=False)
    return path


def test_invoice_repository_full_lifecycle(database_path):
    contractors = ContractorRepository(database_path)
    investments = InvestmentRepository(database_path)
    categories = CategoryRepository(database_path)
    invoices = InvoiceRepository(database_path)

    contractor = contractors.create(
        Contractor(
            name="Bud-Mat Sp. z o.o.",
            nip="5250001009",
            contractor_type="SUPPLIER",
        )
    )
    investment = investments.create(
        Investment(
            name="Osiedle Słoneczne",
            location="Warszawa",
            start_date="2026-01-10",
            planned_end_date="2027-06-30",
            budget=5_000_000.0,
        )
    )
    category = categories.create(
        Category(name="materiały testowe", category_type="COST")
    )

    assert contractor.id is not None
    assert investment.id is not None
    assert category.id is not None

    created = invoices.create(
        Invoice(
            invoice_number="FV/06/2026/001",
            issue_date="2026-06-15",
            payment_date="2026-06-29",
            contractor_id=contractor.id,
            investment_id=investment.id,
            category_id=category.id,
            invoice_type=InvoiceType.COST,
            status=InvoiceStatus.DRAFT_MANUAL,
            net_amount=1_000.0,
            vat_amount=230.0,
            gross_amount=1_230.0,
            source_file="invoice-001.pdf",
            file_hash="test-hash-001",
        )
    )

    assert created.id is not None
    fetched = invoices.get_by_id(created.id)
    assert fetched == created
    assert invoices.find_by_status(InvoiceStatus.DRAFT_MANUAL) == [created]
    assert invoices.find_by_investment(investment.id) == [created]

    updated = invoices.update(
        replace(
            created,
            status=InvoiceStatus.APPROVED,
            payment_status="PAID",
        )
    )
    assert updated.status is InvoiceStatus.APPROVED
    assert updated.payment_status == "PAID"

    duplicate = invoices.find_duplicate(
        invoice_number=updated.invoice_number,
        contractor_id=contractor.id,
    )
    assert duplicate is not None
    assert duplicate.id == updated.id

    assert invoices.soft_delete(updated.id) is True
    deleted = invoices.get_by_id(updated.id)
    assert deleted is not None
    assert deleted.status is InvoiceStatus.DELETED
    assert invoices.list_all() == []
    assert invoices.list_all(include_deleted=True) == [deleted]
    assert (
        invoices.find_duplicate(
            invoice_number=updated.invoice_number,
            contractor_id=contractor.id,
        )
        is None
    )
