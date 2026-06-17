"""PDF upload, text extraction, and manual invoice verification."""

from __future__ import annotations

import hashlib
from datetime import date, timedelta

import streamlit as st

from invoice_manager.models.contractor import Contractor
from invoice_manager.models.investment import Investment
from invoice_manager.models.invoice import Invoice, InvoiceStatus, InvoiceType
from invoice_manager.ui.components import (
    build_app_context,
    configure_page,
    page_header,
)
from invoice_manager.ui.forms import invoice_type_label, status_label
from invoice_manager.ui.messages import show_service_exception
from invoice_manager.validators.nip_validator import validate_nip

ANALYSIS_KEY = "pdf_document_analysis"
FILE_HASH_KEY = "pdf_document_hash"


def parsed_date(value: str | None, fallback: date) -> date:
    if not value:
        return fallback
    try:
        return date.fromisoformat(value)
    except ValueError:
        return fallback


def matching_contractor_index(contractors, fields) -> int:
    for index, contractor in enumerate(contractors):
        if fields.nip and contractor.nip:
            if contractor.nip.replace("-", "").replace(" ", "") == fields.nip:
                return index
        if fields.contractor_name and contractor.name.casefold() == fields.contractor_name.casefold():
            return index
    return 0


configure_page("AI Review")
page_header(
    "AI Review — faktura PDF",
    "Odczytaj dokument lokalnie i zweryfikuj pola przed zapisem.",
)

try:
    context = build_app_context()
except Exception as error:
    st.error(f"Nie udało się przygotować obsługi PDF: {error}")
    st.stop()

uploaded_file = st.file_uploader("Dokument PDF", type=("pdf",))
if uploaded_file is None:
    st.info("Wybierz fakturę PDF o maksymalnym rozmiarze 10 MB.")
    st.stop()

content = uploaded_file.getvalue()
file_hash = hashlib.sha256(content).hexdigest()
if st.session_state.get(FILE_HASH_KEY) != file_hash:
    st.session_state[FILE_HASH_KEY] = file_hash
    st.session_state.pop(ANALYSIS_KEY, None)

file_size_mb = len(content) / (1024 * 1024)
details = st.columns(2)
details[0].metric("Nazwa pliku", uploaded_file.name)
details[1].metric("Rozmiar", f"{file_size_mb:.2f} MB")

if st.button("Odczytaj PDF", type="primary", use_container_width=True):
    try:
        with st.spinner("Odczytywanie dokumentu..."):
            st.session_state[ANALYSIS_KEY] = context.document_service.process_pdf(
                content,
                uploaded_file.name,
                uploaded_file.type,
            )
    except Exception as error:
        show_service_exception(error)

analysis = st.session_state.get(ANALYSIS_KEY)
if analysis is None:
    st.stop()

for warning in analysis.warnings:
    st.warning(warning)

st.subheader("Odczytany tekst")
if analysis.text_result.text:
    excerpt = analysis.text_result.text[:5000]
    st.text_area(
        "Fragment dokumentu",
        value=excerpt,
        height=220,
        disabled=True,
    )
else:
    st.info(
        "Nie znaleziono tekstu. Możesz wprowadzić dane ręcznie, ale ten dokument "
        "prawdopodobnie wymaga OCR."
    )

fields = analysis.fields

with st.expander("Dodaj brakującego kontrahenta"):
    with st.form("pdf_quick_contractor"):
        contractor_name = st.text_input(
            "Nazwa kontrahenta",
            value=fields.contractor_name or "",
        )
        contractor_nip = st.text_input("NIP (opcjonalnie)", value=fields.nip or "")
        add_contractor = st.form_submit_button("Dodaj kontrahenta")
    if add_contractor:
        errors = validate_nip(contractor_nip) if contractor_nip.strip() else []
        if not contractor_name.strip():
            st.error("Nazwa kontrahenta jest wymagana.")
        elif errors:
            for error in errors:
                st.error(error)
        else:
            try:
                context.lookup_service.create_contractor(
                    Contractor(
                        name=contractor_name.strip(),
                        contractor_type="SUPPLIER",
                        nip=contractor_nip.strip() or None,
                    )
                )
                st.success("Kontrahent został dodany.")
                st.rerun()
            except Exception as error:
                show_service_exception(error)

