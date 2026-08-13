from harness.mileday.ai_draft_judge import AiDraftJudgeResult
from harness.mileday.ai_draft_runner import _evaluate_ai_draft_record
from harness.mileday.dataset import load_ai_schedule_draft_cases
from harness.schemas import RequestResult, ResultStatus, RuntimeMetrics


class PassingJudge:
    def evaluate(self, case, draft):
        return AiDraftJudgeResult(is_aligned=True, score=0.95, reason="좋은 초안입니다.")


class RejectingJudge:
    def evaluate(self, case, draft):
        return AiDraftJudgeResult(is_aligned=False, score=0.7, reason="요청과 맞지 않습니다.")


def _request_result(case_id="draft-001"):
    return RequestResult(
        run_id="prompt-draft-1",
        model_id="gemini-3.5-flash-lite",
        dataset_id="mileday-ai-schedule-draft",
        case_id=case_id,
        status=ResultStatus.PASSED,
        parsed_output={"evaluation_family": "mileday_ai_draft", "case_id": case_id},
        metrics=RuntimeMetrics(latency_ms=100),
    )


def test_evaluate_ai_draft_record_builds_payload_after_validation():
    case = load_ai_schedule_draft_cases("tests/fixtures/mileday/ai_schedule_draft.json")[0]
    raw = """
    {
      "goal": {"title": "데이터 분석 과제", "deadline": "2026-09-30"},
      "milestones": [
        {"title": "자료 수집", "scheduled_date": "2026-08-22"},
        {"title": "분석 수행", "scheduled_date": "2026-09-06"},
        {"title": "보고서 정리", "scheduled_date": "2026-09-27"}
      ],
      "planning_preference": {"intensity": "relaxed", "preferred_days": ["saturday", "sunday"]}
    }
    """

    result = _evaluate_ai_draft_record(_request_result(), case, raw, judge=PassingJudge())

    assert result.status == ResultStatus.PASSED
    assert result.parsed_output["draft_validation"]["is_valid"] is True
    assert result.parsed_output["create_payload_preview"]["write_policy"] == "user_confirmation_required"
    assert "INSERT INTO public.goals" in result.parsed_output["sql_preview"]
    assert result.parsed_output["draft_judge"]["reason"] == "좋은 초안입니다."


def test_evaluate_ai_draft_record_rejects_deterministic_invalid_before_judge():
    case = load_ai_schedule_draft_cases("tests/fixtures/mileday/ai_schedule_draft.json")[0]
    raw = """
    {
      "goal": {"title": "", "deadline": "2026-10-31"},
      "milestones": [],
      "planning_preference": {"intensity": "balanced", "preferred_days": []}
    }
    """

    result = _evaluate_ai_draft_record(_request_result(), case, raw, judge=RejectingJudge())

    assert result.status == ResultStatus.INVALID
    assert "draft_judge" not in result.parsed_output
    assert "EMPTY_GOAL_TITLE" in result.parsed_output["draft_validation"]["failure_codes"]
