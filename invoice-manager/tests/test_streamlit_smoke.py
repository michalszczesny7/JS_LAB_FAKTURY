"""Smoke checks for Streamlit entry points and empty UI data."""

from __future__ import annotations

from pathlib import Path

import pytest

from invoice_manager.ui.tables import (
    DashboardMetrics,
    calculate_dashboard_metrics,
    filter_invoices,
    prepare_invoice_rows,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_PATH = PROJECT_ROOT / "app.py"
PAGE_PATHS = (
    PROJECT_ROOT / "pages" / "1_Dashboard.py",
    PROJECT_ROOT / "pages" / "2_Faktury.py",
    PROJECT_ROOT / "pages" / "3_Dodaj_fakture.py",
    PROJECT_ROOT / "pages" / "4_Import_AI.py",
    PROJECT_ROOT / "pages" / "5_Raporty.py",
    PROJECT_ROOT / "pages" / "7_Jakosc_Ekstrakcji.py",
)


def test_streamlit_entry_files_exist_and_compile():
    for path in (APP_PATH, *PAGE_PATHS):
        assert path.is_file(), f"Missing Streamlit entry point: {path}"
        compile(path.read_text(encoding="utf-8"), str(path), "exec")


def test_ui_helpers_handle_empty_data():
    assert calculate_dashboard_metrics([]) == DashboardMetrics(
        approved_count=0,
        costs=0,
        revenue=0,
        balance=0,
        unpaid_count=0,
        overdue_count=0,
    )
    assert prepare_invoice_rows([], {}, {}, {}) == []
    assert filter_invoices([]) == []


def test_app_runs_without_streamlit_exceptions():
    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest

    app = AppTest.from_file(str(APP_PATH), default_timeout=10).run()
    assert not app.exception
