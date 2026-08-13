from __future__ import annotations

import json
import re
from collections import Counter
from datetime import date
from typing import Any

from exceptions.common import BadRequestError
from infrastructure.gemini_client import GeminiClient, get_gemini_client
from schemas.ai_schedule_schemas import AiScheduleDraftRequest


DEFAULT_GOAL_COLOR = "#7F9278"
DEFAULT_MILESTONE_COLOR = "#55A873"
PROMPT_VERSION = "v1-product-ai-draft"
WEEKDAYS = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)
JSON_BLOCK_PATTERN = re.compile(r"```(?:json)?\s*(?P<body>.*?)```", re.DOTALL | re.IGNORECASE)


class AiScheduleService:
    def __init__(self, gemini_client: GeminiClient | None = None) -> None:
        self.gemini_client = gemini_client or get_gemini_client()

    def create_draft(
        self,
        *,
        user_id: str,
        body: AiScheduleDraftRequest,
    ) -> dict[str, Any]:
        raw_output = self.gemini_client.generate_json(
            prompt=build_ai_schedule_draft_prompt(body),
            response_schema=ai_schedule_draft_response_schema(),
        )
        draft = parse_ai_schedule_draft_output(raw_output)
        validation = validate_ai_schedule_draft(body, draft)
        if not validation["is_valid"]:
            raise BadRequestError(
                message="AI 일정 초안이 저장 가능한 형식이 아닙니다.",
                detail={"failure_codes": validation["failure_codes"]},
            )

        editable_draft = _with_ui_fields(draft)
        return {
            **editable_draft,
            "validation": validation,
            "create_goal_payload": build_create_goal_payload(editable_draft),
        }


def build_ai_schedule_draft_prompt(body: AiScheduleDraftRequest) -> str:
    availability = [
        {
            "date": item.date.isoformat(),
            "available_minutes": item.available_minutes,
        }
        for item in body.availability
    ]
    return (
        "You create an editable MileDay schedule draft from a Korean user request.\n"
        "Return exactly one JSON object matching the response schema.\n"
        "Do not return markdown, explanations, SQL, database ids, slot ids, or mutation fields.\n"
        "Keep JSON field names and enum values in English. Write goal and milestone titles in Korean.\n\n"
        "[ROLE]\n"
        "- Interpret the user's goal, deadline, preferred days, and pace.\n"
        "- Split the goal into concrete milestone tasks a user can edit before saving.\n"
        "- Choose milestone dates only from AVAILABLE_DATES and never after the goal deadline.\n"
        "- The user will confirm and edit the draft before DB write; do not decide storage.\n\n"
        "[COUNT_POLICY]\n"
        "- If the user asks for an exact count or range, follow it.\n"
        "- If no count is requested, create 1 to 6 milestones.\n"
        "- Simple goals may have 1 or 2 milestones. Project-like goals should usually have 2 or more.\n\n"
        "[PREFERENCE_POLICY]\n"
        "- relaxed: leave spacing between milestones and avoid using every possible date.\n"
        "- balanced: spread milestones evenly before the deadline.\n"
        "- intensive: schedule earlier available dates when the user wants a fast plan.\n"
        "- Use preferred_days only when the request clearly implies them.\n\n"
        f"[TODAY]\n{body.today.isoformat()}\n\n"
        f"[TIMEZONE]\n{body.timezone}\n\n"
        "[AVAILABLE_DATES]\n"
        f"{json.dumps(availability, ensure_ascii=False, sort_keys=True)}\n\n"
        f"[PROMPT_VERSION]\n{PROMPT_VERSION}\n\n"
        f"[USER_REQUEST]\n{body.prompt}\n"
    )


def ai_schedule_draft_response_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "goal": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "deadline": {"type": "string"},
                },
                "required": ["title", "deadline"],
            },
            "milestones": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "scheduled_date": {"type": "string"},
                    },
                    "required": ["title", "scheduled_date"],
                },
            },
            "planning_preference": {
                "type": "object",
                "properties": {
                    "intensity": {
                        "type": "string",
                        "enum": ["relaxed", "balanced", "intensive"],
                    },
                    "preferred_days": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": list(WEEKDAYS),
                        },
                    },
                },
                "required": ["intensity", "preferred_days"],
            },
        },
        "required": ["goal", "milestones", "planning_preference"],
    }


def parse_ai_schedule_draft_output(raw_output: str) -> dict[str, Any]:
    payload = _load_json_object(raw_output)
    goal = payload.get("goal") if isinstance(payload.get("goal"), dict) else {}
    milestones = payload.get("milestones") if isinstance(payload.get("milestones"), list) else []
    preference = (
        payload.get("planning_preference")
        if isinstance(payload.get("planning_preference"), dict)
        else {}
    )
    return {
        "goal": {
            "title": _clean_string(goal.get("title")),
            "deadline": _clean_string(goal.get("deadline")),
        },
        "milestones": [
            {
                "title": _clean_string(item.get("title")),
                "scheduled_date": _clean_string(item.get("scheduled_date")),
            }
            for item in milestones
            if isinstance(item, dict)
        ],
        "planning_preference": {
            "intensity": _clean_string(preference.get("intensity")),
            "preferred_days": [
                _clean_string(day)
                for day in preference.get("preferred_days", [])
                if isinstance(day, str)
            ],
        },
    }


