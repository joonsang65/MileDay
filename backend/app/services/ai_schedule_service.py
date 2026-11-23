from __future__ import annotations

import json
from typing import Any

from exceptions.common import BadRequestError
from infrastructure.gemini_client import GeminiClient, get_gemini_client
from schemas.ai_schedule_schemas import AiScheduleDraftRequest
from services.ai_schedule_parser import ParsedScheduleDraft, parse_ai_schedule_draft_output
from services.ai_schedule_validation import WEEKDAYS, validate_ai_schedule_draft


DEFAULT_GOAL_COLOR = "#7F9278"
PROMPT_VERSION = "v1-product-ai-draft"


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


def build_create_goal_payload(draft: dict[str, Any]) -> dict[str, Any]:
    goal = draft["goal"]
    milestones = draft["milestones"]
    goal_color = DEFAULT_GOAL_COLOR
    return {
        "goal": {
            "title": goal["title"],
            "deadline": goal["deadline"],
            "is_completed": False,
            "is_recurring": False,
            "recurrence_type": None,
            "color": goal_color,
        },
        "milestones": [
            {
                "title": item["title"],
                "scheduled_date": item["scheduled_date"],
                "color": goal_color,
                "is_completed": False,
            }
            for item in milestones
            if item.get("selected", True)
        ],
        "write_policy": "user_confirmation_required",
    }


def _with_ui_fields(draft: ParsedScheduleDraft) -> dict[str, Any]:
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


def get_ai_schedule_service() -> AiScheduleService:
    return AiScheduleService()
