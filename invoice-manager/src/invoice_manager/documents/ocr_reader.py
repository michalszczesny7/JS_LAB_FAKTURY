"""Local OCR helpers backed by Tesseract and Poppler command-line tools."""

from __future__ import annotations

import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

DEFAULT_OCR_LANGUAGES = "pol+eng"
DEFAULT_MAX_PAGES = 50


class OCRUnavailableError(RuntimeError):
    """Raised when the local OCR runtime is unavailable or fails."""


def extract_text_from_image(
    content: bytes,
    *,
    languages: str = DEFAULT_OCR_LANGUAGES,
) -> str:
    """Recognize text in PNG/JPEG bytes with local Tesseract OCR."""

    try:
        result = subprocess.run(
            ("tesseract", "stdin", "stdout", "-l", languages),
            input=content,
            capture_output=True,
            check=False,
            timeout=120,
        )
    except FileNotFoundError as error:
        raise OCRUnavailableError(
            "OCR wymaga programu Tesseract z językami pol i eng."
        ) from error
    except subprocess.TimeoutExpired as error:
        raise OCRUnavailableError("OCR obrazu przekroczył limit czasu.") from error

    if result.returncode != 0:
        details = result.stderr.decode("utf-8", errors="replace").strip()
        raise OCRUnavailableError(f"Tesseract nie odczytał obrazu: {details}")
    return result.stdout.decode("utf-8", errors="replace").strip()


def extract_text_from_scanned_pdf(
    content: bytes,
    *,
    languages: str = DEFAULT_OCR_LANGUAGES,
    max_pages: int = DEFAULT_MAX_PAGES,
) -> str:
    """Render PDF pages and recognize each page with Tesseract."""

    page_images = _render_with_pymupdf(content, max_pages=max_pages)
    if page_images is not None:
        return "\n".join(
            text
            for image in page_images
            if (text := extract_text_from_image(image, languages=languages))
        ).strip()

    with TemporaryDirectory(prefix="invoice-ocr-") as temporary_directory:
        temporary_path = Path(temporary_directory)
        source_path = temporary_path / "document.pdf"
        output_prefix = temporary_path / "page"
        source_path.write_bytes(content)
        try:
            rendered = subprocess.run(
                (
                    "pdftoppm",
                    "-png",
                    "-r",
                    "200",
                    "-f",
                    "1",
                    "-l",
                    str(max_pages),
                    str(source_path),
                    str(output_prefix),
                ),
                capture_output=True,
                check=False,
                timeout=180,
            )
        except FileNotFoundError as error:
            raise OCRUnavailableError(
                "OCR skanowanego PDF wymaga programu pdftoppm (Poppler)."
            ) from error
        except subprocess.TimeoutExpired as error:
            raise OCRUnavailableError("Renderowanie PDF przekroczyło limit czasu.") from error

        if rendered.returncode != 0:
            details = rendered.stderr.decode("utf-8", errors="replace").strip()
            raise OCRUnavailableError(f"Nie udało się wyrenderować PDF: {details}")

        page_paths = sorted(temporary_path.glob("page-*.png"))
        if not page_paths:
            raise OCRUnavailableError("PDF nie zawiera stron możliwych do OCR.")
        return "\n".join(
            text
            for page_path in page_paths
            if (text := extract_text_from_image(page_path.read_bytes(), languages=languages))
        ).strip()


def _render_with_pymupdf(
    content: bytes,
    *,
    max_pages: int,
) -> list[bytes] | None:
    """Return rendered PNG pages, or None when PyMuPDF is not installed."""

    try:
        import fitz
    except ImportError:
        return None

    try:
        document = fitz.open(stream=content, filetype="pdf")
        matrix = fitz.Matrix(2.5, 2.5)
        return [
            document[index].get_pixmap(matrix=matrix, alpha=False).tobytes("png")
            for index in range(min(document.page_count, max_pages))
        ]
    except Exception as error:
        raise OCRUnavailableError(f"Nie udało się wyrenderować PDF: {error}") from error
    finally:
        if "document" in locals():
            document.close()
