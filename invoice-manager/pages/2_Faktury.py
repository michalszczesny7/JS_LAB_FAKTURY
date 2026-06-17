"""Invoice list, filters, and workflow actions."""

from __future__ import annotations

import streamlit as st

from invoice_manager.models.invoice import InvoiceStatus, InvoiceType
from invoice_manager.ui.components import (
    build_app_context,
    configure_page,
    page_header,
)
from invoice_manager.ui.forms import invoice_type_label, status_label
from invoice_manager.ui.messages import (
    queue_success,
    show_pending_message,
    show_service_exception,
)
from invoice_manager.ui.tables import filter_invoices, prepare_invoice_rows


configure_page("Faktury")
page_header("Faktury", "Przeglądaj dokumenty i zarządzaj ich statusem.")
show_pending_message()

try:
    context = build_app_context()
    invoices = context.invoice_repository.list_all(include_deleted=True)
    contractors = context.lookup_service.list_contractors()
    investments = context.lookup_service.list_investments()
    categories = context.lookup_service.list_categories()
except Exception as error:
    st.error(f"Nie udało się odczytać danych: {error}")
    st.info("Wróć na stronę główną i zainicjalizuj bazę danych.")
    st.stop()

if not invoices:
    st.info("Nie ma jeszcze żadnych faktur.")
    st.page_link("pages/3_Dodaj_fakture.py", label="Dodaj pierwszą fakturę")
    st.stop()

filter_row = st.columns(5)
with filter_row[0]:
    selected_status = st.selectbox(
        "Status",
        [None, *InvoiceStatus],
        format_func=lambda value: "Wszystkie" if value is None else status_label(value),
    )
with filter_row[1]:
    selected_investment = st.selectbox(
        "Inwestycja",
        [None, *investments],
        format_func=lambda value: "Wszystkie" if value is None else value.name,
    )
with filter_row[2]:
    selected_contractor = st.selectbox(
        "Kontrahent",
        [None, *contractors],
        format_func=lambda value: "Wszyscy" if value is None else value.name,
    )
with filter_row[3]:
    selected_category = st.selectbox(
        "Kategoria",
        [None, *categories],
        format_func=lambda value: "Wszystkie" if value is None else value.name,
    )
with filter_row[4]:
    selected_type = st.selectbox(
        "Typ",
        [None, *InvoiceType],
        format_func=lambda value: (
            "Wszystkie" if value is None else invoice_type_label(value)
        ),
    )

filtered = filter_invoices(
    invoices,
    status=selected_status,
    investment_id=selected_investment.id if selected_investment else None,
    contractor_id=selected_contractor.id if selected_contractor else None,
    category_id=selected_category.id if selected_category else None,
    invoice_type=selected_type,
)

contractor_names = {item.id: item.name for item in contractors if item.id is not None}
investment_names = {item.id: item.name for item in investments if item.id is not None}
category_names = {item.id: item.name for item in categories if item.id is not None}
rows = prepare_invoice_rows(
    filtered,
    contractor_names,
    investment_names,
    category_names,
)

st.caption(f"Wyniki: {len(filtered)}")
st.dataframe(
    rows,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Netto": st.column_config.NumberColumn(format="%.2f zł"),
        "VAT": st.column_config.NumberColumn(format="%.2f zł"),
        "Brutto": st.column_config.NumberColumn(format="%.2f zł"),
    },
)

st.subheader("Operacje")
if not filtered:
    st.info("Brak faktur spełniających wybrane filtry.")
    st.stop()

selected_invoice = st.selectbox(
    "Faktura",
    filtered,
    format_func=lambda item: f"{item.invoice_number} | {status_label(item.status)}",
)
is_deleted = selected_invoice.status is InvoiceStatus.DELETED
actions = st.columns(3)

with actions[0]:
    if st.button(
        "Zatwierdź",
        type="primary",
        use_container_width=True,
        disabled=is_deleted or selected_invoice.status is InvoiceStatus.APPROVED,
    ):
        try:
            context.invoice_service.approve_invoice(selected_invoice.id)
            queue_success("Faktura została zatwierdzona.")
            st.rerun()
        except Exception as error:
            show_service_exception(error)

with actions[1]:
    if st.button(
        "Odrzuć",
        use_container_width=True,
        disabled=is_deleted or selected_invoice.status is InvoiceStatus.REJECTED,
    ):
        try:
            context.invoice_service.reject_invoice(selected_invoice.id)
            queue_success("Faktura została odrzucona.")
            st.rerun()
        except Exception as error:
            show_service_exception(error)

with actions[2]:
    confirm_delete = st.checkbox(
        "Potwierdzam usunięcie",
        disabled=is_deleted,
    )
    if st.button(
        "Usuń",
        use_container_width=True,
        disabled=is_deleted or not confirm_delete,
    ):
        try:
            context.invoice_service.soft_delete_invoice(selected_invoice.id)
            queue_success("Faktura została oznaczona jako usunięta.")
            st.rerun()
        except Exception as error:
            show_service_exception(error)
