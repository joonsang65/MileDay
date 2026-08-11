from __future__ import annotations

import re
from datetime import date
from typing import Any

from harness.mileday.dataset import MileDayMultiTurnCase
from harness.mileday.api_prompt import allowed_slots


def _plan_items_from_mileday_intent(
    case: MileDayMultiTurnCase,
    intent: dict[str, Any],
) -> list[dict[str, str]]:
    tasks = [task for task in intent.get("tasks", []) if isinstance(task, str) and task.strip()]
    min_items = case.expected.constraints.min_milestones
    max_items = case.expected.constraints.max_milestones
    item_count = min(max(len(tasks), min_items), max_items)
    if not tasks:
        tasks = [case.input.initial_goal.title]
    existing_dates = {item.scheduled_date for item in case.input.existing_schedule}
    slots = [
        slot
        for slot in allowed_slots(case)
        if slot["scheduled_date"] not in existing_dates
    ][:item_count]
    plan_items: list[dict[str, str]] = []
    for index, slot in enumerate(slots):
        raw_task = tasks[index] if index < len(tasks) else f"{case.input.initial_goal.title} {index + 1}단계"
        task = _sanitize_mileday_task(raw_task, case)
        plan_items.append({"slot_id": slot["slot_id"], "task": task})
    return plan_items


def _patch_items_from_mileday_intent(
    case: MileDayMultiTurnCase,
    turn_id: int,
    intent: dict[str, Any],
    previous_parsed: dict[str, Any] | None,
) -> list[dict[str, str]]:
    previous_plan_items = previous_parsed.get("plan_items") if isinstance(previous_parsed, dict) else []
    if not isinstance(previous_plan_items, list):
        return []
    request = case.turns[turn_id - 1].content
    if _is_add_request(request):
        return []
    if _is_date_move_request(request):
        return []
    tasks = [task for task in intent.get("tasks", []) if isinstance(task, str) and task.strip()]
    target_text = f"{intent.get('target', '')} {intent.get('change', '')} {' '.join(tasks)}"
    combined_text = f"{target_text} {request}"
    requested_destination_days = _requested_destination_weekdays(combined_text)
    if requested_destination_days and not _destination_days_available(case, requested_destination_days):
        return []

    target_slot_ids = _select_mileday_patch_target_slot_ids(case, previous_plan_items, combined_text)
    if not target_slot_ids:
        return []
    replacement = _replacement_task_from_intent(intent, case)
    return [{"slot_id": slot_id, "task": replacement} for slot_id in target_slot_ids]


def _add_items_from_mileday_intent(
    case: MileDayMultiTurnCase,
    turn_id: int,
    intent: dict[str, Any],
    previous_parsed: dict[str, Any] | None,
) -> list[dict[str, str]]:
    request = case.turns[turn_id - 1].content
    if not _is_add_request(request):
        return []
    previous_plan_items = previous_parsed.get("plan_items") if isinstance(previous_parsed, dict) else []
    if not isinstance(previous_plan_items, list):
        return []
    used_slot_ids = {
        item.get("slot_id")
        for item in previous_plan_items
        if isinstance(item, dict) and isinstance(item.get("slot_id"), str)
    }
    for slot in allowed_slots(case):
        if slot["slot_id"] not in used_slot_ids:
            return [{"slot_id": slot["slot_id"], "task": _task_from_update_request(request, case)}]
    return []


def _is_add_request(text: str) -> bool:
    return any(keyword in text for keyword in ("추가", "넣어", "새로"))


def _remove_slot_ids_from_mileday_intent(
    case: MileDayMultiTurnCase,
    turn_id: int,
    intent: dict[str, Any],
    previous_parsed: dict[str, Any] | None,
) -> list[str]:
    request = case.turns[turn_id - 1].content
    if not _is_remove_request(request):
        return []
    previous_plan_items = previous_parsed.get("plan_items") if isinstance(previous_parsed, dict) else []
    if not isinstance(previous_plan_items, list):
        return []
    target_text = _target_only_text(f"{intent.get('target', '')} {intent.get('change', '')} {request}")
    return _select_mileday_patch_target_slot_ids(case, previous_plan_items, target_text)


def _is_remove_request(text: str) -> bool:
    return any(keyword in text for keyword in ("빼", "제외", "삭제", "없애"))


def _is_date_move_request(text: str) -> bool:
    return any(
        keyword in text
        for keyword in ("하루 앞당", "하루 뒤", "한 주", "일주일", "앞으로 당", "앞당겨", "미뤄", "연기")
    )


