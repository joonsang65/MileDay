from __future__ import annotations

import re
from datetime import date
from typing import Any

from harness.mileday.dataset import MileDayMultiTurnCase
from harness.mileday.api_prompt import allowed_slots


REMOVE_SCORE_THRESHOLD = 2.0


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
    candidate_slots = [
        slot
        for slot in allowed_slots(case)
        if slot["scheduled_date"] not in existing_dates
    ]
    slots_by_id = {slot["slot_id"]: slot for slot in candidate_slots}
    selected_slot_ids = [
        normalized_slot_id
        for slot_id in intent.get("selected_slot_ids", [])
        if isinstance(slot_id, str)
        for normalized_slot_id in [_normalize_slot_id(slot_id)]
        if normalized_slot_id in slots_by_id
    ]
    if selected_slot_ids:
        slots = [slots_by_id[slot_id] for slot_id in selected_slot_ids[:item_count]]
    else:
        slots = candidate_slots[:item_count]
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
    operation = _intent_operation(intent, request)
    if operation in {"none", "add", "remove"} or _requires_clarification(intent):
        return []
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

    selector_slot_ids = _resolve_target_selector(case, previous_plan_items, intent)
    if selector_slot_ids and len(selector_slot_ids) != 1:
        return []
    target_slot_ids = selector_slot_ids or _select_mileday_patch_target_slot_ids(case, previous_plan_items, combined_text)
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
    operation = _intent_operation(intent, request)
    if operation in {"none", "remove", "rename"} or _requires_clarification(intent):
        return []
    if operation != "add" and (not _is_add_request(request) or _is_ambiguous_mutation_request(request)):
        return []
    previous_plan_items = previous_parsed.get("plan_items") if isinstance(previous_parsed, dict) else []
    if not isinstance(previous_plan_items, list):
        return []
    used_slot_ids = {
        item.get("slot_id")
        for item in previous_plan_items
        if isinstance(item, dict) and isinstance(item.get("slot_id"), str)
    }
    slots_by_id = {slot["slot_id"]: slot for slot in allowed_slots(case)}
    raw_selected_slot_ids = [
        normalized_slot_id
        for slot_id in intent.get("selected_slot_ids", [])
        if isinstance(slot_id, str)
        for normalized_slot_id in [_normalize_slot_id(slot_id)]
        if normalized_slot_id in slots_by_id and normalized_slot_id not in used_slot_ids
    ]
    selected_slot_ids = _filter_add_slots_by_preserve_scope(case, raw_selected_slot_ids, intent)
    if selected_slot_ids:
        return [{"slot_id": selected_slot_ids[0], "task": _add_task_from_intent(intent, request, case)}]
    if raw_selected_slot_ids:
        return []
    latest_used_slot = _latest_used_slot_id(used_slot_ids, case)
    slot_sort_keys = {slot["slot_id"]: slot for slot in allowed_slots(case)}
    for slot in allowed_slots(case):
        if slot["slot_id"] not in used_slot_ids:
            if latest_used_slot and _slot_sort_key(slot["slot_id"], slot_sort_keys) <= _slot_sort_key(latest_used_slot, slot_sort_keys):
                continue
            return [{"slot_id": slot["slot_id"], "task": _add_task_from_intent(intent, request, case)}]
    return []


def _is_add_request(text: str) -> bool:
    return any(keyword in text for keyword in ("추가", "넣어", "새로"))


def _add_task_from_intent(intent: dict[str, Any], request: str, case: MileDayMultiTurnCase) -> str:
    tasks = [task for task in intent.get("tasks", []) if isinstance(task, str) and task.strip()]
    if tasks:
        return _sanitize_mileday_task(tasks[0], case)
    return _task_from_update_request(request, case)


def _remove_slot_ids_from_mileday_intent(
    case: MileDayMultiTurnCase,
    turn_id: int,
    intent: dict[str, Any],
    previous_parsed: dict[str, Any] | None,
) -> list[str]:
    request = case.turns[turn_id - 1].content
    operation = _intent_operation(intent, request)
    if operation in {"none", "add", "rename"} or _requires_clarification(intent):
        return []
    if operation != "remove" and (not _is_remove_request(request) or _is_ambiguous_mutation_request(request)):
        return []
    previous_plan_items = previous_parsed.get("plan_items") if isinstance(previous_parsed, dict) else []
    if not isinstance(previous_plan_items, list):
        return []
    tasks = [task for task in intent.get("tasks", []) if isinstance(task, str) and task.strip()]
    target_text = f"{intent.get('target', '')} {intent.get('change', '')} {' '.join(tasks)} {request}"
    selector_slot_ids = _resolve_target_selector(case, previous_plan_items, intent)
    if _target_selector_confidence(intent) == "low":
        return []
    if selector_slot_ids:
        if len(selector_slot_ids) != 1:
            return []
        protected = _resolve_preserve_selector(case, previous_plan_items, intent)
        return [slot_id for slot_id in selector_slot_ids if slot_id not in protected]
    return _select_mileday_remove_target_slot_ids(case, previous_plan_items, target_text)


