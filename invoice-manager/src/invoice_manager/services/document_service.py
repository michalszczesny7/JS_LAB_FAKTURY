"""Secure invoice-document upload, analysis, and verified persistence."""

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
from invoice_manager.documents.ocr_reader import (
    extract_text_from_image,
    extract_text_from_scanned_pdf,
)
from invoice_manager.models.invoice import Invoice, InvoiceStatus
from invoice_manager.repositories.invoice_repository import InvoiceRepository
from invoice_manager.services.invoice_service import InvoiceService

SUPPORTED_DOCUMENT_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".csv"}
ACCEPTED_MIME_TYPES = {
    ".pdf": {"application/pdf", "application/x-pdf", ""},
    ".jpg": {"image/jpeg", "image/jpg", ""},
    ".jpeg": {"image/jpeg", "image/jpg", ""},
    ".png": {"image/png", ""},
    ".csv": {
        "text/csv",
        "application/csv",
        "application/vnd.ms-excel",
        "text/plain",
        "",
    },
}


class DocumentValidationError(ValueError):
    """Raised when an uploaded document violates safety rules."""


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


@dataclass(slots=True, frozen=True)
class StoredDocument:
    original_filename: str
    stored_path: Path
    relative_path: str
    file_size: int
    file_hash: str


def sanitize_document_filename(filename: str) -> str:
    """Return a portable supported filename without traversal characters."""

    source_name = Path(filename or "document.pdf").name
    suffix = Path(source_name).suffix.casefold()
    if suffix not in SUPPORTED_DOCUMENT_EXTENSIONS:
        suffix = ".pdf"
    normalized = unicodedata.normalize("NFKD", source_name)
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
    stem = Path(ascii_name).stem
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("._-")
    stem = stem[:80] or "document"
    return f"{stem}{suffix}"


def sanitize_pdf_filename(filename: str) -> str:
    """Return a portable PDF filename without path traversal characters."""

    source_name = f"{Path(filename or 'document').stem}.pdf"
    return sanitize_document_filename(source_name)


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
        """Backward-compatible strict PDF processing entry point."""

        if Path(filename).suffix.casefold() != ".pdf":
            raise DocumentValidationError("Dozwolone są wyłącznie pliki PDF.")
        return self.process_document(content, filename, mime_type)

    def process_document(
        self,
        content: bytes,
        filename: str,
        mime_type: str | None = None,
    ) -> DocumentAnalysis:
        """Validate, read, extract fields, and store a supported document."""

        extension = self._validate_upload(content, filename, mime_type)
        text_result = self._extract_text(content, extension)
        fields = extract_invoice_fields(text_result.text)
        stored = self._store_document(content, filename)
        return DocumentAnalysis(
            original_filename=stored.original_filename,
            stored_path=stored.stored_path,
            relative_path=stored.relative_path,
            file_size=stored.file_size,
            file_hash=stored.file_hash,
            text_result=text_result,
            fields=fields,
            warnings=[*text_result.warnings, *fields.warnings],
        )

    def store_source_document(
        self,
        content: bytes,
        filename: str,
        mime_type: str | None = None,
    ) -> StoredDocument:
        """Validate and store a manual invoice attachment without analyzing it."""

        self._validate_upload(content, filename, mime_type)
        return self._store_document(content, filename)

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
    ) -> str:
        extension = Path(filename).suffix.casefold()
        if extension not in SUPPORTED_DOCUMENT_EXTENSIONS:
            raise DocumentValidationError(
                "Dozwolone pliki faktur: PDF, JPG, JPEG, PNG lub CSV."
            )
        normalized_mime = (mime_type or "").casefold()
        if normalized_mime not in ACCEPTED_MIME_TYPES[extension]:
            raise DocumentValidationError(
                f"Typ MIME nie pasuje do pliku {extension.lstrip('.').upper()}."
            )
        if not content:
            raise DocumentValidationError("Przesłany plik jest pusty.")
        if len(content) > self.max_file_size:
            limit_mb = self.max_file_size / (1024 * 1024)
            raise DocumentValidationError(
                f"Plik przekracza limit {limit_mb:.0f} MB."
            )
        stripped = content.lstrip()
        if extension == ".pdf" and not stripped.startswith(b"%PDF-"):
            raise DocumentValidationError("Zawartość pliku nie ma nagłówka PDF.")
        if extension in {".jpg", ".jpeg"} and not content.startswith(b"\xff\xd8\xff"):
            raise DocumentValidationError("Zawartość pliku nie ma nagłówka JPEG.")
        if extension == ".png" and not content.startswith(b"\x89PNG\r\n\x1a\n"):
            raise DocumentValidationError("Zawartość pliku nie ma nagłówka PNG.")
        if extension == ".csv":
            if content.startswith(b"MZ") or b"\x00" in content[:4096]:
                raise DocumentValidationError("Plik CSV zawiera niedozwolone dane binarne.")
            self._decode_csv(content)
        return extension

    def _extract_text(self, content: bytes, extension: str) -> PdfTextResult:
        if extension == ".pdf":
            return extract_text_from_pdf(
                content,
                ocr_fallback=extract_text_from_scanned_pdf,
            )
        if extension in {".jpg", ".jpeg", ".png"}:
            warnings: list[str] = []
            try:
                text = extract_text_from_image(content)
            except Exception as error:
                text = ""
                warnings.append(f"OCR nie został wykonany: {error}")
            if not text:
                warnings.append("OCR obrazu nie zwrócił tekstu.")
            return PdfTextResult(
                text=text,
                page_count=1,
                processed_pages=1,
                warnings=warnings,
                used_ocr=bool(text),
            )
        text, encoding_warning = self._decode_csv(content)
        warnings = [encoding_warning] if encoding_warning else []
        return PdfTextResult(text, 1, 1, warnings=warnings)

    @staticmethod
    def _decode_csv(content: bytes) -> tuple[str, str | None]:
        for encoding in ("utf-8-sig", "utf-8", "cp1250"):
            try:
                return content.decode(encoding), (
                    None
                    if encoding in {"utf-8-sig", "utf-8"}
                    else "Plik CSV odczytano w kodowaniu Windows-1250."
                )
            except UnicodeDecodeError:
                continue
        raise DocumentValidationError(
            "Plik CSV musi używać kodowania UTF-8 lub Windows-1250."
        )

    def _store_document(self, content: bytes, filename: str) -> StoredDocument:
        file_hash = hashlib.sha256(content).hexdigest()
        safe_name = sanitize_document_filename(filename)
        suffix = Path(safe_name).suffix
        target = self.upload_directory / (
            f"{Path(safe_name).stem}-{file_hash[:12]}{suffix}"
        )
        self.upload_directory.mkdir(parents=True, exist_ok=True)
        try:
            with target.open("xb") as output:
                output.write(content)
        except FileExistsError:
            pass
        try:
            relative_path = target.relative_to(PROJECT_ROOT).as_posix()
        except ValueError:
            relative_path = target.as_posix()
        return StoredDocument(
            original_filename=Path(filename).name,
            stored_path=target,
            relative_path=relative_path,
            file_size=len(content),
            file_hash=file_hash,
        )
