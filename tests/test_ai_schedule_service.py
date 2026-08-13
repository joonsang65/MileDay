from __future__ import annotations

import json
from datetime import date

import pytest

from exceptions.common import BadRequestError
from schemas.ai_schedule_schemas import AiScheduleAvailability, AiScheduleDraftRequest
from services.ai_schedule_service import (
    AiScheduleService,
    ai_schedule_draft_response_schema,
    build_ai_schedule_draft_prompt,
    build_create_goal_payload,
    get_ai_schedule_service,
    parse_ai_schedule_draft_output,
    validate_ai_schedule_draft,
)


class FakeGeminiClient:
    def __init__(self, output: dict) -> None:
        self.output = output
        self.requests: list[dict] = []

    def generate_json(self, *, prompt: str, response_schema: dict, timeout_seconds: float = 30.0) -> str:
        self.requests.append(
            {
                "prompt": prompt,
                "response_schema": response_schema,
                "timeout_seconds": timeout_seconds,
            }
        )
        return json.dumps(self.output, ensure_ascii=False)


def draft_request() -> AiScheduleDraftRequest:
    return AiScheduleDraftRequest(
        prompt="9월 말까지 데이터 분석 과제를 끝내고 싶어. 주말 위주로 3개만 잡아줘.",
        today=date(2026, 8, 14),
        timezone="Asia/Seoul",
        availability=[
            AiScheduleAvailability(date=date(2026, 8, 22), available_minutes=240),
            AiScheduleAvailability(date=date(2026, 9, 5), available_minutes=180),
            AiScheduleAvailability(date=date(2026, 9, 19), available_minutes=240),
        ],
    )


def valid_model_output() -> dict:
    return {
        "goal": {
            "title": "데이터 분석 과제 마무리",
            "deadline": "2026-09-30",
        },
        "milestones": [
            {"title": "자료 수집과 전처리", "scheduled_date": "2026-08-22"},
            {"title": "분석 결과 정리", "scheduled_date": "2026-09-05"},
            {"title": "보고서 작성", "scheduled_date": "2026-09-19"},
        ],
        "planning_preference": {
            "intensity": "relaxed",
            "preferred_days": ["saturday"],
        },
    }


def test_prompt_contains_user_request_and_availability() -> None:
    prompt = build_ai_schedule_draft_prompt(draft_request())

    assert "[USER_REQUEST]" in prompt
    assert "데이터 분석 과제" in prompt
    assert "2026-08-22" in prompt
    assert "Do not return markdown" in prompt


def test_response_schema_requires_only_ai_draft_fields() -> None:
    schema = ai_schedule_draft_response_schema()

    assert schema["required"] == ["goal", "milestones", "planning_preference"]
    milestone_properties = schema["properties"]["milestones"]["items"]["properties"]
    assert "scheduled_date" in milestone_properties
    assert "goal_id" not in milestone_properties
    assert "selected_slot_ids" not in schema["properties"]


def test_parse_ai_schedule_draft_output_normalizes_json() -> None:
    parsed = parse_ai_schedule_draft_output(
        "```json\n" + json.dumps(valid_model_output(), ensure_ascii=False) + "\n```"
    )

    assert parsed["goal"]["title"] == "데이터 분석 과제 마무리"
    assert parsed["milestones"][0]["scheduled_date"] == "2026-08-22"
    assert parsed["planning_preference"]["preferred_days"] == ["saturday"]


def test_validate_ai_schedule_draft_rejects_outside_availability() -> None:
    draft = valid_model_output()
    draft["milestones"][0]["scheduled_date"] = "2026-08-23"

    validation = validate_ai_schedule_draft(draft_request(), draft)

    assert validation["is_valid"] is False
    assert "MILESTONE_OUTSIDE_AVAILABILITY" in validation["failure_codes"]