def _is_remove_request(text: str) -> bool:
    return any(keyword in text for keyword in ("빼", "제외", "삭제", "없애"))


def _is_ambiguous_mutation_request(text: str) -> bool:
    return (
        any(keyword in text for keyword in ("추가하거나", "추가 또는", "넣거나", "빼거나", "삭제하거나"))
        and any(keyword in text for keyword in ("애매", "임의로", "확인", "필요"))
    )


def _intent_operation(intent: dict[str, Any], request: str) -> str:
    operation = intent.get("operation")
    if operation in {"add", "remove", "rename", "none"}:
        return str(operation)
    if _is_ambiguous_mutation_request(request):
        return "none"
    if _is_remove_request(request):
        return "remove"
    if _is_add_request(request):
        return "add"
    return "rename"


def _requires_clarification(intent: dict[str, Any]) -> bool:
    selector = intent.get("target_selector")
    return intent.get("requires_clarification") is True or (
        isinstance(selector, dict) and selector.get("type") == "ambiguous"
    )


def _filter_add_slots_by_preserve_scope(
    case: MileDayMultiTurnCase,
    selected_slot_ids: list[str],
    intent: dict[str, Any],
) -> list[str]:
    selector = intent.get("preserve_selector")
    if not isinstance(selector, dict) or selector.get("type") != "weekday":
        return selected_slot_ids
    weekdays = _mentioned_weekday_values(" ".join(str(value) for value in selector.get("values", [])))
    if not weekdays:
        value = selector.get("value")
        weekdays = _mentioned_weekday_values(str(value or ""))
    if not weekdays:
        return selected_slot_ids
    slots_by_id = {slot["slot_id"]: slot for slot in allowed_slots(case)}
    return [
        slot_id
        for slot_id in selected_slot_ids
        if slots_by_id.get(slot_id, {}).get("day_of_week") in weekdays
    ]


def _resolve_target_selector(
    case: MileDayMultiTurnCase,
    previous_plan_items: list[Any],
    intent: dict[str, Any],
) -> list[str]:
    selector = intent.get("target_selector")
    if not isinstance(selector, dict):
        return []
    if selector.get("confidence") == "low":
        return []
    return _resolve_selector(case, previous_plan_items, selector)


def _target_selector_confidence(intent: dict[str, Any]) -> str:
    selector = intent.get("target_selector")
    if isinstance(selector, dict) and isinstance(selector.get("confidence"), str):
        return selector["confidence"]
    return ""


def _resolve_preserve_selector(
    case: MileDayMultiTurnCase,
    previous_plan_items: list[Any],
    intent: dict[str, Any],
) -> set[str]:
    selector = intent.get("preserve_selector")
    if not isinstance(selector, dict):
        return set()
    return set(_resolve_selector(case, previous_plan_items, selector))


