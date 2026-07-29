from __future__ import annotations

import json
from typing import Any, Protocol

import httpx
from pydantic import BaseModel, ConfigDict, Field

from harness.mileday.dataset import MileDayGenerationCase
from harness.schemas import EvaluationError, FailureCategory


class ExplanationJudgeResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    is_aligned: bool
    score: float = Field(ge=0.0, le=1.0)
    reason: str
    skipped: bool = False
    error: EvaluationError | None = None


class BatchQualitySummaryResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    overall_summary: str
    risk_signals: list[str] = Field(default_factory=list)
    improvement_actions: list[str] = Field(default_factory=list)
    skipped: bool = False
    error: EvaluationError | None = None


class ExplanationJudge(Protocol):
    def evaluate(
        self,
        case: MileDayGenerationCase,
        explanation: str,
        parsed_output: dict[str, Any],
    ) -> ExplanationJudgeResult:
        """Judge whether the user-facing explanation matches generated milestones."""


class GeminiExplanationJudge:
    """Gemini-backed judge for MileDay explanation and milestone alignment."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "gemini-3.5-flash",
        base_url: str = "https://generativelanguage.googleapis.com/v1beta",
        timeout_seconds: float = 30.0,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def evaluate(
        self,
        case: MileDayGenerationCase,
        explanation: str,
        parsed_output: dict[str, Any],
    ) -> ExplanationJudgeResult:
        payload = _gemini_json_payload(
            build_explanation_judge_prompt(case, explanation, parsed_output),
            {
                "type": "object",
                "properties": {
                    "is_aligned": {"type": "boolean"},
                    "score": {"type": "number"},
                    "reason": {"type": "string"},
                },
                "required": ["is_aligned", "score", "reason"],
            },
        )
        try:
            response_json = self._post_generate_content(payload)
            return _parse_gemini_judge_response(response_json)
        except httpx.HTTPStatusError as exc:
            return _failed_explanation_judge_result(
                f"Gemini explanation judge failed: {exc}. Response body: {_response_error_detail(exc.response)}"
            )
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            return _failed_explanation_judge_result(f"Gemini explanation judge failed: {exc}")

    def summarize_batch_quality(self, context: dict[str, Any]) -> BatchQualitySummaryResult:
        payload = _gemini_json_payload(
            build_batch_quality_summary_prompt(context),
            {
                "type": "object",
                "properties": {
                    "overall_summary": {"type": "string"},
                    "risk_signals": {"type": "array", "items": {"type": "string"}},
                    "improvement_actions": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["overall_summary", "risk_signals", "improvement_actions"],
            },
        )
        try:
            response_json = self._post_generate_content(payload)
            return _parse_batch_quality_summary_response(response_json)
        except httpx.HTTPStatusError as exc:
            return _failed_batch_quality_summary_result(
                f"Gemini batch quality summary failed: {exc}. Response body: {_response_error_detail(exc.response)}"
            )
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            return _failed_batch_quality_summary_result(f"Gemini batch quality summary failed: {exc}")

    def _post_generate_content(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = httpx.post(
            f"{self.base_url}/models/{self.model}:generateContent",
            headers={
                "x-goog-api-key": self.api_key,
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        return response.json()


def skipped_explanation_judge_result() -> ExplanationJudgeResult:
    return ExplanationJudgeResult(
        is_aligned=True,
        score=0.0,
        reason="Gemini explanation judge was skipped because GEMINI_API_KEY is not configured.",
        skipped=True,
    )


def skipped_batch_quality_summary_result() -> BatchQualitySummaryResult:
    return BatchQualitySummaryResult(
        overall_summary="Gemini API key가 설정되지 않아 LLM 기반 품질 요약을 건너뛰었습니다.",
        skipped=True,
    )


def build_explanation_judge_prompt(
    case: MileDayGenerationCase,
    explanation: str,
    parsed_output: dict[str, Any],
) -> str:
    return (
        "당신은 MileDay 일정 생성 결과를 평가하는 심사자입니다.\n"
        "설명문이 사용자가 이해할 수 있는 한국어 설명인지, 그리고 JSON milestones의 핵심 일정 내용과 일치하는지 평가하세요.\n"
        "일정이 실제 사용자에게 실행 가능하지 않거나 설명문이 일정 생성 규칙과 어긋나면 낮게 평가하세요.\n"
        "내부 추론은 출력하지 말고 JSON 객체 하나만 출력하세요.\n"
        '필드: {"is_aligned": boolean, "score": number, "reason": string}\n'
        "score는 0.0~1.0이며, 0.8 이상이면 설명문이 milestones와 충분히 일치한다고 봅니다.\n"
        "\n"
        f"목표: {case.input.goal_title}\n"
        f"마감일: {case.input.deadline}\n"
        f"제약: {json.dumps(case.input.constraints, ensure_ascii=False, sort_keys=True)}\n"
        "\n"
        "[EXPLANATION]\n"
        f"{explanation}\n"
        "\n"
        "[MILESTONES_JSON]\n"
        f"{json.dumps(parsed_output, ensure_ascii=False, sort_keys=True)}\n"
    )


def build_batch_quality_summary_prompt(context: dict[str, Any]) -> str:
    return (
        "당신은 MileDay 로컬 LLM 평가 결과를 정리하는 품질 분석가입니다.\n"
        "아래 batch 집계 데이터만 근거로 사용하세요. 데이터에 없는 사실, 모델 성능, 원인은 추측하지 마세요.\n"
        "전체 요약은 한국어 3~5문장으로 작성하세요.\n"
        "위험 신호는 사용자에게 전달되면 문제가 될 수 있는 출력 품질 리스크만 작성하세요.\n"
        "개선 방안은 프롬프트, parser, dataset, 모델 선택 또는 평가 운영 관점에서 실행 가능한 항목으로 작성하세요.\n"
        "내부 추론은 출력하지 말고 JSON 객체 하나만 출력하세요.\n"
        '필드: {"overall_summary": string, "risk_signals": string[], "improvement_actions": string[]}\n'
        "\n"
        "[BATCH_CONTEXT]\n"
        f"{json.dumps(context, ensure_ascii=False, sort_keys=True)}\n"
    )


def _gemini_json_payload(prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
    return {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}],
            }
        ],
        "generationConfig": {
            "temperature": 0,
            "responseMimeType": "application/json",
            "responseSchema": schema,
        },
    }


def _parse_gemini_judge_response(response_json: dict[str, Any]) -> ExplanationJudgeResult:
    parsed = _parse_gemini_json_text(response_json)
    score = min(1.0, max(0.0, float(parsed["score"])))
    return ExplanationJudgeResult(
        is_aligned=bool(parsed["is_aligned"]) and score >= 0.8,
        score=score,
        reason=str(parsed["reason"]),
    )


def _parse_batch_quality_summary_response(response_json: dict[str, Any]) -> BatchQualitySummaryResult:
    parsed = _parse_gemini_json_text(response_json)
    return BatchQualitySummaryResult(
        overall_summary=str(parsed["overall_summary"]),
        risk_signals=[str(item) for item in parsed.get("risk_signals", [])],
        improvement_actions=[str(item) for item in parsed.get("improvement_actions", [])],
    )


def _parse_gemini_json_text(response_json: dict[str, Any]) -> dict[str, Any]:
    text = response_json["candidates"][0]["content"]["parts"][0]["text"]
    return json.loads(_strip_fenced_json(text))


def _failed_explanation_judge_result(message: str) -> ExplanationJudgeResult:
    return ExplanationJudgeResult(
        is_aligned=False,
        score=0.0,
        reason="Gemini explanation judge could not produce a valid decision.",
        skipped=True,
        error=EvaluationError(category=FailureCategory.EXTERNAL_DEPENDENCY, message=message),
    )


def _failed_batch_quality_summary_result(message: str) -> BatchQualitySummaryResult:
    return BatchQualitySummaryResult(
        overall_summary="Gemini 기반 batch 품질 요약 생성에 실패했습니다.",
        skipped=True,
        error=EvaluationError(category=FailureCategory.EXTERNAL_DEPENDENCY, message=message),
    )


def _strip_fenced_json(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if len(lines) >= 3 and lines[-1].strip() == "```":
            return "\n".join(lines[1:-1]).strip()
    return stripped


def _response_error_detail(response: httpx.Response) -> str:
    text = response.text.strip()
    if len(text) > 1000:
        return text[:1000] + "..."
    return text
