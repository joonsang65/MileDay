from __future__ import annotations

import json
import re
from typing import Any, TypedDict

from exceptions.common import BadRequestError


JSON_BLOCK_PATTERN = re.compile(r"```(?:json)?\s*(?P<body>.*?)```", re.DOTALL | re.IGNORECASE)


class ParsedGoal(TypedDict):
    title: str
    deadline: str


class ParsedMilestone(TypedDict):
    title: str
    scheduled_date: str


class ParsedPlanningPreference(TypedDict):
    intensity: str
    preferred_days: list[str]


class ParsedScheduleDraft(TypedDict):
    goal: ParsedGoal
    milestones: list[ParsedMilestone]
    planning_preference: ParsedPlanningPreference


def parse_ai_schedule_draft_output(raw_output: str) -> ParsedScheduleDraft:
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
