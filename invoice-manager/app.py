"""Streamlit entry point for Invoice Manager."""

from __future__ import annotations

import streamlit as st

from invoice_manager.config import get_database_path
from invoice_manager.db.init_db import initialize_database
from invoice_manager.ui.components import configure_page, page_header

configure_page("Start")
page_header(
    "Invoice Manager",
    "Proste zarządzanie fakturami kosztowymi i sprzedażowymi dla inwestycji.",
)

database_path = get_database_path()

if not database_path.exists():
    st.warning("Baza danych nie została jeszcze utworzona.")
    st.code("PYTHONPATH=src python3 -m invoice_manager.db.init_db", language="bash")
    if st.button("Zainicjalizuj bazę", type="primary"):
        try:
            initialized_path = initialize_database(database_path)
            st.success(f"Baza danych została utworzona: {initialized_path}")
            st.rerun()
        except Exception as error:
            st.error(f"Nie udało się zainicjalizować bazy: {error}")
else:
    st.success("Baza danych jest gotowa.")
    st.write(
        "Właściwe widoki aplikacji są dostępne w menu bocznym. "
        "Rozpocznij od dodania faktury lub przejdź do dashboardu."
    )
    navigation = st.columns(3)
    with navigation[0]:
        st.page_link("pages/1_Dashboard.py", label="Dashboard", use_container_width=True)
    with navigation[1]:
        st.page_link("pages/2_Faktury.py", label="Faktury", use_container_width=True)
    with navigation[2]:
        st.page_link(
            "pages/3_Dodaj_fakture.py",
            label="Dodaj fakturę",
            use_container_width=True,
        )

st.divider()
st.caption(f"Baza danych: {database_path}")