def _replacement_task_from_intent(intent: dict[str, Any], case: MileDayMultiTurnCase) -> str:
    request_task = _task_from_update_request(str(intent.get("change") or ""), case)
    if request_task != case.input.initial_goal.title:
        return request_task
    tasks = [task for task in intent.get("tasks", []) if isinstance(task, str) and task.strip()]
    for task in tasks:
        if any(placeholder in task for placeholder in ("추가할 작업명", "유지할 작업명", "삭제할 작업명")):
            continue
        return _sanitize_mileday_task(task, case)
    change = str(intent.get("change") or "").strip()
    if change and not any(placeholder in change for placeholder in ("작업명 목록", "작업 목록")):
        return _sanitize_mileday_task(change, case)
    return case.input.initial_goal.title


def _sanitize_mileday_task(task: str, case: MileDayMultiTurnCase) -> str:
    request_task = _task_from_update_request(task, case)
    if request_task != case.input.initial_goal.title:
        return request_task
    cleaned = re.sub(r"\d{1,2}\s*시(?:\s*\d{1,2}\s*분)?\s*[~-]\s*\d{1,2}\s*시(?:\s*\d{1,2}\s*분)?", "", task)
    cleaned = re.sub(r"\d{1,2}:\d{2}\s*-\s*\d{1,2}:\d{2}", "", cleaned)
    cleaned = re.sub(r"(월|화|수|목|금|토|일)요일\s*(오전|오후)?", "", cleaned)
    cleaned = cleaned.replace("오전", "").replace("오후", "")
    cleaned = cleaned.strip(" -~:()")
    if "포장" in task:
        return "포장 관련 작업"
    if _contains_disallowed_english_task_text(cleaned):
        return case.input.initial_goal.title
    if not cleaned:
        return case.input.initial_goal.title
    return cleaned


def _task_from_update_request(text: str, case: MileDayMultiTurnCase) -> str:
    normalized = text.lower()
    if "회화 녹음" in text or ("피드백" in text and "회화" in text):
        return "회화 녹음 및 피드백"
    if "회복" in text:
        return "회복 위주 운동"
    if "포장" in text:
        return "포장 관련 작업"
    if "기술 블로그" in text or "블로그 글" in text:
        return "기술 블로그 글 작성"
    if "1시간" in text or "한 시간" in text or ("reduce" in normalized and ("hour" in normalized or "duration" in normalized)):
        return "1시간 축소 학습"
    return case.input.initial_goal.title


def _requested_destination_weekdays(text: str) -> set[str]:
    if not any(keyword in text for keyword in ("옮", "이동", "변경")):
        return set()
    return _mentioned_weekday_values(text)


def _destination_days_available(case: MileDayMultiTurnCase, weekdays: set[str]) -> bool:
    available_days = {item.day_of_week for item in case.input.availability}
    return weekdays <= available_days


def _select_mileday_patch_target_slot_ids(
    case: MileDayMultiTurnCase,
    previous_plan_items: list[Any],
    target_text: str,
) -> list[str]:
    slots_by_id = {slot["slot_id"]: slot for slot in allowed_slots(case)}
    previous_slot_ids = [
        item.get("slot_id")
        for item in previous_plan_items
        if isinstance(item, dict) and isinstance(item.get("slot_id"), str)
    ]
    explicit_slot_ids = [
        slot_id
        for slot_id in re.findall(r"\bS\d{3}\b", target_text)
        if slot_id in previous_slot_ids
    ]
    if explicit_slot_ids:
        return list(dict.fromkeys(explicit_slot_ids))
    reduced_weekdays = _reduced_duration_weekdays(target_text)
    if reduced_weekdays:
        reduced_matches = [
            slot_id
            for slot_id in previous_slot_ids
            if slot_id in slots_by_id and slots_by_id[slot_id]["day_of_week"] in reduced_weekdays
        ]
        return _limit_single_target_if_requested(target_text, reduced_matches, slots_by_id)
    target_only_text = _target_only_text(target_text)
    weekdays = _mentioned_weekday_values(target_only_text)
    requested_week_index = _requested_plan_week_index(target_text)
    if requested_week_index is not None:
        week_matches = _slot_ids_in_plan_week(previous_slot_ids, slots_by_id, requested_week_index)
        if week_matches:
            return _limit_single_target_if_requested(target_text, week_matches, slots_by_id)
    matching_slot_ids = [
        slot_id
        for slot_id in previous_slot_ids
        if slot_id in slots_by_id and (not weekdays or slots_by_id[slot_id]["day_of_week"] in weekdays)
    ]
    if any(keyword in target_text for keyword in ("마지막", "최종")) and matching_slot_ids:
        return [max(matching_slot_ids, key=lambda slot_id: slots_by_id.get(slot_id, {}).get("scheduled_date", ""))]
    if weekdays:
        return _limit_single_target_if_requested(target_text, matching_slot_ids, slots_by_id)
    keywords = _target_keywords(target_text)
    if keywords:
        keyword_matches = []
        for item in previous_plan_items:
            if not isinstance(item, dict):
                continue
            slot_id = item.get("slot_id")
            task = item.get("task")
            if (
                isinstance(slot_id, str)
                and isinstance(task, str)
                and slot_id in matching_slot_ids
                and any(keyword in task for keyword in keywords)
            ):
                keyword_matches.append(slot_id)
        if keyword_matches:
            return _limit_single_target_if_requested(target_text, keyword_matches, slots_by_id)
        if any(keyword in target_only_text for keyword in keywords):
            return []
    if _single_patch_target_requested(target_text) and previous_slot_ids:
        return [previous_slot_ids[0]]
    return []


