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


def _positive_int_setting(name: str, default: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError:
        return default
    return value if value > 0 else default


APP_ENV = os.getenv("APP_ENV", "development").strip() or "development"
DATA_DIR = PROJECT_ROOT / "data"
PDF_UPLOAD_DIR = DATA_DIR / "uploaded_invoices"
MAX_UPLOAD_SIZE_MB = _positive_int_setting("MAX_UPLOAD_SIZE_MB", 10)
MAX_PDF_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024
DEFAULT_DATABASE_PATH = DATA_DIR / "invoices.db"
_database_setting = (
    os.getenv("INVOICE_MANAGER_DB_PATH")
    or os.getenv("DATABASE_PATH")
    or str(DEFAULT_DATABASE_PATH)
)
DATABASE_PATH = Path(_database_setting).expanduser()
if not DATABASE_PATH.is_absolute():
    DATABASE_PATH = PROJECT_ROOT / DATABASE_PATH
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
