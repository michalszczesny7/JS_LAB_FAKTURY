"""Tests for lightweight PDF text extraction behavior."""

from __future__ import annotations

import sys
from types import SimpleNamespace

from invoice_manager.documents.pdf_reader import extract_text_from_pdf


class FakePage:
    def __init__(self, text: str | None) -> None:
        self.text = text

    def extract_text(self) -> str | None:
        return self.text


def install_fake_pypdf(monkeypatch, page_texts: list[str | None]) -> None:
    class FakeReader:
        is_encrypted = False

        def __init__(self, _stream) -> None:
            self.pages = [FakePage(text) for text in page_texts]

    monkeypatch.setitem(sys.modules, "pypdf", SimpleNamespace(PdfReader=FakeReader))


def test_pdf_reader_extracts_embedded_text(monkeypatch):
    install_fake_pypdf(monkeypatch, ["Faktura nr FV/1", "Brutto: 123,00 PLN"])
    result = extract_text_from_pdf(b"%PDF-test")

    assert "FV/1" in result.text
    assert result.page_count == 2
    assert result.processed_pages == 2
    assert result.warnings == []


def test_empty_pdf_text_returns_ocr_warning(monkeypatch):
    install_fake_pypdf(monkeypatch, [None, "   "])
    result = extract_text_from_pdf(b"%PDF-scan")

    assert result.text == ""
    assert any("OCR" in warning for warning in result.warnings)
    assert result.used_ocr is False


def test_optional_ocr_hook_is_used_for_empty_text(monkeypatch):
    install_fake_pypdf(monkeypatch, [""])
    result = extract_text_from_pdf(
        b"%PDF-scan",
        ocr_fallback=lambda _content: "Tekst z OCR",
    )

    assert result.text == "Tekst z OCR"
    assert result.used_ocr is True
