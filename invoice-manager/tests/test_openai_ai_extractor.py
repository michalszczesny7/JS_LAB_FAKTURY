"""Tests for OpenAI extraction without network calls."""

from types import SimpleNamespace

from invoice_manager.ai.openai_ai_extractor import OpenAIInvoiceAIExtractor


class FakeResponses:
    def __init__(self, output_text: str):
        self.output_text = output_text
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(output_text=self.output_text)


class FakeClient:
    def __init__(self, output_text: str):
        self.responses = FakeResponses(output_text)


def test_missing_api_key_returns_warning_without_creating_client(monkeypatch):
    extractor = OpenAIInvoiceAIExtractor(api_key="")
    monkeypatch.setattr(
        extractor,
        "_get_client",
        lambda: (_ for _ in ()).throw(AssertionError("client must not be created")),
    )

    result = extractor.extract("Faktura nr FV/1")

    assert result.invoice_number is None
    assert any("OPENAI_API_KEY" in warning for warning in result.warnings)


def test_openai_response_is_parsed_with_strict_json_schema():
    raw = """{
        "invoice_number": "FV/API/1",
        "issue_date": "2026-06-17",
        "payment_date": null,
        "contractor_name": "Test Bud",
        "contractor_nip": null,
        "invoice_type": "COST",
        "category": "Materiały",
        "net_amount": 100,
        "vat_amount": 23,
        "gross_amount": 123,
        "payment_status": "UNPAID",
        "confidence": 0.91,
        "field_confidence": {
            "invoice_number": 0.99,
            "issue_date": 0.95,
            "payment_date": null,
            "contractor_name": 0.9,
            "contractor_nip": null,
            "invoice_type": 0.8,
            "category": 0.7,
            "net_amount": 0.99,
            "vat_amount": 0.99,
            "gross_amount": 0.99,
            "payment_status": 0.6
        },
        "warnings": []
    }"""
    client = FakeClient(raw)
    extractor = OpenAIInvoiceAIExtractor(client=client, model="test-model")

    result = extractor.extract("tekst faktury")

    assert result.invoice_number == "FV/API/1"
    assert result.raw_response == raw
    assert len(client.responses.calls) == 1
    call = client.responses.calls[0]
    assert call["model"] == "test-model"
    assert call["text"]["format"]["type"] == "json_schema"
    assert call["text"]["format"]["strict"] is True


def test_invalid_ai_response_becomes_readable_warning():
    client = FakeClient("this is not json")
    result = OpenAIInvoiceAIExtractor(client=client).extract("tekst faktury")

    assert result.invoice_number is None
    assert any("Nie udało się odczytać" in warning for warning in result.warnings)
