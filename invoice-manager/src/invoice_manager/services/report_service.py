"""Periodic invoice reports, filtering, and aggregate calculations."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import date

from invoice_manager.models.invoice import InvoiceStatus, InvoiceType
from invoice_manager.repositories.invoice_repository import InvoiceRepository
from invoice_manager.services.lookup_service import LookupService


@dataclass(frozen=True, slots=True)
class ReportFilters:
    date_from: date | None = None
    date_to: date | None = None
    investment_id: int | None = None
    contractor_id: int | None = None
    category_id: int | None = None
    invoice_type: InvoiceType | None = None
    status: InvoiceStatus | None = None
    payment_status: str | None = None
    include_deleted: bool = False


@dataclass(frozen=True, slots=True)
class ReportKpis:
    invoice_count: int
    net_total: float
    vat_total: float
    gross_total: float
    approved_count: int
    rejected_count: int
    deleted_count: int


@dataclass(frozen=True, slots=True)
class ReportInvoiceRow:
    id: int | None
    invoice_number: str
    issue_date: str
    payment_date: str | None
    contractor: str
    investment: str
    category: str
    invoice_type: str
    status: str
    payment_status: str
    net_amount: float
    vat_amount: float
    gross_amount: float
    source_file: str | None

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ReportGroupRow:
    name: str
    invoice_count: int
    net_total: float
    vat_total: float
    gross_total: float

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ReportData:
    filters: ReportFilters
    invoices: list[ReportInvoiceRow]
    kpis: ReportKpis
    by_investment: list[ReportGroupRow]
    by_contractor: list[ReportGroupRow]
    monthly: list[ReportGroupRow]
    by_status: list[ReportGroupRow]


class ReportService:
    def __init__(
        self,
        invoice_repository: InvoiceRepository,
        lookup_service: LookupService,
    ) -> None:
        self.invoice_repository = invoice_repository
        self.lookup_service = lookup_service

    def generate(self, filters: ReportFilters | None = None) -> ReportData:
        filters = filters or ReportFilters()
        if filters.date_from and filters.date_to and filters.date_from > filters.date_to:
            raise ValueError("Data początkowa nie może być późniejsza niż końcowa.")

        invoices = self.invoice_repository.list_all(
            include_deleted=filters.include_deleted
        )
        filtered = [invoice for invoice in invoices if self._matches(invoice, filters)]
        contractor_names = self.lookup_service.contractor_names()
        investment_names = self.lookup_service.investment_names()
        category_names = self.lookup_service.category_names()

        rows = [
            ReportInvoiceRow(
                id=invoice.id,
                invoice_number=invoice.invoice_number,
                issue_date=invoice.issue_date,
                payment_date=invoice.payment_date,
                contractor=contractor_names.get(invoice.contractor_id, "Nieznany"),
                investment=investment_names.get(invoice.investment_id, "Nieznana"),
                category=category_names.get(invoice.category_id, "Nieznana"),
                invoice_type=invoice.invoice_type.value,
                status=invoice.status.value,
                payment_status=invoice.payment_status,
                net_amount=invoice.net_amount,
                vat_amount=invoice.vat_amount,
                gross_amount=invoice.gross_amount,
                source_file=invoice.source_file,
            )
            for invoice in filtered
        ]
        kpis = ReportKpis(
            invoice_count=len(filtered),
            net_total=sum(invoice.net_amount for invoice in filtered),
            vat_total=sum(invoice.vat_amount for invoice in filtered),
            gross_total=sum(invoice.gross_amount for invoice in filtered),
            approved_count=sum(
                invoice.status is InvoiceStatus.APPROVED for invoice in filtered
            ),
            rejected_count=sum(
                invoice.status is InvoiceStatus.REJECTED for invoice in filtered
            ),
            deleted_count=sum(
                invoice.status is InvoiceStatus.DELETED for invoice in filtered
            ),
        )
        return ReportData(
            filters=filters,
            invoices=rows,
            kpis=kpis,
            by_investment=self._group(
                rows, lambda row: row.investment, chronological=False
            ),
            by_contractor=self._group(
                rows, lambda row: row.contractor, chronological=False
            ),
            monthly=self._group(
                rows, lambda row: row.issue_date[:7], chronological=True
            ),
            by_status=self._group(rows, lambda row: row.status, chronological=False),
        )

    @staticmethod
    def _matches(invoice: object, filters: ReportFilters) -> bool:
        try:
            issue_date = date.fromisoformat(invoice.issue_date)
        except ValueError:
            return False
        return (
            (filters.date_from is None or issue_date >= filters.date_from)
            and (filters.date_to is None or issue_date <= filters.date_to)
            and (
                filters.investment_id is None
                or invoice.investment_id == filters.investment_id
            )
            and (
                filters.contractor_id is None
                or invoice.contractor_id == filters.contractor_id
            )
            and (
                filters.category_id is None
                or invoice.category_id == filters.category_id
            )
            and (
                filters.invoice_type is None
                or invoice.invoice_type is filters.invoice_type
            )
            and (filters.status is None or invoice.status is filters.status)
            and (
                filters.payment_status is None
                or invoice.payment_status == filters.payment_status
            )
        )

    @staticmethod
    def _group(
        rows: list[ReportInvoiceRow],
        key_function: object,
        *,
        chronological: bool,
    ) -> list[ReportGroupRow]:
        grouped: dict[str, list[ReportInvoiceRow]] = defaultdict(list)
        for row in rows:
            grouped[key_function(row)].append(row)
        result = [
            ReportGroupRow(
                name=name,
                invoice_count=len(items),
                net_total=sum(item.net_amount for item in items),
                vat_total=sum(item.vat_amount for item in items),
                gross_total=sum(item.gross_amount for item in items),
            )
            for name, items in grouped.items()
        ]
        if chronological:
            return sorted(result, key=lambda item: item.name)
        return sorted(result, key=lambda item: (-item.gross_total, item.name.casefold()))
