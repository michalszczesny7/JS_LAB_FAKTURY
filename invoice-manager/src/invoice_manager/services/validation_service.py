"""Aggregation of invoice business validation rules."""

from __future__ import annotations

from dataclasses import dataclass, field

from invoice_manager.models.invoice import Invoice
from invoice_manager.repositories.category_repository import CategoryRepository
from invoice_manager.repositories.contractor_repository import ContractorRepository
from invoice_manager.repositories.investment_repository import InvestmentRepository
from invoice_manager.repositories.invoice_repository import InvoiceRepository
from invoice_manager.validators.amount_validator import validate_amounts
from invoice_manager.validators.date_validator import validate_invoice_dates
from invoice_manager.validators.duplicate_validator import DuplicateValidator
from invoice_manager.validators.invoice_validator import validate_required_fields
from invoice_manager.validators.nip_validator import validate_nip
from invoice_manager.validators.status_validator import validate_status


@dataclass(slots=True)
class ValidationResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.errors

    def add_errors(self, errors: list[str]) -> None:
        for error in errors:
            if error not in self.errors:
                self.errors.append(error)


class ValidationService:
    def __init__(
        self,
        invoice_repository: InvoiceRepository,
        contractor_repository: ContractorRepository | None = None,
        investment_repository: InvestmentRepository | None = None,
        category_repository: CategoryRepository | None = None,
    ) -> None:
        self.invoice_repository = invoice_repository
        self.contractor_repository = contractor_repository
        self.investment_repository = investment_repository
        self.category_repository = category_repository
        self.duplicate_validator = DuplicateValidator(invoice_repository)

    def validate_invoice(
        self,
        invoice: Invoice,
        *,
        allow_duplicate: bool = False,
    ) -> ValidationResult:
        """Run all configured validators and return one combined result."""

        result = ValidationResult()
        result.add_errors(validate_required_fields(invoice))
        result.add_errors(
            validate_invoice_dates(invoice.issue_date, invoice.payment_date)
        )
        result.add_errors(
            validate_amounts(
                invoice.net_amount,
                invoice.vat_amount,
                invoice.gross_amount,
            )
        )

        if not allow_duplicate:
            result.add_errors(self.duplicate_validator.validate(invoice))

        self._validate_related_records(invoice, result)
        result.add_errors(validate_status(invoice.status, result.errors))
        return result

    def _validate_related_records(
        self,
        invoice: Invoice,
        result: ValidationResult,
    ) -> None:
        if self.contractor_repository and isinstance(invoice.contractor_id, int):
            contractor = self.contractor_repository.get_by_id(invoice.contractor_id)
            if contractor is None:
                result.add_errors(["Wybrany kontrahent nie istnieje."])
            elif contractor.nip:
                result.add_errors(validate_nip(contractor.nip))

        if self.investment_repository and isinstance(invoice.investment_id, int):
            if self.investment_repository.get_by_id(invoice.investment_id) is None:
                result.add_errors(["Wybrana inwestycja nie istnieje."])

        if self.category_repository and isinstance(invoice.category_id, int):
            if self.category_repository.get_by_id(invoice.category_id) is None:
                result.add_errors(["Wybrana kategoria nie istnieje."])
