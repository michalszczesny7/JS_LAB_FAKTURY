"""CRUD operations for investments."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from invoice_manager.db.connection import database_connection
from invoice_manager.models.investment import Investment


class InvestmentRepository:
    def __init__(self, database_path: str | Path | None = None) -> None:
        self.database_path = database_path

    @staticmethod
    def _from_row(row: sqlite3.Row) -> Investment:
        return Investment(
            id=row["id"],
            name=row["name"],
            location=row["location"],
            start_date=row["start_date"],
            planned_end_date=row["planned_end_date"],
            budget=row["budget"],
            created_at=row["created_at"],
        )

    def create(self, investment: Investment) -> Investment:
        with database_connection(self.database_path) as connection:
            cursor = connection.execute(
                """
                INSERT INTO investments (
                    name, location, start_date, planned_end_date, budget
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    investment.name,
                    investment.location,
                    investment.start_date,
                    investment.planned_end_date,
                    investment.budget,
                ),
            )
            connection.commit()
            investment_id = cursor.lastrowid

        created = self.get_by_id(investment_id)
        if created is None:
            raise RuntimeError("Failed to read the created investment.")
        return created

    def get_by_id(self, investment_id: int) -> Investment | None:
        with database_connection(self.database_path) as connection:
            row = connection.execute(
                "SELECT * FROM investments WHERE id = ?",
                (investment_id,),
            ).fetchone()
        return self._from_row(row) if row else None

    def list_all(self) -> list[Investment]:
        with database_connection(self.database_path) as connection:
            rows = connection.execute(
                "SELECT * FROM investments ORDER BY name, id"
            ).fetchall()
        return [self._from_row(row) for row in rows]

    def update(self, investment: Investment) -> Investment:
        if investment.id is None:
            raise ValueError("Investment id is required for update.")

        with database_connection(self.database_path) as connection:
            cursor = connection.execute(
                """
                UPDATE investments
                SET name = ?,
                    location = ?,
                    start_date = ?,
                    planned_end_date = ?,
                    budget = ?
                WHERE id = ?
                """,
                (
                    investment.name,
                    investment.location,
                    investment.start_date,
                    investment.planned_end_date,
                    investment.budget,
                    investment.id,
                ),
            )
            connection.commit()

        if cursor.rowcount == 0:
            raise LookupError(f"Investment {investment.id} does not exist.")
        updated = self.get_by_id(investment.id)
        if updated is None:
            raise RuntimeError("Failed to read the updated investment.")
        return updated

    def delete(self, investment_id: int) -> bool:
        with database_connection(self.database_path) as connection:
            cursor = connection.execute(
                "DELETE FROM investments WHERE id = ?",
                (investment_id,),
            )
            connection.commit()
        return cursor.rowcount > 0
