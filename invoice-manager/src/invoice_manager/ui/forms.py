"""Invoice form controls and human-readable enum labels."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

import streamlit as st

from invoice_manager.models.category import Category
from invoice_manager.models.contractor import Contractor
from invoice_manager.models.investment import Investment
from invoice_manager.models.invoice import Invoice, InvoiceStatus, InvoiceType
from invoice_manager.ui.tables import (
    PAYMENT_STATUS_LABELS,
    invoice_type_label,
    payment_status_label,
    status_label,
)


def calculate_gross_amount(net_amount: float, vat_amount: float) -> float:
    """Return the invoice gross amount rounded to currency precision."""

    return round(float(net_amount) + float(vat_amount), 2)


@dataclass(slots=True, frozen=True)
class SourceDocumentUpload:
    content: bytes
    filename: str
    mime_type: str | None


def render_invoice_form(
    contractors: list[Contractor],
    investments: list[Investment],
    categories: list[Category],
) -> tuple[Invoice, bool, SourceDocumentUpload | None] | None:
    """Render the manual invoice form and return a submission when sent."""

    with st.form("manual_invoice_form", clear_on_submit=False):
        identity_left, identity_right = st.columns(2)
        with identity_left:
            invoice_number = st.text_input("Numer faktury", placeholder="FV/2026/001")
            contractor = st.selectbox(
                "Kontrahent",
                contractors,
                format_func=lambda item: item.name,
            )
            investment = st.selectbox(
                "Inwestycja",
                investments,
                format_func=lambda item: item.name,
            )
        with identity_right:
            invoice_type = st.selectbox(
                "Typ faktury",
                list(InvoiceType),
                format_func=invoice_type_label,
            )
            category = st.selectbox(
                "Kategoria",
                categories,
                format_func=lambda item: item.name,
            )
            source_file = st.file_uploader(
                "Plik źródłowy (opcjonalnie)",
                type=("pdf", "jpg", "jpeg", "png", "csv"),
                help="Dozwolone są dokumenty PDF, JPG, JPEG, PNG i CSV do 10 MB.",
            )

        date_left, date_middle, date_right = st.columns(3)
        with date_left:
            issue_date = st.date_input("Data wystawienia", value=date.today())
        with date_middle:
            has_payment_date = st.checkbox("Ustaw termin płatności", value=True)
        with date_right:
            payment_date = st.date_input(
                "Data płatności",
                value=date.today() + timedelta(days=14),
                disabled=not has_payment_date,
            )

        amount_left, amount_middle, amount_right = st.columns(3)
        with amount_left:
            net_amount = st.number_input(
                "Kwota netto", min_value=0.0, step=0.01, format="%.2f"
            )
        with amount_middle:
            vat_amount = st.number_input(
                "Kwota VAT", min_value=0.0, step=0.01, format="%.2f"
            )
        with amount_right:
            gross_amount = calculate_gross_amount(net_amount, vat_amount)
            st.number_input(
                "Kwota brutto",
                min_value=0.0,
                value=gross_amount,
                step=0.01,
                format="%.2f",
                disabled=True,
                help="Wyliczana automatycznie jako netto + VAT.",
            )
        st.caption("Kwota brutto zostanie automatycznie przeliczona przy zapisie.")

        payment_status = st.selectbox(
            "Status płatności",
            list(PAYMENT_STATUS_LABELS),
            format_func=payment_status_label,
        )
        save_mode = st.radio(
            "Sposób zapisu",
            (InvoiceStatus.DRAFT_MANUAL, InvoiceStatus.APPROVED),
            format_func=status_label,
            horizontal=True,
        )
        submitted = st.form_submit_button(
            "Zapisz fakturę", type="primary", use_container_width=True
        )

    if not submitted:
        return None

    invoice = Invoice(
        invoice_number=invoice_number.strip(),
        issue_date=issue_date.isoformat(),
        payment_date=payment_date.isoformat() if has_payment_date else None,
        contractor_id=contractor.id,
        investment_id=investment.id,
        category_id=category.id,
        invoice_type=invoice_type,
        status=save_mode,
        net_amount=float(net_amount),
        vat_amount=float(vat_amount),
        gross_amount=calculate_gross_amount(net_amount, vat_amount),
        payment_status=payment_status,
    )
    source_upload = (
        SourceDocumentUpload(
            content=source_file.getvalue(),
            filename=source_file.name,
            mime_type=source_file.type,
        )
        if source_file is not None
        else None
    )
    return invoice, save_mode is InvoiceStatus.APPROVED, source_upload
