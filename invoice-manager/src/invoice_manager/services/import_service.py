"""Analyze and import invoices from mapped tabular data."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from invoice_manager.importers.mapping import (
    suggest_column_mapping,
    validate_column_mapping,
)
from invoice_manager.importers.parsers import (
    normalize_invoice_number,
    normalize_name,
    normalize_name_key,
    parse_amount,
    parse_date,
)
from invoice_manager.importers.readers import ImportedTable, read_import_file
from invoice_manager.models.contractor import Contractor
from invoice_manager.models.import_result import (
    ImportPreview,
    ImportResult,
    ImportRowAnalysis,
)
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
from invoice_manager.validators.amount_validator import validate_amounts
from invoice_manager.validators.date_validator import validate_invoice_dates

INVOICE_TYPE_ALIASES = {
    "KOSZTOWA": InvoiceType.COST,
    "KOSZT": InvoiceType.COST,
    "SPRZEDAZOWA": InvoiceType.SALES,
    "SPRZEDAŻOWA": InvoiceType.SALES,
    "SPRZEDAZ": InvoiceType.SALES,
    "SPRZEDAŻ": InvoiceType.SALES,
}


class ImportService:
    def __init__(
        self,
        invoice_repository: InvoiceRepository,
        contractor_repository: ContractorRepository,
        investment_repository: InvestmentRepository,
        category_repository: CategoryRepository,
        invoice_service: InvoiceService,
    ) -> None:
        self.invoice_repository = invoice_repository
        self.contractor_repository = contractor_repository
        self.investment_repository = investment_repository
        self.category_repository = category_repository
        self.invoice_service = invoice_service

    def read_file(self, content: bytes, filename: str) -> ImportedTable:
        return read_import_file(content, filename)

    def suggest_mapping(self, headers: list[str]) -> dict[str, str | None]:
        return suggest_column_mapping(headers)

    def analyze(
        self,
        table: ImportedTable,
        mapping: dict[str, str | None],
        *,
        default_category_id: int,
        default_invoice_type: InvoiceType = InvoiceType.COST,
        default_status: InvoiceStatus = InvoiceStatus.DRAFT_MANUAL,
        source_file: str | None = None,
    ) -> ImportPreview:
        mapping_errors = validate_column_mapping(mapping)
        preview = ImportPreview(
            headers=table.headers,
            source_rows=table.rows,
            mapping=mapping,
            mapping_errors=mapping_errors,
        )
        if mapping_errors:
            return preview

        contractors = self._entities_by_name(self.contractor_repository.list_all())
        investments = self._entities_by_name(self.investment_repository.list_all())
        categories = self._entities_by_name(self.category_repository.list_all())
        category_ids = {
            item.id for item in self.category_repository.list_all() if item.id is not None
        }
        seen: dict[tuple[str, str], int] = {}

        for offset, source in enumerate(table.rows, start=2):
            row = ImportRowAnalysis(row_number=offset, source=source)
            self._parse_row(
                row,
                mapping,
                contractors=contractors,
                investments=investments,
                categories=categories,
                category_ids=category_ids,
                default_category_id=default_category_id,
                default_invoice_type=default_invoice_type,
                default_status=default_status,
                source_file=source_file,
            )
            self._detect_duplicate(row, seen)
            preview.rows.append(row)
        return preview

    def execute(
        self,
        preview: ImportPreview,
        *,
        create_missing_entities: bool = False,
    ) -> ImportResult:
        if preview.mapping_errors:
            return ImportResult(
                total_rows=preview.total_rows,
                skipped_rows=preview.total_rows,
                error_rows=preview.total_rows,
                errors=preview.mapping_errors.copy(),
            )

        result = ImportResult(
            total_rows=preview.total_rows,
            valid_rows=preview.valid_rows,
            duplicate_rows=preview.duplicate_rows,
        )
        contractors = self._entities_by_name(self.contractor_repository.list_all())
        investments = self._entities_by_name(self.investment_repository.list_all())

        for row in preview.rows:
            result.warnings.extend(
                f"Wiersz {row.row_number}: {warning}" for warning in row.warnings
            )
            if row.duplicate_kind:
                continue
            if row.errors:
                result.errors.extend(
                    f"Wiersz {row.row_number}: {error}" for error in row.errors
                )
                continue

            contractor = contractors.get(str(row.values["contractor_key"]))
            investment = investments.get(str(row.values["investment_key"]))
            if contractor is None and create_missing_entities:
                contractor = self.contractor_repository.create(
                    Contractor(
                        name=str(row.values["contractor_name"]),
                        contractor_type="SUPPLIER",
                    )
                )
                contractors[str(row.values["contractor_key"])] = contractor
            if investment is None and create_missing_entities:
                investment = self.investment_repository.create(
                    Investment(name=str(row.values["investment_name"]))
                )
                investments[str(row.values["investment_key"])] = investment

            if contractor is None or investment is None:
                missing = []
                if contractor is None:
                    missing.append("kontrahenta")
                if investment is None:
                    missing.append("inwestycji")
                result.errors.append(
                    f"Wiersz {row.row_number}: nie utworzono brakującego "
                    + " i ".join(missing)
                    + "."
                )
                continue

            duplicate = self.invoice_repository.find_duplicate(
                str(row.values["invoice_number"]), contractor.id
            )
            if duplicate is not None:
                result.duplicate_rows += 1
                continue

            invoice = self._build_invoice(row, contractor.id, investment.id)
            try:
                created = self.invoice_service.create_invoice(
                    invoice,
                    approve=invoice.status is InvoiceStatus.APPROVED,
                )
            except InvoiceValidationError as error:
                result.errors.extend(
                    f"Wiersz {row.row_number}: {message}"
                    for message in error.result.errors
                )
                continue
            if created.id is not None:
                result.imported_invoice_ids.append(created.id)
            result.imported_rows += 1

        result.error_rows = len(
            {
                int(error.split(":", 1)[0].replace("Wiersz ", ""))
                for error in result.errors
                if error.startswith("Wiersz ")
            }
        )
        result.skipped_rows = result.total_rows - result.imported_rows
        return result

    def _parse_row(
        self,
        row: ImportRowAnalysis,
        mapping: dict[str, str | None],
        *,
        contractors: dict[str, object],
        investments: dict[str, object],
        categories: dict[str, object],
        category_ids: set[int],
        default_category_id: int,
        default_invoice_type: InvoiceType,
        default_status: InvoiceStatus,
        source_file: str | None,
    ) -> None:
        value = lambda field: row.source.get(mapping[field]) if mapping.get(field) else None
        invoice_number = normalize_invoice_number(value("invoice_number"))
        contractor_name = normalize_name(value("contractor"))
        investment_name = normalize_name(value("investment"))
        if not invoice_number:
            row.errors.append("Numer faktury jest wymagany.")
        if not contractor_name:
            row.errors.append("Kontrahent jest wymagany.")
        if not investment_name:
            row.errors.append("Inwestycja jest wymagana.")

        issue_date = self._parse_value(row, "data faktury", parse_date, value("issue_date"), True)
        payment_date = self._parse_value(
            row, "termin płatności", parse_date, value("payment_date"), False
        )
        net_amount = self._parse_value(
            row, "kwota netto", parse_amount, value("net_amount"), False
        )
        vat_amount = self._parse_value(
            row, "kwota VAT", parse_amount, value("vat_amount"), False
        )
        gross_amount = self._parse_value(
            row, "kwota brutto", parse_amount, value("gross_amount"), False
        )
        vat_amount = 0.0 if vat_amount is None else vat_amount
        if net_amount is None and gross_amount is None:
            row.errors.append("Kwota netto lub brutto jest wymagana.")
        elif net_amount is None:
            net_amount = gross_amount - vat_amount
        elif gross_amount is None:
            gross_amount = net_amount + vat_amount

        if net_amount is not None and gross_amount is not None:
            row.errors.extend(validate_amounts(net_amount, vat_amount, gross_amount))
        if issue_date is not None:
            row.errors.extend(validate_invoice_dates(issue_date, payment_date))

        contractor_key = normalize_name_key(contractor_name)
        investment_key = normalize_name_key(investment_name)
        if contractor_key and contractor_key not in contractors:
            row.warnings.append(
                f"Nieznany kontrahent: {contractor_name}. Może zostać utworzony automatycznie."
            )
        if investment_key and investment_key not in investments:
            row.warnings.append(
                f"Nieznana inwestycja: {investment_name}. Może zostać utworzona automatycznie."
            )

        category_id = default_category_id
        category_name = normalize_name(value("category"))
        if category_name:
            category = categories.get(normalize_name_key(category_name))
            if category is None:
                row.errors.append(f"Nieznana kategoria: {category_name}.")
            else:
                category_id = category.id
        if category_id not in category_ids:
            row.errors.append("Domyślna kategoria nie istnieje.")

        invoice_type = self._parse_invoice_type(
            row, value("invoice_type"), default_invoice_type
        )
        status = self._parse_status(row, value("status"), default_status)
        payment_status = normalize_invoice_number(value("payment_status")) or "UNPAID"

        row.values.update(
            invoice_number=invoice_number,
            contractor_name=contractor_name,
            contractor_key=contractor_key,
            contractor_id=getattr(contractors.get(contractor_key), "id", None),
            investment_name=investment_name,
            investment_key=investment_key,
            investment_id=getattr(investments.get(investment_key), "id", None),
            category_id=category_id,
            issue_date=issue_date,
            payment_date=payment_date,
            net_amount=net_amount,
            vat_amount=vat_amount,
            gross_amount=gross_amount,
            invoice_type=invoice_type,
            status=status,
            payment_status=payment_status,
            source_file=Path(source_file).name if source_file else None,
        )

    def _detect_duplicate(
        self,
        row: ImportRowAnalysis,
        seen: dict[tuple[str, str], int],
    ) -> None:
        invoice_number = str(row.values.get("invoice_number") or "")
        contractor_key = str(row.values.get("contractor_key") or "")
        if not invoice_number or not contractor_key:
            return
        key = (invoice_number, contractor_key)
        if key in seen:
            row.duplicate_kind = "FILE"
            row.warnings.append(
                f"Duplikat w pliku; pierwszy wpis znajduje się w wierszu {seen[key]}."
            )
            return
        seen[key] = row.row_number

        contractor_id = row.values.get("contractor_id")
        if isinstance(contractor_id, int):
            duplicate = self.invoice_repository.find_duplicate(
                invoice_number, contractor_id
            )
            if duplicate is not None:
                row.duplicate_kind = "DATABASE"
                row.warnings.append(
                    f"Duplikat istniejący w bazie danych (id: {duplicate.id})."
                )

    @staticmethod
    def _parse_value(
        row: ImportRowAnalysis,
        label: str,
        parser: object,
        value: object,
        required: bool,
    ) -> object:
        try:
            return parser(value, required=required)
        except ValueError as error:
            row.errors.append(f"{label.capitalize()}: {error}")
            return None

    @staticmethod
    def _entities_by_name(entities: Iterable[object]) -> dict[str, object]:
        return {
            normalize_name_key(getattr(entity, "name")): entity
            for entity in entities
        }

    @staticmethod
    def _parse_invoice_type(
        row: ImportRowAnalysis,
        value: object,
        default: InvoiceType,
    ) -> InvoiceType:
        text = normalize_invoice_number(value)
        if not text:
            return default
        try:
            return InvoiceType(text)
        except ValueError:
            if text in INVOICE_TYPE_ALIASES:
                return INVOICE_TYPE_ALIASES[text]
            row.errors.append(f"Nieprawidłowy typ faktury: {value}.")
            return default

    @staticmethod
    def _parse_status(
        row: ImportRowAnalysis,
        value: object,
        default: InvoiceStatus,
    ) -> InvoiceStatus:
        text = normalize_invoice_number(value)
        if not text:
            return default
        try:
            return InvoiceStatus(text)
        except ValueError:
            row.errors.append(f"Nieprawidłowy status faktury: {value}.")
            return default

    @staticmethod
    def _build_invoice(
        row: ImportRowAnalysis,
        contractor_id: int,
        investment_id: int,
    ) -> Invoice:
        return Invoice(
            invoice_number=str(row.values["invoice_number"]),
            issue_date=str(row.values["issue_date"]),
            payment_date=row.values["payment_date"],
            contractor_id=contractor_id,
            investment_id=investment_id,
            category_id=int(row.values["category_id"]),
            invoice_type=row.values["invoice_type"],
            status=row.values["status"],
            net_amount=float(row.values["net_amount"]),
            vat_amount=float(row.values["vat_amount"]),
            gross_amount=float(row.values["gross_amount"]),
            payment_status=str(row.values["payment_status"]),
            source_file=row.values["source_file"],
        )
