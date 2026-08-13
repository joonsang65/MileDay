from __future__ import annotations

import json

from harness.mileday.ai_draft_schema import AI_DRAFT_PROMPT_VERSION
from harness.mileday.dataset import AiScheduleDraftCase


def build_ai_schedule_draft_prompt(case: AiScheduleDraftCase) -> str:
    availability = [
        {
            "date": item.date,
            "available_minutes": item.available_minutes,
        }
        for item in case.availability
    ]
    expected = {
        "deadline_latest": case.expected.deadline_latest,
        "milestone_count_min": case.expected.milestone_count_min,
        "milestone_count_max": case.expected.milestone_count_max,
        "preferred_weekdays": case.expected.preferred_weekdays,
        "intensity": case.expected.intensity,
        "allow_single_milestone": case.expected.allow_single_milestone,
    }
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
        "[TODAY]\n"
        f"{case.today}\n\n"
        "[TIMEZONE]\n"
        f"{case.timezone}\n\n"
        "[AVAILABLE_DATES]\n"
        f"{json.dumps(availability, ensure_ascii=False, sort_keys=True)}\n\n"
        "[EXPECTED_TEST_CONSTRAINTS]\n"
        f"{json.dumps(expected, ensure_ascii=False, sort_keys=True)}\n\n"
        "[PROMPT_VERSION]\n"
        f"{AI_DRAFT_PROMPT_VERSION}\n\n"
        "[USER_REQUEST]\n"
        f"{case.user_prompt}\n"
    )
