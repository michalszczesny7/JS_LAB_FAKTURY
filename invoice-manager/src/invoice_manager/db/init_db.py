"""Create the SQLite schema and optionally seed basic categories."""

from __future__ import annotations

import argparse
from pathlib import Path

from invoice_manager.db.connection import database_connection

SCHEMA_PATH = Path(__file__).with_name("schema.sql")

DEFAULT_CATEGORIES = (
    ("materiały budowlane", "COST"),
    ("robocizna", "COST"),
    ("podwykonawcy", "COST"),
    ("sprzęt", "COST"),
    ("transport", "COST"),
    ("projektowanie", "COST"),
    ("administracja", "COST"),
    ("sprzedaż lokalu", "SALES"),
    ("inne", "OTHER"),
)


def initialize_database(
    database_path: str | Path | None = None,
    *,
    seed_categories: bool = True,
) -> Path:
    """Initialize the database from schema.sql and return its path."""

    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    resolved_path = Path(database_path).expanduser() if database_path else None

    with database_connection(resolved_path) as connection:
        connection.executescript(schema)
        if seed_categories:
            connection.executemany(
                """
                INSERT OR IGNORE INTO categories (name, category_type)
                VALUES (?, ?)
                """,
                DEFAULT_CATEGORIES,
            )
        connection.commit()

        row = connection.execute("PRAGMA database_list").fetchone()
        actual_path = Path(row["file"])

    return actual_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize the invoice database.")
    parser.add_argument("--db", type=Path, help="Optional SQLite database path.")
    parser.add_argument(
        "--no-seed",
        action="store_true",
        help="Do not insert the default categories.",
    )
    args = parser.parse_args()

    database_path = initialize_database(args.db, seed_categories=not args.no_seed)
    print(f"Database initialized: {database_path}")


if __name__ == "__main__":
    main()
