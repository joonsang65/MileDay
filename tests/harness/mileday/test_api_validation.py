from harness.mileday.api_db_payload import build_insert_sql_preview, build_sql_parameters
from harness.mileday.api_validation import validate_api_multiturn_plan_output
from harness.mileday.dataset import GOAL_DB_FIELDS, MILESTONE_DB_FIELDS, load_mileday_multiturn_cases


def test_validation_builds_db_payload_schema():
    case = load_mileday_multiturn_cases("tests/fixtures/mileday/multiturn_schedule.pretty.json")[0]
    parsed = {
        "action": "create",
        "plan_items": [
            {"slot_id": "S001", "task": "기초 정리"},
            {"slot_id": "S002", "task": "문제 풀이"},
            {"slot_id": "S003", "task": "오답 정리"},
        ],
        "patch_items": [],
        "add_items": [],
        "remove_slot_ids": [],
        "requires_confirmation": True,
    }

    result = validate_api_multiturn_plan_output(case, 1, parsed, None)
    payload = result["rule_based_db_payload"]

    assert result["errors"] == []
    assert set(payload["goal"]) == set(GOAL_DB_FIELDS)
    assert all(set(item) == set(MILESTONE_DB_FIELDS) for item in payload["milestones"])


def test_validation_rejects_invalid_slot_for_availability_gate():
    case = load_mileday_multiturn_cases("tests/fixtures/mileday/multiturn_schedule.pretty.json")[0]
    parsed = {
        "action": "create",
        "plan_items": [{"slot_id": "S999", "task": "기초 정리"}],
        "patch_items": [],
        "add_items": [],
        "remove_slot_ids": [],
        "requires_confirmation": True,
    }

    result = validate_api_multiturn_plan_output(case, 1, parsed, None)

    assert "plan_slot_valid" in result["deterministic_validation"]["failed_check_names"]
    assert "availability_alignment" in result["deterministic_validation"]["failed_check_names"]


def test_sql_preview_is_pure_and_parameterized():
    payload = {
        "goal": {
            "title": "시험",
            "deadline": "2026-09-01",
            "is_recurring": False,
            "recurrence_type": None,
            "color": "#4F46E5",
        },
        "milestones": [
            {
                "title": "[월 19:00-21:00] 기초 정리",
                "color": "#000000",
                "scheduled_date": "2026-08-17",
            }
        ],
    }

    preview = build_insert_sql_preview(payload)
    params = build_sql_parameters(payload, user_id="user-1")

    assert "Preview only" in preview
    assert "INSERT INTO public.goals" in preview
    assert "INSERT INTO public.milestones" in preview
    assert "inserted_goal.id" in preview
    assert ":user_id" in preview
    assert "is_completed" in preview
    assert "false" in preview
    assert ":milestone_1_title" in preview
    assert params == {
        "user_id": "user-1",
        "goal_title": "시험",
        "goal_deadline": "2026-09-01",
        "goal_is_recurring": False,
        "goal_recurrence_type": None,
        "goal_color": "#4F46E5",
        "milestone_1_title": "[월 19:00-21:00] 기초 정리",
        "milestone_1_color": "#000000",
        "milestone_1_scheduled_date": "2026-08-17",
    }
