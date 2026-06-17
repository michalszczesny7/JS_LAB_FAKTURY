"""CSV export for filtered invoice reports."""

from __future__ import annotations

import csv
from io import StringIO

from invoice_manager.services.report_service import ReportData

CSV_HEADERS = (
    "ID",
    "Numer faktury",
    "Data wystawienia",
    "Termin płatności",
    "Kontrahent",
    "Inwestycja",
    "Kategoria",
    "Typ faktury",
    "Status faktury",
    "Status płatności",
    "Netto",
    "VAT",
    "Brutto",
    "Plik źródłowy",
)


def export_report_csv(report: ReportData) -> bytes:
    """Return a semicolon-separated UTF-8 CSV with the filtered invoices."""

    stream = StringIO(newline="")
    writer = csv.writer(stream, delimiter=";", lineterminator="\n")
    writer.writerow(CSV_HEADERS)
    for row in report.invoices:
        writer.writerow(
            (
                row.id,
                row.invoice_number,
                row.issue_date,
                row.payment_date or "",
                row.contractor,
                row.investment,
                row.category,
                row.invoice_type,
                row.status,
                row.payment_status,
                row.net_amount,
                row.vat_amount,
                row.gross_amount,
                row.source_file or "",
            )
        )
    return stream.getvalue().encode("utf-8-sig")
