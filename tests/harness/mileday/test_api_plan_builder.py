from harness.mileday.api_plan_builder import (
    apply_plan_patch,
    build_add_items,
    build_patch_items,
    build_plan_items,
    build_remove_slot_ids,
)
from harness.mileday.dataset import load_mileday_multiturn_cases


def test_create_plan_items_use_available_slots():
    case = load_mileday_multiturn_cases("tests/fixtures/mileday/multiturn_schedule.pretty.json")[0]

    items = build_plan_items(case, {"tasks": ["기초 정리", "문제 풀이", "오답 정리"]})

    assert [item["slot_id"] for item in items] == ["S001", "S002", "S003"]
    assert items[0]["task"] == "기초 정리"


def test_partial_update_targets_explicit_slot_id():
    case = load_mileday_multiturn_cases("tests/fixtures/mileday/multiturn_schedule.pretty.json")[0]
    previous = {"plan_items": [{"slot_id": "S001", "task": "기초 정리"}, {"slot_id": "S002", "task": "문제 풀이"}]}

    patches = build_patch_items(case, 2, {"target": "S002", "change": "더 구체화", "tasks": ["심화 문제 풀이"]}, previous)

    assert patches == [{"slot_id": "S002", "task": "심화 문제 풀이"}]
    assert apply_plan_patch(previous["plan_items"], patches)[1]["task"] == "심화 문제 풀이"


def test_add_request_uses_next_unused_slot():
    base_case = load_mileday_multiturn_cases("tests/fixtures/mileday/multiturn_schedule.pretty.json")[2]
    turns = list(base_case.turns)
    turns[2] = turns[2].model_copy(update={"content": "기술 블로그 글 작성 일정을 하나 추가해줘."})
    case = base_case.model_copy(update={"turns": turns})
    previous = {"plan_items": [{"slot_id": "S001", "task": "초안"}, {"slot_id": "S002", "task": "정리"}]}

    assert build_add_items(case, 3, {"tasks": ["기술 블로그 글 작성"]}, previous) == [
        {"slot_id": "S003", "task": "기술 블로그 글 작성"}
    ]


def test_remove_request_selects_target_slot():
    base_case = load_mileday_multiturn_cases("tests/fixtures/mileday/multiturn_schedule.pretty.json")[0]
    turns = list(base_case.turns)
    turns[1] = turns[1].model_copy(update={"content": "S002 일정은 제외해줘."})
    case = base_case.model_copy(update={"turns": turns})
    previous = {"plan_items": [{"slot_id": "S001", "task": "초안"}, {"slot_id": "S002", "task": "정리"}]}

    assert build_remove_slot_ids(case, 2, {"target": "S002", "change": "제외", "tasks": []}, previous) == ["S002"]
