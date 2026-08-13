from __future__ import annotations

import json
import re
from typing import Any

from harness.mileday.ai_draft_schema import AI_DRAFT_PROMPT_VERSION


JSON_BLOCK_PATTERN = re.compile(r"```(?:json)?\s*(?P<body>.*?)```", re.DOTALL | re.IGNORECASE)


def parse_ai_schedule_draft_output(raw_output: str) -> dict[str, Any]:
    payload = _load_json_object(raw_output)
    goal = payload.get("goal") if isinstance(payload.get("goal"), dict) else {}
    milestones = payload.get("milestones") if isinstance(payload.get("milestones"), list) else []
    preference = (
        payload.get("planning_preference")
        if isinstance(payload.get("planning_preference"), dict)
        else {}
    )
    normalized = {
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
        "prompt_version": AI_DRAFT_PROMPT_VERSION,
    }
    return normalized


def _load_json_object(raw_output: str) -> dict[str, Any]:
    text = raw_output.strip()
    match = JSON_BLOCK_PATTERN.fullmatch(text)
    if match is not None:
        text = match.group("body").strip()
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid AI draft JSON: {exc.msg}") from exc
    if not isinstance(value, dict):
        raise ValueError("AI draft output must be a JSON object.")
    return value


def _clean_string(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""
