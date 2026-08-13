from __future__ import annotations

import json
import re
from datetime import date
from typing import Any

from harness.mileday.api_constants import (
    MILEDAY_API_MULTITURN_PROMPT_VERSION,
    MILEDAY_MULTITURN_REFERENCE_TIMEZONE,
)
from harness.mileday.dataset import MileDayMultiTurnCase
from harness.mileday.time_prefix import canonical_title_prefix, date_day_of_week, ko_weekday


def api_schedule_intent_response_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["create", "partial_update"]},
            "operation": {"type": "string", "enum": ["add", "remove", "rename", "none"]},
            "target": {"type": "string"},
            "target_selector_type": {
                "type": "string",
                "enum": ["slot_id", "slot_id_list", "task_text", "weekday", "position", "duration", "ambiguous"],
            },
            "target_selector_value": {"type": "string"},
            "target_selector_confidence": {"type": "string", "enum": ["high", "medium", "low"]},
            "preserve_selector_type": {
                "type": "string",
                "enum": ["none", "slot_id", "slot_id_list", "weekday", "latest_added"],
            },
            "preserve_selector_values": {"type": "array", "items": {"type": "string"}},
            "requires_clarification": {"type": "boolean"},
            "selected_slot_ids": {"type": "array", "items": {"type": "string"}},
            "change": {"type": "string"},
            "tasks": {"type": "array", "items": {"type": "string"}},
            "mutation_safety_check": {
                "type": "string",
                "enum": [
                    "single_target_matched",
                    "no_target_matched",
                    "multiple_targets_matched",
                    "ambiguous_request",
                    "create_scope_checked",
                ],
            },
        },
        "required": [
            "action",
            "operation",
            "target",
            "target_selector_type",
            "target_selector_value",
            "target_selector_confidence",
            "preserve_selector_type",
            "preserve_selector_values",
            "requires_clarification",
            "selected_slot_ids",
            "change",
            "tasks",
            "mutation_safety_check",
        ],
    }