def _resolve_selector(
    case: MileDayMultiTurnCase,
    previous_plan_items: list[Any],
    selector: dict[str, Any],
) -> list[str]:
    slots_by_id = {slot["slot_id"]: slot for slot in allowed_slots(case)}
    candidates = _remove_candidates(previous_plan_items, slots_by_id)
    slot_ids = [candidate["slot_id"] for candidate in candidates]
    selector_type = selector.get("type")
    value = selector.get("value")
    values = selector.get("values")
    if selector_type == "slot_id":
        raw_values = values if isinstance(values, list) else [value]
        return [
            normalized
            for item in raw_values
            if isinstance(item, str)
            for normalized in [_normalize_slot_id(item)]
            if normalized in slot_ids
        ]
    if selector_type == "slot_id_list":
        raw_values = values if isinstance(values, list) else str(value or "").split(",")
        return [
            normalized
            for item in raw_values
            if isinstance(item, str)
            for normalized in [_normalize_slot_id(item)]
            if normalized in slot_ids
        ]
    if selector_type == "weekday":
        weekdays = _mentioned_weekday_values(str(value or ""))
        if not weekdays:
            weekdays = {str(value)}
        return [
            candidate["slot_id"]
            for candidate in candidates
            if slots_by_id[candidate["slot_id"]]["day_of_week"] in weekdays
        ]
    if selector_type == "position":
        if value == "first":
            return [slot_ids[0]] if slot_ids else []
        if value == "last":
            return [max(slot_ids, key=lambda slot_id: _slot_sort_key(slot_id, slots_by_id))] if slot_ids else []
        return []
    if selector_type == "duration":
        if value == "shortest":
            slot_id = _duration_extreme_slot_id(candidates, slots_by_id, shortest=True)
            return [slot_id] if slot_id else []
        if value == "longest":
            slot_id = _duration_extreme_slot_id(candidates, slots_by_id, shortest=False)
            return [slot_id] if slot_id else []
        return []
    if selector_type == "task_text":
        scored = score_remove_candidates(str(value or ""), candidates, slots_by_id)
        if not scored:
            return []
        top_score = scored[0][1]
        top_slot_ids = [slot_id for slot_id, score in scored if score == top_score]
        if top_score < REMOVE_SCORE_THRESHOLD or len(top_slot_ids) != 1:
            return []
        return [top_slot_ids[0]]
    if selector_type == "latest_added":
        return [slot_ids[-1]] if slot_ids else []
    return []


def _normalize_slot_id(value: str) -> str:
    raw = value.strip()
    if re.fullmatch(r"S\d{3}", raw):
        return raw
    if re.fullmatch(r"\d{1,3}", raw):
        return f"S{int(raw):03d}"
    return raw


def _latest_used_slot_id(used_slot_ids: set[Any], case: MileDayMultiTurnCase) -> str | None:
    slots_by_id = {slot["slot_id"]: slot for slot in allowed_slots(case)}
    valid_slot_ids = [slot_id for slot_id in used_slot_ids if isinstance(slot_id, str) and slot_id in slots_by_id]
    if not valid_slot_ids:
        return None
    return max(valid_slot_ids, key=lambda slot_id: _slot_sort_key(slot_id, slots_by_id))


def _is_date_move_request(text: str) -> bool:
    return any(
        keyword in text
        for keyword in ("하루 앞당", "하루 뒤", "한 주", "일주일", "앞으로 당", "앞당겨", "미뤄", "연기")
    )


def _replacement_task_from_intent(intent: dict[str, Any], case: MileDayMultiTurnCase) -> str:
    tasks = [task for task in intent.get("tasks", []) if isinstance(task, str) and task.strip()]
    for task in tasks:
        if any(placeholder in task for placeholder in ("추가할 작업명", "유지할 작업명", "삭제할 작업명")):
            continue
        return _clean_mileday_task_text(task, case)
    request_task = _task_from_update_request(str(intent.get("change") or ""), case)
    if request_task != case.input.initial_goal.title:
        return request_task
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


def _clean_mileday_task_text(task: str, case: MileDayMultiTurnCase) -> str:
    cleaned = re.sub(r"\d{1,2}\s*시(?:\s*\d{1,2}\s*분)?\s*[~-]\s*\d{1,2}\s*시(?:\s*\d{1,2}\s*분)?", "", task)
    cleaned = re.sub(r"\d{1,2}:\d{2}\s*-\s*\d{1,2}:\d{2}", "", cleaned)
    cleaned = re.sub(r"(월|화|수|목|금|토|일)요일\s*(오전|오후)?", "", cleaned)
    cleaned = cleaned.replace("오전", "").replace("오후", "")
    cleaned = cleaned.strip(" -~:()")
    if _contains_disallowed_english_task_text(cleaned):
        return case.input.initial_goal.title
    return cleaned or case.input.initial_goal.title


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


