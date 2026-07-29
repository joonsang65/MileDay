from pathlib import Path

from harness.mileday.constraints import (
    ScheduleFailureCode,
    validate_schedule_output,
)
from harness.mileday.dataset import load_mileday_generation_cases
from harness.schemas import FailureCategory


FIXTURE_PATH = Path("tests/fixtures/mileday/synthetic_schedule.jsonl")


def _case():
    return load_mileday_generation_cases(FIXTURE_PATH)[0]


def _valid_output():
    return {
        "milestones": [
            {
                "title": "Prepare certification outline",
                "scheduled_date": "2026-09-01",
                "description": "List exam domains.",
            },
            {
                "title": "Complete practice set",
                "scheduled_date": "2026-09-15",
                "description": "Review weak areas.",
            },
            {
                "title": "Final review",
                "scheduled_date": "2026-09-29",
                "description": "Confirm readiness.",
            },
        ]
    }


def test_valid_schedule_output_passes_and_preserves_raw_output():
    raw_output = '{"milestones":[]}'

    result = validate_schedule_output(_case(), _valid_output(), raw_output=raw_output)

    assert result.is_valid is True
    assert result.failures == []
    assert result.raw_output == raw_output
    assert result.category is None


def test_invalid_json_string_fails_before_shape_validation():
    result = validate_schedule_output(_case(), '{"milestones": [')

    assert result.is_valid is False
    assert result.category == FailureCategory.PARSER_ERROR
    assert result.failures[0].code == ScheduleFailureCode.INVALID_JSON


def test_invalid_parsed_shape_fails():
    result = validate_schedule_output(_case(), ["not", "an", "object"])

    assert result.is_valid is False
    assert result.failures[0].code == ScheduleFailureCode.INVALID_SHAPE


def test_bad_date_format_fails():
    output = _valid_output()
    output["milestones"][0]["scheduled_date"] = "2026/09/01"

    result = validate_schedule_output(_case(), output)

    assert ScheduleFailureCode.BAD_DATE_FORMAT in {failure.code for failure in result.failures}


def test_too_few_milestones_fails():
    output = {"milestones": [_valid_output()["milestones"][0]]}

    result = validate_schedule_output(_case(), output)

    assert ScheduleFailureCode.TOO_FEW_MILESTONES in {failure.code for failure in result.failures}


def test_too_many_milestones_fails():
    output = _valid_output()
    output["milestones"] = output["milestones"] * 3

    result = validate_schedule_output(_case(), output)

    assert ScheduleFailureCode.TOO_MANY_MILESTONES in {failure.code for failure in result.failures}


def test_latest_allowed_date_violation_fails():
    output = _valid_output()
    output["milestones"][2]["scheduled_date"] = "2026-10-01"

    result = validate_schedule_output(_case(), output)

    assert ScheduleFailureCode.DEADLINE_VIOLATION in {failure.code for failure in result.failures}


def test_missing_required_fields_fail():
    output = _valid_output()
    output["milestones"][0].pop("title")

    result = validate_schedule_output(_case(), output)

    assert ScheduleFailureCode.MISSING_REQUIRED_FIELD in {failure.code for failure in result.failures}


def test_explicit_weekly_recurrence_is_checked():
    case = load_mileday_generation_cases(FIXTURE_PATH)[1]
    output = {
        "milestones": [
            {"title": "Plan topic", "scheduled_date": "2026-09-01", "description": "Start."},
            {"title": "Draft project", "scheduled_date": "2026-09-10", "description": "Draft."},
        ]
    }

    result = validate_schedule_output(case, output)

    assert ScheduleFailureCode.RECURRENCE_RULE_VIOLATION in {
        failure.code for failure in result.failures
    }