def _single_patch_target_requested(text: str) -> bool:
    normalized = text.lower()
    return any(
        keyword in normalized
        for keyword in (
            "하나만",
            "한 개만",
            "1개만",
            "하나",
            "one",
            "single",
            "only one",
        )
    )


def _limit_single_target_if_requested(
    request_text: str,
    slot_ids: list[str],
    slots_by_id: dict[str, dict[str, str]],
) -> list[str]:
    if not _single_patch_target_requested(request_text):
        return slot_ids
    if not slot_ids:
        return []
    return [max(slot_ids, key=lambda slot_id: slots_by_id.get(slot_id, {}).get("scheduled_date", ""))]


def _requested_plan_week_index(text: str) -> int | None:
    normalized = text.lower()
    if "두 번째 주" in text or "2번째 주" in text or "둘째 주" in text or "second week" in normalized:
        return 2
    if "첫 번째 주" in text or "1번째 주" in text or "첫째 주" in text or "first week" in normalized:
        return 1
    return None


def _slot_ids_in_plan_week(
    previous_slot_ids: list[str],
    slots_by_id: dict[str, dict[str, str]],
    week_index: int,
) -> list[str]:
    ordered_slot_ids = [
        slot_id
        for slot_id in previous_slot_ids
        if slot_id in slots_by_id and slots_by_id[slot_id].get("scheduled_date")
    ]
    if week_index <= 0 or not ordered_slot_ids:
        return []
    week_key_by_slot_id = {
        slot_id: date.fromisoformat(slots_by_id[slot_id]["scheduled_date"]).isocalendar()[:2]
        for slot_id in ordered_slot_ids
    }
    ordered_week_keys = []
    for slot_id in ordered_slot_ids:
        week_key = week_key_by_slot_id[slot_id]
        if week_key not in ordered_week_keys:
            ordered_week_keys.append(week_key)
    if week_index > len(ordered_week_keys):
        return []
    target_week = ordered_week_keys[week_index - 1]
    return [slot_id for slot_id in ordered_slot_ids if week_key_by_slot_id[slot_id] == target_week]


def _target_keywords(text: str) -> list[str]:
    candidates = ["회복", "포장", "복습", "암기", "발표", "일본어", "회화", "러닝", "달리기"]
    return [keyword for keyword in candidates if keyword in text]


def _target_only_text(text: str) -> str:
    before_maintain = re.split(r"유지|maintain|keep", text, maxsplit=1, flags=re.IGNORECASE)[0]
    markers = ["바꿔", "변경", "줄", "빼", "제외", "몰아", "옮", "이동", "앞당"]
    marker_positions = [before_maintain.find(marker) for marker in markers if before_maintain.find(marker) >= 0]
    if marker_positions:
        return before_maintain[: min(marker_positions)]
    return before_maintain


def _reduced_duration_weekdays(text: str) -> set[str]:
    normalized = text.lower()
    if not any(keyword in normalized for keyword in ("줄", "1시간", "한 시간", "reduce", "shorter")):
        return set()
    focused_weekdays = set()
    for match in re.finditer(r"([월화수목금토일]요일)[^.!?\n]*(?:1시간|한 시간|줄)", text):
        focused_weekdays.update(_mentioned_weekday_values(match.group(1)))
    for match in re.finditer(r"(mondays?|tuesdays?|wednesdays?|thursdays?|fridays?|saturdays?|sundays?)[^.!?\n]*(?:1\s*hour|reduce|shorter)", normalized):
        focused_weekdays.update(_mentioned_weekday_values(match.group(1)))
    if focused_weekdays:
        return focused_weekdays
    target_part = re.split(r"유지|maintain|keep", text, maxsplit=1, flags=re.IGNORECASE)[0]
    return _mentioned_weekday_values(target_part)


