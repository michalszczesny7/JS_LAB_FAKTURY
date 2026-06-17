"""CRUD operations for invoice categories."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from invoice_manager.db.connection import database_connection
from invoice_manager.models.category import Category


class CategoryRepository:
    def __init__(self, database_path: str | Path | None = None) -> None:
        self.database_path = database_path

    @staticmethod
    def _from_row(row: sqlite3.Row) -> Category:
        return Category(
            id=row["id"],
            name=row["name"],
            category_type=row["category_type"],
            created_at=row["created_at"],
        )

    def create(self, category: Category) -> Category:
        with database_connection(self.database_path) as connection:
            cursor = connection.execute(
                """
                INSERT INTO categories (name, category_type)
                VALUES (?, ?)
                """,
                (category.name, category.category_type),
            )
            connection.commit()
            category_id = cursor.lastrowid

        created = self.get_by_id(category_id)
        if created is None:
            raise RuntimeError("Failed to read the created category.")
        return created

    def get_by_id(self, category_id: int) -> Category | None:
        with database_connection(self.database_path) as connection:
            row = connection.execute(
                "SELECT * FROM categories WHERE id = ?",
                (category_id,),
            ).fetchone()
        return self._from_row(row) if row else None

    def list_all(self) -> list[Category]:
        with database_connection(self.database_path) as connection:
            rows = connection.execute(
                "SELECT * FROM categories ORDER BY name, id"
            ).fetchall()
        return [self._from_row(row) for row in rows]

    def update(self, category: Category) -> Category:
        if category.id is None:
            raise ValueError("Category id is required for update.")

        with database_connection(self.database_path) as connection:
            cursor = connection.execute(
                """
                UPDATE categories
                SET name = ?, category_type = ?
                WHERE id = ?
                """,
                (category.name, category.category_type, category.id),
            )
            connection.commit()

        if cursor.rowcount == 0:
            raise LookupError(f"Category {category.id} does not exist.")
        updated = self.get_by_id(category.id)
        if updated is None:
            raise RuntimeError("Failed to read the updated category.")
        return updated

    def delete(self, category_id: int) -> bool:
        with database_connection(self.database_path) as connection:
            cursor = connection.execute(
                "DELETE FROM categories WHERE id = ?",
                (category_id,),
            )
            connection.commit()
        return cursor.rowcount > 0
