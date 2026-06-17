"""CSV and XLSX invoice import workflow."""

from __future__ import annotations

import hashlib

import streamlit as st

from invoice_manager.importers.mapping import IMPORT_FIELDS
from invoice_manager.models.invoice import InvoiceStatus, InvoiceType
from invoice_manager.ui.components import (
    build_app_context,
    configure_page,
    page_header,
)
from invoice_manager.ui.forms import invoice_type_label, status_label
from invoice_manager.ui.messages import show_service_exception

PREVIEW_KEY = "invoice_import_preview"
REPORT_KEY = "invoice_import_report"
FILE_HASH_KEY = "invoice_import_file_hash"


def issue_rows(preview) -> list[dict[str, object]]:
    return [
        {
            "Wiersz": row.row_number,
            "Numer faktury": row.values.get("invoice_number", ""),
            "Kontrahent": row.values.get("contractor_name", ""),
            "Status": (
                "Duplikat"
                if row.duplicate_kind
                else "Błąd"
                if row.errors
                else "Poprawny"
            ),
            "Rodzaj duplikatu": row.duplicate_kind or "",
            "Błędy": " | ".join(row.errors),
            "Ostrzeżenia": " | ".join(row.warnings),
        }
        for row in preview.rows
    ]


configure_page("Import")
page_header(
    "Import faktur",
    "Wczytaj CSV lub XLSX, sprawdź mapowanie i zweryfikuj dane przed zapisem.",
)

try:
    context = build_app_context()
    categories = context.lookup_service.list_categories()
except Exception as error:
    st.error(f"Nie udało się przygotować importu: {error}")
    st.stop()

if not categories:
    st.warning("Brak kategorii. Najpierw zainicjalizuj bazę danych.")
    st.stop()

uploaded_file = st.file_uploader("Plik źródłowy", type=("csv", "xlsx"))
if uploaded_file is None:
    st.info("Wybierz plik CSV lub XLSX, aby rozpocząć import.")
    st.stop()

content = uploaded_file.getvalue()
file_hash = hashlib.sha256(content).hexdigest()
if st.session_state.get(FILE_HASH_KEY) != file_hash:
    st.session_state[FILE_HASH_KEY] = file_hash
    st.session_state.pop(PREVIEW_KEY, None)
    st.session_state.pop(REPORT_KEY, None)

try:
    table = context.import_service.read_file(content, uploaded_file.name)
except Exception as error:
    st.error(f"Nie udało się odczytać pliku: {error}")
    st.stop()

st.subheader("Podgląd danych")
st.caption(f"Wiersze danych: {len(table.rows)} | Kolumny: {len(table.headers)}")
st.dataframe(table.rows[:20], use_container_width=True, hide_index=True)

st.subheader("Mapowanie kolumn")
suggested = context.import_service.suggest_mapping(table.headers)
mapping: dict[str, str | None] = {}
mapping_columns = st.columns(3)
for index, (field, label) in enumerate(IMPORT_FIELDS.items()):
    with mapping_columns[index % 3]:
        options = [None, *table.headers]
        suggestion = suggested.get(field)
        default_index = options.index(suggestion) if suggestion in options else 0
        mapping[field] = st.selectbox(
            label,
            options,
            index=default_index,
            format_func=lambda value: "Brak mapowania" if value is None else value,
            key=f"import_mapping_{file_hash}_{field}",
        )

defaults = st.columns(3)
with defaults[0]:
    default_category = st.selectbox(
        "Domyślna kategoria",
        categories,
        format_func=lambda item: item.name,
    )
with defaults[1]:
    default_invoice_type = st.selectbox(
        "Domyślny typ faktury",
        list(InvoiceType),
        format_func=invoice_type_label,
    )
with defaults[2]:
    default_status = st.selectbox(
        "Domyślny status",
        (
            InvoiceStatus.DRAFT_MANUAL,
            InvoiceStatus.NEEDS_REVIEW,
            InvoiceStatus.APPROVED,
        ),
        format_func=status_label,
    )

create_missing = st.checkbox(
    "Utwórz brakujących kontrahentów i inwestycje podczas importu",
    value=False,
)

if st.button("Analizuj dane", type="primary", use_container_width=True):
    try:
        st.session_state[PREVIEW_KEY] = context.import_service.analyze(
            table,
            mapping,
            default_category_id=default_category.id,
            default_invoice_type=default_invoice_type,
            default_status=default_status,
            source_file=uploaded_file.name,
        )
        st.session_state.pop(REPORT_KEY, None)
    except Exception as error:
        show_service_exception(error)

preview = st.session_state.get(PREVIEW_KEY)
if preview is None:
    st.stop()

st.divider()
st.subheader("Wynik analizy")
if preview.mapping_errors:
    for error in preview.mapping_errors:
        st.error(error)
    st.stop()

metrics = st.columns(4)
metrics[0].metric("Wiersze", preview.total_rows)
metrics[1].metric("Poprawne", preview.valid_rows)
metrics[2].metric("Z błędami", preview.error_rows)
metrics[3].metric("Duplikaty", preview.duplicate_rows)

analysis_rows = issue_rows(preview)
st.dataframe(analysis_rows, use_container_width=True, hide_index=True)

duplicates = [row for row in analysis_rows if row["Rodzaj duplikatu"]]
if duplicates:
    st.subheader("Duplikaty pomijane podczas importu")
    st.dataframe(duplicates, use_container_width=True, hide_index=True)

if any(row.warnings for row in preview.rows):
    st.warning(
        "Analiza zawiera ostrzeżenia. Nieznane podmioty zostaną utworzone tylko "
        "po zaznaczeniu odpowiedniej opcji."
    )

if st.button(
    "Wykonaj import",
    type="primary",
    use_container_width=True,
    disabled=preview.valid_rows == 0,
):
    try:
        st.session_state[REPORT_KEY] = context.import_service.execute(
            preview,
            create_missing_entities=create_missing,
        )
    except Exception as error:
        show_service_exception(error)

report = st.session_state.get(REPORT_KEY)
if report is not None:
    st.divider()
    st.subheader("Raport importu")
    report_metrics = st.columns(5)
    report_metrics[0].metric("W pliku", report.total_rows)
    report_metrics[1].metric("Poprawne", report.valid_rows)
    report_metrics[2].metric("Zaimportowane", report.imported_rows)
    report_metrics[3].metric("Pominięte", report.skipped_rows)
    report_metrics[4].metric("Duplikaty", report.duplicate_rows)
    if report.imported_rows:
        st.success(f"Zaimportowano faktury: {report.imported_rows}.")
    if report.errors:
        st.error("Błędy importu:")
        for error in report.errors:
            st.markdown(f"- {error}")
    if report.warnings:
        with st.expander("Ostrzeżenia"):
            for warning in report.warnings:
                st.markdown(f"- {warning}")