def _mentioned_weekday_values(text: str) -> set[str]:
    labels = {
        "월요일": "monday",
        "화요일": "tuesday",
        "수요일": "wednesday",
        "목요일": "thursday",
        "금요일": "friday",
        "토요일": "saturday",
        "일요일": "sunday",
        "monday": "monday",
        "mondays": "monday",
        "tuesday": "tuesday",
        "tuesdays": "tuesday",
        "wednesday": "wednesday",
        "wednesdays": "wednesday",
        "thursday": "thursday",
        "thursdays": "thursday",
        "friday": "friday",
        "fridays": "friday",
        "saturday": "saturday",
        "saturdays": "saturday",
        "sunday": "sunday",
        "sundays": "sunday",
    }
    normalized = text.lower()
    return {day for label, day in labels.items() if label in normalized}


def _apply_mileday_plan_patch(
    previous_plan_items: list[Any],
    patch_items: list[Any],
) -> list[dict[str, str]]:
    patch_by_slot = {
        item.get("slot_id"): item.get("task")
        for item in patch_items
        if isinstance(item, dict) and isinstance(item.get("slot_id"), str)
    }
    merged: list[dict[str, str]] = []
    for item in previous_plan_items:
        if not isinstance(item, dict):
            continue
        slot_id = item.get("slot_id")
        task = item.get("task")
        if not isinstance(slot_id, str) or not isinstance(task, str):
            continue
        merged.append({"slot_id": slot_id, "task": str(patch_by_slot.get(slot_id, task))})
    return merged


def _expand_mileday_patch_items_for_weekday_request(
    case: MileDayMultiTurnCase,
    previous_plan_items: list[Any],
    patch_items: list[dict[str, str]],
    user_request: str,
) -> list[dict[str, str]]:
    if not patch_items:
        return patch_items
    if "만" in user_request:
        return patch_items
    requested_weekdays = {
        day
        for label, day in {
            "월요일": "monday",
            "월": "monday",
            "화요일": "tuesday",
            "화": "tuesday",
            "수요일": "wednesday",
            "수": "wednesday",
            "목요일": "thursday",
            "목": "thursday",
            "금요일": "friday",
            "금": "friday",
            "토요일": "saturday",
            "토": "saturday",
            "일요일": "sunday",
            "일": "sunday",
        }.items()
        if label in user_request
    }
    if not requested_weekdays:
        return patch_items

    slots_by_id = {slot["slot_id"]: slot for slot in allowed_slots(case)}
    previous_slot_ids = [
        item.get("slot_id")
        for item in previous_plan_items
        if isinstance(item, dict) and isinstance(item.get("slot_id"), str)
    ]
    patch_by_day: dict[str, str] = {}
    for item in patch_items:
        slot = slots_by_id.get(item["slot_id"])
        if slot is not None and slot["day_of_week"] in requested_weekdays:
            patch_by_day[slot["day_of_week"]] = item["task"]
    if not patch_by_day:
        return patch_items

    expanded_by_slot = {item["slot_id"]: item for item in patch_items}
    for slot_id in previous_slot_ids:
        slot = slots_by_id.get(slot_id)
        if slot is None:
            continue
        task = patch_by_day.get(slot["day_of_week"])
        if task is not None:
            expanded_by_slot[slot_id] = {"slot_id": slot_id, "task": task}
    return list(expanded_by_slot.values())


def _contains_disallowed_english_task_text(task: str) -> bool:
    normalized = re.sub(r"(?i)\b\d+\s*(km|m|cm|mm|kg|g|ml|l)\b", "", task)
    normalized = re.sub(r"\b[A-Z]{2,8}\b", "", normalized)
    return re.search(r"[A-Za-z]{2,}", normalized) is not None


def _mentioned_korean_weekdays(task: str) -> set[str]:
    labels = {
        "월요일": "monday",
        "화요일": "tuesday",
        "수요일": "wednesday",
        "목요일": "thursday",
        "금요일": "friday",
        "토요일": "saturday",
        "일요일": "sunday",
    }
    return {day for label, day in labels.items() if label in task}