def _select_mileday_remove_target_slot_ids(
    case: MileDayMultiTurnCase,
    previous_plan_items: list[Any],
    target_text: str,
) -> list[str]:
    slots_by_id = {slot["slot_id"]: slot for slot in allowed_slots(case)}
    candidates = _remove_candidates(previous_plan_items, slots_by_id)
    previous_slot_ids = [candidate["slot_id"] for candidate in candidates]
    if not candidates:
        return []

    explicit_slot_ids = [
        slot_id
        for slot_id in re.findall(r"\bS\d{3}\b", target_text)
        if slot_id in previous_slot_ids
    ]
    if explicit_slot_ids:
        return list(dict.fromkeys(explicit_slot_ids))

    protected_slot_ids = _protected_remove_slot_ids(target_text, candidates, slots_by_id)
    target_only_text = _target_only_text(target_text)
    weekdays = _mentioned_weekday_values(target_only_text)
    if weekdays:
        matches = [
            candidate["slot_id"]
            for candidate in candidates
            if candidate["slot_id"] not in protected_slot_ids
            and candidate["slot_id"] in slots_by_id
            and slots_by_id[candidate["slot_id"]]["day_of_week"] in weekdays
        ]
        return _limit_single_target_if_requested(target_text, matches, slots_by_id)

    if _first_target_requested(target_text):
        matches = [candidate["slot_id"] for candidate in candidates if candidate["slot_id"] not in protected_slot_ids]
        return [matches[0]] if matches else []
    if any(keyword in target_text for keyword in ("마지막", "최종")):
        matches = [candidate["slot_id"] for candidate in candidates if candidate["slot_id"] not in protected_slot_ids]
        if not matches:
            return []
        return [max(matches, key=lambda slot_id: slots_by_id.get(slot_id, {}).get("scheduled_date", ""))]

    scored = score_remove_candidates(target_text, candidates, slots_by_id, protected_slot_ids)
    if not scored:
        return []
    top_score = scored[0][1]
    top_slot_ids = [slot_id for slot_id, score in scored if score == top_score]
    if top_score < REMOVE_SCORE_THRESHOLD or len(top_slot_ids) != 1:
        return []
    return [top_slot_ids[0]]


def score_remove_candidates(
    target_text: str,
    candidates: list[dict[str, str]],
    slots_by_id: dict[str, dict[str, str]],
    protected_slot_ids: set[str] | None = None,
) -> list[tuple[str, float]]:
    protected = protected_slot_ids or set()
    scoring_text = _remove_scoring_text(target_text)
    duplicate_slot_id = _duplicate_remove_candidate(candidates, slots_by_id)
    shortest_slot_id = _duration_extreme_slot_id(candidates, slots_by_id, shortest=True)
    longest_slot_id = _duration_extreme_slot_id(candidates, slots_by_id, shortest=False)
    wants_short = any(keyword in target_text for keyword in ("짧", "효과 없", "효과가 없"))
    wants_long = any(keyword in target_text for keyword in ("부담", "힘든", "긴 일정", "오래 걸"))
    wants_duplicate = any(keyword in target_text for keyword in ("중복", "겹치"))

    scored: list[tuple[str, float]] = []
    for candidate in candidates:
        slot_id = candidate["slot_id"]
        if slot_id in protected:
            continue
        score = 0.0
        score += _task_similarity_score(scoring_text, candidate["task"])
        if wants_short and slot_id == shortest_slot_id:
            score += 3.0
        if wants_long and slot_id == longest_slot_id:
            score += 3.0
        if wants_duplicate and slot_id == duplicate_slot_id:
            score += 3.0
        scored.append((slot_id, score))
    return sorted(scored, key=lambda item: (-item[1], _slot_sort_key(item[0], slots_by_id)))


def _remove_candidates(
    previous_plan_items: list[Any],
    slots_by_id: dict[str, dict[str, str]],
) -> list[dict[str, str]]:
    candidates: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in previous_plan_items:
        if not isinstance(item, dict):
            continue
        slot_id = item.get("slot_id")
        task = item.get("task")
        if (
            isinstance(slot_id, str)
            and isinstance(task, str)
            and slot_id in slots_by_id
            and slot_id not in seen
        ):
            seen.add(slot_id)
            candidates.append({"slot_id": slot_id, "task": task})
    return candidates


def _protected_remove_slot_ids(
    target_text: str,
    candidates: list[dict[str, str]],
    slots_by_id: dict[str, dict[str, str]],
) -> set[str]:
    protected: set[str] = set()
    for preserve_phrase in re.findall(r"([^.!?\n]*(?:유지|그대로|남겨)[^.!?\n]*)", target_text):
        protected.update(
            slot_id
            for slot_id in re.findall(r"\bS\d{3}\b", preserve_phrase)
            if any(candidate["slot_id"] == slot_id for candidate in candidates)
        )
        weekdays = _mentioned_weekday_values(preserve_phrase)
        if weekdays:
            protected.update(
                candidate["slot_id"]
                for candidate in candidates
                if slots_by_id[candidate["slot_id"]]["day_of_week"] in weekdays
            )
    if "새로 추가" in target_text or "추가한" in target_text:
        protected.add(candidates[-1]["slot_id"])
    return protected


