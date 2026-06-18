"""Application paths and environment-based configuration."""

from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # Keeps non-AI commands usable before dependencies are installed.
    load_dotenv = None

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if load_dotenv is not None:
    load_dotenv(PROJECT_ROOT / ".env")

DATA_DIR = PROJECT_ROOT / "data"
PDF_UPLOAD_DIR = DATA_DIR / "uploaded_invoices"
MAX_PDF_SIZE_BYTES = 10 * 1024 * 1024
DEFAULT_DATABASE_PATH = DATA_DIR / "invoices.db"
DATABASE_PATH = Path(
    os.getenv("INVOICE_MANAGER_DB_PATH", str(DEFAULT_DATABASE_PATH))
).expanduser()
DEFAULT_OPENAI_MODEL = "gpt-5-mini"


def get_database_path() -> Path:
    """Return the configured SQLite database path."""

    return DATABASE_PATH


def get_openai_api_key() -> str | None:
    """Return the configured API key without exposing it to the UI."""

    return os.getenv("OPENAI_API_KEY", "").strip() or None


def get_openai_model() -> str:
    """Return the configured model or a cost-conscious extraction default."""

    return os.getenv("OPENAI_MODEL", "").strip() or DEFAULT_OPENAI_MODEL


def get_ai_provider() -> str:
    """Return a supported default provider, falling back safely to mock."""

    provider = os.getenv("AI_PROVIDER", "mock").strip().casefold()
    return provider if provider in {"local", "mock", "openai"} else "mock"
