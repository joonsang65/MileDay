from __future__ import annotations

from typing import Any


AI_DRAFT_PROMPT_VERSION = "v1-ai-draft"
AI_DRAFT_DATASET_ID = "mileday-ai-schedule-draft"
AI_DRAFT_MODEL_ID = "gemini-3.5-flash-lite"
AI_DRAFT_FIXTURE = "tests/fixtures/mileday/ai_schedule_draft.json"
AI_DRAFT_RUNTIME_OPTIONS = {"thinking_level": "minimal"}


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
                            "enum": [
                                "monday",
                                "tuesday",
                                "wednesday",
                                "thursday",
                                "friday",
                                "saturday",
                                "sunday",
                            ],
                        },
                    },
                },
                "required": ["intensity", "preferred_days"],
            },
        },
        "required": ["goal", "milestones", "planning_preference"],
    }
