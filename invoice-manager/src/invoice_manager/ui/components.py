"""Shared Streamlit page components and application dependencies."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import streamlit as st

from invoice_manager.repositories.category_repository import CategoryRepository
from invoice_manager.repositories.contractor_repository import ContractorRepository
from invoice_manager.repositories.investment_repository import InvestmentRepository
from invoice_manager.repositories.invoice_repository import InvoiceRepository
from invoice_manager.services.invoice_service import InvoiceService
from invoice_manager.services.import_service import ImportService
from invoice_manager.services.lookup_service import LookupService
from invoice_manager.services.validation_service import ValidationService


@dataclass(slots=True)
class AppContext:
    invoice_repository: InvoiceRepository
    invoice_service: InvoiceService
    import_service: ImportService
    lookup_service: LookupService


def build_app_context(database_path: str | Path | None = None) -> AppContext:
    """Build repositories and services used by a Streamlit page."""

    invoices = InvoiceRepository(database_path)
    contractors = ContractorRepository(database_path)
    investments = InvestmentRepository(database_path)
    categories = CategoryRepository(database_path)
    validation = ValidationService(invoices, contractors, investments, categories)
    invoice_service = InvoiceService(invoices, validation)
    return AppContext(
        invoice_repository=invoices,
        invoice_service=invoice_service,
        import_service=ImportService(
            invoices,
            contractors,
            investments,
            categories,
            invoice_service,
        ),
        lookup_service=LookupService(contractors, investments, categories),
    )


def configure_page(title: str) -> None:
    st.set_page_config(page_title=f"{title} | Invoice Manager", layout="wide")


def page_header(title: str, description: str | None = None) -> None:
    st.title(title)
    if description:
        st.caption(description)


def section_divider() -> None:
    st.divider()


def help_section(text: str) -> None:
    with st.expander("Pomoc"):
        st.write(text)
