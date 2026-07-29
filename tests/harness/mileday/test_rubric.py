from pathlib import Path

from harness.mileday.constraints import validate_schedule_output
from harness.mileday.dataset import load_mileday_generation_cases
from harness.mileday.rubric import (
    RUBRIC_DOCUMENTATION,
    evaluate_semantic_rubric,
)
from harness.schemas import FailureCategory


FIXTURE_PATH = Path("tests/fixtures/mileday/synthetic_schedule.jsonl")


class MockJudge:
    def evaluate(self, case, parsed_output):
        return {"judge_fit": 0.8, "judge_clarity": 1.2}


def _valid_case_and_output():
    case = load_mileday_generation_cases(FIXTURE_PATH)[0]
    output = {
        "milestones": [
            {
                "title": "Certification exam outline",
                "scheduled_date": "2026-09-01",
                "description": "Prepare certification exam domains.",
            },
            {
                "title": "Certification practice",
                "scheduled_date": "2026-09-15",
                "description": "Solve timed practice questions.",
            },
            {
                "title": "Certification final review",
                "scheduled_date": "2026-09-29",
                "description": "Review missed questions.",
            },
        ]
    }
    return case, output


def test_rubric_documentation_is_available():
    assert "goal_alignment" in RUBRIC_DOCUMENTATION
    assert "actionability" in RUBRIC_DOCUMENTATION


def test_valid_schedule_gets_dimension_scores_and_aggregate():
    case, output = _valid_case_and_output()
    validation = validate_schedule_output(case, output, raw_output="raw text")

    result = evaluate_semantic_rubric(case, output, validation)

    assert result.is_valid is True
    assert result.skipped is False
    assert result.aggregate_score is not None
    assert {item.name for item in result.dimension_scores} == {
        "actionability",
        "goal_alignment",
        "schedule_balance",
    }
    assert result.raw_output == "raw text"


def test_invalid_schedule_is_hard_gated():
    case, output = _valid_case_and_output()
    output["milestones"] = []
    validation = validate_schedule_output(case, output, raw_output="bad raw")

    result = evaluate_semantic_rubric(case, output, validation)

    assert result.is_valid is False
    assert result.skipped is True
    assert result.aggregate_score is None
    assert result.raw_output == "bad raw"


def test_missing_required_judge_dependency_degrades_without_fabricated_score():
    case, output = _valid_case_and_output()
    validation = validate_schedule_output(case, output)

    result = evaluate_semantic_rubric(case, output, validation, require_judge=True)

    assert result.skipped is True
    assert result.aggregate_score is None
    assert result.error is not None
    assert result.error.category == FailureCategory.EXTERNAL_DEPENDENCY


def test_mock_judge_scores_are_used_and_clamped():
    case, output = _valid_case_and_output()
    validation = validate_schedule_output(case, output)

    result = evaluate_semantic_rubric(case, output, validation, judge=MockJudge())

    score_by_name = {item.name: item.score for item in result.dimension_scores}
    assert score_by_name["judge_fit"] == 0.8
    assert score_by_name["judge_clarity"] == 1.0
    assert result.aggregate_score is not None