def test_validate_ai_schedule_draft_reports_shape_and_preference_errors() -> None:
    draft = {
        "goal": {"title": " ", "deadline": "2026-08-01"},
        "milestones": [
            "not-a-dict",
            {"title": "", "scheduled_date": "bad-date"},
            {"title": "중복 작업", "scheduled_date": "2026-08-22"},
            {"title": "중복 작업", "scheduled_date": "2026-08-22"},
            {"title": "초안 작업", "scheduled_date": "2026-09-05"},
            {"title": "검토 작업", "scheduled_date": "2026-09-19"},
            {"title": "추가 작업", "scheduled_date": "2026-09-19"},
        ],
        "planning_preference": {
            "intensity": "fast",
            "preferred_days": "weekend",
        },
    }

    validation = validate_ai_schedule_draft(draft_request(), draft)

    assert validation["is_valid"] is False
    assert "EMPTY_GOAL_TITLE" in validation["failure_codes"]
    assert "DEADLINE_NOT_FUTURE" in validation["failure_codes"]
    assert "INVALID_MILESTONE_SHAPE" in validation["failure_codes"]
    assert "EMPTY_MILESTONE_TITLE" in validation["failure_codes"]
    assert "INVALID_MILESTONE_DATE" in validation["failure_codes"]
    assert "DUPLICATE_MILESTONE" in validation["failure_codes"]
    assert "INVALID_INTENSITY" in validation["failure_codes"]
    assert "INVALID_PREFERRED_DAYS" in validation["failure_codes"]
    assert "MILESTONE_COUNT_HIGH" in validation["warnings"]


def test_validate_ai_schedule_draft_warns_when_preferred_days_not_reflected() -> None:
    draft = valid_model_output()
    draft["planning_preference"]["preferred_days"] = ["monday"]

    validation = validate_ai_schedule_draft(draft_request(), draft)

    assert validation["is_valid"] is True
    assert "PREFERRED_DAYS_NOT_REFLECTED" in validation["warnings"]


def test_parse_ai_schedule_draft_output_rejects_invalid_json() -> None:
    with pytest.raises(BadRequestError):
        parse_ai_schedule_draft_output("not-json")


def test_parse_ai_schedule_draft_output_rejects_non_object_json() -> None:
    with pytest.raises(BadRequestError):
        parse_ai_schedule_draft_output("[]")


def test_build_create_goal_payload_matches_existing_goal_api_shape() -> None:
    draft = {
        "goal": valid_model_output()["goal"],
        "milestones": [
            {
                "client_id": "draft-1",
                "title": "자료 수집과 전처리",
                "scheduled_date": "2026-08-22",
                "selected": True,
            },
            {
                "client_id": "draft-2",
                "title": "분석 결과 정리",
                "scheduled_date": "2026-09-05",
                "selected": False,
            },
        ],
        "planning_preference": valid_model_output()["planning_preference"],
    }

    payload = build_create_goal_payload(draft)

    assert payload["goal"] == {
        "title": "데이터 분석 과제 마무리",
        "deadline": "2026-09-30",
        "is_recurring": False,
        "recurrence_type": None,
        "color": "#7F9278",
    }
    assert len(payload["milestones"]) == 1
    assert payload["milestones"][0]["color"] == "#55A873"
    assert payload["write_policy"] == "user_confirmation_required"


def test_ai_schedule_service_returns_editable_draft_and_payload() -> None:
    fake_client = FakeGeminiClient(valid_model_output())
    service = AiScheduleService(gemini_client=fake_client)

    result = service.create_draft(user_id="user-1", body=draft_request())

    assert result["goal"]["title"] == "데이터 분석 과제 마무리"
    assert result["milestones"][0]["client_id"] == "draft-1"
    assert result["milestones"][0]["selected"] is True
    assert result["validation"]["is_valid"] is True
    assert result["create_goal_payload"]["write_policy"] == "user_confirmation_required"
    assert fake_client.requests[0]["response_schema"]["required"] == [
        "goal",
        "milestones",
        "planning_preference",
    ]


def test_ai_schedule_service_rejects_invalid_model_output() -> None:
    invalid = valid_model_output()
    invalid["milestones"][0]["scheduled_date"] = "2026-10-01"
    service = AiScheduleService(gemini_client=FakeGeminiClient(invalid))

    with pytest.raises(BadRequestError) as exc_info:
        service.create_draft(user_id="user-1", body=draft_request())

    assert "MILESTONE_AFTER_DEADLINE" in exc_info.value.detail["failure_codes"]


def test_get_ai_schedule_service_uses_configured_client(monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_SCHEDULE_MODEL", "test-model")

    from core.config import get_settings

    get_settings.cache_clear()
    service = get_ai_schedule_service()

    assert service.gemini_client.api_key == "test-key"
    assert service.gemini_client.model == "test-model"
    get_settings.cache_clear()
