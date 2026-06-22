"""Periodic invoice reports and filtered CSV/XLSX exports."""

from __future__ import annotations

from datetime import date

import streamlit as st

from invoice_manager.exporters import export_report_csv, export_report_xlsx
from invoice_manager.models.invoice import InvoiceStatus, InvoiceType
from invoice_manager.services.report_service import ReportFilters
from invoice_manager.ui.components import (
    build_app_context,
    configure_page,
    page_header,
)
from invoice_manager.ui.forms import (
    PAYMENT_STATUS_LABELS,
    invoice_type_label,
    payment_status_label,
    status_label,
)

FILTERS_KEY = "invoice_report_filters"


def currency(value: float) -> str:
    return f"{value:,.2f} zł".replace(",", " ")


def invoice_rows(report) -> list[dict[str, object]]:
    return [
        {
            "ID": row.id,
            "Numer": row.invoice_number,
            "Data": row.issue_date,
            "Termin płatności": row.payment_date or "-",
            "Kontrahent": row.contractor,
            "Inwestycja": row.investment,
            "Kategoria": row.category,
            "Typ": invoice_type_label(InvoiceType(row.invoice_type)),
            "Status": status_label(InvoiceStatus(row.status)),
            "Płatność": payment_status_label(row.payment_status),
            "Netto": row.net_amount,
            "VAT": row.vat_amount,
            "Brutto": row.gross_amount,
        }
        for row in report.invoices
    ]


def group_rows(items, label: str) -> list[dict[str, object]]:
    return [
        {
            label: item.name,
            "Liczba faktur": item.invoice_count,
            "Netto": item.net_total,
            "VAT": item.vat_total,
            "Brutto": item.gross_total,
        }
        for item in items
    ]


def show_table(rows: list[dict[str, object]]) -> None:
    if not rows:
        st.info("Brak danych dla wybranych filtrów.")
        return
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


configure_page("Raporty")
page_header(
    "Raporty",
    "Filtruj faktury, analizuj podsumowania i pobieraj dane w CSV lub XLSX.",
)

try:
    context = build_app_context()
    contractors = context.lookup_service.list_contractors()
    investments = context.lookup_service.list_investments()
    categories = context.lookup_service.list_categories()
    all_invoices = context.invoice_repository.list_all(include_deleted=True)
except Exception as error:
    st.error(f"Nie udało się przygotować raportu: {error}")
    st.stop()

available_dates = []
for invoice in all_invoices:
    try:
        available_dates.append(date.fromisoformat(invoice.issue_date))
    except ValueError:
        continue
minimum_date = min(available_dates, default=date.today())
maximum_date = max(available_dates, default=date.today())

with st.form("report_filters"):
    use_date_range = st.checkbox("Ogranicz zakres dat", value=False)
    date_columns = st.columns(2)
    with date_columns[0]:
        date_from = st.date_input("Data od", value=minimum_date)
    with date_columns[1]:
        date_to = st.date_input("Data do", value=maximum_date)

    first_row = st.columns(3)
    with first_row[0]:
        investment = st.selectbox(
            "Inwestycja",
            [None, *investments],
            format_func=lambda item: "Wszystkie" if item is None else item.name,
        )
    with first_row[1]:
        contractor = st.selectbox(
            "Kontrahent",
            [None, *contractors],
            format_func=lambda item: "Wszyscy" if item is None else item.name,
        )
    with first_row[2]:
        category = st.selectbox(
            "Kategoria",
            [None, *categories],
            format_func=lambda item: "Wszystkie" if item is None else item.name,
        )

    second_row = st.columns(3)
    with second_row[0]:
        invoice_type = st.selectbox(
            "Typ faktury",
            [None, *InvoiceType],
            format_func=lambda item: (
                "Wszystkie" if item is None else invoice_type_label(item)
            ),
        )
    with second_row[1]:
        invoice_status = st.selectbox(
            "Status faktury",
            [None, *InvoiceStatus],
            format_func=lambda item: "Wszystkie" if item is None else status_label(item),
        )
    with second_row[2]:
        payment_status = st.selectbox(
            "Status płatności",
            [None, *PAYMENT_STATUS_LABELS],
            format_func=lambda item: (
                "Wszystkie" if item is None else payment_status_label(item)
            ),
        )

    include_deleted = st.checkbox("Uwzględnij miękko usunięte faktury", value=False)
    refresh = st.form_submit_button(
        "Odśwież raport", type="primary", use_container_width=True
    )

if refresh or FILTERS_KEY not in st.session_state:
    st.session_state[FILTERS_KEY] = ReportFilters(
        date_from=date_from if use_date_range else None,
        date_to=date_to if use_date_range else None,
        investment_id=investment.id if investment else None,
        contractor_id=contractor.id if contractor else None,
        category_id=category.id if category else None,
        invoice_type=invoice_type,
        status=invoice_status,
        payment_status=payment_status,
        include_deleted=include_deleted,
    )

try:
    report = context.report_service.generate(st.session_state[FILTERS_KEY])
except ValueError as error:
    st.error(str(error))
    st.stop()

st.divider()
kpis = st.columns(4)
kpis[0].metric("Liczba faktur", report.kpis.invoice_count)
kpis[1].metric("Suma netto", currency(report.kpis.net_total))
kpis[2].metric("Suma VAT", currency(report.kpis.vat_total))
kpis[3].metric("Suma brutto", currency(report.kpis.gross_total))

status_kpis = st.columns(3)
status_kpis[0].metric("Zatwierdzone", report.kpis.approved_count)
status_kpis[1].metric("Odrzucone", report.kpis.rejected_count)
status_kpis[2].metric("Usunięte", report.kpis.deleted_count)

st.subheader("Wartość faktur w czasie")
monthly_chart_rows = group_rows(report.monthly, "Miesiąc")
if monthly_chart_rows:
    st.bar_chart(
        monthly_chart_rows,
        x="Miesiąc",
        y=("Netto", "VAT"),
        x_label="Miesiąc",
        y_label="Wartość [zł]",
        use_container_width=True,
    )
else:
    st.info("Brak danych do wyświetlenia wykresu.")

tabs = st.tabs(
    (
        "Faktury",
        "Według inwestycji",
        "Według kontrahentów",
        "Miesięcznie",
        "Według statusu",
    )
)
with tabs[0]:
    show_table(invoice_rows(report))
with tabs[1]:
    show_table(group_rows(report.by_investment, "Inwestycja"))
with tabs[2]:
    show_table(group_rows(report.by_contractor, "Kontrahent"))
with tabs[3]:
    show_table(group_rows(report.monthly, "Miesiąc"))
with tabs[4]:
    show_table(group_rows(report.by_status, "Status"))

st.subheader("Eksport")
filename_suffix = date.today().isoformat()
downloads = st.columns(2)
with downloads[0]:
    st.download_button(
        "Pobierz CSV",
        data=export_report_csv(report),
        file_name=f"raport_faktur_{filename_suffix}.csv",
        mime="text/csv",
        use_container_width=True,
    )
with downloads[1]:
    try:
        xlsx_data = export_report_xlsx(report)
    except RuntimeError as error:
        st.warning(str(error))
    else:
        st.download_button(
            "Pobierz XLSX",
            data=xlsx_data,
            file_name=f"raport_faktur_{filename_suffix}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
