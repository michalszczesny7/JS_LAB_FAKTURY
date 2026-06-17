"""SQLite connection factory used by repositories and scripts."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from invoice_manager.config import get_database_path


def get_connection(database_path: str | Path | None = None) -> sqlite3.Connection:
    """Create a configured SQLite connection.

    The parent directory is created automatically, foreign keys are enabled,
    and rows can be accessed by column name.
    """

    path = Path(database_path) if database_path is not None else get_database_path()
    path = path.expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


@contextmanager
def database_connection(
    database_path: str | Path | None = None,
) -> Iterator[sqlite3.Connection]:
    """Yield a connection and always close it after use."""

    connection = get_connection(database_path)
    try:
        yield connection
    finally:
        connection.close()
