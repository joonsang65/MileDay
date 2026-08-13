from __future__ import annotations

from collections import Counter
from datetime import date
from typing import Any

from harness.mileday.dataset import AiScheduleDraftCase


WEEKDAYS = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)


def validate_ai_schedule_draft(case: AiScheduleDraftCase, draft: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    warnings: list[str] = []
    goal = draft.get("goal") if isinstance(draft.get("goal"), dict) else {}
    milestones = draft.get("milestones") if isinstance(draft.get("milestones"), list) else []
    preference = (
        draft.get("planning_preference")
        if isinstance(draft.get("planning_preference"), dict)
        else {}
    )

    today = date.fromisoformat(case.today)
    expected_deadline_latest = date.fromisoformat(case.expected.deadline_latest)
    availability_dates = {item.date for item in case.availability}

    title = goal.get("title")
    deadline_text = goal.get("deadline")
    deadline = _parse_date(deadline_text)
    if not isinstance(title, str) or not title.strip():
        failures.append("EMPTY_GOAL_TITLE")
    if deadline is None:
        failures.append("INVALID_DEADLINE")
    else:
        if deadline <= today:
            failures.append("DEADLINE_NOT_FUTURE")
        if deadline > expected_deadline_latest:
            failures.append("DEADLINE_AFTER_EXPECTED")

    if not milestones:
        failures.append("NO_MILESTONES")
    _validate_milestone_count(case, milestones, failures)
    _validate_milestones(milestones, deadline, availability_dates, failures)
    _validate_preference(case, milestones, preference, failures, warnings)

    return {
        "is_valid": not failures,
        "failure_codes": sorted(set(failures)),
        "warnings": sorted(set(warnings)),
        "checks": {
            "schema_valid": _has_required_shape(draft),
            "goal_title_valid": "EMPTY_GOAL_TITLE" not in failures,
            "deadline_valid": "INVALID_DEADLINE" not in failures
            and "DEADLINE_NOT_FUTURE" not in failures
            and "DEADLINE_AFTER_EXPECTED" not in failures,
            "milestone_count_valid": "MILESTONE_COUNT_TOO_LOW" not in failures
            and "MILESTONE_COUNT_TOO_HIGH" not in failures
            and "NO_MILESTONES" not in failures,
            "milestone_dates_valid": "INVALID_MILESTONE_DATE" not in failures
            and "MILESTONE_AFTER_DEADLINE" not in failures
            and "MILESTONE_OUTSIDE_AVAILABILITY" not in failures,
            "duplicate_valid": "DUPLICATE_MILESTONE" not in failures,
            "preference_valid": "INTENSITY_MISMATCH" not in failures
            and "PREFERRED_WEEKDAY_MISMATCH" not in failures,
        },
    }


def _validate_milestone_count(
    case: AiScheduleDraftCase,
    milestones: list[Any],
    failures: list[str],
) -> None:
    count = len(milestones)
    minimum = case.expected.milestone_count_min
    maximum = case.expected.milestone_count_max
    if minimum is None:
        minimum = 1 if case.expected.allow_single_milestone else 2
    if maximum is None:
        maximum = 6
    if count < minimum:
        failures.append("MILESTONE_COUNT_TOO_LOW")
    if count > maximum:
        failures.append("MILESTONE_COUNT_TOO_HIGH")


def _validate_milestones(
    milestones: list[Any],
    deadline: date | None,
    availability_dates: set[str],
    failures: list[str],
) -> None:
    seen = Counter()
    for item in milestones:
        if not isinstance(item, dict):
            failures.append("INVALID_MILESTONE_SHAPE")
            continue
        title = item.get("title")
        scheduled_date_text = item.get("scheduled_date")
        if not isinstance(title, str) or not title.strip():
            failures.append("EMPTY_MILESTONE_TITLE")
        scheduled_date = _parse_date(scheduled_date_text)
        if scheduled_date is None:
            failures.append("INVALID_MILESTONE_DATE")
            continue
        if deadline is not None and scheduled_date > deadline:
            failures.append("MILESTONE_AFTER_DEADLINE")
        if scheduled_date_text not in availability_dates:
            failures.append("MILESTONE_OUTSIDE_AVAILABILITY")
        seen[(str(title).strip(), scheduled_date_text)] += 1
    if any(count > 1 for count in seen.values()):
        failures.append("DUPLICATE_MILESTONE")


def _validate_preference(
    case: AiScheduleDraftCase,
    milestones: list[Any],
    preference: dict[str, Any],
    failures: list[str],
    warnings: list[str],
) -> None:
    expected_intensity = case.expected.intensity
    if expected_intensity is not None and preference.get("intensity") != expected_intensity:
        failures.append("INTENSITY_MISMATCH")

    preferred_weekdays = set(case.expected.preferred_weekdays)
    if not preferred_weekdays:
        return
    valid_dates = [
        parsed
        for item in milestones
        if isinstance(item, dict)
        for parsed in [_parse_date(item.get("scheduled_date"))]
        if parsed is not None
    ]
    if not valid_dates:
        return
    matched = sum(1 for item in valid_dates if WEEKDAYS[item.weekday()] in preferred_weekdays)
    if matched / len(valid_dates) < 0.5:
        failures.append("PREFERRED_WEEKDAY_MISMATCH")
    output_days = preference.get("preferred_days")
    if isinstance(output_days, list) and preferred_weekdays.isdisjoint(str(day) for day in output_days):
        warnings.append("PREFERRED_DAYS_NOT_REFLECTED_IN_METADATA")


def _has_required_shape(draft: dict[str, Any]) -> bool:
    goal = draft.get("goal")
    milestones = draft.get("milestones")
    preference = draft.get("planning_preference")
    return (
        isinstance(goal, dict)
        and isinstance(goal.get("title"), str)
        and isinstance(goal.get("deadline"), str)
        and isinstance(milestones, list)
        and isinstance(preference, dict)
        and isinstance(preference.get("intensity"), str)
        and isinstance(preference.get("preferred_days"), list)
    )


def _parse_date(value: object) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None
