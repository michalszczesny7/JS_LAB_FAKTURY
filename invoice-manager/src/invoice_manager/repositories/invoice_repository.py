"""Persistence and query operations for invoices."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from invoice_manager.db.connection import database_connection
from invoice_manager.models.invoice import Invoice, InvoiceStatus, InvoiceType


class InvoiceRepository:
    def __init__(self, database_path: str | Path | None = None) -> None:
        self.database_path = database_path

    @staticmethod
    def _from_row(row: sqlite3.Row) -> Invoice:
        return Invoice(
            id=row["id"],
            invoice_number=row["invoice_number"],
            issue_date=row["issue_date"],
            payment_date=row["payment_date"],
            contractor_id=row["contractor_id"],
            investment_id=row["investment_id"],
            category_id=row["category_id"],
            invoice_type=InvoiceType(row["invoice_type"]),
            status=InvoiceStatus(row["status"]),
            net_amount=row["net_amount"],
            vat_amount=row["vat_amount"],
            gross_amount=row["gross_amount"],
            payment_status=row["payment_status"],
            source_file=row["source_file"],
            file_hash=row["file_hash"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def create(self, invoice: Invoice) -> Invoice:
        with database_connection(self.database_path) as connection:
            cursor = connection.execute(
                """
                INSERT INTO invoices (
                    invoice_number,
                    issue_date,
                    payment_date,
                    contractor_id,
                    investment_id,
                    category_id,
                    invoice_type,
                    status,
                    net_amount,
                    vat_amount,
                    gross_amount,
                    payment_status,
                    source_file,
                    file_hash
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    invoice.invoice_number,
                    invoice.issue_date,
                    invoice.payment_date,
                    invoice.contractor_id,
                    invoice.investment_id,
                    invoice.category_id,
                    invoice.invoice_type.value,
                    invoice.status.value,
                    invoice.net_amount,
                    invoice.vat_amount,
                    invoice.gross_amount,
                    invoice.payment_status,
                    invoice.source_file,
                    invoice.file_hash,
                ),
            )
            connection.commit()
            invoice_id = cursor.lastrowid

        created = self.get_by_id(invoice_id)
        if created is None:
            raise RuntimeError("Failed to read the created invoice.")
        return created

    def get_by_id(self, invoice_id: int) -> Invoice | None:
        with database_connection(self.database_path) as connection:
            row = connection.execute(
                "SELECT * FROM invoices WHERE id = ?",
                (invoice_id,),
            ).fetchone()
        return self._from_row(row) if row else None

    def list_all(self, *, include_deleted: bool = False) -> list[Invoice]:
        query = "SELECT * FROM invoices"
        parameters: tuple[str, ...] = ()
        if not include_deleted:
            query += " WHERE status != ?"
            parameters = (InvoiceStatus.DELETED.value,)
        query += " ORDER BY issue_date DESC, id DESC"

        with database_connection(self.database_path) as connection:
            rows = connection.execute(query, parameters).fetchall()
        return [self._from_row(row) for row in rows]

    def update(self, invoice: Invoice) -> Invoice:
        if invoice.id is None:
            raise ValueError("Invoice id is required for update.")

        with database_connection(self.database_path) as connection:
            cursor = connection.execute(
                """
                UPDATE invoices
                SET invoice_number = ?,
                    issue_date = ?,
                    payment_date = ?,
                    contractor_id = ?,
                    investment_id = ?,
                    category_id = ?,
                    invoice_type = ?,
                    status = ?,
                    net_amount = ?,
                    vat_amount = ?,
                    gross_amount = ?,
                    payment_status = ?,
                    source_file = ?,
                    file_hash = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    invoice.invoice_number,
                    invoice.issue_date,
                    invoice.payment_date,
                    invoice.contractor_id,
                    invoice.investment_id,
                    invoice.category_id,
                    invoice.invoice_type.value,
                    invoice.status.value,
                    invoice.net_amount,
                    invoice.vat_amount,
                    invoice.gross_amount,
                    invoice.payment_status,
                    invoice.source_file,
                    invoice.file_hash,
                    invoice.id,
                ),
            )
            connection.commit()

        if cursor.rowcount == 0:
            raise LookupError(f"Invoice {invoice.id} does not exist.")
        updated = self.get_by_id(invoice.id)
        if updated is None:
            raise RuntimeError("Failed to read the updated invoice.")
        return updated

    def soft_delete(self, invoice_id: int) -> bool:
        with database_connection(self.database_path) as connection:
            cursor = connection.execute(
                """
                UPDATE invoices
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND status != ?
                """,
                (
                    InvoiceStatus.DELETED.value,
                    invoice_id,
                    InvoiceStatus.DELETED.value,
                ),
            )
            connection.commit()
        return cursor.rowcount > 0

    def soft_delete_many(self, invoice_ids: list[int]) -> int:
        """Soft-delete multiple invoices in one transaction."""

        unique_ids = sorted(set(invoice_ids))
        if not unique_ids:
            return 0
        placeholders = ", ".join("?" for _ in unique_ids)
        with database_connection(self.database_path) as connection:
            cursor = connection.execute(
                f"""
                UPDATE invoices
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id IN ({placeholders}) AND status != ?
                """,
                (
                    InvoiceStatus.DELETED.value,
                    *unique_ids,
                    InvoiceStatus.DELETED.value,
                ),
            )
            connection.commit()
        return cursor.rowcount

    def find_duplicate(
        self,
        invoice_number: str,
        contractor_id: int,
        *,
        exclude_invoice_id: int | None = None,
        include_deleted: bool = False,
    ) -> Invoice | None:
        conditions = ["invoice_number = ?", "contractor_id = ?"]
        parameters: list[object] = [invoice_number, contractor_id]

        if exclude_invoice_id is not None:
            conditions.append("id != ?")
            parameters.append(exclude_invoice_id)
        if not include_deleted:
            conditions.append("status != ?")
            parameters.append(InvoiceStatus.DELETED.value)

        query = (
            "SELECT * FROM invoices WHERE "
            + " AND ".join(conditions)
            + " ORDER BY id LIMIT 1"
        )
        with database_connection(self.database_path) as connection:
            row = connection.execute(query, parameters).fetchone()
        return self._from_row(row) if row else None

    def find_by_status(
        self,
        status: InvoiceStatus,
        *,
        include_deleted: bool = False,
    ) -> list[Invoice]:
        if status is InvoiceStatus.DELETED and not include_deleted:
            return []

        with database_connection(self.database_path) as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM invoices
                WHERE status = ?
                ORDER BY issue_date DESC, id DESC
                """,
                (status.value,),
            ).fetchall()
        return [self._from_row(row) for row in rows]

    def find_by_investment(
        self,
        investment_id: int,
        *,
        include_deleted: bool = False,
    ) -> list[Invoice]:
        query = "SELECT * FROM invoices WHERE investment_id = ?"
        parameters: list[object] = [investment_id]
        if not include_deleted:
            query += " AND status != ?"
            parameters.append(InvoiceStatus.DELETED.value)
        query += " ORDER BY issue_date DESC, id DESC"

        with database_connection(self.database_path) as connection:
            rows = connection.execute(query, parameters).fetchall()
        return [self._from_row(row) for row in rows]