def build_api_multiturn_prompt(
    case: MileDayMultiTurnCase,
    turn_id: int,
    transcript: list[dict[str, str]],
) -> str:
    """Build the API-only prompt with a compact English output contract."""

    turn = case.turns[turn_id - 1]
    allowed_slots = mileday_multiturn_allowed_slots(case)
    reference_date_context = mileday_multiturn_reference_date_context()
    return (
        "You are the MileDay schedule intent parser.\n"
        "Return one JSON object matching the response schema. If no schema is active, return one [SCHEDULE_INTENT] block with the same fields.\n"
        "Do not return markdown, explanations, DB ids, SQL, or DB payloads.\n"
        "Task names must be Korean and must not include weekdays, dates, AM/PM, or times.\n\n"
        "[CONTRACT]\n"
        "- Keep field names and enum values in English exactly as defined by the schema.\n"
        "- Translate Korean user intent into action, operation, selectors, selected_slot_ids, and tasks.\n"
        "- create: selected_slot_ids and tasks are required; their lengths and order must match.\n"
        "- add: tasks must contain only new milestone titles. Choose one unused selected_slot_id from [AVAILABLE_SLOTS] after last_plan_slot_id when possible. If no safe slot is clear, leave selected_slot_ids empty and use target_selector_type=position or ambiguous.\n"
        "- remove: tasks must be empty. Select exactly one existing slot from [PREVIOUS_PLAN_TARGETS], or require clarification.\n"
        "- rename: keep the same date/time and select exactly one existing slot. tasks contains the new title only.\n"
        "- none: no mutation. Use it for unclear requests, low confidence, or requests that ask not to decide arbitrarily.\n\n"
        "[SELECTOR_VALUES]\n"
        "- target_selector_type: slot_id, slot_id_list, task_text, weekday, position, duration, or ambiguous.\n"
        "- target_selector_value examples: S002, S002,S004, task phrase, monday, saturday, first, last, shortest, longest, none.\n"
        "- preserve_selector_type: none, slot_id, slot_id_list, weekday, or latest_added.\n"
        "- mutation_safety_check: create_scope_checked for create; single_target_matched only when exactly one target is clear; ambiguous_request when clarification is needed.\n\n"
        "[SAFETY]\n"
        "- Never invent goal_id or milestone_id. The parser resolves DB ids after validation.\n"
        "- Do not rewrite preserved milestones for add/remove.\n"
        "- Do not change dates or times for rename.\n"
        "- Do not use all available slots when the request asks for only a subset.\n\n"
        "[TIME_PLANNING]\n"
        "- Read each slot as date, time_range, and duration_minutes.\n"
        "- Short slots should get light tasks such as review, check, organize, confirm, or memo.\n"
        "- Long slots should get core tasks such as write, build, solve, implement, rehearse, or analyze.\n"
        "- If the user maps short/long slots to task types, follow that mapping exactly.\n"
        "- Create schedules should progress toward the deadline; do not use only the earliest slots when later slots are available.\n"
        "- Add should use an unused slot after the current plan when possible. Use [PLAN_SLOT_BASELINE].last_plan_slot_id as the baseline, then choose a later available slot id. If preserve_selector limits scope, add inside that scope.\n\n"
        "[EXAMPLES]\n"
        "{\"action\":\"create\",\"operation\":\"none\",\"target\":\"goal schedule\",\"target_selector_type\":\"ambiguous\",\"target_selector_value\":\"none\",\"target_selector_confidence\":\"high\",\"preserve_selector_type\":\"none\",\"preserve_selector_values\":[],\"requires_clarification\":false,\"selected_slot_ids\":[\"S001\",\"S003\"],\"change\":\"create selected milestones\",\"tasks\":[\"자료 범위 확인\",\"최종 점검\"],\"mutation_safety_check\":\"create_scope_checked\"}\n"
        "{\"action\":\"partial_update\",\"operation\":\"add\",\"target\":\"new milestone\",\"target_selector_type\":\"position\",\"target_selector_value\":\"last\",\"target_selector_confidence\":\"high\",\"preserve_selector_type\":\"none\",\"preserve_selector_values\":[],\"requires_clarification\":false,\"selected_slot_ids\":[\"S006\"],\"change\":\"add one milestone\",\"tasks\":[\"추가 점검 작업\"],\"mutation_safety_check\":\"single_target_matched\"}\n"
        "{\"action\":\"partial_update\",\"operation\":\"remove\",\"target\":\"S002\",\"target_selector_type\":\"slot_id\",\"target_selector_value\":\"S002\",\"target_selector_confidence\":\"high\",\"preserve_selector_type\":\"none\",\"preserve_selector_values\":[],\"requires_clarification\":false,\"selected_slot_ids\":[],\"change\":\"remove one milestone\",\"tasks\":[],\"mutation_safety_check\":\"single_target_matched\"}\n"
        "{\"action\":\"partial_update\",\"operation\":\"none\",\"target\":\"needs confirmation\",\"target_selector_type\":\"ambiguous\",\"target_selector_value\":\"none\",\"target_selector_confidence\":\"low\",\"preserve_selector_type\":\"none\",\"preserve_selector_values\":[],\"requires_clarification\":true,\"selected_slot_ids\":[],\"change\":\"do not mutate\",\"tasks\":[],\"mutation_safety_check\":\"ambiguous_request\"}\n\n"
        "[EVALUATION_CONTEXT]\n"
        f"expected_action: {turn.expected_action}\n"
        f"max_tasks: {case.expected.constraints.max_milestones}\n"
        f"latest_allowed_date: {case.expected.constraints.latest_allowed_date}\n"
        f"prompt_version: {MILEDAY_API_MULTITURN_PROMPT_VERSION}\n\n"
        "[REFERENCE_DATE]\n"
        f"{json.dumps(_ko_reference_date_context(reference_date_context), ensure_ascii=False, sort_keys=True)}\n\n"
        "[GOAL]\n"
        f"{json.dumps(_ko_goal_context(case), ensure_ascii=False, sort_keys=True)}\n\n"
        "[AVAILABLE_SLOTS]\n"
        f"{json.dumps(_ko_allowed_slot_context(allowed_slots), ensure_ascii=False, sort_keys=True)}\n\n"
        "[PREVIOUS_PLAN_TARGETS]\n"
        f"{_api_previous_plan_targets(case, transcript)}\n\n"
        "[PLAN_SLOT_BASELINE]\n"
        f"{json.dumps(_api_plan_slot_baseline(case, transcript), ensure_ascii=False, sort_keys=True)}\n\n"
        "[PREVIOUS_CONVERSATION]\n"
        f"{mileday_multiturn_transcript_text(transcript)}\n\n"
        "[USER_REQUEST]\n"
        f"{turn.content}\n"
    )


def _api_previous_plan_targets(case: MileDayMultiTurnCase, transcript: list[dict[str, str]]) -> str:
    if not transcript:
        return "none"
    slots_by_id = {slot["slot_id"]: slot for slot in mileday_multiturn_allowed_slots(case)}
    lines: list[str] = []
    seen: set[str] = set()
    for message in transcript:
        if message.get("role") != "assistant":
            continue
        for match in re.finditer(r"(S\d{3})\s*\|\s*([^\n\r]+)", message.get("content", "")):
            slot_id = match.group(1)
            if slot_id in seen or slot_id not in slots_by_id:
                continue
            seen.add(slot_id)
            slot = slots_by_id[slot_id]
            task = match.group(2).strip()
            lines.append(f"- {slot_id} | {slot['scheduled_date']} | {slot['weekday']} | {task}")
    return "\n".join(lines) if lines else "none"


