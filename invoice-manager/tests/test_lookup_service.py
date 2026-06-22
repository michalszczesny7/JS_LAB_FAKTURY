"""Integration tests for safe lookup-data deletion."""

from __future__ import annotations

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
from invoice_manager.services.lookup_service import LookupInUseError, LookupService


def test_only_unused_contractors_and_investments_can_be_deleted(tmp_path):
    database_path = tmp_path / "lookups.db"
    initialize_database(database_path, seed_categories=False)
    contractors = ContractorRepository(database_path)
    investments = InvestmentRepository(database_path)
    categories = CategoryRepository(database_path)
    invoices = InvoiceRepository(database_path)
    service = LookupService(contractors, investments, categories, invoices)

    used_contractor = contractors.create(Contractor("Używany", "SUPPLIER"))
    unused_contractor = contractors.create(Contractor("Nieużywany", "SUPPLIER"))
    used_investment = investments.create(Investment("Używana inwestycja"))
    unused_investment = investments.create(Investment("Nieużywana inwestycja"))
    category = categories.create(Category("Materiały", "COST"))
    invoice = invoices.create(
        Invoice(
            invoice_number="FV/LOOKUP/1",
            issue_date="2026-06-22",
            contractor_id=used_contractor.id,
            investment_id=used_investment.id,
            category_id=category.id,
            invoice_type=InvoiceType.COST,
            status=InvoiceStatus.DRAFT_MANUAL,
            net_amount=100.0,
            vat_amount=23.0,
            gross_amount=123.0,
        )
    )
    invoices.soft_delete(invoice.id)

    assert service.delete_contractor(unused_contractor.id) is True
    assert service.delete_investment(unused_investment.id) is True
    assert contractors.get_by_id(unused_contractor.id) is None
    assert investments.get_by_id(unused_investment.id) is None

    with pytest.raises(LookupInUseError, match="1 fakturami"):
        service.delete_contractor(used_contractor.id)
    with pytest.raises(LookupInUseError, match="1 fakturami"):
        service.delete_investment(used_investment.id)

    assert contractors.get_by_id(used_contractor.id) is not None
    assert investments.get_by_id(used_investment.id) is not None