with st.expander("Dodaj brakującą inwestycję"):
    with st.form("pdf_quick_investment"):
        investment_name = st.text_input("Nazwa inwestycji")
        investment_location = st.text_input("Lokalizacja (opcjonalnie)")
        add_investment = st.form_submit_button("Dodaj inwestycję")
    if add_investment:
        if not investment_name.strip():
            st.error("Nazwa inwestycji jest wymagana.")
        else:
            try:
                context.lookup_service.create_investment(
                    Investment(
                        name=investment_name.strip(),
                        location=investment_location.strip() or None,
                    )
                )
                st.success("Inwestycja została dodana.")
                st.rerun()
            except Exception as error:
                show_service_exception(error)

contractors = context.lookup_service.list_contractors()
investments = context.lookup_service.list_investments()
categories = context.lookup_service.list_categories()
if not contractors or not investments or not categories:
    missing = []
    if not contractors:
        missing.append("kontrahenta")
    if not investments:
        missing.append("inwestycję")
    if not categories:
        missing.append("kategorię")
    st.warning("Przed zapisem dodaj: " + ", ".join(missing) + ".")
    st.stop()

st.divider()
st.subheader("Weryfikacja pól")
with st.form("pdf_verification_form"):
    first_row = st.columns(2)
    with first_row[0]:
        invoice_number = st.text_input(
            "Numer faktury",
            value=fields.invoice_number or "",
        )
        contractor = st.selectbox(
            "Kontrahent",
            contractors,
            index=matching_contractor_index(contractors, fields),
            format_func=lambda item: item.name,
        )
        investment = st.selectbox(
            "Inwestycja",
            investments,
            format_func=lambda item: item.name,
        )
    with first_row[1]:
        category = st.selectbox(
            "Kategoria",
            categories,
            format_func=lambda item: item.name,
        )
        invoice_type = st.selectbox(
            "Typ faktury",
            list(InvoiceType),
            format_func=invoice_type_label,
        )
        st.text_input("Waluta wykryta w PDF", value=fields.currency or "", disabled=True)

    date_row = st.columns(3)
    with date_row[0]:
        issue_date = st.date_input(
            "Data wystawienia",
            value=parsed_date(fields.issue_date, date.today()),
        )
    with date_row[1]:
        has_payment_date = st.checkbox(
            "Ustaw termin płatności",
            value=fields.payment_date is not None,
        )
    with date_row[2]:
        payment_date = st.date_input(
            "Termin płatności",
            value=parsed_date(fields.payment_date, date.today() + timedelta(days=14)),
            disabled=not has_payment_date,
        )

    amount_row = st.columns(3)
    with amount_row[0]:
        net_amount = st.number_input(
            "Kwota netto",
            min_value=0.0,
            value=float(fields.net_amount or 0.0),
            step=0.01,
            format="%.2f",
        )
    with amount_row[1]:
        vat_amount = st.number_input(
            "Kwota VAT",
            min_value=0.0,
            value=float(fields.vat_amount or 0.0),
            step=0.01,
            format="%.2f",
        )
    with amount_row[2]:
        gross_amount = st.number_input(
            "Kwota brutto",
            min_value=0.0,
            value=float(fields.gross_amount or 0.0),
            step=0.01,
            format="%.2f",
        )

    save_mode = st.radio(
        "Sposób zapisu",
        (InvoiceStatus.NEEDS_REVIEW, InvoiceStatus.APPROVED),
        format_func=status_label,
        horizontal=True,
    )
    duplicate = context.document_service.find_duplicate(
        invoice_number.strip(), contractor.id
    )
    if duplicate is not None:
        st.warning(
            "Ta faktura już istnieje dla wybranego kontrahenta "
            f"(id: {duplicate.id})."
        )
    submitted = st.form_submit_button(
        "Zapisz fakturę",
        type="primary",
        use_container_width=True,
        disabled=duplicate is not None,
    )

if submitted:
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
        gross_amount=float(gross_amount),
    )
    try:
        created = context.document_service.save_verified_invoice(
            analysis,
            invoice,
            approve=save_mode is InvoiceStatus.APPROVED,
        )
        st.success(f"Faktura {created.invoice_number} została zapisana.")
        st.page_link("pages/2_Faktury.py", label="Przejdź do listy faktur")
    except Exception as error:
        show_service_exception(error)
