from __future__ import annotations

from collections import Counter
from datetime import date
from typing import Any

from schemas.ai_schedule_schemas import AiScheduleDraftRequest
from services.ai_schedule_parser import ParsedMilestone, ParsedPlanningPreference, ParsedScheduleDraft


WEEKDAYS = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)


def validate_ai_schedule_draft(
    request: AiScheduleDraftRequest,
    draft: ParsedScheduleDraft,
) -> dict[str, Any]:
    failures: list[str] = []
    warnings: list[str] = []
    goal = draft["goal"]
    milestones = draft["milestones"]
    availability_dates = {item.date.isoformat() for item in request.availability}

    deadline = _parse_date(goal["deadline"])
    if not goal["title"]:
        failures.append("EMPTY_GOAL_TITLE")
    if deadline is None:
        failures.append("INVALID_DEADLINE")
    elif deadline <= request.today:
        failures.append("DEADLINE_NOT_FUTURE")

    if not milestones:
        failures.append("NO_MILESTONES")
    if len(milestones) > 6:
        warnings.append("MILESTONE_COUNT_HIGH")

    valid_dates = _validate_milestones(milestones, deadline, availability_dates, failures)
    _validate_preference(valid_dates, draft["planning_preference"], failures, warnings)
    return {
        "is_valid": not failures,
        "failure_codes": sorted(set(failures)),
        "warnings": sorted(set(warnings)),
    }


def _validate_milestones(
    milestones: list[ParsedMilestone],
    deadline: date | None,
    availability_dates: set[str],
    failures: list[str],
) -> list[date]:
    seen = Counter()
    valid_dates: list[date] = []
    for item in milestones:
        title = item["title"]
        scheduled_date_text = item["scheduled_date"]
        scheduled_date = _parse_date(scheduled_date_text)
        if not title:
            failures.append("EMPTY_MILESTONE_TITLE")
        if scheduled_date is None:
            failures.append("INVALID_MILESTONE_DATE")
            continue
        valid_dates.append(scheduled_date)
        if deadline is not None and scheduled_date > deadline:
            failures.append("MILESTONE_AFTER_DEADLINE")
        if scheduled_date_text not in availability_dates:
            failures.append("MILESTONE_OUTSIDE_AVAILABILITY")
        seen[(title, scheduled_date_text)] += 1
    if any(count > 1 for count in seen.values()):
        failures.append("DUPLICATE_MILESTONE")
    return valid_dates


def _validate_preference(
    valid_dates: list[date],
    preference: ParsedPlanningPreference,
    failures: list[str],
    warnings: list[str],
) -> None:
    if preference["intensity"] not in {"relaxed", "balanced", "intensive"}:
        failures.append("INVALID_INTENSITY")
    preferred_days = preference["preferred_days"]
    if any(day not in WEEKDAYS for day in preferred_days):
        failures.append("INVALID_PREFERRED_DAYS")
    if preferred_days and valid_dates:
        if not any(WEEKDAYS[item.weekday()] in preferred_days for item in valid_dates):
            warnings.append("PREFERRED_DAYS_NOT_REFLECTED")


def _parse_date(value: str) -> date | None:
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None
