from harness.cli import MILEDAY_MULTITURN_FIXTURE
from harness.mileday.dataset import load_mileday_multiturn_cases
from harness.mileday.api_prompt import (
    MILEDAY_API_MULTITURN_PROMPT_VERSION,
    api_schedule_intent_response_schema,
    build_api_multiturn_prompt,
)


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
    assert "[CONTRACT]" in prompt
    assert "[SELECTOR_VALUES]" in prompt
    assert "[SAFETY]" in prompt
    assert "[TIME_PLANNING]" in prompt
    assert "[EXAMPLES]" in prompt
    assert "Keep field names and enum values in English" in prompt
    assert "target_selector_type" in prompt
    assert "requires_clarification" in prompt
    assert "selected_slot_ids" in prompt
    assert "Never invent goal_id or milestone_id" in prompt
    assert "Prefer one unused selected_slot_id" in prompt
    assert "remove: tasks must be empty" in prompt
    assert "rename: keep the same date/time" in prompt
    assert "Do not rewrite preserved milestones" in prompt
    assert "Do not use all available slots" in prompt
    assert "duration_minutes" in prompt
    assert "Short slots should get light tasks" in prompt
    assert "Long slots should get core tasks" in prompt
    assert "progress toward the deadline" in prompt
    assert "S001" in prompt
    assert "[SCHEDULE_INTENT]" in prompt
    assert "mutation_safety_check" in prompt
    assert "Example rename JSON" not in prompt


def test_api_prompt_response_schema_matches_intent_contract():
    schema = api_schedule_intent_response_schema()

    assert schema["type"] == "object"
    required = set(schema["required"])
    assert {
        "action",
        "operation",
        "selected_slot_ids",
        "target_selector_type",
        "target_selector_value",
        "target_selector_confidence",
        "preserve_selector_type",
        "preserve_selector_values",
        "requires_clarification",
        "tasks",
        "mutation_safety_check",
    }.issubset(required)
    assert schema["properties"]["action"]["enum"] == ["create", "partial_update"]
    assert schema["properties"]["operation"]["enum"] == ["add", "remove", "rename", "none"]
