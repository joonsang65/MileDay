from harness.mileday.api_intent import (
    extract_schedule_intent_block,
    fallback_schedule_intent,
    parse_schedule_intent_json,
    parse_schedule_intent_block,
)
from harness.mileday.dataset import load_mileday_multiturn_cases


def test_extracts_korean_schedule_intent_block():
    raw = "prefix\n[일정_의도]\n행동: 생성\n대상: 전체\n변경: 생성\n작업:\n- 기초 정리\n[/일정_의도]"

    assert "행동: 생성" in extract_schedule_intent_block(raw)


def test_parses_schedule_intent_contract():
    intent, errors = parse_schedule_intent_block(
        "action: partial_update\n"
        "target: S001\n"
        "change: 더 구체화\n"
        "tasks:\n"
        "- 개념별 예제 풀이"
    )

    assert errors == []
    assert intent == {
        "action": "partial_update",
        "operation": "",
        "target": "S001",
        "change": "더 구체화",
        "target_selector": {},
        "preserve_selector": {},
        "requires_clarification": False,
        "selected_slot_ids": [],
        "mutation_safety_check": "",
        "tasks": ["개념별 예제 풀이"],
    }


def test_parses_selector_contract():
    intent, errors = parse_schedule_intent_block(
        "action: partial_update\n"
        "operation: remove\n"
        "target: 숙소 비교\n"
        "target_selector_type: task_text\n"
        "target_selector_value: 숙소 비교\n"
        "target_selector_confidence: high\n"
        "preserve_selector_type: slot_id_list\n"
        "preserve_selector_values: S003, S004\n"
        "requires_clarification: false\n"
        "selected_slot_ids: S001, S003\n"
        "change: 삭제\n"
        "tasks:\n"
    )

    assert errors == []
    assert intent["operation"] == "remove"
    assert intent["target_selector"] == {
        "type": "task_text",
        "value": "숙소 비교",
        "confidence": "high",
    }
    assert intent["preserve_selector"] == {"type": "slot_id_list", "values": ["S003", "S004"]}
    assert intent["requires_clarification"] is False
    assert intent["selected_slot_ids"] == ["S001", "S003"]


def test_line_contract_filters_none_slot_lists():
    intent, errors = parse_schedule_intent_block(
        "action: partial_update\n"
        "operation: add\n"
        "target: 추가\n"
        "target_selector_type: position\n"
        "target_selector_value: last\n"
        "target_selector_confidence: high\n"
        "preserve_selector_type: none\n"
        "preserve_selector_values: none\n"
        "requires_clarification: false\n"
        "selected_slot_ids: none\n"
        "change: 추가\n"
        "tasks:\n"
        "- 점검 작업\n"
    )

    assert errors == []
    assert intent["selected_slot_ids"] == []
    assert intent["preserve_selector"]["values"] == []


def test_parses_structured_json_contract():
    intent, errors = parse_schedule_intent_json(
        """
{
  "action": "partial_update",
  "operation": "remove",
  "target": "S002",
  "target_selector_type": "slot_id",
  "target_selector_value": "S002",
  "target_selector_confidence": "high",
  "preserve_selector_type": "none",
  "preserve_selector_values": [],
  "requires_clarification": false,
  "selected_slot_ids": [],
  "change": "삭제",
  "tasks": [],
  "mutation_safety_check": "single_target_matched"
}
""".strip()
    )

    assert errors == []
    assert intent["operation"] == "remove"
    assert intent["target_selector"] == {"type": "slot_id", "value": "S002", "confidence": "high"}
    assert intent["preserve_selector"] == {"type": "none", "values": []}
    assert intent["mutation_safety_check"] == "single_target_matched"


def test_rejects_invalid_explicit_action():
    intent, errors = parse_schedule_intent_block(
        "action: delete\n"
        "target: S001\n"
        "change: 삭제\n"
        "tasks:\n"
        "- 기초 정리"
    )

    assert intent["action"] == "delete"
    assert "action must be create or partial_update." in errors


def test_freeform_fallback_uses_expected_action_and_task_candidates():
    case = load_mileday_multiturn_cases("tests/fixtures/mileday/multiturn_schedule.pretty.json")[0]

    intent = fallback_schedule_intent(case, 1, "- 기초 범위 확인\n- 핵심 개념 정리\n- 최종 점검")

    assert intent["action"] == "create"
    assert intent["source"] == "freeform_fallback"
    assert intent["tasks"][:2] == ["기초 범위 확인", "핵심 개념 정리"]
