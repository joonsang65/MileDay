from __future__ import annotations

import json
import re
from datetime import date
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from harness.mileday.dataset import MileDayGenerationCase
from harness.schemas import FailureCategory


DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class ScheduleFailureCode(StrEnum):
    INVALID_JSON = "INVALID_JSON"
    INVALID_SHAPE = "INVALID_SHAPE"
    BAD_DATE_FORMAT = "BAD_DATE_FORMAT"
    TOO_FEW_MILESTONES = "TOO_FEW_MILESTONES"
    TOO_MANY_MILESTONES = "TOO_MANY_MILESTONES"
    DEADLINE_VIOLATION = "DEADLINE_VIOLATION"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    RECURRENCE_RULE_VIOLATION = "RECURRENCE_RULE_VIOLATION"


class ScheduleValidationFailure(BaseModel):
    code: ScheduleFailureCode
    message: str
    path: str | None = None


class ScheduleValidationResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    dataset_id: str
    case_id: str
    is_valid: bool
    failures: list[ScheduleValidationFailure] = Field(default_factory=list)
    raw_output: str | None = None
    category: FailureCategory | None = None


def validate_schedule_output(
    case: MileDayGenerationCase,
    parsed_output: Any,
    *,
    raw_output: str | None = None,
) -> ScheduleValidationResult:
    failures: list[ScheduleValidationFailure] = []
    output = _coerce_output(parsed_output, failures)
    milestones = _extract_milestones(output, failures)
    if milestones is not None:
        _validate_required_fields(case, milestones, failures)
        scheduled_dates = _validate_dates(milestones, failures)
        _validate_milestone_count(case, milestones, failures)
        _validate_latest_allowed_date(case, scheduled_dates, failures)
        _validate_recurrence(case, scheduled_dates, failures)

    return ScheduleValidationResult(
        dataset_id=case.dataset_id,
        case_id=case.case_id,
        is_valid=not failures,
        failures=failures,
        raw_output=raw_output,
        category=FailureCategory.PARSER_ERROR if failures else None,
    )


def _coerce_output(
    parsed_output: Any,
    failures: list[ScheduleValidationFailure],
) -> Any:
    if isinstance(parsed_output, str):
        try:
            return json.loads(parsed_output)
        except json.JSONDecodeError as exc:
            failures.append(
                ScheduleValidationFailure(
                    code=ScheduleFailureCode.INVALID_JSON,
                    message=f"Model output is not valid JSON: {exc.msg}",
                )
            )
            return None
    return parsed_output


def _extract_milestones(
    output: Any,
    failures: list[ScheduleValidationFailure],
) -> list[dict[str, Any]] | None:
    if output is None:
        return None
    if not isinstance(output, dict):
        failures.append(
            ScheduleValidationFailure(
                code=ScheduleFailureCode.INVALID_SHAPE,
                message="Schedule output must be a JSON object.",
            )
        )
        return None
    milestones = output.get("milestones")
    if not isinstance(milestones, list) or not all(isinstance(item, dict) for item in milestones):
        failures.append(
            ScheduleValidationFailure(
                code=ScheduleFailureCode.INVALID_SHAPE,
                message="Schedule output must contain milestones as a list of objects.",
                path="milestones",
            )
        )
        return None
    return milestones


def _validate_required_fields(
    case: MileDayGenerationCase,
    milestones: list[dict[str, Any]],
    failures: list[ScheduleValidationFailure],
) -> None:
    for index, milestone in enumerate(milestones):
        for field_name in case.expected.required_fields:
            if field_name not in milestone or _is_blank(milestone[field_name]):
                failures.append(
                    ScheduleValidationFailure(
                        code=ScheduleFailureCode.MISSING_REQUIRED_FIELD,
                        message=f"Milestone {index} is missing required field {field_name!r}.",
                        path=f"milestones[{index}].{field_name}",
                    )
                )


def _validate_dates(
    milestones: list[dict[str, Any]],
    failures: list[ScheduleValidationFailure],
) -> list[date]:
    dates: list[date] = []
    for index, milestone in enumerate(milestones):
        value = milestone.get("scheduled_date")
        if not isinstance(value, str) or not DATE_PATTERN.fullmatch(value.strip()):
            failures.append(
                ScheduleValidationFailure(
                    code=ScheduleFailureCode.BAD_DATE_FORMAT,
                    message=f"Milestone {index} scheduled_date must use YYYY-MM-DD.",
                    path=f"milestones[{index}].scheduled_date",
                )
            )
            continue
        try:
            dates.append(date.fromisoformat(value.strip()))
        except ValueError:
            failures.append(
                ScheduleValidationFailure(
                    code=ScheduleFailureCode.BAD_DATE_FORMAT,
                    message=f"Milestone {index} scheduled_date is not a valid calendar date.",
                    path=f"milestones[{index}].scheduled_date",
                )
            )
    return dates


def _validate_milestone_count(
    case: MileDayGenerationCase,
    milestones: list[dict[str, Any]],
    failures: list[ScheduleValidationFailure],
) -> None:
    count = len(milestones)
    if count < case.expected.min_milestones:
        failures.append(
            ScheduleValidationFailure(
                code=ScheduleFailureCode.TOO_FEW_MILESTONES,
                message=(
                    f"Expected at least {case.expected.min_milestones} milestones, "
                    f"got {count}."
                ),
                path="milestones",
            )
        )
    if count > case.expected.max_milestones:
        failures.append(
            ScheduleValidationFailure(
                code=ScheduleFailureCode.TOO_MANY_MILESTONES,
                message=(
                    f"Expected at most {case.expected.max_milestones} milestones, "
                    f"got {count}."
                ),
                path="milestones",
            )
        )


def _validate_latest_allowed_date(
    case: MileDayGenerationCase,
    scheduled_dates: list[date],
    failures: list[ScheduleValidationFailure],
) -> None:
    latest_allowed = date.fromisoformat(case.expected.latest_allowed_date)
    for index, scheduled_date in enumerate(scheduled_dates):
        if scheduled_date > latest_allowed:
            failures.append(
                ScheduleValidationFailure(
                    code=ScheduleFailureCode.DEADLINE_VIOLATION,
                    message=(
                        f"Milestone {index} scheduled_date exceeds latest_allowed_date "
                        f"{case.expected.latest_allowed_date}."
                    ),
                    path=f"milestones[{index}].scheduled_date",
                )
            )


def _validate_recurrence(
    case: MileDayGenerationCase,
    scheduled_dates: list[date],
    failures: list[ScheduleValidationFailure],
) -> None:
    recurrence = case.input.constraints.get("recurrence")
    if recurrence in (None, "", "none"):
        return
    if recurrence != "weekly":
        failures.append(
            ScheduleValidationFailure(
                code=ScheduleFailureCode.RECURRENCE_RULE_VIOLATION,
                message=f"Unsupported explicit recurrence constraint: {recurrence}",
                path="input.constraints.recurrence",
            )
        )
        return
    sorted_dates = sorted(scheduled_dates)
    if len(sorted_dates) < 2:
        return
    for previous, current in zip(sorted_dates, sorted_dates[1:]):
        if (current - previous).days != 7:
            failures.append(
                ScheduleValidationFailure(
                    code=ScheduleFailureCode.RECURRENCE_RULE_VIOLATION,
                    message="Weekly recurrence requires generated dates to be 7 days apart.",
                    path="milestones[*].scheduled_date",
                )
            )
            return


def _is_blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and value.strip() == "")
