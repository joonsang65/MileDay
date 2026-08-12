from __future__ import annotations

import re
from datetime import date
from typing import Any

from harness.mileday.api_db_payload import build_schedule_db_payload
from harness.mileday.dataset import GOAL_DB_FIELDS, MILESTONE_DB_FIELDS, MileDayMultiTurnCase
from harness.mileday.api_prompt import allowed_slots as build_allowed_slots
from harness.mileday.api_plan_builder import (
    apply_plan_patch,
    contains_disallowed_english_task_text,
    expand_patch_items_for_weekday_request,
    mentioned_korean_weekdays,
    single_patch_target_requested,
)
from harness.mileday.time_prefix import parse_canonical_milestone_title


def _validate_mileday_multiturn_plan_output(
    case: MileDayMultiTurnCase,
    turn_id: int,
    parsed: dict[str, Any],
    previous_parsed: dict[str, Any] | None,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    failed_checks: list[dict[str, str]] = []

    def add_error(check: str, message: str, *, code: str | None = None, safety_gate: bool = False) -> None:
        errors.append(message)
        failed_checks.append(
            {
                "check": check,
                "failure_code": code or _failure_code_for_check(check),
                "severity": "critical" if safety_gate else "error",
                "message": message,
                "safety_gate": safety_gate,
                "validator_source": "deterministic",
            }
        )

    turn = case.turns[turn_id - 1]
    expected_action = turn.expected_action
    expected_operation = turn.expected_operation
    intent = parsed.get("intent")
    intent = intent if isinstance(intent, dict) else {}
    fallback_used = bool(parsed.get("freeform_fallback_used")) or intent.get("source") == "freeform_fallback"
    intent_action = intent.get("action") if isinstance(intent.get("action"), str) else ""
    intent_operation = intent.get("operation") if isinstance(intent.get("operation"), str) else ""
    intent_action_valid = not intent_action or intent_action == expected_action
    if not intent_action_valid:
        add_error(
            "intent_action_valid",
            f"Model intent action {intent_action!r} does not match expected action {expected_action!r}.",
            code="INTENT_CONTRACT_ERROR",
            safety_gate=True,
        )
    intent_operation_valid = _intent_operation_matches_expected(
        intent_operation=intent_operation,
        expected_action=expected_action,
        expected_operation=expected_operation,
        fallback_used=fallback_used,
    )
    if not intent_operation_valid:
        add_error(
            "intent_operation_valid",
            f"Model intent operation {intent_operation!r} does not match expected operation {expected_operation!r}.",
            code="INTENT_CONTRACT_ERROR",
            safety_gate=True,
        )
    raw_plan_items = parsed.get("plan_items")
    raw_patch_items = parsed.get("patch_items")
    raw_remove_slot_ids = parsed.get("remove_slot_ids")
    raw_add_items = parsed.get("add_items")
    if expected_action == "partial_update":
        previous_plan_items = previous_parsed.get("plan_items") if isinstance(previous_parsed, dict) else None
        if not isinstance(previous_plan_items, list):
            add_error("previous_plan_present", "partial_update requires previous parsed plan_items", code="STATE_LOSS")
            previous_plan_items = []
        patch_items = raw_patch_items if isinstance(raw_patch_items, list) else []
        patch_items = expand_patch_items_for_weekday_request(
            case,
            previous_plan_items,
            patch_items,
            case.turns[turn_id - 1].content,
        )
        plan_items = apply_plan_patch(previous_plan_items, patch_items)
        remove_slot_ids = {
            slot_id
            for slot_id in raw_remove_slot_ids
            if isinstance(raw_remove_slot_ids, list) and isinstance(slot_id, str)
        }
        if remove_slot_ids:
            plan_items = [item for item in plan_items if item.get("slot_id") not in remove_slot_ids]
        add_items = raw_add_items if isinstance(raw_add_items, list) else []
        if add_items:
            plan_items.extend(add_items)
    else:
        patch_items = []
        remove_slot_ids = set()
        add_items = []
        plan_items = raw_plan_items
    required_fields_present = (
        parsed.get("action") == expected_action
        and isinstance(plan_items, list)
    )
    if not required_fields_present:
        add_error("required_fields_present", "Parsed v11 output must contain action and plan_items", code="INTENT_CONTRACT_ERROR")

    confirmation_valid = parsed.get("requires_confirmation") is True
    if not confirmation_valid:
        add_error("requires_confirmation_valid", "requires_confirmation must be true", code="APPROVAL_GUARD_VIOLATION", safety_gate=True)

    available_slots = build_allowed_slots(case)
    slots_by_id = {slot["slot_id"]: slot for slot in available_slots}
    selected_milestones: list[dict[str, Any]] = []
    slot_ids_seen: set[str] = set()
    source_items = patch_items if expected_action == "partial_update" else plan_items
    partial_update_scope_valid = True
    if expected_action == "partial_update":
        if single_patch_target_requested(case.turns[turn_id - 1].content) and len(patch_items) > 1:
            partial_update_scope_valid = False
            add_error(
                "partial_update_scope_valid",
                "Single-target partial_update requests must change at most one slot.",
                code="INTENT_CONTRACT_ERROR",
                safety_gate=True,
            )
    plan_schema_valid = isinstance(source_items, list) and all(isinstance(item, dict) for item in source_items)
    plan_slot_valid = True
    if not plan_schema_valid:
        add_error("plan_schema_valid", "plan_items/patch_items must be a list of objects", code="PAYLOAD_SCHEMA_ERROR")
        source_items = []

    valid_patch_slot_ids = {item.get("slot_id") for item in previous_parsed.get("plan_items", [])} if isinstance(previous_parsed, dict) else set()
    for item in source_items or []:
        slot_id = item.get("slot_id")
        task = item.get("task")
        if not isinstance(slot_id, str) or slot_id not in slots_by_id:
            plan_slot_valid = False
            add_error("plan_slot_valid", f"Unknown slot_id: {slot_id!r}", code="TARGET_NOT_FOUND")
            continue
        if expected_action == "partial_update" and slot_id not in valid_patch_slot_ids:
            plan_slot_valid = False
            add_error("patch_slot_valid", f"PATCH slot_id was not present in previous PLAN: {slot_id}", code="TARGET_NOT_FOUND", safety_gate=True)
            continue
        if slot_id in slot_ids_seen:
            plan_slot_valid = False
            add_error("plan_slot_valid", f"Duplicate slot_id: {slot_id}", code="PAYLOAD_SCHEMA_ERROR")
            continue
        slot_ids_seen.add(slot_id)
        if not isinstance(task, str) or not task.strip():
            plan_slot_valid = False
            add_error("plan_task_valid", f"Task must be a non-empty string for {slot_id}", code="PAYLOAD_SCHEMA_ERROR")
            continue
        if task.strip().startswith("[") or re.search(r"\d{1,2}:\d{2}", task):
            plan_slot_valid = False
            add_error("plan_task_valid", f"Task must not include weekday/time prefix for {slot_id}", code="TIME_PREFIX_MISMATCH")
            continue
        slot = slots_by_id[slot_id]
        mentioned_weekdays = mentioned_korean_weekdays(task)
        if mentioned_weekdays and slot["day_of_week"] not in mentioned_weekdays:
            plan_slot_valid = False
            add_error("plan_task_valid", f"Task weekday text does not match slot weekday for {slot_id}", code="DATE_WEEKDAY_MISMATCH")
            continue
        if "오전" in task or "오후" in task:
            plan_slot_valid = False
            add_error("plan_task_valid", f"Task must not include time-of-day text for {slot_id}", code="TIME_PREFIX_MISMATCH")
            continue
        if contains_disallowed_english_task_text(task):
            plan_slot_valid = False
            add_error("plan_task_valid", f"Task must be written in Korean for {slot_id}", code="INTENT_CONTRACT_ERROR")
            continue

    slot_ids_seen = set()
    for item in plan_items or []:
        slot_id = item.get("slot_id")
        task = item.get("task")
        if not isinstance(slot_id, str) or slot_id not in slots_by_id:
            continue
        if slot_id in slot_ids_seen:
            continue
        slot_ids_seen.add(slot_id)
        if not isinstance(task, str) or not task.strip():
            continue
        if (
            task.strip().startswith("[")
            or re.search(r"\d{1,2}:\d{2}", task)
            or "오전" in task
            or "오후" in task
            or contains_disallowed_english_task_text(task)
        ):
            continue
        mentioned_weekdays = mentioned_korean_weekdays(task)
        slot = slots_by_id[slot_id]
        if mentioned_weekdays and slot["day_of_week"] not in mentioned_weekdays:
            continue
        selected_milestones.append({"slot_id": slot_id, "task": task.strip()})

    min_items = case.expected.constraints.min_milestones if expected_action == "create" else 1
    max_items = case.expected.constraints.max_milestones
    milestone_count_valid = min_items <= len(selected_milestones) <= max_items
    if not milestone_count_valid:
        add_error("milestone_count_valid", "Final PLAN item count is outside the expected min/max range", code="PAYLOAD_SCHEMA_ERROR")

    subset_scope_result = _validate_create_subset_scope(case, turn_id, selected_milestones, slots_by_id)
    create_subset_scope_valid = subset_scope_result["is_valid"]
    if not create_subset_scope_valid:
        add_error(
            "create_subset_scope_valid",
            subset_scope_result["message"],
            code="CREATE_SUBSET_SCOPE_MISMATCH",
            safety_gate=True,
        )

    time_difficulty_result = _validate_time_difficulty_alignment(case, turn_id, selected_milestones, slots_by_id)
    schedule_progression_valid = time_difficulty_result["is_valid"]
    if not schedule_progression_valid:
        add_error(
            "schedule_progression_valid",
            time_difficulty_result["message"],
            code="TIME_DIFFICULTY_MISMATCH",
        )

    db_operation = _db_operation_for_turn(
        expected_action=expected_action,
        patch_items=patch_items,
        add_items=add_items,
        remove_slot_ids=sorted(remove_slot_ids),
    )
    rule_based_db_payload = build_schedule_db_payload(
        case,
        selected_milestones,
        slots_by_id,
        operation=db_operation,
        patch_items=patch_items,
        add_items=add_items,
        remove_slot_ids=sorted(remove_slot_ids),
    )
    milestone_payloads = rule_based_db_payload["milestones"]
    effective_parsed = {
        **parsed,
        "plan_items": plan_items,
        "patch_items": patch_items,
        "remove_slot_ids": sorted(remove_slot_ids),
        "add_items": add_items,
        "db_payload": rule_based_db_payload,
        "rule_based_db_payload": rule_based_db_payload,
    }

    availability_result = _validate_multiturn_availability_alignment(case, milestone_payloads)
    availability_alignment = availability_result["is_valid"]
    weekday_date_alignment = availability_result["weekday_date_alignment"]
    if not availability_alignment:
        for message in availability_result["errors"]:
            add_error("availability_alignment", message, code="AVAILABILITY_VIOLATION", safety_gate=True)
    if availability_alignment and not weekday_date_alignment:
        add_error("weekday_date_alignment", "Milestone title weekday does not match scheduled_date weekday", code="DATE_WEEKDAY_MISMATCH", safety_gate=True)
    if availability_result["warnings"]:
        warnings.extend(availability_result["warnings"])

    latest_allowed = case.expected.constraints.latest_allowed_date
    deadline_compliance = all(
        isinstance(milestone.get("scheduled_date"), str)
        and milestone["scheduled_date"] <= latest_allowed
        for milestone in milestone_payloads
    )
    if not deadline_compliance:
        add_error("deadline_compliance", "All generated scheduled_date values must be before the case deadline", code="DEADLINE_VIOLATION", safety_gate=True)

    previous_plan_slot_ids = set(_plan_slot_ids(previous_parsed))
    current_plan_slot_ids = {
        item.get("slot_id")
        for item in plan_items or []
        if isinstance(item, dict) and isinstance(item.get("slot_id"), str)
    }

    effect = case.expected.effect

    actual_added_count = len(current_plan_slot_ids - previous_plan_slot_ids)
    actual_removed_count = len(previous_plan_slot_ids - current_plan_slot_ids)

    explicit_add_count = len(add_items) if isinstance(add_items, list) else 0
    explicit_remove_count = len(remove_slot_ids)
    explicit_patch_count = len(patch_items) if isinstance(patch_items, list) else 0
    add_preserve_scope_result = _validate_add_preserve_scope(intent, add_items, slots_by_id)
    add_preserve_scope_valid = add_preserve_scope_result["is_valid"]
    if expected_action == "partial_update" and expected_operation == "add" and not add_preserve_scope_valid:
        add_error(
            "add_preserve_scope_valid",
            add_preserve_scope_result["message"],
            code="PRESERVE_SCOPE_VIOLATION",
            safety_gate=True,
        )
    model_safety_check = intent.get("mutation_safety_check")
    model_safety_check = model_safety_check if isinstance(model_safety_check, str) else ""
    actual_safety_check = _actual_mutation_safety_check(
        db_operation=db_operation,
        explicit_add_count=explicit_add_count,
        explicit_remove_count=explicit_remove_count,
        explicit_patch_count=explicit_patch_count,
        requires_clarification=bool(intent.get("requires_clarification")),
    )
    self_check_matches = not model_safety_check or model_safety_check == actual_safety_check

    operation_effect_valid = True

    if expected_action == "partial_update" and expected_operation == "add":
        if explicit_add_count <= 0 or actual_added_count <= 0:
            operation_effect_valid = False
            add_error(
                "operation_effect_valid",
                "Expected add operation, but no new schedule item was added.",
                code="PARTIAL_UPDATE_EFFECT_MISMATCH",
                safety_gate=True,
            )

    if expected_action == "partial_update" and expected_operation == "remove":
        if explicit_remove_count <= 0 or actual_removed_count <= 0:
            operation_effect_valid = False
            add_error(
                "operation_effect_valid",
                "Expected remove operation, but no new schedule item was removed.",
                code="PARTIAL_UPDATE_EFFECT_MISMATCH",
                safety_gate=True,
            )

    if expected_action == "partial_update" and (
        expected_operation == "none" or effect.expected_no_op or effect.expected_clarification
    ):
        mutated = explicit_patch_count > 0 or explicit_add_count > 0 or explicit_remove_count > 0
        plan_changed = current_plan_slot_ids != previous_plan_slot_ids

        if mutated or plan_changed:
            operation_effect_valid = False
            add_error(
                "operation_effect_valid",
                "Expected no-op/clarification, but the schedule was changed.",
                code="UNEXPECTED_MUTATION",
                safety_gate=True,
            )

    previous_titles = set(_milestone_titles(previous_parsed))
    current_titles = set(_milestone_titles(effective_parsed))
    state_regression_count = (
        len(previous_plan_slot_ids - current_plan_slot_ids)
        if previous_plan_slot_ids
        else len(previous_titles - current_titles)
        if previous_titles
        else 0
    )
    completed_existing_titles = [
        milestone.title for milestone in case.input.existing_schedule if milestone.is_completed
    ]
    completed_milestones_preserved = all(
        any(title in current_title for current_title in current_titles)
        for title in completed_existing_titles
    )
    if completed_existing_titles and not completed_milestones_preserved:
        warnings.append("Completed existing milestones are outside the v8 PLAN output.")

    db_payload_schema_valid = set(rule_based_db_payload["goal"]) == set(GOAL_DB_FIELDS) and all(
        set(item) == set(MILESTONE_DB_FIELDS) for item in milestone_payloads
    )
    if not db_payload_schema_valid:
        add_error("db_payload_schema_valid", "DB payload contains missing or extra fields.", code="PAYLOAD_SCHEMA_ERROR")
    safety_gate_failures = [item for item in failed_checks if item.get("safety_gate") is True]
    local_flags = [
        required_fields_present,
        plan_schema_valid,
        plan_slot_valid,
        db_payload_schema_valid,
        confirmation_valid,
        deadline_compliance,
        milestone_count_valid,
        availability_alignment,
        weekday_date_alignment,
        partial_update_scope_valid,
        operation_effect_valid,
        create_subset_scope_valid,
        intent_action_valid,
        intent_operation_valid,
        add_preserve_scope_valid,
        schedule_progression_valid,
    ]
    return {
        "errors": errors,
        "warnings": warnings,
        "local_score": round(sum(1 for flag in local_flags if flag) / len(local_flags), 3),
        "effective_parsed_json": effective_parsed,
        "rule_based_db_payload": rule_based_db_payload,
        "deterministic_validation": {
            "is_valid": len(errors) == 0,
            "failed_checks": failed_checks,
            "failed_check_names": sorted({item["check"] for item in failed_checks}),
            "failure_codes": sorted({item["failure_code"] for item in failed_checks}),
        },
        "failure_taxonomy": failed_checks,
        "safety_gate": {
            "passed": len(safety_gate_failures) == 0,
            "violations": safety_gate_failures,
            "violation_count": len(safety_gate_failures),
        },
        "contract": {
            "required_fields_present": required_fields_present,
            "db_payload_schema_valid": db_payload_schema_valid,
            "requires_confirmation_valid": confirmation_valid,
            "plan_schema_valid": plan_schema_valid,
            "plan_slot_valid": plan_slot_valid,
            "patch_applied": expected_action == "partial_update",
            "partial_update_scope_valid": partial_update_scope_valid,
            "operation_effect_valid": operation_effect_valid,
            "create_subset_scope_valid": create_subset_scope_valid,
            "intent_action_valid": intent_action_valid,
            "intent_operation_valid": intent_operation_valid,
            "fallback_used": fallback_used,
            "add_preserve_scope_valid": add_preserve_scope_valid,
            "schedule_progression_valid": schedule_progression_valid,
        },
        "state": {
            "previous_context_used": previous_parsed is not None,
            "unmentioned_milestones_preserved": state_regression_count == 0,
            "completed_milestones_preserved": completed_milestones_preserved,
            "partial_update_scope_valid": partial_update_scope_valid,
            "state_regression_count": state_regression_count,
            "operation_effect": {
                "db_operation": db_operation,
                "expected_operation": expected_operation,
                "explicit_add_count": explicit_add_count,
                "explicit_remove_count": explicit_remove_count,
                "explicit_patch_count": explicit_patch_count,
                "actual_added_count": actual_added_count,
                "actual_removed_count": actual_removed_count,
            },
            "mutation_safety_check": {
                "model": model_safety_check,
                "actual": actual_safety_check,
                "matches": self_check_matches,
            },
            "create_subset_scope": subset_scope_result,
            "add_preserve_scope": add_preserve_scope_result,
            "fallback": {
                "used": fallback_used,
                "source": intent.get("source") if isinstance(intent.get("source"), str) else "",
            },
        },
        "schedule_quality": {
            "availability_alignment": availability_alignment,
            "weekday_date_alignment": weekday_date_alignment,
            "deadline_compliance": deadline_compliance,
            "milestone_count_valid": milestone_count_valid,
            "schedule_progression_valid": schedule_progression_valid,
            "explanation_alignment": None,
            "create_subset_scope_valid": create_subset_scope_valid,
            "time_difficulty_alignment": time_difficulty_result,
        },
    }


def _milestone_titles(parsed: dict[str, Any] | None) -> list[str]:
    if not isinstance(parsed, dict):
        return []
    db_payload = parsed.get("db_payload")
    if not isinstance(db_payload, dict):
        return []
    milestones = db_payload.get("milestones")
    if not isinstance(milestones, list):
        return []
    return [str(item["title"]) for item in milestones if isinstance(item, dict) and isinstance(item.get("title"), str)]


def _plan_slot_ids(parsed: dict[str, Any] | None) -> list[str]:
    if not isinstance(parsed, dict):
        return []
    plan_items = parsed.get("plan_items")
    if not isinstance(plan_items, list):
        return []
    return [
        str(item["slot_id"])
        for item in plan_items
        if isinstance(item, dict) and isinstance(item.get("slot_id"), str)
    ]


def _db_operation_for_turn(
    *,
    expected_action: str,
    patch_items: list[Any],
    add_items: list[Any],
    remove_slot_ids: list[str],
) -> str:
    if expected_action == "create":
        return "create"
    operations = []
    if add_items:
        operations.append("add")
    if remove_slot_ids:
        operations.append("remove")
    if patch_items:
        operations.append("rename")
    if not operations:
        return "none"
    return operations[0] if len(operations) == 1 else "partial_update"


def _intent_operation_matches_expected(
    *,
    intent_operation: str,
    expected_action: str,
    expected_operation: str | None,
    fallback_used: bool,
) -> bool:
    if fallback_used or not intent_operation:
        return True
    if expected_action == "create":
        return intent_operation == "none"
    if expected_operation is None:
        return True
    return intent_operation == expected_operation


def _validate_add_preserve_scope(
    intent: dict[str, Any],
    add_items: list[Any],
    slots_by_id: dict[str, dict[str, str]],
) -> dict[str, Any]:
    selector = intent.get("preserve_selector")
    if not isinstance(selector, dict) or selector.get("type") != "weekday" or not add_items:
        return {"is_valid": True, "message": "", "expected_weekdays": [], "actual_weekdays": []}
    expected_weekdays = _weekday_values_from_selector(selector)
    if not expected_weekdays:
        return {"is_valid": True, "message": "", "expected_weekdays": [], "actual_weekdays": []}
    actual_weekdays = {
        slots_by_id[item["slot_id"]]["day_of_week"]
        for item in add_items
        if isinstance(item, dict)
        and isinstance(item.get("slot_id"), str)
        and item["slot_id"] in slots_by_id
    }
    if actual_weekdays <= expected_weekdays:
        return {
            "is_valid": True,
            "message": "",
            "expected_weekdays": sorted(expected_weekdays),
            "actual_weekdays": sorted(actual_weekdays),
        }
    return {
        "is_valid": False,
        "message": "Add selected slots violate the preserved weekday scope.",
        "expected_weekdays": sorted(expected_weekdays),
        "actual_weekdays": sorted(actual_weekdays),
    }


def _weekday_values_from_selector(selector: dict[str, Any]) -> set[str]:
    values = selector.get("values")
    raw_values = values if isinstance(values, list) else [selector.get("value")]
    text = " ".join(str(value) for value in raw_values if value is not None)
    weekdays = _requested_allowed_days(text)
    explicit = {
        value
        for value in raw_values
        if isinstance(value, str)
        for value in [value.strip().lower()]
        if value in {
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        }
    }
    return weekdays | explicit


def _validate_time_difficulty_alignment(
    case: MileDayMultiTurnCase,
    turn_id: int,
    selected_milestones: list[dict[str, Any]],
    slots_by_id: dict[str, dict[str, str]],
) -> dict[str, Any]:
    turn = case.turns[turn_id - 1]
    if turn.expected_action != "create":
        return {"is_valid": True, "message": "", "required": False}
    if not _requests_short_long_alignment(turn.content, case.metadata):
        return {"is_valid": True, "message": "", "required": False}
    selected_slot_ids = [
        item["slot_id"]
        for item in selected_milestones
        if isinstance(item.get("slot_id"), str) and item["slot_id"] in slots_by_id
    ]
    if len(selected_slot_ids) < 2:
        return {
            "is_valid": False,
            "message": "Short/long time planning requires at least two selected slots.",
            "required": True,
            "selected_slot_ids": selected_slot_ids,
        }
    available_durations = {
        slot_id: _slot_duration_minutes(slot["time_range"])
        for slot_id, slot in slots_by_id.items()
    }
    selected_durations = [available_durations[slot_id] for slot_id in selected_slot_ids]
    min_available = min(available_durations.values())
    max_available = max(available_durations.values())
    includes_short = min_available in selected_durations
    includes_long = max_available in selected_durations
    if includes_short and includes_long:
        return {
            "is_valid": True,
            "message": "",
            "required": True,
            "selected_slot_ids": selected_slot_ids,
            "selected_duration_minutes": selected_durations,
        }
    return {
        "is_valid": False,
        "message": "Explicit short/long request must include both shortest and longest available slot durations.",
        "required": True,
        "selected_slot_ids": selected_slot_ids,
        "selected_duration_minutes": selected_durations,
        "min_available_duration": min_available,
        "max_available_duration": max_available,
    }


def _requests_short_long_alignment(text: str, metadata: dict[str, Any]) -> bool:
    tags = metadata.get("tags")
    if isinstance(tags, list) and {"short_slot", "long_slot"} <= {str(tag) for tag in tags}:
        return True
    return ("짧" in text and "긴" in text) or ("short" in text.lower() and "long" in text.lower())


def _slot_duration_minutes(time_range: str) -> int:
    start, end = time_range.split("-", maxsplit=1)
    start_hours, start_minutes = [int(part) for part in start.split(":", maxsplit=1)]
    end_hours, end_minutes = [int(part) for part in end.split(":", maxsplit=1)]
    return (end_hours * 60 + end_minutes) - (start_hours * 60 + start_minutes)


def _actual_mutation_safety_check(
    *,
    db_operation: str,
    explicit_add_count: int,
    explicit_remove_count: int,
    explicit_patch_count: int,
    requires_clarification: bool,
) -> str:
    if requires_clarification:
        return "ambiguous_request"
    if db_operation == "create":
        return "create_scope_checked"
    if db_operation == "none":
        return "no_target_matched"
    if db_operation in {"remove", "rename"}:
        target_count = explicit_remove_count if db_operation == "remove" else explicit_patch_count
        if target_count == 1:
            return "single_target_matched"
        if target_count > 1:
            return "multiple_targets_matched"
        return "no_target_matched"
    if db_operation == "add":
        return "single_target_matched" if explicit_add_count == 1 else "multiple_targets_matched"
    return "multiple_targets_matched"


def _validate_create_subset_scope(
    case: MileDayMultiTurnCase,
    turn_id: int,
    selected_milestones: list[dict[str, Any]],
    slots_by_id: dict[str, dict[str, str]],
) -> dict[str, Any]:
    turn = case.turns[turn_id - 1]
    if turn.expected_action != "create":
        return {"is_valid": True, "message": "", "expected_day_count": None, "actual_day_count": None}

    request = turn.content
    selected_days = {
        slots_by_id[item["slot_id"]]["day_of_week"]
        for item in selected_milestones
        if isinstance(item.get("slot_id"), str) and item["slot_id"] in slots_by_id
    }
    expected_day_count = _requested_subset_day_count(request)
    allowed_days = _requested_allowed_days(request)

    if allowed_days and not selected_days <= allowed_days:
        return {
            "is_valid": False,
            "message": "Selected slots include weekdays outside the requested subset.",
            "expected_day_count": expected_day_count,
            "actual_day_count": len(selected_days),
            "allowed_days": sorted(allowed_days),
            "selected_days": sorted(selected_days),
        }
    if expected_day_count is not None and len(selected_days) != expected_day_count:
        return {
            "is_valid": False,
            "message": "Selected slot weekdays do not match the requested subset day count.",
            "expected_day_count": expected_day_count,
            "actual_day_count": len(selected_days),
            "allowed_days": sorted(allowed_days),
            "selected_days": sorted(selected_days),
        }
    return {
        "is_valid": True,
        "message": "",
        "expected_day_count": expected_day_count,
        "actual_day_count": len(selected_days),
        "allowed_days": sorted(allowed_days),
        "selected_days": sorted(selected_days),
    }


def _requested_subset_day_count(text: str) -> int | None:
    if "주말 중 하루" in text or "주말 중 1일" in text or "주말 중 하루만" in text:
        return 1
    if not any(keyword in text for keyword in ("골라", "선택", "중", "그중")):
        return None
    for label, count in {"1": 1, "한": 1, "하루": 1, "2": 2, "두": 2, "3": 3, "세": 3}.items():
        if re.search(rf"{label}\s*일\s*만", text):
            return count
    return None


def _requested_allowed_days(text: str) -> set[str]:
    allowed_days: set[str] = set()
    if "주말" in text:
        allowed_days.update({"saturday", "sunday"})
    labels = {
        "월": "monday",
        "화": "tuesday",
        "수": "wednesday",
        "목": "thursday",
        "금": "friday",
        "토": "saturday",
        "일": "sunday",
    }
    for compact, days in {
        "월수금": {"monday", "wednesday", "friday"},
        "화목토": {"tuesday", "thursday", "saturday"},
        "토일": {"saturday", "sunday"},
    }.items():
        if compact in text:
            allowed_days.update(days)
    for label, day in labels.items():
        if f"{label}요일" in text:
            allowed_days.add(day)
    return allowed_days


def _validate_multiturn_availability_alignment(
    case: MileDayMultiTurnCase,
    milestones: list[dict[str, Any]],
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if not milestones:
        return {
            "is_valid": False,
            "weekday_date_alignment": False,
            "errors": ["At least one milestone is required for availability validation."],
            "warnings": warnings,
        }
    windows = {
        (window.day_of_week, window.start_time, window.end_time)
        for window in case.input.availability
    }
    title_prefix_valid = True
    weekday_date_alignment = True
    for milestone in milestones:
        title = milestone.get("title")
        scheduled_date = milestone.get("scheduled_date")
        if not isinstance(title, str):
            title_prefix_valid = False
            errors.append("Milestone title must be a string.")
            continue
        parsed_title = parse_canonical_milestone_title(title)
        if parsed_title is None:
            title_prefix_valid = False
            errors.append(f"Milestone title must start with a bracketed weekday/time range: {title}")
            continue
        if (parsed_title.day_of_week, parsed_title.start_time, parsed_title.end_time) not in windows:
            title_prefix_valid = False
            errors.append(f"Milestone title uses unavailable weekday/time: {title}")
        if isinstance(scheduled_date, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", scheduled_date):
            actual_day = _date_day_of_week(scheduled_date)
            if actual_day is not None and actual_day != parsed_title.day_of_week:
                weekday_date_alignment = False
                errors.append(
                    f"Milestone title weekday does not match scheduled_date: {title} / {scheduled_date}"
                )
        else:
            weekday_date_alignment = False
            warnings.append(f"Cannot verify weekday/date alignment for invalid date: {scheduled_date}")
    return {
        "is_valid": title_prefix_valid and weekday_date_alignment,
        "weekday_date_alignment": weekday_date_alignment,
        "errors": errors,
        "warnings": warnings,
    }


def _failure_code_for_check(check: str) -> str:
    return {
        "previous_plan_present": "STATE_LOSS",
        "required_fields_present": "INTENT_CONTRACT_ERROR",
        "requires_confirmation_valid": "APPROVAL_GUARD_VIOLATION",
        "plan_schema_valid": "PAYLOAD_SCHEMA_ERROR",
        "plan_slot_valid": "TARGET_NOT_FOUND",
        "patch_slot_valid": "TARGET_NOT_FOUND",
        "plan_task_valid": "INTENT_CONTRACT_ERROR",
        "milestone_count_valid": "PAYLOAD_SCHEMA_ERROR",
        "availability_alignment": "AVAILABILITY_VIOLATION",
        "weekday_date_alignment": "DATE_WEEKDAY_MISMATCH",
        "deadline_compliance": "DEADLINE_VIOLATION",
        "db_payload_schema_valid": "PAYLOAD_SCHEMA_ERROR",
        "create_subset_scope_valid": "CREATE_SUBSET_SCOPE_MISMATCH",
        "intent_action_valid": "INTENT_CONTRACT_ERROR",
        "intent_operation_valid": "INTENT_CONTRACT_ERROR",
        "add_preserve_scope_valid": "PRESERVE_SCOPE_VIOLATION",
        "schedule_progression_valid": "TIME_DIFFICULTY_MISMATCH",
    }.get(check, "JUDGE_REJECTION")


def _parse_milestone_title_time_prefix(title: str) -> tuple[str, str, str] | None:
    match = re.match(r"^\[(?P<weekday>[^\s\]]+)\s+(?P<start>\d{2}:\d{2})-(?P<end>\d{2}:\d{2})\]", title)
    if match is None:
        return None
    weekday = match.group("weekday")
    day_of_week = {
        "월": "monday",
        "월요일": "monday",
        "화": "tuesday",
        "화요일": "tuesday",
        "수": "wednesday",
        "수요일": "wednesday",
        "목": "thursday",
        "목요일": "thursday",
        "금": "friday",
        "금요일": "friday",
        "토": "saturday",
        "토요일": "saturday",
        "일": "sunday",
        "일요일": "sunday",
    }.get(weekday)
    if day_of_week is None:
        return None
    return day_of_week, match.group("start"), match.group("end")


def _date_day_of_week(raw_date: str) -> str | None:
    try:
        weekday_index = date.fromisoformat(raw_date).weekday()
    except ValueError:
        return None
    return [
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    ][weekday_index]

def validate_api_multiturn_plan_output(
    case: MileDayMultiTurnCase,
    turn_id: int,
    parsed: dict[str, Any],
    previous_parsed: dict[str, Any] | None,
) -> dict[str, Any]:
    return _validate_mileday_multiturn_plan_output(case, turn_id, parsed, previous_parsed)
