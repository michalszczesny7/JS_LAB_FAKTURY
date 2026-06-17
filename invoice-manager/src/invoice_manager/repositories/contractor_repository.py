"""CRUD operations for contractors."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from invoice_manager.db.connection import database_connection
from invoice_manager.models.contractor import Contractor


class ContractorRepository:
    def __init__(self, database_path: str | Path | None = None) -> None:
        self.database_path = database_path

    @staticmethod
    def _from_row(row: sqlite3.Row) -> Contractor:
        return Contractor(
            id=row["id"],
            name=row["name"],
            nip=row["nip"],
            contractor_type=row["contractor_type"],
            created_at=row["created_at"],
        )

    def create(self, contractor: Contractor) -> Contractor:
        with database_connection(self.database_path) as connection:
            cursor = connection.execute(
                """
                INSERT INTO contractors (name, nip, contractor_type)
                VALUES (?, ?, ?)
                """,
                (contractor.name, contractor.nip, contractor.contractor_type),
            )
            connection.commit()
            contractor_id = cursor.lastrowid

        created = self.get_by_id(contractor_id)
        if created is None:
            raise RuntimeError("Failed to read the created contractor.")
        return created

    def get_by_id(self, contractor_id: int) -> Contractor | None:
        with database_connection(self.database_path) as connection:
            row = connection.execute(
                "SELECT * FROM contractors WHERE id = ?",
                (contractor_id,),
            ).fetchone()
        return self._from_row(row) if row else None

    def list_all(self) -> list[Contractor]:
        with database_connection(self.database_path) as connection:
            rows = connection.execute(
                "SELECT * FROM contractors ORDER BY name, id"
            ).fetchall()
        return [self._from_row(row) for row in rows]

    def update(self, contractor: Contractor) -> Contractor:
        if contractor.id is None:
            raise ValueError("Contractor id is required for update.")

        with database_connection(self.database_path) as connection:
            cursor = connection.execute(
                """
                UPDATE contractors
                SET name = ?, nip = ?, contractor_type = ?
                WHERE id = ?
                """,
                (
                    contractor.name,
                    contractor.nip,
                    contractor.contractor_type,
                    contractor.id,
                ),
            )
            connection.commit()

        if cursor.rowcount == 0:
            raise LookupError(f"Contractor {contractor.id} does not exist.")
        updated = self.get_by_id(contractor.id)
        if updated is None:
            raise RuntimeError("Failed to read the updated contractor.")
        return updated

    def delete(self, contractor_id: int) -> bool:
        with database_connection(self.database_path) as connection:
            cursor = connection.execute(
                "DELETE FROM contractors WHERE id = ?",
                (contractor_id,),
            )
            connection.commit()
        return cursor.rowcount > 0
