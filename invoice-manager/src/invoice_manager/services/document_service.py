"""Secure PDF upload, analysis, and verified invoice persistence."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass, field, replace
from pathlib import Path

from invoice_manager.config import (
    MAX_PDF_SIZE_BYTES,
    PDF_UPLOAD_DIR,
    PROJECT_ROOT,
)
from invoice_manager.documents.field_extractor import (
    ExtractedInvoiceFields,
    extract_invoice_fields,
)
from invoice_manager.documents.pdf_reader import PdfTextResult, extract_text_from_pdf
from invoice_manager.models.invoice import Invoice, InvoiceStatus
from invoice_manager.repositories.invoice_repository import InvoiceRepository
from invoice_manager.services.invoice_service import InvoiceService

ACCEPTED_PDF_MIME_TYPES = {"application/pdf", "application/x-pdf", ""}


class DocumentValidationError(ValueError):
    """Raised when an uploaded document violates PDF safety rules."""


class DuplicateDocumentError(ValueError):
    """Raised when the verified invoice already exists in the database."""


@dataclass(slots=True)
class DocumentAnalysis:
    original_filename: str
    stored_path: Path
    relative_path: str
    file_size: int
    file_hash: str
    text_result: PdfTextResult
    fields: ExtractedInvoiceFields
    warnings: list[str] = field(default_factory=list)


def sanitize_pdf_filename(filename: str) -> str:
    """Return a portable PDF filename without path traversal characters."""

    source_name = Path(filename or "document.pdf").name
    normalized = unicodedata.normalize("NFKD", source_name)
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
    stem = Path(ascii_name).stem
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("._-")
    stem = stem[:80] or "document"
    return f"{stem}.pdf"


class DocumentService:
    def __init__(
        self,
        invoice_repository: InvoiceRepository,
        invoice_service: InvoiceService,
        *,
        upload_directory: str | Path = PDF_UPLOAD_DIR,
        max_file_size: int = MAX_PDF_SIZE_BYTES,
    ) -> None:
        self.invoice_repository = invoice_repository
        self.invoice_service = invoice_service
        self.upload_directory = Path(upload_directory)
        self.max_file_size = max_file_size

    def process_pdf(
        self,
        content: bytes,
        filename: str,
        mime_type: str | None = None,
    ) -> DocumentAnalysis:
        """Validate, read, extract fields, and store a PDF without overwriting."""

        self._validate_upload(content, filename, mime_type)
        text_result = extract_text_from_pdf(content)
        fields = extract_invoice_fields(text_result.text)
        file_hash = hashlib.sha256(content).hexdigest()
        stored_path = self._store_pdf(content, filename, file_hash)
        try:
            relative_path = stored_path.relative_to(PROJECT_ROOT).as_posix()
        except ValueError:
            relative_path = stored_path.as_posix()
        return DocumentAnalysis(
            original_filename=Path(filename).name,
            stored_path=stored_path,
            relative_path=relative_path,
            file_size=len(content),
            file_hash=file_hash,
            text_result=text_result,
            fields=fields,
            warnings=[*text_result.warnings, *fields.warnings],
        )

    def save_verified_invoice(
        self,
        analysis: DocumentAnalysis,
        invoice: Invoice,
        *,
        approve: bool = False,
    ) -> Invoice:
        duplicate = self.invoice_repository.find_duplicate(
            invoice.invoice_number,
            invoice.contractor_id,
        )
        if duplicate is not None:
            raise DuplicateDocumentError(
                "Faktura o tym numerze dla wybranego kontrahenta już istnieje "
                f"(id: {duplicate.id})."
            )
        linked_invoice = replace(
            invoice,
            source_file=analysis.relative_path,
            file_hash=analysis.file_hash,
            status=InvoiceStatus.APPROVED if approve else invoice.status,
        )
        return self.invoice_service.create_invoice(linked_invoice, approve=approve)

    def find_duplicate(self, invoice_number: str, contractor_id: int) -> Invoice | None:
        if not invoice_number.strip() or contractor_id <= 0:
            return None
        return self.invoice_repository.find_duplicate(
            invoice_number.strip(), contractor_id
        )

    def _validate_upload(
        self,
        content: bytes,
        filename: str,
        mime_type: str | None,
    ) -> None:
        if Path(filename).suffix.casefold() != ".pdf":
            raise DocumentValidationError("Dozwolone są wyłącznie pliki PDF.")
        if mime_type is not None and mime_type.casefold() not in ACCEPTED_PDF_MIME_TYPES:
            raise DocumentValidationError("Typ MIME przesłanego pliku nie jest PDF.")
        if not content:
            raise DocumentValidationError("Przesłany plik jest pusty.")
        if len(content) > self.max_file_size:
            limit_mb = self.max_file_size / (1024 * 1024)
            raise DocumentValidationError(
                f"Plik przekracza limit {limit_mb:.0f} MB."
            )
        if not content.lstrip().startswith(b"%PDF-"):
            raise DocumentValidationError("Zawartość pliku nie ma nagłówka PDF.")

    def _store_pdf(self, content: bytes, filename: str, file_hash: str) -> Path:
        safe_name = sanitize_pdf_filename(filename)
        target = self.upload_directory / (
            f"{Path(safe_name).stem}-{file_hash[:12]}.pdf"
        )
        self.upload_directory.mkdir(parents=True, exist_ok=True)
        try:
            with target.open("xb") as output:
                output.write(content)
        except FileExistsError:
            pass
        return target
