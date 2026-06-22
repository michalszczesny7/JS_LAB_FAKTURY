"""Invoice list, filters, and workflow actions."""

from __future__ import annotations

from dataclasses import replace
from datetime import date

import streamlit as st

from invoice_manager.models.invoice import InvoiceStatus, InvoiceType
from invoice_manager.ui.components import (
    build_app_context,
    configure_page,
    page_header,
)
from invoice_manager.ui.forms import (
    calculate_gross_amount,
    invoice_type_label,
    status_label,
)
from invoice_manager.ui.messages import (
    queue_success,
    show_pending_message,
    show_service_exception,
)
from invoice_manager.ui.tables import (
    PAYMENT_STATUS_LABELS,
    filter_invoices,
    payment_status_label,
    prepare_invoice_rows,
)


def related_index(items, selected_id: int | None) -> int:
    for index, item in enumerate(items):
        if item.id == selected_id:
            return index
    return 0


def invoice_date(value: str | None, fallback: date) -> date:
    try:
        return date.fromisoformat(value) if value else fallback
    except ValueError:
        return fallback


configure_page("Faktury")
page_header("Faktury", "Przeglądaj dokumenty i zarządzaj ich statusem.")
show_pending_message()

try:
    context = build_app_context()
    invoices = context.invoice_repository.list_all(include_deleted=False)
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
selectable_rows = [{"Wybierz": False, **row} for row in rows]
edited_rows = st.data_editor(
    selectable_rows,
    use_container_width=True,
    hide_index=True,
    disabled=[column for column in selectable_rows[0] if column != "Wybierz"]
    if selectable_rows
    else True,
    column_config={
        "Wybierz": st.column_config.CheckboxColumn(
            "Wybierz",
            help="Zaznacz faktury przeznaczone do masowego usunięcia.",
            default=False,
        ),
        "Netto": st.column_config.NumberColumn(format="%.2f zł"),
        "VAT": st.column_config.NumberColumn(format="%.2f zł"),
        "Brutto": st.column_config.NumberColumn(format="%.2f zł"),
    },
)

selected_rows = (
    edited_rows.to_dict("records")
    if hasattr(edited_rows, "to_dict")
    else list(edited_rows)
)
selected_ids = [
    int(row["ID"])
    for row in selected_rows
    if row.get("Wybierz") and row.get("ID") is not None
]
bulk_actions = st.columns((2, 1))
with bulk_actions[0]:
    st.caption(f"Zaznaczone faktury: {len(selected_ids)}")
with bulk_actions[1]:
    confirm_bulk_delete = st.checkbox(
        "Potwierdzam masowe usunięcie",
        disabled=not selected_ids,
    )
    if st.button(
        "Usuń zaznaczone",
        use_container_width=True,
        disabled=not selected_ids or not confirm_bulk_delete,
    ):
        try:
            deleted_count = context.invoice_service.soft_delete_invoices(selected_ids)
            queue_success(
                f"Oznaczono jako usunięte: {deleted_count} faktur."
            )
            st.rerun()
        except Exception as error:
            show_service_exception(error)

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

st.divider()
st.subheader("Edycja faktury")
st.caption(
    "Możesz zmienić wszystkie dane biznesowe. ID pozostaje stałe, a brutto "
    "jest obliczane automatycznie jako netto + VAT."
)