def _build_mileday_rule_based_user_message(
    case: MileDayMultiTurnCase,
    turn_id: int,
    parsed: dict[str, Any],
    previous_parsed: dict[str, Any] | None,
) -> str:
    availability = _format_mileday_availability(case)
    action = parsed.get("action")
    plan_items = parsed.get("plan_items")
    patch_items = parsed.get("patch_items")
    add_items = parsed.get("add_items")
    remove_slot_ids = parsed.get("remove_slot_ids")
    plan_count = len(plan_items) if isinstance(plan_items, list) else 0
    patch_count = len(patch_items) if isinstance(patch_items, list) else 0
    add_count = len(add_items) if isinstance(add_items, list) else 0
    remove_count = len(remove_slot_ids) if isinstance(remove_slot_ids, list) else 0
    previous_count = len(previous_parsed.get("plan_items", [])) if isinstance(previous_parsed, dict) else 0
    goal_title = case.input.initial_goal.title
    deadline = case.input.initial_goal.deadline
    requires_confirmation = "DB 반영 전 사용자 확인이 필요합니다."

    if action == "create":
        return (
            f"{goal_title} 목표를 {deadline}까지 진행할 수 있도록 {plan_count}개 일정을 제안했습니다. "
            f"가능 시간은 {availability}입니다. "
            f"{requires_confirmation}"
        )
    if patch_count == 0:
        if add_count > 0:
            return (
                f"요청한 일정 추가 {add_count}건을 반영하고, 기존 일정은 유지했습니다. "
                f"전체 일정 수는 {plan_count or previous_count}개이며 가능 시간은 {availability}입니다. "
                f"{requires_confirmation}"
            )
        if remove_count > 0:
            return (
                f"요청한 일정 제외 {remove_count}건을 반영하고, 나머지 일정은 유지했습니다. "
                f"전체 일정 수는 {plan_count or previous_count}개이며 가능 시간은 {availability}입니다. "
                f"{requires_confirmation}"
            )
        return (
            f"요청한 변경은 현재 가능한 시간({availability}) 안에서 바로 반영하기 어렵습니다. "
            "기존 일정은 변경하지 않았습니다. "
            f"{requires_confirmation}"
        )
    return (
        f"요청한 변경 {patch_count}건을 반영하고, 나머지 일정은 유지했습니다. "
        f"전체 일정 수는 {plan_count or previous_count}개이며 가능 시간은 {availability}입니다. "
        f"{requires_confirmation}"
    )


def _format_mileday_availability(case: MileDayMultiTurnCase) -> str:
    day_labels = {
        "monday": "월",
        "tuesday": "화",
        "wednesday": "수",
        "thursday": "목",
        "friday": "금",
        "saturday": "토",
        "sunday": "일",
    }
    return ", ".join(
        f"{day_labels.get(item.day_of_week, item.day_of_week)} {item.start_time}-{item.end_time}"
        for item in case.input.availability
    )

def build_plan_items(case: MileDayMultiTurnCase, intent: dict[str, Any]) -> list[dict[str, str]]:
    return _plan_items_from_mileday_intent(case, intent)


def build_patch_items(case: MileDayMultiTurnCase, turn_id: int, intent: dict[str, Any], previous_parsed: dict[str, Any] | None) -> list[dict[str, str]]:
    return _patch_items_from_mileday_intent(case, turn_id, intent, previous_parsed)


def build_add_items(case: MileDayMultiTurnCase, turn_id: int, intent: dict[str, Any], previous_parsed: dict[str, Any] | None) -> list[dict[str, str]]:
    return _add_items_from_mileday_intent(case, turn_id, intent, previous_parsed)


def build_remove_slot_ids(case: MileDayMultiTurnCase, turn_id: int, intent: dict[str, Any], previous_parsed: dict[str, Any] | None) -> list[str]:
    return _remove_slot_ids_from_mileday_intent(case, turn_id, intent, previous_parsed)


def apply_plan_patch(previous_plan_items: list[Any], patch_items: list[Any]) -> list[dict[str, str]]:
    return _apply_mileday_plan_patch(previous_plan_items, patch_items)


def expand_patch_items_for_weekday_request(case: MileDayMultiTurnCase, previous_plan_items: list[Any], patch_items: list[dict[str, str]], user_request: str) -> list[dict[str, str]]:
    return _expand_mileday_patch_items_for_weekday_request(case, previous_plan_items, patch_items, user_request)


def single_patch_target_requested(text: str) -> bool:
    return _single_patch_target_requested(text)


def contains_disallowed_english_task_text(task: str) -> bool:
    return _contains_disallowed_english_task_text(task)


def mentioned_korean_weekdays(task: str) -> set[str]:
    return _mentioned_korean_weekdays(task)


def build_rule_based_user_message(case: MileDayMultiTurnCase, turn_id: int, parsed: dict[str, Any], previous_parsed: dict[str, Any] | None) -> str:
    return _build_mileday_rule_based_user_message(case, turn_id, parsed, previous_parsed)


def task_from_update_request(text: str, case: MileDayMultiTurnCase) -> str:
    return _task_from_update_request(text, case)