def _api_plan_slot_baseline(case: MileDayMultiTurnCase, transcript: list[dict[str, str]]) -> dict[str, str | list[str]]:
    plan_slot_ids = _previous_plan_slot_ids(case, transcript)
    return {
        "last_plan_slot_id": plan_slot_ids[-1] if plan_slot_ids else "none",
        "current_plan_slot_ids": plan_slot_ids,
        "add_rule": "For add, choose an unused AVAILABLE_SLOTS slot_id greater than last_plan_slot_id when possible.",
    }


def _previous_plan_slot_ids(case: MileDayMultiTurnCase, transcript: list[dict[str, str]]) -> list[str]:
    if not transcript:
        return []
    valid_slot_ids = {slot["slot_id"] for slot in mileday_multiturn_allowed_slots(case)}
    slot_ids: list[str] = []
    for message in transcript:
        if message.get("role") != "assistant":
            continue
        for slot_id in re.findall(r"\bS\d{3}\b", message.get("content", "")):
            if slot_id in valid_slot_ids and slot_id not in slot_ids:
                slot_ids.append(slot_id)
    return slot_ids


def mileday_multiturn_transcript_text(transcript: list[dict[str, str]]) -> str:
    if not transcript:
        return "이전 대화 없음."
    chunks = []
    for index, message in enumerate(transcript, start=1):
        role = message["role"]
        content = message["content"].strip()
        chunks.append(f"{index}. {role}:\n{content}")
    return "\n\n".join(chunks)


def _ko_reference_date_context(context: dict[str, str]) -> dict[str, str]:
    return {
        "오늘": context["today"],
        "요일": context["weekday"],
        "시간대": "한국 표준시",
    }


def _ko_goal_context(case: MileDayMultiTurnCase) -> dict[str, str | bool | None]:
    goal = case.input.initial_goal
    return {
        "제목": goal.title,
        "마감일": goal.deadline,
        "반복여부": "예" if goal.is_recurring else "아니오",
        "반복유형": goal.recurrence_type or "",
        "색상": goal.color,
    }


def _ko_allowed_slot_context(slots: list[dict[str, str]]) -> list[dict[str, str]]:
    return [
        {
            "순번": str(index),
            "날짜": slot["scheduled_date"],
            "요일": slot["weekday"],
            "시간": slot["time_range"],
            "duration_minutes": _slot_duration_minutes(slot["time_range"]),
        }
        for index, slot in enumerate(slots, start=1)
    ]


def _slot_duration_minutes(time_range: str) -> int:
    start, end = time_range.split("-", maxsplit=1)
    start_hour, start_minute = [int(part) for part in start.split(":", maxsplit=1)]
    end_hour, end_minute = [int(part) for part in end.split(":", maxsplit=1)]
    return (end_hour * 60 + end_minute) - (start_hour * 60 + start_minute)


def mileday_multiturn_reference_date_context() -> dict[str, str]:
    today = date.today()
    day_of_week = date_day_of_week(today.isoformat())
    return {
        "today": today.isoformat(),
        "weekday": ko_weekday(day_of_week),
        "day_of_week": day_of_week or "",
        "timezone": MILEDAY_MULTITURN_REFERENCE_TIMEZONE,
    }


def mileday_multiturn_allowed_slots(case: MileDayMultiTurnCase) -> list[dict[str, str]]:
    start_date = date.today()
    end_date = date.fromisoformat(case.expected.constraints.latest_allowed_date)
    availability_by_day = {item.day_of_week: item for item in case.input.availability}
    slots: list[dict[str, str]] = []
    slot_index = 1
    current = start_date
    while current <= end_date:
        day_of_week = date_day_of_week(current.isoformat())
        window = availability_by_day.get(day_of_week or "")
        if window is not None:
            weekday_ko = ko_weekday(day_of_week)
            time_range = f"{window.start_time}-{window.end_time}"
            slots.append(
                {
                    "slot_id": f"S{slot_index:03d}",
                    "scheduled_date": current.isoformat(),
                    "day_of_week": day_of_week,
                    "weekday": weekday_ko,
                    "time_range": time_range,
                    "title_prefix": canonical_title_prefix(day_of_week or "", window.start_time, window.end_time),
                }
            )
            slot_index += 1
        current = date.fromordinal(current.toordinal() + 1)
    return slots

def append_plan_targets_to_transcript(content: str, parsed_json: dict[str, Any]) -> str:
    plan_items = parsed_json.get("plan_items")
    if not isinstance(plan_items, list):
        return content
    lines = []
    for item in plan_items:
        if not isinstance(item, dict):
            continue
        slot_id = item.get("slot_id")
        task = item.get("task")
        if isinstance(slot_id, str) and isinstance(task, str):
            lines.append(f"- {slot_id} | {task}")
    if not lines:
        return content
    return content.rstrip() + "\n\n[CURRENT_PLAN_TARGETS]\n" + "\n".join(lines)


def turn_case_id(case_id: str, turn_id: int) -> str:
    return f"{case_id}-turn-{turn_id}"


def allowed_slots(case: MileDayMultiTurnCase) -> list[dict[str, str]]:
    return mileday_multiturn_allowed_slots(case)
