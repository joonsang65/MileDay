from __future__ import annotations

from typing import Any

import httpx

from core.config import get_settings
from exceptions.common import ExternalServiceError


class GeminiClient:
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str = "https://generativelanguage.googleapis.com/v1beta",
        client: httpx.Client | None = None,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self._client = client

    def generate_json(
        self,
        *,
        prompt: str,
        response_schema: dict[str, Any],
        timeout_seconds: float = 30.0,
    ) -> str:
        client = self._client or httpx.Client(timeout=timeout_seconds)
        should_close = self._client is None
        try:
            response = client.post(
                f"{self.base_url}/models/{self.model}:generateContent",
                headers={
                    "x-goog-api-key": self.api_key,
                    "Content-Type": "application/json",
                },
                json={
                    "contents": [
                        {
                            "role": "user",
                            "parts": [{"text": prompt}],
                        }
                    ],
                    "generationConfig": {
                        "responseMimeType": "application/json",
                        "responseSchema": response_schema,
                        "temperature": 0.2,
                    },
                },
                timeout=timeout_seconds,
            )
            response.raise_for_status()
            return _extract_text(response.json())
        except httpx.HTTPError as exc:
            raise ExternalServiceError(
                message="AI 일정 초안 생성 요청에 실패했습니다.",
                detail={"type": exc.__class__.__name__},
            ) from exc
        except (KeyError, TypeError, ValueError) as exc:
            raise ExternalServiceError(
                message="AI 일정 초안 응답을 해석하지 못했습니다.",
                detail={"type": exc.__class__.__name__},
            ) from exc
        finally:
            if should_close:
                client.close()


def _extract_text(response_json: dict[str, Any]) -> str:
    candidates = response_json.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise ValueError("missing candidates")
    content = candidates[0].get("content")
    if not isinstance(content, dict):
        raise ValueError("missing content")
    parts = content.get("parts")
    if not isinstance(parts, list):
        raise ValueError("missing parts")
    return "".join(str(part.get("text", "")) for part in parts if isinstance(part, dict))


def get_gemini_client() -> GeminiClient:
    settings = get_settings()
    if not settings.gemini_api_key:
        raise ExternalServiceError(
            message="AI 일정 초안 생성 설정이 없습니다.",
            detail={"missing": ["GEMINI_API_KEY"]},
        )
    return GeminiClient(
        api_key=settings.gemini_api_key,
        model=settings.gemini_schedule_model,
        base_url=settings.gemini_api_base_url,
    )
