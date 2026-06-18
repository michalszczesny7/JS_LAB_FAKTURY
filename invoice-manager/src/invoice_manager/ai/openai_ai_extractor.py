"""OpenAI Responses API adapter for structured invoice extraction."""

from __future__ import annotations

import json
from typing import Any

from invoice_manager.ai.ai_extractor import InvoiceAIExtractor
from invoice_manager.ai.invoice_ai_schema import (
    AIInvoiceExtractionResult,
    invoice_extraction_json_schema,
)
from invoice_manager.ai.prompts import SYSTEM_PROMPT, build_user_prompt
from invoice_manager.config import get_openai_api_key, get_openai_model


class OpenAIInvoiceAIExtractor(InvoiceAIExtractor):
    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        client: Any | None = None,
    ) -> None:
        self.api_key = api_key if api_key is not None else get_openai_api_key()
        self.model = model or get_openai_model()
        self._client = client

    @property
    def is_configured(self) -> bool:
        return self._client is not None or bool(self.api_key)

    def extract(self, text: str) -> AIInvoiceExtractionResult:
        if not text.strip():
            return _failure("Brak tekstu faktury do analizy przez OpenAI.")
        if not self.is_configured:
            return _failure(
                "Brak OPENAI_API_KEY — ekstraktor OpenAI nie został uruchomiony."
            )

        try:
            response = self._get_client().responses.create(
                model=self.model,
                input=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": build_user_prompt(text)},
                ],
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "invoice_extraction",
                        "strict": True,
                        "schema": invoice_extraction_json_schema(),
                    }
                },
            )
            raw_response = getattr(response, "output_text", "") or ""
            payload = json.loads(raw_response)
            if not isinstance(payload, dict):
                raise ValueError("odpowiedź JSON nie jest obiektem")
            return AIInvoiceExtractionResult.from_mapping(
                payload,
                raw_response=raw_response,
            )
        except Exception as error:
            return _failure(f"Nie udało się odczytać odpowiedzi OpenAI: {error}")

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError as error:
                raise RuntimeError(
                    "Integracja OpenAI wymaga pakietu openai z requirements.txt."
                ) from error
            self._client = OpenAI(api_key=self.api_key)
        return self._client


def _failure(message: str) -> AIInvoiceExtractionResult:
    return AIInvoiceExtractionResult(warnings=[message])
