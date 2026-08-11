from __future__ import annotations

import re
from typing import Any

from harness.mileday.dataset import MileDayMultiTurnCase
from harness.mileday.api_plan_builder import task_from_update_request


def _extract_schedule_intent_block(raw_output: str) -> str | None:
    match = re.search(
        r"\[(?:SCHEDULE_INTENT|일정_의도)\]\s*(?P<intent>.*?)\s*\[/(?:SCHEDULE_INTENT|일정_의도)\]",
        raw_output,
        re.DOTALL,
    )
    if match is None:
        return None
    intent = match.group("intent").strip()
    return intent or None


def _parse_mileday_schedule_intent_block(intent_block: str) -> tuple[dict[str, Any], list[str]]:
    intent: dict[str, Any] = {"action": "", "target": "", "change": "", "tasks": []}
    errors: list[str] = []
    key_map = {
        "action": "action",
        "행동": "action",
        "target": "target",
        "대상": "target",
        "change": "change",
        "변경": "change",
    }
    action_map = {
        "create": "create",
        "생성": "create",
        "partial_update": "partial_update",
        "부분수정": "partial_update",
        "부분 수정": "partial_update",
    }
    in_tasks = False
    for line_number, raw_line in enumerate(intent_block.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        lower = line.lower()
        if lower in {"tasks:", "작업:"}:
            in_tasks = True
            continue
        if in_tasks:
            if not line.startswith("- "):
                errors.append(f"Line {line_number} in tasks must start with '- '.")
                continue
            task = line[2:].strip()
            if not task:
                errors.append(f"Line {line_number} has an empty task.")
                continue
            intent["tasks"].append(task)
            continue
        if ":" not in line:
            errors.append(f"Line {line_number} must use 'key: value'.")
            continue
        key, value = [part.strip() for part in line.split(":", 1)]
        key = key_map.get(key.lower(), key_map.get(key))
        if key is None:
            errors.append(f"Line {line_number} has an unsupported key: {key}.")
            continue
        if key == "action":
            value = action_map.get(value.lower(), action_map.get(value, value))
        intent[key] = value
    if intent["action"] not in {"create", "partial_update"}:
        errors.append("action must be create or partial_update.")
    if not intent["target"]:
        errors.append("target must not be empty.")
    if not intent["change"]:
        errors.append("change must not be empty.")
    if not isinstance(intent["tasks"], list):
        errors.append("tasks must be a list.")
    return intent, errors


def _fallback_mileday_schedule_intent(
    case: MileDayMultiTurnCase,
    turn_id: int,
    raw_output: str,
) -> dict[str, Any] | None:
    if not raw_output.strip():
        return None
    tasks = _extract_candidate_tasks_from_freeform_output(raw_output)
    expected_action = case.turns[turn_id - 1].expected_action
    if expected_action == "partial_update" and not tasks:
        tasks = [task_from_update_request(case.turns[turn_id - 1].content, case)]
    elif expected_action == "create" and len(tasks) < case.expected.constraints.min_milestones:
        tasks = _default_mileday_tasks_for_goal(case)
    return {
        "action": expected_action,
        "target": case.input.initial_goal.title,
        "change": case.turns[turn_id - 1].content,
        "tasks": tasks,
        "source": "freeform_fallback",
    }


def _extract_candidate_tasks_from_freeform_output(raw_output: str) -> list[str]:
    tasks: list[str] = []
    for raw_line in raw_output.splitlines():
        line = raw_line.strip().strip("|").strip()
        if not line:
            continue
        if any(token in line for token in ('"title_prefix"', '"weekday"', '"scheduled_date"', "---", "날짜", "색상:", "완료여부:")):
            continue
        if line.startswith(("[", "{", "}", "```", "#")):
            continue
        if "|" in line:
            cells = [cell.strip() for cell in line.split("|") if cell.strip()]
            text = cells[-1] if cells else ""
        elif line.startswith("- "):
            text = line[2:].strip()
        else:
            text = line
        text = re.sub(r"^제목\s*:\s*", "", text).strip()
        text = re.sub(r"^\d{4}-\d{2}-\d{2}\s*", "", text).strip()
        text = re.sub(r"^S\d{3}\s*", "", text).strip()
        text = re.sub(r"^\[[^\]]+\]\s*", "", text).strip()
        if re.fullmatch(r"[월화수목금토일]요일?\(?\d{1,2}:\d{2}-\d{1,2}:\d{2}\)?", text):
            continue
        if 2 <= len(text) <= 40 and re.search(r"[가-힣]", text):
            tasks.append(text)
    deduped: list[str] = []
    for task in tasks:
        if task not in deduped:
            deduped.append(task)
    return deduped[:8]


def _default_mileday_tasks_for_goal(case: MileDayMultiTurnCase) -> list[str]:
    title = case.input.initial_goal.title
    return [
        f"{title} 준비",
        f"{title} 기초 진행",
        f"{title} 핵심 진행",
        f"{title} 중간 점검",
        f"{title} 최종 점검",
    ]

def extract_schedule_intent_block(raw_output: str) -> str | None:
    return _extract_schedule_intent_block(raw_output)


def parse_schedule_intent_block(intent_block: str) -> tuple[dict[str, Any], list[str]]:
    return _parse_mileday_schedule_intent_block(intent_block)


def fallback_schedule_intent(case: MileDayMultiTurnCase, turn_id: int, raw_output: str) -> dict[str, Any] | None:
    return _fallback_mileday_schedule_intent(case, turn_id, raw_output)
