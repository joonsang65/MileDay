from harness.mileday.ai_draft_prompt import build_ai_schedule_draft_prompt
from harness.mileday.dataset import load_ai_schedule_draft_cases


def test_ai_draft_prompt_matches_service_draft_scope():
    case = load_ai_schedule_draft_cases("tests/fixtures/mileday/ai_schedule_draft.json")[0]

    prompt = build_ai_schedule_draft_prompt(case)

    assert "Return exactly one JSON object matching the response schema" in prompt
    assert "Do not return markdown, explanations, SQL, database ids, slot ids, or mutation fields" in prompt
    assert "The user will confirm and edit the draft before DB write" in prompt
    assert "selected_slot_ids" not in prompt
    assert "target_selector" not in prompt
    assert "db_payload" not in prompt
    assert case.user_prompt in prompt
    assert "2026-08-22" in prompt
