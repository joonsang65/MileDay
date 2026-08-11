from harness.cli import MILEDAY_MULTITURN_FIXTURE
from harness.mileday.dataset import load_mileday_multiturn_cases
from harness.mileday.api_prompt import MILEDAY_API_MULTITURN_PROMPT_VERSION, build_api_multiturn_prompt


def test_api_prompt_has_flash_lite_partial_update_rules():
    case = load_mileday_multiturn_cases(MILEDAY_MULTITURN_FIXTURE)[0]
    transcript = [
        {
            "role": "assistant",
            "content": "[CURRENT_PLAN_TARGETS]\n- S001 | 시험 범위 확인\n- S002 | 기본 개념 정리",
        }
    ]

    prompt = build_api_multiturn_prompt(case, 2, transcript)

    assert MILEDAY_API_MULTITURN_PROMPT_VERSION in prompt
    assert "[PARTIAL_UPDATE_RULES]" in prompt
    assert "[PARTIAL_UPDATE_SCOPE_MAP]" in prompt
    assert "[TARGET_RULES]" in prompt
    assert "[PARTIAL_UPDATE_EXAMPLES]" in prompt
    assert "exactly one existing slot_id" in prompt
    assert "rewrite all task names" in prompt
    assert "S001" in prompt
    assert "[SCHEDULE_INTENT]" in prompt