with st.form(f"edit_invoice_{selected_invoice.id}"):
    identity_columns = st.columns(3)
    with identity_columns[0]:
        st.number_input("ID", value=selected_invoice.id, disabled=True)
        invoice_number = st.text_input(
            "Numer faktury",
            value=selected_invoice.invoice_number,
        )
    with identity_columns[1]:
        contractor = st.selectbox(
            "Kontrahent",
            contractors,
            index=related_index(contractors, selected_invoice.contractor_id),
            format_func=lambda item: item.name,
        )
        investment = st.selectbox(
            "Inwestycja",
            investments,
            index=related_index(investments, selected_invoice.investment_id),
            format_func=lambda item: item.name,
        )
    with identity_columns[2]:
        category = st.selectbox(
            "Kategoria",
            categories,
            index=related_index(categories, selected_invoice.category_id),
            format_func=lambda item: item.name,
        )
        invoice_type = st.selectbox(
            "Typ faktury",
            list(InvoiceType),
            index=list(InvoiceType).index(selected_invoice.invoice_type),
            format_func=invoice_type_label,
        )

    date_columns = st.columns(3)
    with date_columns[0]:
        issue_date = st.date_input(
            "Data wystawienia",
            value=invoice_date(selected_invoice.issue_date, date.today()),
        )
    with date_columns[1]:
        has_payment_date = st.checkbox(
            "Ustaw termin płatności",
            value=selected_invoice.payment_date is not None,
        )
    with date_columns[2]:
        payment_date = st.date_input(
            "Termin płatności",
            value=invoice_date(selected_invoice.payment_date, date.today()),
            disabled=not has_payment_date,
        )

    amount_columns = st.columns(3)
    with amount_columns[0]:
        net_amount = st.number_input(
            "Kwota netto",
            min_value=0.0,
            value=float(selected_invoice.net_amount),
            step=0.01,
            format="%.2f",
        )
    with amount_columns[1]:
        vat_amount = st.number_input(
            "Kwota VAT",
            min_value=0.0,
            value=float(selected_invoice.vat_amount),
            step=0.01,
            format="%.2f",
        )
    with amount_columns[2]:
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

    workflow_columns = st.columns(2)
    with workflow_columns[0]:
        invoice_status = st.selectbox(
            "Status faktury",
            list(InvoiceStatus),
            index=list(InvoiceStatus).index(selected_invoice.status),
            format_func=status_label,
        )
    with workflow_columns[1]:
        payment_status = st.selectbox(
            "Status płatności",
            list(PAYMENT_STATUS_LABELS),
            index=list(PAYMENT_STATUS_LABELS).index(selected_invoice.payment_status),
            format_func=payment_status_label,
        )

    st.caption(
        "Aktualny plik źródłowy: " + (selected_invoice.source_file or "brak")
    )
    source_file = st.file_uploader(
        "Zastąp plik źródłowy (opcjonalnie)",
        type=("pdf", "jpg", "jpeg", "png", "csv"),
    )
    remove_source = st.checkbox(
        "Odłącz obecny plik źródłowy",
        value=False,
        disabled=selected_invoice.source_file is None,
    )
    submitted_edit = st.form_submit_button(
        "Zapisz zmiany",
        type="primary",
        use_container_width=True,
    )

if submitted_edit:
    source_path = selected_invoice.source_file
    file_hash = selected_invoice.file_hash
    try:
        if remove_source:
            source_path = None
            file_hash = None
        if source_file is not None:
            stored_document = context.document_service.store_source_document(
                source_file.getvalue(),
                source_file.name,
                source_file.type,
            )
            source_path = stored_document.relative_path
            file_hash = stored_document.file_hash

        updated_invoice = replace(
            selected_invoice,
            invoice_number=invoice_number.strip(),
            issue_date=issue_date.isoformat(),
            payment_date=payment_date.isoformat() if has_payment_date else None,
            contractor_id=contractor.id,
            investment_id=investment.id,
            category_id=category.id,
            invoice_type=invoice_type,
            status=invoice_status,
            net_amount=float(net_amount),
            vat_amount=float(vat_amount),
            gross_amount=calculate_gross_amount(net_amount, vat_amount),
            payment_status=payment_status,
            source_file=source_path,
            file_hash=file_hash,
        )
        context.invoice_service.update_invoice(updated_invoice)
        queue_success("Zmiany w fakturze zostały zapisane.")
        st.rerun()
    except Exception as error:
        show_service_exception(error)
