from __future__ import annotations

import json
from typing import Any

import httpx
from pydantic import BaseModel, Field, field_validator

from harness.mileday.api_constants import MILEDAY_API_BASE_URL, MILEDAY_API_JUDGE_MODEL
from harness.mileday.dataset import AiScheduleDraftCase
from harness.schemas import EvaluationError, FailureCategory


class AiDraftJudgeResult(BaseModel):
    is_aligned: bool
    score: float = Field(ge=0, le=1)
    reason: str
    critical_failures: list[str] = Field(default_factory=list)
    error: EvaluationError | None = None

    @field_validator("score", mode="before")
    @classmethod
    def _normalize_score_scale(cls, value: object) -> object:
        if isinstance(value, int | float) and 1 < float(value) <= 5:
            return float(value) / 5
        return value


class GeminiAiDraftJudge:
    def __init__(
        self,
        *,
        api_key: str,
        model: str = MILEDAY_API_JUDGE_MODEL,
        base_url: str = MILEDAY_API_BASE_URL,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")

    def evaluate(self, case: AiScheduleDraftCase, draft: dict[str, Any]) -> AiDraftJudgeResult:
        try:
            response = httpx.post(
                f"{self.base_url}/models/{self.model}:generateContent",
                headers={"x-goog-api-key": self.api_key, "Content-Type": "application/json"},
                json={
                    "contents": [{"role": "user", "parts": [{"text": build_ai_draft_judge_prompt(case, draft)}]}],
                    "generationConfig": {
                        "responseMimeType": "application/json",
                        "responseSchema": _judge_response_schema(),
                    },
                },
                timeout=120,
            )
            response.raise_for_status()
            return _parse_judge_response(response.json())
        except httpx.TimeoutException as exc:
            return _failed_judge_result(FailureCategory.TIMEOUT, str(exc))
        except httpx.HTTPError as exc:
            return _failed_judge_result(FailureCategory.EXTERNAL_DEPENDENCY, str(exc))
        except (ValueError, KeyError, TypeError) as exc:
            return _failed_judge_result(FailureCategory.PARSER_ERROR, str(exc))


def build_ai_draft_judge_prompt(case: AiScheduleDraftCase, draft: dict[str, Any]) -> str:
    return (
        "당신은 MileDay AI 일정 초안 품질을 평가하는 judge입니다.\n"
        "DB schema, SQL 가능 여부, 날짜 포맷 유효성은 이미 deterministic validation이 검사합니다.\n"
        "당신은 사용자 요청 반영 품질만 평가합니다.\n\n"
        "[평가 기준]\n"
        "- 목표 제목과 milestone이 사용자 목표를 잘 반영하는가\n"
        "- milestone이 실제 수행 가능한 작업 단위인가\n"
        "- 일정 강도와 선호 요일이 자연스럽게 반영됐는가\n"
        "- 사용자가 저장 전 편집하기 좋은 초안인가\n"
        "- 치명적 오류가 있으면 is_aligned=false로 판단한다\n\n"
        "[출력 기준]\n"
        "- score는 반드시 0.0~1.0 범위의 소수로 출력한다. 5점 만점 척도를 사용하지 않는다.\n"
        "- 예: 완벽하면 1.0, 충분히 좋으면 0.9, 부족하면 0.7 이하.\n\n"
        "[사용자 요청]\n"
        f"{case.user_prompt}\n\n"
        "[기대 조건]\n"
        f"{json.dumps(case.expected.model_dump(mode='json'), ensure_ascii=False, sort_keys=True)}\n\n"
        "[AI 초안]\n"
        f"{json.dumps(draft, ensure_ascii=False, sort_keys=True)}\n"
    )


def _judge_response_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "is_aligned": {"type": "boolean"},
            "score": {
                "type": "number",
                "minimum": 0,
                "maximum": 1,
                "description": "0.0 to 1.0 score. Do not use a 1 to 5 scale.",
            },
            "reason": {"type": "string"},
            "critical_failures": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["is_aligned", "score", "reason", "critical_failures"],
    }


def _parse_judge_response(response_json: dict[str, Any]) -> AiDraftJudgeResult:
    candidates = response_json["candidates"]
    text = "".join(part.get("text", "") for part in candidates[0]["content"]["parts"])
    payload = json.loads(text)
    result = AiDraftJudgeResult.model_validate(payload)
    if result.score < 0.85:
        return result.model_copy(update={"is_aligned": False})
    if result.critical_failures:
        return result.model_copy(update={"is_aligned": False})
    return result


def _failed_judge_result(category: FailureCategory, message: str) -> AiDraftJudgeResult:
    return AiDraftJudgeResult(
        is_aligned=False,
        score=0,
        reason="AI draft judge could not produce a valid decision.",
        critical_failures=[],
        error=EvaluationError(category=category, message=message),
    )
