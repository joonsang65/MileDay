from __future__ import annotations

from collections.abc import Iterator
from time import perf_counter
from typing import Any

import httpx

from harness.runtime.base import RuntimeChunk, RuntimeRequest, RuntimeResponse
from harness.schemas import EvaluationError, FailureCategory, RuntimeMetrics


class GeminiRuntime:
    """Runtime adapter for Gemini generateContent-compatible text generation."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://generativelanguage.googleapis.com/v1beta",
        client: httpx.Client | None = None,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self._client = client

    def stream(self, request: RuntimeRequest) -> Iterator[RuntimeChunk]:
        response = self.generate(request)
        yield RuntimeChunk(
            text=response.text,
            done=True,
            metadata={
                **response.metadata,
                **({"error": response.error.model_dump(mode="json")} if response.error else {}),
            },
        )

    def generate(self, request: RuntimeRequest) -> RuntimeResponse:
        started_at = perf_counter()
        metadata: dict[str, object] = {}
        client = self._client or httpx.Client(timeout=request.timeout_seconds)
        should_close = self._client is None
        try:
            response = client.post(
                f"{self.base_url}/models/{request.model_tag}:generateContent",
                headers={
                    "x-goog-api-key": self.api_key,
                    "Content-Type": "application/json",
                },
                json=_gemini_payload(request),
                timeout=request.timeout_seconds,
            )
            completed_at = perf_counter()
            _raise_for_http_status(response)
            response_json = response.json()
            metadata = {
                "provider": "gemini",
                "usage_metadata": response_json.get("usageMetadata", {}),
            }
            text = _extract_gemini_text(response_json)
            metrics = _metrics_from_usage(
                metadata["usage_metadata"],
                latency_ms=_elapsed_ms(started_at, completed_at),
            )
            return RuntimeResponse(
                model_tag=request.model_tag,
                text=text,
                metrics=metrics,
                metadata=metadata,
            )
        except httpx.TimeoutException as exc:
            return _error_response(
                request,
                started_at,
                FailureCategory.TIMEOUT,
                str(exc),
                metadata=metadata,
            )
        except httpx.HTTPError as exc:
            return _error_response(
                request,
                started_at,
                FailureCategory.EXTERNAL_DEPENDENCY,
                str(exc),
                metadata=metadata,
            )
        except (ValueError, KeyError, TypeError) as exc:
            return _error_response(
                request,
                started_at,
                FailureCategory.PARSER_ERROR,
                f"Invalid Gemini response: {exc}",
                metadata=metadata,
            )
        finally:
            if should_close:
                client.close()


def _gemini_payload(request: RuntimeRequest) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": request.prompt}],
            }
        ],
    }
    if request.system:
        payload["systemInstruction"] = {"parts": [{"text": request.system}]}

    generation_config = _generation_config(request)
    if generation_config:
        payload["generationConfig"] = generation_config
    return payload


def _generation_config(request: RuntimeRequest) -> dict[str, Any]:
    config: dict[str, Any] = {}
    for source, target in {
        "temperature": "temperature",
        "top_p": "topP",
        "topP": "topP",
        "top_k": "topK",
        "topK": "topK",
        "max_tokens": "maxOutputTokens",
        "maxOutputTokens": "maxOutputTokens",
    }.items():
        if source in request.options:
            config[target] = request.options[source]
    thinking_level = request.options.get("thinking_level") or request.options.get("thinkingLevel")
    if isinstance(thinking_level, str) and thinking_level:
        config["thinkingConfig"] = {"thinkingLevel": thinking_level}

    if request.response_format == "json":
        config["responseMimeType"] = "application/json"
    elif isinstance(request.response_format, dict):
        config["responseMimeType"] = "application/json"
        config["responseSchema"] = request.response_format
    return config


def _extract_gemini_text(response_json: dict[str, Any]) -> str:
    candidates = response_json.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise ValueError("missing candidates")
    content = candidates[0].get("content")
    if not isinstance(content, dict):
        raise ValueError("missing candidate content")
    parts = content.get("parts")
    if not isinstance(parts, list):
        raise ValueError("missing candidate parts")
    return "".join(str(part.get("text", "")) for part in parts if isinstance(part, dict))


def _raise_for_http_status(response: httpx.Response) -> None:
    if response.status_code == 404:
        raise httpx.HTTPStatusError(
            f"Gemini model or endpoint was not found: HTTP {response.status_code}",
            request=response.request,
            response=response,
        )
    response.raise_for_status()


def _metrics_from_usage(usage: object, *, latency_ms: int) -> RuntimeMetrics:
    output_tokens = None
    if isinstance(usage, dict):
        candidates_token_count = usage.get("candidatesTokenCount")
        if isinstance(candidates_token_count, int):
            output_tokens = candidates_token_count
    tokens_per_second = None
    if output_tokens is not None and latency_ms > 0:
        tokens_per_second = output_tokens / (latency_ms / 1000)
    return RuntimeMetrics(
        ttft_ms=None,
        latency_ms=latency_ms,
        tokens_per_second=tokens_per_second,
    )


def _error_response(
    request: RuntimeRequest,
    started_at: float,
    category: FailureCategory,
    message: str,
    *,
    metadata: dict[str, object],
) -> RuntimeResponse:
    completed_at = perf_counter()
    return RuntimeResponse(
        model_tag=request.model_tag,
        text="",
        metrics=RuntimeMetrics(
            latency_ms=_elapsed_ms(started_at, completed_at),
        ),
        metadata=metadata,
        error=EvaluationError(category=category, message=message),
    )


def _elapsed_ms(started_at: float, completed_at: float) -> int:
    return max(1, round((completed_at - started_at) * 1000))
