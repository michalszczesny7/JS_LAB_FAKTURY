"""Lightweight text extraction from PDFs with an optional OCR hook."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from io import BytesIO

DEFAULT_MAX_PAGES = 50


class PdfReadError(ValueError):
    """Raised when a PDF cannot be read safely."""


@dataclass(slots=True)
class PdfTextResult:
    text: str
    page_count: int
    processed_pages: int
    warnings: list[str] = field(default_factory=list)
    used_ocr: bool = False


def extract_text_from_pdf(
    content: bytes,
    *,
    max_pages: int = DEFAULT_MAX_PAGES,
    ocr_fallback: Callable[[bytes], str] | None = None,
) -> PdfTextResult:
    """Extract embedded text and optionally invoke an OCR provider when empty."""

    try:
        from pypdf import PdfReader
    except ImportError as error:
        raise RuntimeError(
            "Odczyt PDF wymaga pakietu pypdf z requirements.txt."
        ) from error

    try:
        reader = PdfReader(BytesIO(content))
        if reader.is_encrypted and reader.decrypt("") == 0:
            raise PdfReadError("PDF jest zaszyfrowany i wymaga hasła.")
        page_count = len(reader.pages)
        processed_pages = min(page_count, max_pages)
        warnings: list[str] = []
        if page_count > max_pages:
            warnings.append(
                f"Dokument ma {page_count} stron. Odczytano pierwsze {max_pages}."
            )
        page_texts = [
            reader.pages[index].extract_text() or ""
            for index in range(processed_pages)
        ]
    except PdfReadError:
        raise
    except Exception as error:
        raise PdfReadError(f"Nie udało się odczytać pliku PDF: {error}") from error

    text = "\n".join(part.strip() for part in page_texts if part.strip()).strip()
    used_ocr = False
    if not text and ocr_fallback is not None:
        text = (ocr_fallback(content) or "").strip()
        used_ocr = bool(text)
    if not text:
        warnings.append(
            "PDF nie zawiera warstwy tekstowej. Skan wymaga opcjonalnego OCR, "
            "który nie jest włączony w tej wersji."
        )
    return PdfTextResult(
        text=text,
        page_count=page_count,
        processed_pages=processed_pages,
        warnings=warnings,
        used_ocr=used_ocr,
    )
