from __future__ import annotations

from types import SimpleNamespace

import pytest

from invoice_manager.documents.ocr_reader import (
    OCRUnavailableError,
    extract_text_from_image,
)


def test_image_ocr_returns_tesseract_stdout(monkeypatch):
    monkeypatch.setattr(
        "invoice_manager.documents.ocr_reader.subprocess.run",
        lambda *_args, **_kwargs: SimpleNamespace(
            returncode=0,
            stdout="Tekst faktury".encode(),
            stderr=b"",
        ),
    )

    assert extract_text_from_image(b"image") == "Tekst faktury"


def test_image_ocr_reports_missing_tesseract(monkeypatch):
    def missing_runtime(*_args, **_kwargs):
        raise FileNotFoundError

    monkeypatch.setattr(
        "invoice_manager.documents.ocr_reader.subprocess.run",
        missing_runtime,
    )

    with pytest.raises(OCRUnavailableError, match="Tesseract"):
        extract_text_from_image(b"image")
