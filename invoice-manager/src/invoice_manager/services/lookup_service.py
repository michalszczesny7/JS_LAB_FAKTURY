"""Lookup data used by invoice forms and tables."""

from __future__ import annotations

from invoice_manager.models.category import Category
from invoice_manager.models.contractor import Contractor
from invoice_manager.models.investment import Investment
from invoice_manager.repositories.category_repository import CategoryRepository
from invoice_manager.repositories.contractor_repository import ContractorRepository
from invoice_manager.repositories.investment_repository import InvestmentRepository
from invoice_manager.repositories.invoice_repository import InvoiceRepository


class LookupInUseError(LookupError):
    """Raised when lookup data is still referenced by invoices."""


class LookupService:
    def __init__(
        self,
        contractor_repository: ContractorRepository,
        investment_repository: InvestmentRepository,
        category_repository: CategoryRepository,
        invoice_repository: InvoiceRepository | None = None,
    ) -> None:
        self.contractor_repository = contractor_repository
        self.investment_repository = investment_repository
        self.category_repository = category_repository
        self.invoice_repository = invoice_repository

    def list_contractors(self) -> list[Contractor]:
        return self.contractor_repository.list_all()

    def list_investments(self) -> list[Investment]:
        return self.investment_repository.list_all()

    def list_categories(self) -> list[Category]:
        return self.category_repository.list_all()

    def create_contractor(self, contractor: Contractor) -> Contractor:
        return self.contractor_repository.create(contractor)

    def create_investment(self, investment: Investment) -> Investment:
        return self.investment_repository.create(investment)

    def delete_contractor(self, contractor_id: int) -> bool:
        if self.contractor_repository.get_by_id(contractor_id) is None:
            raise LookupError(f"Kontrahent {contractor_id} nie istnieje.")
        linked_count = (
            self.invoice_repository.count_by_contractor(contractor_id)
            if self.invoice_repository is not None
            else 0
        )
        if linked_count:
            raise LookupInUseError(
                "Nie można usunąć kontrahenta — jest powiązany z "
                f"{linked_count} fakturami."
            )
        return self.contractor_repository.delete(contractor_id)

    def delete_investment(self, investment_id: int) -> bool:
        if self.investment_repository.get_by_id(investment_id) is None:
            raise LookupError(f"Inwestycja {investment_id} nie istnieje.")
        linked_count = (
            self.invoice_repository.count_by_investment(investment_id)
            if self.invoice_repository is not None
            else 0
        )
        if linked_count:
            raise LookupInUseError(
                "Nie można usunąć inwestycji — jest powiązana z "
                f"{linked_count} fakturami."
            )
        return self.investment_repository.delete(investment_id)

    def contractor_names(self) -> dict[int, str]:
        return {
            item.id: item.name
            for item in self.list_contractors()
            if item.id is not None
        }

    def investment_names(self) -> dict[int, str]:
        return {
            item.id: item.name
            for item in self.list_investments()
            if item.id is not None
        }

    def category_names(self) -> dict[int, str]:
        return {
            item.id: item.name
            for item in self.list_categories()
            if item.id is not None
        }
