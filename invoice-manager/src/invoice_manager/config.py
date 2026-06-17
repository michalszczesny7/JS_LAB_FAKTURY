"""Application paths and environment-based configuration."""

from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
DEFAULT_DATABASE_PATH = DATA_DIR / "invoices.db"
DATABASE_PATH = Path(
    os.getenv("INVOICE_MANAGER_DB_PATH", str(DEFAULT_DATABASE_PATH))
).expanduser()


def get_database_path() -> Path:
    """Return the configured SQLite database path."""

    return DATABASE_PATH
