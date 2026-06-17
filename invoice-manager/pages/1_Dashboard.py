"""Basic approved-invoice dashboard."""

from __future__ import annotations

import streamlit as st

from invoice_manager.ui.components import (
    build_app_context,
    configure_page,
    page_header,
)
from invoice_manager.ui.tables import calculate_dashboard_metrics


def currency(value: float) -> str:
    return f"{value:,.2f} zł".replace(",", " ")


configure_page("Dashboard")
page_header(
    "Dashboard",
    "Podsumowanie zatwierdzonych faktur i bieżącego stanu płatności.",
)

try:
    context = build_app_context()
    invoices = context.invoice_service.list_approved_invoices()
except Exception as error:
    st.error(f"Nie udało się odczytać danych: {error}")
    st.info("Wróć na stronę główną i zainicjalizuj bazę danych.")
    st.stop()

if not invoices:
    st.info("Brak zatwierdzonych faktur do podsumowania.")
    st.page_link(
        "pages/3_Dodaj_fakture.py",
        label="Dodaj pierwszą fakturę",
        use_container_width=False,
    )
    st.stop()

metrics = calculate_dashboard_metrics(invoices)

primary = st.columns(4)
primary[0].metric("Zatwierdzone faktury", metrics.approved_count)
primary[1].metric("Koszty", currency(metrics.costs))
primary[2].metric("Przychody", currency(metrics.revenue))
primary[3].metric("Bilans", currency(metrics.balance))

secondary = st.columns(2)
secondary[0].metric("Niezapłacone", metrics.unpaid_count)
secondary[1].metric("Po terminie", metrics.overdue_count)