def validate_ai_schedule_draft(
    request: AiScheduleDraftRequest,
    draft: dict[str, Any],
) -> dict[str, Any]:
    failures: list[str] = []
    warnings: list[str] = []
    goal = draft.get("goal") if isinstance(draft.get("goal"), dict) else {}
    milestones = draft.get("milestones") if isinstance(draft.get("milestones"), list) else []
    preference = (
        draft.get("planning_preference")
        if isinstance(draft.get("planning_preference"), dict)
        else {}
    )
    availability_dates = {item.date.isoformat() for item in request.availability}

    deadline = _parse_date(goal.get("deadline"))
    if not _clean_string(goal.get("title")):
        failures.append("EMPTY_GOAL_TITLE")
    if deadline is None:
        failures.append("INVALID_DEADLINE")
    else:
        if deadline <= request.today:
            failures.append("DEADLINE_NOT_FUTURE")

    if not milestones:
        failures.append("NO_MILESTONES")
    if len(milestones) > 6:
        warnings.append("MILESTONE_COUNT_HIGH")

    _validate_milestones(milestones, deadline, availability_dates, failures)
    _validate_preference(milestones, preference, failures, warnings)
    return {
        "is_valid": not failures,
        "failure_codes": sorted(set(failures)),
        "warnings": sorted(set(warnings)),
    }


def build_create_goal_payload(draft: dict[str, Any]) -> dict[str, Any]:
    goal = draft["goal"]
    milestones = draft["milestones"]
    return {
        "goal": {
            "title": goal["title"],
            "deadline": goal["deadline"],
            "is_recurring": False,
            "recurrence_type": None,
            "color": DEFAULT_GOAL_COLOR,
        },
        "milestones": [
            {
                "title": item["title"],
                "scheduled_date": item["scheduled_date"],
                "color": DEFAULT_MILESTONE_COLOR,
                "is_completed": False,
            }
            for item in milestones
            if item.get("selected", True)
        ],
        "write_policy": "user_confirmation_required",
    }


def _with_ui_fields(draft: dict[str, Any]) -> dict[str, Any]:
    return {
        "goal": draft["goal"],
        "milestones": [
            {
                "client_id": f"draft-{index}",
                "title": item["title"],
                "scheduled_date": item["scheduled_date"],
                "selected": True,
            }
            for index, item in enumerate(draft["milestones"], start=1)
        ],
        "planning_preference": draft["planning_preference"],
    }


def _validate_milestones(
    milestones: list[Any],
    deadline: date | None,
    availability_dates: set[str],
    failures: list[str],
) -> None:
    seen = Counter()
    for item in milestones:
        if not isinstance(item, dict):
            failures.append("INVALID_MILESTONE_SHAPE")
            continue
        title = _clean_string(item.get("title"))
        scheduled_date_text = _clean_string(item.get("scheduled_date"))
        scheduled_date = _parse_date(scheduled_date_text)
        if not title:
            failures.append("EMPTY_MILESTONE_TITLE")
        if scheduled_date is None:
            failures.append("INVALID_MILESTONE_DATE")
            continue
        if deadline is not None and scheduled_date > deadline:
            failures.append("MILESTONE_AFTER_DEADLINE")
        if scheduled_date_text not in availability_dates:
            failures.append("MILESTONE_OUTSIDE_AVAILABILITY")
        seen[(title, scheduled_date_text)] += 1
    if any(count > 1 for count in seen.values()):
        failures.append("DUPLICATE_MILESTONE")


def _validate_preference(
    milestones: list[Any],
    preference: dict[str, Any],
    failures: list[str],
    warnings: list[str],
) -> None:
    intensity = preference.get("intensity")
    if intensity not in {"relaxed", "balanced", "intensive"}:
        failures.append("INVALID_INTENSITY")
    preferred_days = preference.get("preferred_days")
    if not isinstance(preferred_days, list):
        failures.append("INVALID_PREFERRED_DAYS")
        return
    invalid_days = [day for day in preferred_days if day not in WEEKDAYS]
    if invalid_days:
        failures.append("INVALID_PREFERRED_DAYS")

    valid_dates = [
        parsed
        for item in milestones
        if isinstance(item, dict)
        for parsed in [_parse_date(item.get("scheduled_date"))]
        if parsed is not None
    ]
    if preferred_days and valid_dates:
        matched = sum(1 for item in valid_dates if WEEKDAYS[item.weekday()] in preferred_days)
        if matched == 0:
            warnings.append("PREFERRED_DAYS_NOT_REFLECTED")


def _load_json_object(raw_output: str) -> dict[str, Any]:
    text = raw_output.strip()
    match = JSON_BLOCK_PATTERN.fullmatch(text)
    if match is not None:
        text = match.group("body").strip()
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise BadRequestError(
            message="AI 일정 초안 JSON을 해석하지 못했습니다.",
            detail={"reason": exc.msg},
        ) from exc
    if not isinstance(value, dict):
        raise BadRequestError(message="AI 일정 초안은 JSON object여야 합니다.")
    return value


def _clean_string(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _parse_date(value: object) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def get_ai_schedule_service() -> AiScheduleService:
    return AiScheduleService()
