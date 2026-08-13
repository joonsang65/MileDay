from __future__ import annotations

import json
from time import sleep
from typing import Any, Protocol

import httpx
from pydantic import BaseModel, ConfigDict, Field

from harness.mileday.dataset import MileDayGenerationCase, MileDayMultiTurnCase
from harness.schemas import EvaluationError, FailureCategory


JUDGE_PASS_THRESHOLD = 0.9


class ExplanationJudgeResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    is_aligned: bool
    score: float = Field(ge=0.0, le=1.0)
    reason: str
    critical_failures: list[str] = Field(default_factory=list)
    dimension_scores: dict[str, float] = Field(default_factory=dict)
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

    def evaluate_multiturn(
        self,
        case: MileDayMultiTurnCase,
        turn_id: int,
        explanation: str,
        parsed_output: dict[str, Any],
        previous_output: dict[str, Any] | None,
    ) -> ExplanationJudgeResult:
        """Judge whether a multiturn response preserves state and applies the current request."""

    def evaluate_case_multiturn(
        self,
        case: MileDayMultiTurnCase,
        turn_outputs: list[dict[str, Any]],
    ) -> ExplanationJudgeResult:
        """Judge accumulated parser output once for the full multiturn case."""


class GeminiExplanationJudge:
    """Gemini-backed judge for MileDay explanation and milestone alignment."""

    RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "gemini-3.5-flash",
        base_url: str = "https://generativelanguage.googleapis.com/v1beta",
        timeout_seconds: float = 30.0,
        max_attempts: int = 3,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.max_attempts = max(1, max_attempts)

    def evaluate(
        self,
        case: MileDayGenerationCase,
        explanation: str,
        parsed_output: dict[str, Any],
    ) -> ExplanationJudgeResult:
        payload = _gemini_json_payload(
            build_explanation_judge_prompt(case, explanation, parsed_output),
            _judge_response_schema(),
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

    def evaluate_multiturn(
        self,
        case: MileDayMultiTurnCase,
        turn_id: int,
        explanation: str,
        parsed_output: dict[str, Any],
        previous_output: dict[str, Any] | None,
    ) -> ExplanationJudgeResult:
        payload = _gemini_json_payload(
            build_multiturn_explanation_judge_prompt(
                case,
                turn_id,
                explanation,
                parsed_output,
                previous_output,
            ),
            _judge_response_schema(),
        )
        try:
            response_json = self._post_generate_content(payload)
            return _parse_gemini_judge_response(response_json)
        except httpx.HTTPStatusError as exc:
            return _failed_explanation_judge_result(
                f"Gemini multiturn explanation judge failed: {exc}. Response body: {_response_error_detail(exc.response)}"
            )
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            return _failed_explanation_judge_result(f"Gemini multiturn explanation judge failed: {exc}")

    def evaluate_case_multiturn(
        self,
        case: MileDayMultiTurnCase,
        turn_outputs: list[dict[str, Any]],
    ) -> ExplanationJudgeResult:
        payload = _gemini_json_payload(
            build_case_multiturn_explanation_judge_prompt(case, turn_outputs),
            _judge_response_schema(),
        )
        try:
            response_json = self._post_generate_content(payload)
            return _parse_gemini_judge_response(response_json)
        except httpx.HTTPStatusError as exc:
            return _failed_explanation_judge_result(
                f"Gemini case-level multiturn explanation judge failed: {exc}. Response body: {_response_error_detail(exc.response)}"
            )
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            return _failed_explanation_judge_result(f"Gemini case-level multiturn explanation judge failed: {exc}")

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
        for attempt in range(self.max_attempts):
            sleep(0.5 * (2**attempt))
            try:
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
            except httpx.HTTPStatusError as exc:
                if not self._should_retry_status(exc.response.status_code, attempt):
                    raise
            except (httpx.TimeoutException, httpx.NetworkError):
                if attempt >= self.max_attempts - 1:
                    raise
        raise RuntimeError("Gemini judge retry loop ended without a response.")

    def _should_retry_status(self, status_code: int, attempt: int) -> bool:
        return status_code in self.RETRYABLE_STATUS_CODES and attempt < self.max_attempts - 1


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
        '필드: {"is_aligned": boolean, "score": number, "reason": string, "critical_failures": string[], "dimension_scores": object}\n'
        "score는 0.0~1.0입니다. 0.9 이상이고 critical_failures가 비어 있을 때만 is_aligned=true로 판단하세요.\n"
        "dimension_scores에는 goal_alignment, schedule_constraint_fit, explanation_payload_consistency, user_readiness를 0.0~1.0 점수로 넣으세요.\n"
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


def build_multiturn_explanation_judge_prompt(
    case: MileDayMultiTurnCase,
    turn_id: int,
    explanation: str,
    parsed_output: dict[str, Any],
    previous_output: dict[str, Any] | None,
) -> str:
    turn = case.turns[turn_id - 1]
    return (
        "당신은 MileDay 멀티턴 일정 수정 결과를 평가하는 한국어 품질 심사자입니다.\n"
        "현재 turn의 사용자 요청이 이전 일정 상태에 대해 정확히 반영되었는지 평가하세요.\n"
        "데이터에 없는 사실을 추측하지 말고, 아래 입력과 출력만 근거로 판단하세요.\n"
        "내부 추론은 출력하지 말고 JSON 객체 하나만 출력하세요.\n"
        '필드: {"is_aligned": boolean, "score": number, "reason": string, "critical_failures": string[], "dimension_scores": object}\n'
        "score는 0.0~1.0입니다. 0.9 이상이고 critical_failures가 비어 있을 때만 is_aligned=true로 판단하세요.\n"
        "dimension_scores에는 current_request_applied, target_scope_correct, unmentioned_items_preserved, date_time_preserved, payload_explanation_consistent, confirmation_required를 0.0~1.0 점수로 넣으세요.\n"
        "\n"
        "[평가 기준]\n"
        "- 설명문이 현재 사용자 요청과 실제 JSON 변경 내용을 일치해서 설명하는가\n"
        "- 사용자가 지정한 가용 요일/시간이 milestone title에 반영되었는가\n"
        "- 가용 요일/시간은 hard constraint이다. 요청한 이동 대상이 가용 시간에 없으면 변경하지 않고 제약을 설명하는 것이 올바르다\n"
        "- 현재 DB payload에는 개별 milestone 시간 길이 필드가 없다. 사용자가 '1시간만 가능'처럼 duration 축소를 요청하면, 기존 시간 prefix를 유지하되 작업명에 축소 의도를 반영해도 올바른 처리로 본다\n"
        "- 특정 기존 일정을 앞당기거나 미루라는 요청에서 해당 일정이 이전 plan에 없거나 날짜 이동 rule이 지원되지 않으면, 임의 변경하지 않고 기존 일정을 유지하는 것이 올바르다\n"
        "- partial_update에서는 요청받은 부분만 변경하고 나머지 일정 상태를 보존했는가\n"
        "- 완료된 기존 milestone을 임의로 변경하지 않았는가\n"
        "- create에서는 완료된 기존 milestone을 새 DB payload에 다시 포함하지 않아도 된다. 단, 같은 날짜/작업을 중복 생성하지 않아야 한다\n"
        "- JSON이 DB 반영 후보로 사용할 수 있는 goal/milestone payload를 제공하는가\n"
        "- DB 업데이트 전 사용자 승인 필요성이 드러나는가\n"
        "\n"
        "[치명 오류]\n"
        "- WRONG_TARGET_SCOPE: 사용자가 지정한 대상이 아닌 slot을 변경함\n"
        "- OVER_PATCHED_SINGLE_TARGET: 하나만/1개만 요청인데 여러 slot을 변경함\n"
        "- UNDER_PATCHED_SCOPE: 수요일/평일/주말 같은 범위 요청인데 일부 대상만 변경함\n"
        "- PRESERVED_ITEM_CHANGED: 유지하라고 한 항목을 변경함\n"
        "- DATE_TIME_CHANGED: 날짜/시간 유지 요청인데 날짜 또는 시간 slot을 변경함\n"
        "- UNSUPPORTED_REFUSAL: 가능한 작업명 변경을 불가능하다고 거부함\n"
        "- PAYLOAD_EXPLANATION_MISMATCH: 설명문과 실제 JSON/patch 내용이 다름\n"
        "치명 오류가 하나라도 있으면 critical_failures에 코드를 넣고 is_aligned=false로 판단하세요.\n"
        "\n"
        f"[CASE_ID]\n{case.case_id}\n"
        f"[TURN_ID]\n{turn_id}\n"
        f"[CURRENT_USER_REQUEST]\n{turn.content}\n"
        f"[EXPECTED_ACTION]\n{turn.expected_action}\n"
        "\n"
        "[GOAL]\n"
        f"{json.dumps(case.input.initial_goal.model_dump(mode='json'), ensure_ascii=False, sort_keys=True)}\n"
        "\n"
        "[AVAILABILITY]\n"
        f"{json.dumps([item.model_dump(mode='json') for item in case.input.availability], ensure_ascii=False, sort_keys=True)}\n"
        "\n"
        "[EXISTING_SCHEDULE]\n"
        f"{json.dumps([item.model_dump(mode='json') for item in case.input.existing_schedule], ensure_ascii=False, sort_keys=True)}\n"
        "\n"
        "[PREVIOUS_JSON]\n"
        f"{json.dumps(previous_output, ensure_ascii=False, sort_keys=True)}\n"
        "\n"
        "[EXPLANATION]\n"
        f"{explanation}\n"
        "\n"
        "[CURRENT_JSON]\n"
        f"{json.dumps(parsed_output, ensure_ascii=False, sort_keys=True)}\n"
    )


def build_case_multiturn_explanation_judge_prompt(
    case: MileDayMultiTurnCase,
    turn_outputs: list[dict[str, Any]],
) -> str:
    expected_turns = [
        {
            "turn_id": turn.turn_id,
            "user_request": turn.content,
            "expected_action": turn.expected_action,
            "expected_operation": turn.expected_operation,
            "expected": _dump_optional_model(getattr(turn, "expected", None)),
        }
        for turn in case.turns
    ]
    compact_outputs = [
        {
            "turn_id": output.get("turn_id"),
            "status": output.get("status"),
            "parsed_json": output.get("parsed_json"),
            "validation": output.get("multiturn_validation"),
            "explanation": output.get("explanation"),
        }
        for output in turn_outputs
    ]
    return (
        "당신은 MileDay 멀티턴 일정 생성 결과를 평가하는 LLM judge입니다.\n"
        "각 turn은 이미 deterministic parsing/validation을 통과했습니다. 누적된 case 전체 동작만 평가하세요.\n"
        "제공된 사용자 요청, expected metadata, parser outputs, validation results만 근거로 판단하세요.\n"
        "출력은 JSON 객체 하나만 반환하세요. markdown, 코드블록, 추가 설명은 출력하지 마세요.\n"
        '필드: {"is_aligned": boolean, "score": number, "reason": string, "critical_failures": string[], "dimension_scores": object}\n'
        "reason은 반드시 자연스러운 한국어 문장으로 작성하세요. 영어로 작성하지 마세요.\n"
        "critical_failures의 코드값은 아래 정의된 영문 코드를 그대로 사용하세요.\n"
        "score는 0.0~1.0입니다. score가 0.9 이상이고 critical_failures가 비어 있을 때만 is_aligned=true로 판단하세요.\n"
        "dimension_scores에는 current_request_applied, target_scope_correct, unmentioned_items_preserved, date_time_preserved, payload_explanation_consistent, confirmation_required를 0.0~1.0 점수로 넣으세요.\n"
        "\n"
        "[CRITICAL_FAILURES]\n"
        "- WRONG_TARGET_SCOPE: 사용자가 요청한 대상 밖의 slot을 변경함.\n"
        "- OVER_PATCHED_SINGLE_TARGET: 정확히 하나의 대상만 변경해야 하는데 여러 slot을 변경함.\n"
        "- PRESERVED_ITEM_CHANGED: 유지해야 하는 slot을 변경함.\n"
        "- DATE_TIME_CHANGED: 사용자가 task/title 변경만 요청했는데 날짜나 시간을 변경함.\n"
        "- PAYLOAD_EXPLANATION_MISMATCH: parser payload와 사용자용 설명이 서로 다름.\n"
        "- UNSAFE_MUTATION: create/add/remove/rename/none operation 효과가 사용자 요청과 맞지 않음.\n"
        "\n"
        "[CASE_ID]\n"
        f"{case.case_id}\n"
        "\n"
        "[GOAL]\n"
        f"{json.dumps(case.input.initial_goal.model_dump(mode='json'), ensure_ascii=False, sort_keys=True)}\n"
        "\n"
        "[AVAILABILITY]\n"
        f"{json.dumps([item.model_dump(mode='json') for item in case.input.availability], ensure_ascii=False, sort_keys=True)}\n"
        "\n"
        "[EXISTING_SCHEDULE]\n"
        f"{json.dumps([item.model_dump(mode='json') for item in case.input.existing_schedule], ensure_ascii=False, sort_keys=True)}\n"
        "\n"
        "[EXPECTED_TURNS]\n"
        f"{json.dumps(expected_turns, ensure_ascii=False, sort_keys=True)}\n"
        "\n"
        "[PARSER_OUTPUTS]\n"
        f"{json.dumps(compact_outputs, ensure_ascii=False, sort_keys=True)}\n"
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


def _judge_response_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "is_aligned": {"type": "boolean"},
            "score": {"type": "number"},
            "reason": {"type": "string"},
            "critical_failures": {"type": "array", "items": {"type": "string"}},
            "dimension_scores": {
                "type": "object",
                "properties": {
                    "goal_alignment": {"type": "number"},
                    "schedule_constraint_fit": {"type": "number"},
                    "explanation_payload_consistency": {"type": "number"},
                    "user_readiness": {"type": "number"},
                    "current_request_applied": {"type": "number"},
                    "target_scope_correct": {"type": "number"},
                    "unmentioned_items_preserved": {"type": "number"},
                    "date_time_preserved": {"type": "number"},
                    "payload_explanation_consistent": {"type": "number"},
                    "confirmation_required": {"type": "number"},
                },
            },
        },
        "required": [
            "is_aligned",
            "score",
            "reason",
            "critical_failures",
            "dimension_scores",
        ],
    }


def _parse_gemini_judge_response(response_json: dict[str, Any]) -> ExplanationJudgeResult:
    parsed = _parse_gemini_json_text(response_json)
    score = min(1.0, max(0.0, float(parsed["score"])))
    critical_failures = [
        str(item)
        for item in parsed.get("critical_failures", [])
        if str(item).strip()
    ]
    dimension_scores = {
        str(name): min(1.0, max(0.0, float(value)))
        for name, value in parsed.get("dimension_scores", {}).items()
    }
    return ExplanationJudgeResult(
        is_aligned=bool(parsed["is_aligned"]) and score >= JUDGE_PASS_THRESHOLD and not critical_failures,
        score=score,
        reason=str(parsed["reason"]),
        critical_failures=critical_failures,
        dimension_scores=dimension_scores,
    )


def _parse_batch_quality_summary_response(response_json: dict[str, Any]) -> BatchQualitySummaryResult:
    parsed = _parse_gemini_json_text(response_json)
    return BatchQualitySummaryResult(
        overall_summary=str(parsed["overall_summary"]),
        risk_signals=[str(item) for item in parsed.get("risk_signals", [])],
        improvement_actions=[str(item) for item in parsed.get("improvement_actions", [])],
    )


def _dump_optional_model(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return value


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
