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


def build_api_multiturn_prompt(
    case: MileDayMultiTurnCase,
    turn_id: int,
    transcript: list[dict[str, str]],
) -> str:
    """Build the API-only prompt with stricter partial-update targeting."""

    turn = case.turns[turn_id - 1]
    allowed_slots = mileday_multiturn_allowed_slots(case)
    reference_date_context = mileday_multiturn_reference_date_context()
    return (
        "You are the MileDay schedule intent parser.\n"
        "Return only one [SCHEDULE_INTENT] block. Do not return JSON, markdown, explanations, dates, or DB payloads.\n"
        "Task names must be Korean and must not include weekdays, dates, AM/PM, or times.\n\n"
        "[OUTPUT_FORMAT]\n"
        "[SCHEDULE_INTENT]\n"
        "action: create or partial_update\n"
        "target: create target, or exactly one existing slot_id/task for partial_update\n"
        "change: requested change\n"
        "tasks:\n"
        "- Korean task name\n"
        "[/SCHEDULE_INTENT]\n\n"
        "[PARTIAL_UPDATE_RULES]\n"
        "- If the expected action is partial_update, write only the changed task candidate.\n"
        "- If the user says '하나만', '1개만', '일정 중 하나', or similar, target exactly one existing item.\n"
        "- Do not target the whole goal title for partial_update unless the user asked to update every item.\n"
        "- Use a target from [PREVIOUS_PLAN_TARGETS] when previous conversation exists.\n"
        "- If the request mentions '두 번째 주', choose one item whose slot date is in the second calendar week of the current plan.\n"
        "- Unmentioned items are preserved by the evaluator, so never rewrite preserved items in tasks.\n\n"
        "[PARTIAL_UPDATE_SCOPE_MAP]\n"
        "- single target: '하나만', '1개만', '일정 중 하나만' -> target one slot_id only, tasks has exactly 1 item.\n"
        "- weekday scope: '수요일 일정만', '화요일만' -> target all matching weekday slot_ids, tasks has one task per target slot.\n"
        "- weekday group scope: '평일 일정', '주말 일정' -> target all weekday or weekend slot_ids, tasks has one task per target slot.\n"
        "- last target: '마지막 일정만', '최종 일정만' -> target the latest slot_id only, tasks has exactly 1 item.\n"
        "- rewrite all task names: '작업명만 다시 정리', '날짜와 시간은 유지하고 작업명만 정리' -> target all existing slot_ids, tasks has one renamed task per existing slot.\n"
        "- add request: '추가해줘' -> describe only the new task candidate, not existing items.\n"
        "- remove request: '빼줘', '제외해줘', '삭제해줘' -> target only the item to remove and keep tasks empty.\n\n"
        "[TARGET_RULES]\n"
        "- For partial_update, target must name concrete slot_id values from [PREVIOUS_PLAN_TARGETS] whenever available.\n"
        "- If several slot_ids must change, write them in target separated by commas, for example: target: S001, S004.\n"
        "- The number of task lines must match the number of changed slot_ids, except remove requests.\n"
        "- Do not select weekend slots for weekday requests. Do not select weekday slots for weekend requests.\n"
        "- If the request says '또는' between scopes, prefer the narrower explicit weekday scope over the broader group scope.\n\n"
        "[PARTIAL_UPDATE_EXAMPLES]\n"
        "User: 두 번째 주 일정 중 하나만 작업명을 더 구체적으로 바꿔줘.\n"
        "Output target: one slot_id in the second week only. Output exactly one task.\n"
        "User: 수요일 또는 평일 일정만 강도를 낮춰줘.\n"
        "Output target: all Wednesday slot_ids only. Output one softened task per Wednesday slot.\n"
        "User: 평일 일정의 강도를 낮추고 주말 일정은 그대로 유지해줘.\n"
        "Output target: all weekday slot_ids only. Never target Saturday or Sunday.\n"
        "User: 날짜와 시간은 유지하고 작업명만 다시 정리해줘.\n"
        "Output target: all existing slot_ids. Output one renamed Korean task for each existing slot.\n\n"
        "[CREATE_RULES]\n"
        "- For create, write 3 to max_tasks Korean task candidates in a natural preparation sequence.\n\n"
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
        }
        for index, slot in enumerate(slots, start=1)
    ]


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
