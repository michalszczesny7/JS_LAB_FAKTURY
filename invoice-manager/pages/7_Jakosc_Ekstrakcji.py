"""Offline quality dashboard for the bundled reference invoices."""

from __future__ import annotations

import streamlit as st

from invoice_manager.evaluation import ExtractionEvaluator, load_reference_cases
from invoice_manager.services.ai_review_service import AIReviewMethod
from invoice_manager.ui.components import configure_page, page_header

METHOD_LABELS = {
    AIReviewMethod.LOCAL: "Lokalna ekstrakcja regex",
    AIReviewMethod.MOCK: "AI demo/mock",
}


def _display_value(value: object) -> str:
    return "null" if value is None else str(value)


configure_page("Jakość ekstrakcji")
page_header(
    "Jakość ekstrakcji faktur",
    "Porównaj wynik offline z oczekiwanymi wartościami fikcyjnych faktur.",
)

method = st.radio(
    "Metoda",
    list(METHOD_LABELS),
    format_func=METHOD_LABELS.get,
    horizontal=True,
)

try:
    cases = load_reference_cases()
except Exception as error:
    st.error(f"Nie udało się wczytać danych referencyjnych: {error}")
    st.stop()

if st.button("Uruchom ocenę", type="primary", width="stretch"):
    st.session_state["extraction_quality_report"] = ExtractionEvaluator().evaluate(
        cases,
        method,
    )

report = st.session_state.get("extraction_quality_report")
if report is None:
    st.info(f"Gotowe przypadki referencyjne: {len(cases)}.")
    st.stop()

metrics = st.columns(4)
metrics[0].metric("Wynik ogólny", f"{report.score:.1%}")
metrics[1].metric("Pola poprawne", report.correct_count)
metrics[2].metric("Pola błędne", report.incorrect_count)
metrics[3].metric("Pola brakujące", report.missing_count)

summary_rows = [
    {
        "Przypadek": result.case_name,
        "Metoda": result.used_method,
        "Poprawne": result.correct_count,
        "Błędne": result.incorrect_count,
        "Brakujące": result.missing_count,
        "Wynik": f"{result.score:.1%}",
    }
    for result in report.results
]
st.dataframe(summary_rows, width="stretch", hide_index=True)

for result in report.results:
    with st.expander(f"{result.case_name} — {result.score:.1%}"):
        st.dataframe(
            [
                {
                    "Pole": comparison.field,
                    "Oczekiwane": _display_value(comparison.expected),
                    "Odczytane": _display_value(comparison.actual),
                    "Status": comparison.status,
                }
                for comparison in result.comparisons
            ],
            width="stretch",
            hide_index=True,
        )
