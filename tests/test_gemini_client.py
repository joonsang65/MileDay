from __future__ import annotations

import httpx
import pytest

from exceptions.common import ExternalServiceError
from infrastructure.gemini_client import GeminiClient, get_gemini_client


class FakeResponse:
    def __init__(self, payload: dict, *, status_error: Exception | None = None) -> None:
        self.payload = payload
        self.status_error = status_error

    def raise_for_status(self) -> None:
        if self.status_error is not None:
            raise self.status_error

    def json(self) -> dict:
        return self.payload


class FakeHttpClient:
    def __init__(self, response: FakeResponse | Exception) -> None:
        self.response = response
        self.closed = False
        self.calls = []

    def post(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        if isinstance(self.response, Exception):
            raise self.response
        return self.response

    def close(self) -> None:
        self.closed = True


def response_payload(text: str) -> dict:
    return {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": text}],
                }
            }
        ]
    }


def test_gemini_client_sends_structured_output_payload() -> None:
    fake_http = FakeHttpClient(FakeResponse(response_payload('{"ok": true}')))
    client = GeminiClient(
        api_key="api-key",
        model="gemini-test",
        base_url="https://example.test",
        client=fake_http,
    )

    result = client.generate_json(
        prompt="draft",
        response_schema={"type": "object"},
        timeout_seconds=3,
    )

    assert result == '{"ok": true}'
    args, kwargs = fake_http.calls[0]
    assert args[0] == "https://example.test/models/gemini-test:generateContent"
    assert kwargs["headers"]["x-goog-api-key"] == "api-key"
    generation_config = kwargs["json"]["generationConfig"]
    assert generation_config["responseMimeType"] == "application/json"
    assert generation_config["responseSchema"] == {"type": "object"}


def test_gemini_client_converts_http_errors() -> None:
    request = httpx.Request("POST", "https://example.test")
    response = httpx.Response(429, request=request)
    fake_http = FakeHttpClient(
        FakeResponse(
            response_payload("{}"),
            status_error=httpx.HTTPStatusError(
                "too many requests",
                request=request,
                response=response,
            ),
        )
    )
    client = GeminiClient(api_key="api-key", model="gemini-test", client=fake_http)

    with pytest.raises(ExternalServiceError) as exc_info:
        client.generate_json(prompt="draft", response_schema={})

    assert exc_info.value.detail["type"] == "HTTPStatusError"


def test_gemini_client_converts_invalid_response() -> None:
    client = GeminiClient(
        api_key="api-key",
        model="gemini-test",
        client=FakeHttpClient(FakeResponse({"candidates": []})),
    )

    with pytest.raises(ExternalServiceError) as exc_info:
        client.generate_json(prompt="draft", response_schema={})

    assert exc_info.value.detail["type"] == "ValueError"


def test_get_gemini_client_requires_api_key(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    from core.config import get_settings

    get_settings.cache_clear()
    with pytest.raises(ExternalServiceError) as exc_info:
        get_gemini_client()

    assert exc_info.value.detail["missing"] == ["GEMINI_API_KEY"]
    get_settings.cache_clear()
