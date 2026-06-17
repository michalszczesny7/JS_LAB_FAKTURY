"""Consistent Streamlit messages for service operations."""

from __future__ import annotations

import streamlit as st

from invoice_manager.services.invoice_service import InvoiceValidationError

FLASH_SUCCESS_KEY = "invoice_manager_success_message"


def show_success(message: str) -> None:
    st.success(message)


def show_error(message: str) -> None:
    st.error(message)


def show_warning(message: str) -> None:
    st.warning(message)


def queue_success(message: str) -> None:
    st.session_state[FLASH_SUCCESS_KEY] = message


def show_pending_message() -> None:
    message = st.session_state.pop(FLASH_SUCCESS_KEY, None)
    if message:
        show_success(message)


def show_service_exception(error: Exception) -> None:
    if isinstance(error, InvoiceValidationError):
        st.error("Nie udało się zapisać faktury:")
        for message in error.result.errors:
            st.markdown(f"- {message}")
        for warning in error.result.warnings:
            st.warning(warning)
        return
    if isinstance(error, LookupError):
        st.error(str(error))
        return
    st.error(f"Operacja nie powiodła się: {error}")