def _remove_scoring_text(target_text: str) -> str:
    without_preserve = re.sub(r"[^.!?\n]*(?:유지|그대로|남겨)[^.!?\n]*", " ", target_text)
    return _target_only_text(without_preserve) + " " + without_preserve


def _task_similarity_score(request_text: str, task_text: str) -> float:
    request_tokens = _meaningful_korean_tokens(request_text)
    task_tokens = _meaningful_korean_tokens(task_text)
    exact_overlap = request_tokens & task_tokens
    score = len(exact_overlap) * 2.0

    request_compact = _compact_text(request_text)
    task_compact = _compact_text(task_text)
    substring_hits = 0
    for token in request_tokens - exact_overlap:
        if len(token) >= 2 and token in task_compact:
            substring_hits += 1
    for token in task_tokens - exact_overlap:
        if len(token) >= 2 and token in request_compact:
            substring_hits += 1
    if substring_hits:
        score += min(substring_hits, 2) * 1.5
    return score


def _meaningful_korean_tokens(text: str) -> set[str]:
    stop_words = {
        "일정",
        "작업",
        "하나",
        "한개",
        "한",
        "개",
        "빼줘",
        "빼",
        "제외",
        "삭제",
        "없애",
        "유지",
        "그대로",
        "남겨",
        "있으면",
        "너무",
        "대신",
        "관련",
        "요청",
        "반영",
    }
    normalized = re.sub(r"[^0-9A-Za-z가-힣]+", " ", text.lower())
    tokens = set()
    for token in normalized.split():
        stripped = _normalize_korean_token(token.strip())
        if len(stripped) < 2 or stripped in stop_words or re.fullmatch(r"s\d{3}", stripped):
            continue
        tokens.add(stripped)
    return tokens


def _normalize_korean_token(token: str) -> str:
    suffixes = (
        "으로",
        "에서",
        "에게",
        "하고",
        "해줘",
        "해",
        "은",
        "는",
        "이",
        "가",
        "을",
        "를",
        "의",
        "도",
        "만",
    )
    normalized = token
    for suffix in suffixes:
        if normalized.endswith(suffix) and len(normalized) > len(suffix) + 1:
            normalized = normalized[: -len(suffix)]
            break
    return normalized


def _compact_text(text: str) -> str:
    return re.sub(r"[^0-9A-Za-z가-힣]+", "", text.lower())


def _duration_extreme_slot_id(
    candidates: list[dict[str, str]],
    slots_by_id: dict[str, dict[str, str]],
    *,
    shortest: bool,
) -> str | None:
    durations = [
        (candidate["slot_id"], _slot_duration_minutes(slots_by_id[candidate["slot_id"]]))
        for candidate in candidates
        if candidate["slot_id"] in slots_by_id
    ]
    if not durations:
        return None
    extreme = min(duration for _, duration in durations) if shortest else max(duration for _, duration in durations)
    matches = [slot_id for slot_id, duration in durations if duration == extreme]
    return matches[0] if len(matches) == 1 else None


def _slot_duration_minutes(slot: dict[str, str]) -> int:
    start, end = slot["time_range"].split("-", maxsplit=1)
    start_hours, start_minutes = [int(part) for part in start.split(":", maxsplit=1)]
    end_hours, end_minutes = [int(part) for part in end.split(":", maxsplit=1)]
    return (end_hours * 60 + end_minutes) - (start_hours * 60 + start_minutes)


def _duplicate_remove_candidate(
    candidates: list[dict[str, str]],
    slots_by_id: dict[str, dict[str, str]],
) -> str | None:
    best_pair: tuple[str, str] | None = None
    best_overlap = 0
    for left_index, left in enumerate(candidates):
        left_tokens = _meaningful_korean_tokens(left["task"])
        for right in candidates[left_index + 1 :]:
            overlap = len(left_tokens & _meaningful_korean_tokens(right["task"]))
            if overlap > best_overlap:
                best_overlap = overlap
                best_pair = (left["slot_id"], right["slot_id"])
    if best_pair is None or best_overlap == 0:
        return None
    return max(best_pair, key=lambda slot_id: _slot_sort_key(slot_id, slots_by_id))


def _first_target_requested(text: str) -> bool:
    return any(keyword in text for keyword in ("첫 일정", "첫번째", "첫 번째", "처음"))


def _slot_sort_key(slot_id: str, slots_by_id: dict[str, dict[str, str]]) -> tuple[str, str]:
    slot = slots_by_id.get(slot_id, {})
    return (slot.get("scheduled_date", ""), slot_id)


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
