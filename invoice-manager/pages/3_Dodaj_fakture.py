"""Manual invoice creation page."""

from __future__ import annotations

from dataclasses import replace

import streamlit as st

from invoice_manager.db.init_db import initialize_database
from invoice_manager.models.contractor import Contractor
from invoice_manager.models.investment import Investment
from invoice_manager.ui.components import (
    build_app_context,
    configure_page,
    page_header,
)
from invoice_manager.ui.forms import render_invoice_form
from invoice_manager.ui.messages import (
    queue_success,
    show_error,
    show_pending_message,
    show_service_exception,
    show_success,
)
from invoice_manager.validators.nip_validator import validate_nip


configure_page("Dodaj fakturę")
page_header("Dodaj fakturę", "Wprowadź dokument ręcznie i zapisz go jako szkic lub zatwierdź.")
show_pending_message()

try:
    context = build_app_context()
except Exception as error:
    st.error(f"Nie udało się połączyć z bazą: {error}")
    st.info("Wróć na stronę główną i zainicjalizuj bazę danych.")
    st.stop()

with st.expander("Szybkie dodawanie kontrahenta"):
    with st.form("quick_contractor_form"):
        contractor_name = st.text_input("Nazwa kontrahenta")
        contractor_nip = st.text_input("NIP (opcjonalnie)")
        contractor_type = st.selectbox(
            "Rodzaj kontrahenta",
            ("SUPPLIER", "CUSTOMER", "BOTH"),
            format_func={
                "SUPPLIER": "Dostawca",
                "CUSTOMER": "Klient",
                "BOTH": "Dostawca i klient",
            }.get,
        )
        add_contractor = st.form_submit_button("Dodaj kontrahenta")
    if add_contractor:
        nip_errors = validate_nip(contractor_nip) if contractor_nip.strip() else []
        if not contractor_name.strip():
            show_error("Nazwa kontrahenta jest wymagana.")
        elif nip_errors:
            for message in nip_errors:
                show_error(message)
        else:
            try:
                context.lookup_service.create_contractor(
                    Contractor(
                        name=contractor_name.strip(),
                        contractor_type=contractor_type,
                        nip=contractor_nip.strip() or None,
                    )
                )
                queue_success("Kontrahent został dodany.")
                st.rerun()
            except Exception as error:
                show_service_exception(error)

with st.expander("Szybkie dodawanie inwestycji"):
    with st.form("quick_investment_form"):
        investment_name = st.text_input("Nazwa inwestycji")
        investment_location = st.text_input("Lokalizacja (opcjonalnie)")
        investment_budget = st.number_input(
            "Budżet", min_value=0.0, step=1000.0, format="%.2f"
        )
        add_investment = st.form_submit_button("Dodaj inwestycję")
    if add_investment:
        if not investment_name.strip():
            show_error("Nazwa inwestycji jest wymagana.")
        else:
            try:
                context.lookup_service.create_investment(
                    Investment(
                        name=investment_name.strip(),
                        location=investment_location.strip() or None,
                        budget=float(investment_budget),
                    )
                )
                queue_success("Inwestycja została dodana.")
                st.rerun()
            except Exception as error:
                show_service_exception(error)

contractors = context.lookup_service.list_contractors()
investments = context.lookup_service.list_investments()
categories = context.lookup_service.list_categories()

with st.expander("Usuń nieużywanego kontrahenta lub inwestycję"):
    st.caption(
        "Można usunąć tylko rekordy, które nie są powiązane z żadną fakturą, "
        "również miękko usuniętą."
    )
    delete_columns = st.columns(2)
    with delete_columns[0]:
        st.markdown("**Kontrahent**")
        if contractors:
            contractor_to_delete = st.selectbox(
                "Wybierz kontrahenta do usunięcia",
                contractors,
                format_func=lambda item: item.name,
            )
            confirm_contractor_delete = st.checkbox(
                "Potwierdzam usunięcie kontrahenta"
            )
            if st.button(
                "Usuń kontrahenta",
                disabled=not confirm_contractor_delete,
                use_container_width=True,
            ):
                try:
                    context.lookup_service.delete_contractor(contractor_to_delete.id)
                    queue_success("Nieużywany kontrahent został usunięty.")
                    st.rerun()
                except Exception as error:
                    show_service_exception(error)
        else:
            st.info("Brak kontrahentów do usunięcia.")

    with delete_columns[1]:
        st.markdown("**Inwestycja**")
        if investments:
            investment_to_delete = st.selectbox(
                "Wybierz inwestycję do usunięcia",
                investments,
                format_func=lambda item: item.name,
            )
            confirm_investment_delete = st.checkbox(
                "Potwierdzam usunięcie inwestycji"
            )
            if st.button(
                "Usuń inwestycję",
                disabled=not confirm_investment_delete,
                use_container_width=True,
            ):
                try:
                    context.lookup_service.delete_investment(investment_to_delete.id)
                    queue_success("Nieużywana inwestycja została usunięta.")
                    st.rerun()
                except Exception as error:
                    show_service_exception(error)
        else:
            st.info("Brak inwestycji do usunięcia.")

missing_data: list[str] = []
if not contractors:
    missing_data.append("kontrahenta")
if not investments:
    missing_data.append("inwestycji")
if not categories:
    missing_data.append("kategorii")

if missing_data:
    st.warning("Przed dodaniem faktury uzupełnij: " + ", ".join(missing_data) + ".")
    if not categories and st.button("Dodaj kategorie domyślne"):
        try:
            initialize_database()
            queue_success("Kategorie domyślne zostały dodane.")
            st.rerun()
        except Exception as error:
            show_service_exception(error)
    st.stop()

st.divider()
submission = render_invoice_form(contractors, investments, categories)
if submission:
    invoice, approve, source_upload = submission
    try:
        if source_upload is not None:
            stored_document = context.document_service.store_source_document(
                source_upload.content,
                source_upload.filename,
                source_upload.mime_type,
            )
            invoice = replace(
                invoice,
                source_file=stored_document.relative_path,
                file_hash=stored_document.file_hash,
            )
        created = context.invoice_service.create_invoice(invoice, approve=approve)
        show_success(f"Faktura {created.invoice_number} została zapisana.")
    except Exception as error:
        show_service_exception(error)
