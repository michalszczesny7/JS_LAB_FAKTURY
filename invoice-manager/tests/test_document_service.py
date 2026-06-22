"""Tests for secure PDF storage and verified invoice persistence."""

from __future__ import annotations

import hashlib

import pytest

from invoice_manager.db.init_db import initialize_database
from invoice_manager.documents.pdf_reader import PdfTextResult
from invoice_manager.models.category import Category
from invoice_manager.models.contractor import Contractor
from invoice_manager.models.investment import Investment
from invoice_manager.models.invoice import Invoice, InvoiceStatus, InvoiceType
from invoice_manager.repositories.category_repository import CategoryRepository
from invoice_manager.repositories.contractor_repository import ContractorRepository
from invoice_manager.repositories.investment_repository import InvestmentRepository
from invoice_manager.repositories.invoice_repository import InvoiceRepository
from invoice_manager.services.document_service import (
    DocumentService,
    DocumentValidationError,
    DuplicateDocumentError,
    sanitize_document_filename,
    sanitize_pdf_filename,
)
from invoice_manager.services.invoice_service import InvoiceService
from invoice_manager.services.validation_service import ValidationService


@pytest.fixture
def document_context(tmp_path):
    database_path = tmp_path / "documents.db"
    initialize_database(database_path, seed_categories=False)
    invoices = InvoiceRepository(database_path)
    contractors = ContractorRepository(database_path)
    investments = InvestmentRepository(database_path)
    categories = CategoryRepository(database_path)
    contractor = contractors.create(Contractor("Test Bud", "SUPPLIER"))
    investment = investments.create(Investment("Projekt Testowy"))
    category = categories.create(Category("Materiały", "COST"))
    validation = ValidationService(invoices, contractors, investments, categories)
    invoice_service = InvoiceService(invoices, validation)
    service = DocumentService(
        invoices,
        invoice_service,
        upload_directory=tmp_path / "uploads",
    )
    return service, invoices, contractor, investment, category


def test_filename_is_sanitized_and_path_components_are_removed():
    assert sanitize_pdf_filename("../../Faktura ąć 01.PDF") == "Faktura_ac_01.pdf"
    assert sanitize_pdf_filename("...pdf") == "document.pdf"
    assert sanitize_document_filename("../Skan faktury.PNG") == "Skan_faktury.png"


def test_non_pdf_upload_is_rejected(document_context):
    service, *_ = document_context
    with pytest.raises(DocumentValidationError, match="wyłącznie pliki PDF"):
        service.process_pdf(b"not a pdf", "invoice.txt", "text/plain")


def test_pdf_is_stored_without_overwriting(monkeypatch, document_context):
    service, *_ = document_context
    text = "Faktura nr FV/1\nData wystawienia: 2026-06-17\nBrutto: 123,00 PLN"
    monkeypatch.setattr(
        "invoice_manager.services.document_service.extract_text_from_pdf",
        lambda _content, **_kwargs: PdfTextResult(text, 1, 1),
    )
    content = b"%PDF-1.4 synthetic"

    first = service.process_pdf(content, "Faktura testowa.pdf", "application/pdf")
    second = service.process_pdf(content, "Faktura testowa.pdf", "application/pdf")

    assert first.stored_path == second.stored_path
    assert first.stored_path.read_bytes() == content
    assert first.file_hash == hashlib.sha256(content).hexdigest()
    assert first.stored_path.name.startswith("Faktura_testowa-")


def test_empty_text_analysis_contains_warning(monkeypatch, document_context):
    service, *_ = document_context
    monkeypatch.setattr(
        "invoice_manager.services.document_service.extract_text_from_pdf",
        lambda _content, **_kwargs: PdfTextResult(
            "",
            1,
            1,
            warnings=["PDF nie zawiera warstwy tekstowej. OCR jest wymagany."],
        ),
    )
    analysis = service.process_pdf(
        b"%PDF-1.4 scan",
        "scan.pdf",
        "application/pdf",
    )
    assert any("OCR" in warning for warning in analysis.warnings)
    assert any("Brak tekstu" in warning for warning in analysis.warnings)


def test_verified_invoice_is_linked_and_duplicate_is_blocked(
    monkeypatch,
    document_context,
):
    service, invoices, contractor, investment, category = document_context
    monkeypatch.setattr(
        "invoice_manager.services.document_service.extract_text_from_pdf",
        lambda _content, **_kwargs: PdfTextResult("Faktura nr FV/PDF/1", 1, 1),
    )
    analysis = service.process_pdf(
        b"%PDF-1.4 invoice",
        "invoice.pdf",
        "application/pdf",
    )
    invoice = Invoice(
        invoice_number="FV/PDF/1",
        issue_date="2026-06-17",
        contractor_id=contractor.id,
        investment_id=investment.id,
        category_id=category.id,
        invoice_type=InvoiceType.COST,
        status=InvoiceStatus.NEEDS_REVIEW,
        net_amount=100.0,
        vat_amount=23.0,
        gross_amount=123.0,
    )

    created = service.save_verified_invoice(analysis, invoice)
    assert created.source_file == analysis.relative_path
    assert created.file_hash == analysis.file_hash
    assert invoices.get_by_id(created.id) == created

    with pytest.raises(DuplicateDocumentError, match="już istnieje"):
        service.save_verified_invoice(analysis, invoice)


def test_manual_source_accepts_image_and_rejects_executable(document_context):
    service, *_ = document_context
    png_content = b"\x89PNG\r\n\x1a\nsynthetic-image"

    stored = service.store_source_document(
        png_content,
        "../Skan faktury.png",
        "image/png",
    )

    assert stored.stored_path.read_bytes() == png_content
    assert stored.stored_path.suffix == ".png"
    with pytest.raises(DocumentValidationError, match="PDF, JPG, JPEG, PNG lub CSV"):
        service.store_source_document(b"MZ executable", "invoice.exe", "application/x-msdownload")


def test_csv_document_is_read_and_analyzed(document_context):
    service, *_ = document_context
    content = (
        "Faktura nr FV/CSV/1\nData wystawienia: 2026-06-19\n"
        "Netto: 100,00 PLN\nVAT: 23,00 PLN\nBrutto: 123,00 PLN\n"
    ).encode()

    analysis = service.process_document(content, "invoice.csv", "text/csv")

    assert analysis.fields.invoice_number == "FV/CSV/1"
    assert analysis.fields.gross_amount == 123.0
    assert analysis.stored_path.suffix == ".csv"


def test_image_document_uses_ocr(monkeypatch, document_context):
    service, *_ = document_context
    monkeypatch.setattr(
        "invoice_manager.services.document_service.extract_text_from_image",
        lambda _content: "Faktura nr FV/OCR/1\nBrutto: 123,00 PLN",
    )

    analysis = service.process_document(
        b"\xff\xd8\xffsynthetic-jpeg",
        "invoice.jpg",
        "image/jpeg",
    )

    assert analysis.text_result.used_ocr is True
    assert analysis.fields.invoice_number == "FV/OCR/1"
