from harness.mileday.api_intent import (
    extract_schedule_intent_block,
    fallback_schedule_intent,
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
        "target": "S001",
        "change": "더 구체화",
        "tasks": ["개념별 예제 풀이"],
    }


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
