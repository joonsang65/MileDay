from __future__ import annotations

import json
from collections.abc import Iterator
from time import perf_counter
from typing import Any

import httpx

from harness.runtime.base import (
    RuntimeAdapterError,
    RuntimeChunk,
    RuntimeRequest,
    RuntimeResponse,
)
from harness.schemas import FailureCategory, RuntimeMetrics


class OllamaRuntime:
    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        client: httpx.Client | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = client

    def stream(self, request: RuntimeRequest) -> Iterator[RuntimeChunk]:
        payload: dict[str, Any] = {
            "model": request.model_tag,
            "prompt": request.prompt,
            "stream": True,
        }
        if request.system is not None:
            payload["system"] = request.system
        if request.options:
            payload["options"] = request.options

        client = self._client or httpx.Client(timeout=request.timeout_seconds)
        should_close = self._client is None
        try:
            with client.stream(
                "POST",
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=request.timeout_seconds,
            ) as response:
                self._raise_for_http_status(response)
                for line in response.iter_lines():
                    if not line:
                        continue
                    data = self._parse_stream_line(line)
                    yield RuntimeChunk(
                        text=str(data.get("response", "")),
                        done=bool(data.get("done", False)),
                        metadata={
                            key: value
                            for key, value in data.items()
                            if key not in {"response", "done"}
                        },
                    )
        except httpx.TimeoutException as exc:
            raise RuntimeAdapterError(FailureCategory.TIMEOUT, str(exc)) from exc
        except httpx.ConnectError as exc:
            raise RuntimeAdapterError(FailureCategory.OLLAMA_UNAVAILABLE, str(exc)) from exc
        except httpx.HTTPError as exc:
            raise RuntimeAdapterError(FailureCategory.EXTERNAL_DEPENDENCY, str(exc)) from exc
        finally:
            if should_close:
                client.close()

    def generate(self, request: RuntimeRequest) -> RuntimeResponse:
        started_at = perf_counter()
        first_token_at: float | None = None
        chunks: list[str] = []
        metadata: dict[str, object] = {}

        try:
            for chunk in self.stream(request):
                if chunk.text and first_token_at is None:
                    first_token_at = perf_counter()
                chunks.append(chunk.text)
                if chunk.done:
                    metadata.update(chunk.metadata)
            completed_at = perf_counter()
        except RuntimeAdapterError as exc:
            completed_at = perf_counter()
            return RuntimeResponse(
                model_tag=request.model_tag,
                text="",
                metrics=RuntimeMetrics(
                    ttft_ms=None,
                    latency_ms=self._elapsed_ms(started_at, completed_at),
                    tokens_per_second=None,
                ),
                metadata=metadata,
                error=exc.to_evaluation_error(),
            )

        return RuntimeResponse(
            model_tag=request.model_tag,
            text="".join(chunks),
            metrics=RuntimeMetrics(
                ttft_ms=(
                    None
                    if first_token_at is None
                    else self._elapsed_ms(started_at, first_token_at)
                ),
                latency_ms=self._elapsed_ms(started_at, completed_at),
                tokens_per_second=self._tokens_per_second(metadata),
            ),
            metadata=metadata,
        )

    def check_health(self, timeout_seconds: int = 5) -> None:
        client = self._client or httpx.Client(timeout=timeout_seconds)
        should_close = self._client is None
        try:
            response = client.get(f"{self.base_url}/api/tags", timeout=timeout_seconds)
            self._raise_for_http_status(response)
        except httpx.TimeoutException as exc:
            raise RuntimeAdapterError(FailureCategory.TIMEOUT, str(exc)) from exc
        except httpx.ConnectError as exc:
            raise RuntimeAdapterError(FailureCategory.OLLAMA_UNAVAILABLE, str(exc)) from exc
        except httpx.HTTPError as exc:
            raise RuntimeAdapterError(FailureCategory.EXTERNAL_DEPENDENCY, str(exc)) from exc
        finally:
            if should_close:
                client.close()

    @staticmethod
    def _parse_stream_line(line: str) -> dict[str, object]:
        try:
            data = json.loads(line)
        except json.JSONDecodeError as exc:
            raise RuntimeAdapterError(
                FailureCategory.PARSER_ERROR,
                f"Invalid Ollama stream JSON: {exc}",
            ) from exc
        if not isinstance(data, dict):
            raise RuntimeAdapterError(
                FailureCategory.PARSER_ERROR,
                "Ollama stream item must be a JSON object.",
            )
        return data

    @staticmethod
    def _raise_for_http_status(response: httpx.Response) -> None:
        if response.status_code == 404:
            raise RuntimeAdapterError(
                FailureCategory.MODEL_NOT_INSTALLED,
                f"Ollama model or endpoint was not found: HTTP {response.status_code}",
            )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise RuntimeAdapterError(
                FailureCategory.EXTERNAL_DEPENDENCY,
                f"Ollama HTTP error: HTTP {response.status_code}",
            ) from exc

    @staticmethod
    def _elapsed_ms(started_at: float, completed_at: float) -> int:
        return max(0, round((completed_at - started_at) * 1000))

    @staticmethod
    def _tokens_per_second(metadata: dict[str, object]) -> float | None:
        eval_count = metadata.get("eval_count")
        eval_duration = metadata.get("eval_duration")
        if not isinstance(eval_count, int) or not isinstance(eval_duration, int):
            return None
        if eval_duration <= 0:
            return None
        return eval_count / (eval_duration / 1_000_000_000)

