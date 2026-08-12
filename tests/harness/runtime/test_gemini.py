import json

import httpx

from harness.runtime.base import RuntimeRequest
from harness.runtime.gemini import GeminiRuntime
from harness.schemas import FailureCategory


def test_gemini_generate_sends_generation_config_and_parses_text():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["headers"] = dict(request.headers)
        captured["payload"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {"text": "[일정_의도]\n"},
                                {"text": "행동: 생성\n[/일정_의도]"},
                            ]
                        }
                    }
                ],
                "usageMetadata": {
                    "promptTokenCount": 10,
                    "candidatesTokenCount": 5,
                    "totalTokenCount": 15,
                },
            },
            request=request,
        )

    runtime = GeminiRuntime(
        api_key="test-key",
        base_url="https://example.test/v1beta",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    response = runtime.generate(
        RuntimeRequest(
            model_tag="gemini-test",
            prompt="make a schedule",
            system="follow the contract",
            response_format="json",
            options={"temperature": 0.1, "top_p": 0.8, "max_tokens": 128},
        )
    )

    assert response.error is None
    assert response.text == "[일정_의도]\n행동: 생성\n[/일정_의도]"
    assert captured["url"] == "https://example.test/v1beta/models/gemini-test:generateContent"
    assert captured["headers"]["x-goog-api-key"] == "test-key"
    assert captured["payload"]["systemInstruction"]["parts"][0]["text"] == "follow the contract"
    assert captured["payload"]["contents"][0]["parts"][0]["text"] == "make a schedule"
    assert captured["payload"]["generationConfig"] == {
        "temperature": 0.1,
        "topP": 0.8,
        "maxOutputTokens": 128,
        "responseMimeType": "application/json",
    }
    assert response.metadata["usage_metadata"]["candidatesTokenCount"] == 5
    assert response.metrics.latency_ms is not None
    assert response.metrics.tokens_per_second is not None


def test_gemini_generate_categorizes_invalid_response():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"candidates": []}, request=request)

    runtime = GeminiRuntime(
        api_key="test-key",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    response = runtime.generate(RuntimeRequest(model_tag="gemini-test", prompt="hello"))

    assert response.error is not None
    assert response.error.category == FailureCategory.PARSER_ERROR


def test_gemini_generate_sends_thinking_level_config():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["payload"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "candidates": [{"content": {"parts": [{"text": "{}"}]}}],
                "usageMetadata": {},
            },
            request=request,
        )

    runtime = GeminiRuntime(
        api_key="test-key",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    response = runtime.generate(
        RuntimeRequest(
            model_tag="gemini-test",
            prompt="hello",
            options={"thinking_level": "minimal"},
        )
    )

    assert response.error is None
    assert captured["payload"]["generationConfig"]["thinkingConfig"] == {"thinkingLevel": "minimal"}


def test_gemini_generate_categorizes_http_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error": {"message": "quota"}}, request=request)

    runtime = GeminiRuntime(
        api_key="test-key",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    response = runtime.generate(RuntimeRequest(model_tag="gemini-test", prompt="hello"))

    assert response.error is not None
    assert response.error.category == FailureCategory.EXTERNAL_DEPENDENCY
