from harness.mileday.ai_draft_payload import (
    build_ai_draft_create_payload,
    build_ai_draft_create_sql_preview,
    build_ai_draft_sql_parameters,
)


def test_ai_draft_payload_builds_create_preview_without_db_ids():
    draft = {
        "goal": {"title": "데이터 분석 과제", "deadline": "2026-09-30"},
        "milestones": [{"title": "자료 수집", "scheduled_date": "2026-08-22"}],
    }

    payload = build_ai_draft_create_payload(draft)
    sql = build_ai_draft_create_sql_preview(payload)
    params = build_ai_draft_sql_parameters(payload, user_id="user-1")

    assert payload["write_policy"] == "user_confirmation_required"
    assert "id" not in payload["goal"]
    assert payload["goal"]["is_recurring"] is False
    assert payload["milestones"][0]["is_completed"] is False
    assert "INSERT INTO public.goals" in sql
    assert "INSERT INTO public.milestones" in sql
    assert "user confirmation" in sql
    assert params["user_id"] == "user-1"
    assert params["goal_title"] == "데이터 분석 과제"
    assert params["milestone_1_scheduled_date"] == "2026-08-22"
