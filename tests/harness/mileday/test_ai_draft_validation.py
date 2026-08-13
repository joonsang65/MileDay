from harness.mileday.ai_draft_validation import validate_ai_schedule_draft
from harness.mileday.dataset import load_ai_schedule_draft_cases


def _draft(**overrides):
    payload = {
        "goal": {"title": "데이터 분석 과제", "deadline": "2026-09-30"},
        "milestones": [
            {"title": "자료 수집", "scheduled_date": "2026-08-22"},
            {"title": "분석 수행", "scheduled_date": "2026-09-06"},
            {"title": "보고서 정리", "scheduled_date": "2026-09-27"},
        ],
        "planning_preference": {"intensity": "relaxed", "preferred_days": ["saturday", "sunday"]},
    }
    payload.update(overrides)
    return payload


def test_ai_draft_validation_accepts_valid_draft():
    case = load_ai_schedule_draft_cases("tests/fixtures/mileday/ai_schedule_draft.json")[0]

    result = validate_ai_schedule_draft(case, _draft())

    assert result["is_valid"] is True
    assert result["failure_codes"] == []
    assert result["checks"]["milestone_dates_valid"] is True


def test_ai_draft_validation_rejects_availability_and_deadline_errors():
    case = load_ai_schedule_draft_cases("tests/fixtures/mileday/ai_schedule_draft.json")[0]

    result = validate_ai_schedule_draft(
        case,
        _draft(
            goal={"title": "데이터 분석 과제", "deadline": "2026-09-30"},
            milestones=[
                {"title": "자료 수집", "scheduled_date": "2026-09-30"},
                {"title": "보고서 정리", "scheduled_date": "2026-10-01"},
            ],
        ),
    )

    assert result["is_valid"] is False
    assert "MILESTONE_OUTSIDE_AVAILABILITY" in result["failure_codes"]
    assert "MILESTONE_AFTER_DEADLINE" in result["failure_codes"]
    assert "MILESTONE_COUNT_TOO_LOW" in result["failure_codes"]


def test_ai_draft_validation_enforces_requested_count_and_preference():
    case = load_ai_schedule_draft_cases("tests/fixtures/mileday/ai_schedule_draft.json")[6]

    result = validate_ai_schedule_draft(
        case,
        {
            "goal": {"title": "알고리즘 스터디", "deadline": "2026-10-15"},
            "milestones": [
                {"title": "기초 정리", "scheduled_date": "2026-08-26"},
                {"title": "문제 풀이", "scheduled_date": "2026-09-09"},
            ],
            "planning_preference": {"intensity": "balanced", "preferred_days": []},
        },
    )

    assert result["is_valid"] is False
    assert "MILESTONE_COUNT_TOO_LOW" in result["failure_codes"]


def test_ai_draft_validation_rejects_duplicate_milestones():
    case = load_ai_schedule_draft_cases("tests/fixtures/mileday/ai_schedule_draft.json")[0]

    result = validate_ai_schedule_draft(
        case,
        _draft(
            milestones=[
                {"title": "자료 수집", "scheduled_date": "2026-08-22"},
                {"title": "자료 수집", "scheduled_date": "2026-08-22"},
                {"title": "보고서 정리", "scheduled_date": "2026-09-27"},
            ],
        ),
    )

    assert result["is_valid"] is False
    assert "DUPLICATE_MILESTONE" in result["failure_codes"]
