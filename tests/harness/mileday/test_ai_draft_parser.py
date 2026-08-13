import pytest

from harness.mileday.ai_draft_parser import parse_ai_schedule_draft_output


def test_ai_draft_parser_normalizes_schema_output():
    draft = parse_ai_schedule_draft_output(
        """
        {
          "goal": {"title": " 데이터 분석 과제 ", "deadline": "2026-09-30"},
          "milestones": [
            {"title": " 자료 수집 ", "scheduled_date": "2026-08-22"}
          ],
          "planning_preference": {"intensity": "relaxed", "preferred_days": ["saturday"]}
        }
        """
    )

    assert draft["goal"]["title"] == "데이터 분석 과제"
    assert draft["milestones"] == [{"title": "자료 수집", "scheduled_date": "2026-08-22"}]
    assert draft["planning_preference"]["preferred_days"] == ["saturday"]


def test_ai_draft_parser_rejects_non_json_output():
    with pytest.raises(ValueError):
        parse_ai_schedule_draft_output("일정을 만들어드릴게요.")
