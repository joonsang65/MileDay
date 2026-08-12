from harness.mileday.api_plan_builder import (
    apply_plan_patch,
    build_add_items,
    build_patch_items,
    build_plan_items,
    build_remove_slot_ids,
)
from harness.mileday.dataset import load_mileday_multiturn_cases


def _case_with_turn_content(case, turn_index: int, content: str):
    turns = list(case.turns)
    turns[turn_index - 1] = turns[turn_index - 1].model_copy(update={"content": content})
    return case.model_copy(update={"turns": turns})


def test_create_plan_items_use_available_slots():
    case = load_mileday_multiturn_cases("tests/fixtures/mileday/multiturn_schedule.pretty.json")[0]

    items = build_plan_items(case, {"tasks": ["기초 정리", "문제 풀이", "오답 정리"]})

    assert [item["slot_id"] for item in items] == ["S001", "S002", "S003"]
    assert items[0]["task"] == "기초 정리"


def test_create_plan_items_use_selected_slot_ids_in_task_order():
    case = load_mileday_multiturn_cases("tests/fixtures/mileday/test_api.json")[2]

    items = build_plan_items(
        case,
        {
            "selected_slot_ids": ["S001", "S003"],
            "tasks": ["기존 자료 정리", "최종 배포 점검"],
        },
    )

    assert items == [
        {"slot_id": "S001", "task": "기존 자료 정리"},
        {"slot_id": "S003", "task": "최종 배포 점검"},
    ]


def test_create_plan_items_normalize_numeric_selected_slot_ids():
    case = load_mileday_multiturn_cases("tests/fixtures/mileday/test_api.json")[5]

    items = build_plan_items(
        case,
        {
            "selected_slot_ids": ["50", "53"],
            "tasks": ["독서 범위 확인", "내용 정리"],
        },
    )

    assert items == [
        {"slot_id": "S050", "task": "독서 범위 확인"},
        {"slot_id": "S053", "task": "내용 정리"},
    ]


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


def test_add_request_uses_next_slot_after_latest_existing_plan_item():
    case = load_mileday_multiturn_cases("tests/fixtures/mileday/test_api.json")[10]
    previous = {
        "plan_items": [
            {"slot_id": "S139", "task": "카드 내역 확인"},
            {"slot_id": "S140", "task": "고정비 파악"},
        ]
    }

    assert build_add_items(
        case,
        2,
        {"operation": "add", "tasks": ["구독 서비스 점검"]},
        previous,
    ) == [{"slot_id": "S141", "task": "구독 서비스 점검"}]


def test_add_request_uses_valid_unused_selected_slot_id():
    case = load_mileday_multiturn_cases("tests/fixtures/mileday/test_api.json")[0]
    previous = {
        "plan_items": [
            {"slot_id": "S001", "task": "과제 범위 및 데이터 수집"},
            {"slot_id": "S005", "task": "기초 통계 분석 및 데이터 정제"},
            {"slot_id": "S010", "task": "데이터 모델링 및 상관관계 분석"},
            {"slot_id": "S017", "task": "분석 결과 시각화 및 보고서 작성"},
            {"slot_id": "S022", "task": "최종 검토 및 피드백 수정"},
        ]
    }

    assert build_add_items(
        case,
        2,
        {"operation": "add", "selected_slot_ids": ["S006"], "tasks": ["자료 시각화 점검"]},
        previous,
    ) == [{"slot_id": "S006", "task": "자료 시각화 점검"}]


def test_add_request_rejects_selected_slot_outside_preserve_weekday_scope():
    case = load_mileday_multiturn_cases("tests/fixtures/mileday/test_api.json")[5]
    previous = {"plan_items": [{"slot_id": "S002", "task": "독서 진행"}]}

    assert build_add_items(
        case,
        2,
        {
            "operation": "add",
            "selected_slot_ids": ["S005"],
            "preserve_selector": {"type": "weekday", "values": ["sunday"]},
            "tasks": ["독서 메모 정리"],
        },
        previous,
    ) == []


def test_add_request_prefers_intent_task_over_goal_title():
    base_case = load_mileday_multiturn_cases("tests/fixtures/mileday/test_api.json")[0]
    previous = {
        "plan_items": [
            {"slot_id": "S001", "task": "요구사항 분석"},
            {"slot_id": "S002", "task": "전처리"},
            {"slot_id": "S003", "task": "모델링"},
            {"slot_id": "S004", "task": "보고서 작성"},
            {"slot_id": "S005", "task": "제출 준비"},
        ]
    }

    assert build_add_items(
        base_case,
        2,
        {"operation": "add", "tasks": ["자료 시각화 점검"]},
        previous,
    ) == [{"slot_id": "S006", "task": "자료 시각화 점검"}]


def test_remove_request_selects_target_slot():
    base_case = load_mileday_multiturn_cases("tests/fixtures/mileday/multiturn_schedule.pretty.json")[0]
    case = _case_with_turn_content(base_case, 2, "S002 일정은 제외해줘.")
    previous = {"plan_items": [{"slot_id": "S001", "task": "초안"}, {"slot_id": "S002", "task": "정리"}]}

    assert build_remove_slot_ids(case, 2, {"target": "S002", "change": "제외", "tasks": []}, previous) == ["S002"]


def test_remove_request_selects_weekday_scope():
    base_case = load_mileday_multiturn_cases("tests/fixtures/mileday/test_api.json")[2]
    case = _case_with_turn_content(base_case, 2, "월요일 일정은 빼줘. 다른 요일은 그대로 둬.")
    previous = {
        "plan_items": [
            {"slot_id": "S001", "task": "자료 정리"},
            {"slot_id": "S002", "task": "화면 개선"},
            {"slot_id": "S003", "task": "최종 점검"},
        ]
    }

    assert build_remove_slot_ids(case, 2, {"target": "월요일", "change": "제외", "tasks": []}, previous) == ["S003"]


def test_remove_request_selects_latest_slot_for_last_target():
    base_case = load_mileday_multiturn_cases("tests/fixtures/mileday/test_api.json")[0]
    case = _case_with_turn_content(base_case, 2, "마지막 일정 하나는 빼줘.")
    previous = {
        "plan_items": [
            {"slot_id": "S001", "task": "자료 정리"},
            {"slot_id": "S002", "task": "분석 실행"},
            {"slot_id": "S003", "task": "최종 점검"},
        ]
    }

    assert build_remove_slot_ids(case, 2, {"target": "마지막 일정", "change": "제외", "tasks": []}, previous) == ["S003"]


def test_remove_request_selects_first_slot_for_first_target():
    base_case = load_mileday_multiturn_cases("tests/fixtures/mileday/test_api.json")[0]
    case = _case_with_turn_content(base_case, 2, "첫 일정 하나는 빼줘.")
    previous = {
        "plan_items": [
            {"slot_id": "S001", "task": "자료 정리"},
            {"slot_id": "S002", "task": "분석 실행"},
            {"slot_id": "S003", "task": "최종 점검"},
        ]
    }

    assert build_remove_slot_ids(case, 2, {"target": "첫 일정", "change": "제외", "tasks": []}, previous) == ["S001"]


def test_remove_request_scores_shortest_slot():
    base_case = load_mileday_multiturn_cases("tests/fixtures/mileday/test_api.json")[1]
    case = _case_with_turn_content(base_case, 2, "너무 짧아서 효과 없는 일정 하나는 삭제해줘.")
    previous = {
        "plan_items": [
            {"slot_id": "S001", "task": "개념 정리"},
            {"slot_id": "S002", "task": "모의고사 풀이"},
            {"slot_id": "S003", "task": "가벼운 복습"},
        ]
    }

    assert build_remove_slot_ids(case, 2, {"target": "효과 없는 일정", "change": "삭제", "tasks": []}, previous) == ["S003"]


def test_remove_request_scores_longest_slot_for_heavy_request():
    base_case = load_mileday_multiturn_cases("tests/fixtures/mileday/test_api.json")[1]
    case = _case_with_turn_content(base_case, 2, "부담 큰 일정 하나는 빼줘.")
    previous = {
        "plan_items": [
            {"slot_id": "S001", "task": "개념 정리"},
            {"slot_id": "S002", "task": "모의고사 풀이"},
            {"slot_id": "S003", "task": "가벼운 복습"},
        ]
    }

    assert build_remove_slot_ids(case, 2, {"target": "부담 큰 일정", "change": "제외", "tasks": []}, previous) == ["S002"]


def test_remove_request_scores_task_similarity():
    base_case = load_mileday_multiturn_cases("tests/fixtures/mileday/test_api.json")[4]
    case = _case_with_turn_content(base_case, 2, "숙소 비교 일정은 하나 빼줘. 다른 준비 일정은 그대로 남겨줘.")
    previous = {
        "plan_items": [
            {"slot_id": "S001", "task": "항공권 확인"},
            {"slot_id": "S002", "task": "숙소 비교"},
            {"slot_id": "S003", "task": "여행 경비 정리"},
        ]
    }

    assert build_remove_slot_ids(case, 2, {"target": "숙소 비교", "change": "제외", "tasks": []}, previous) == ["S002"]


def test_remove_request_prefers_selector_over_natural_language_scoring():
    base_case = load_mileday_multiturn_cases("tests/fixtures/mileday/test_api.json")[1]
    case = _case_with_turn_content(base_case, 2, "부담 큰 일정 하나는 빼줘.")
    previous = {
        "plan_items": [
            {"slot_id": "S001", "task": "개념 정리"},
            {"slot_id": "S002", "task": "모의고사 풀이"},
            {"slot_id": "S003", "task": "가벼운 복습"},
        ]
    }

    assert build_remove_slot_ids(
        case,
        2,
        {
            "operation": "remove",
            "target_selector": {"type": "slot_id", "value": "S001", "confidence": "high"},
            "target": "S001",
            "change": "제외",
            "tasks": [],
        },
        previous,
    ) == ["S001"]


def test_remove_request_low_confidence_selector_returns_no_target():
    base_case = load_mileday_multiturn_cases("tests/fixtures/mileday/test_api.json")[1]
    case = _case_with_turn_content(base_case, 2, "부담 큰 일정 하나는 빼줘.")
    previous = {
        "plan_items": [
            {"slot_id": "S001", "task": "개념 정리"},
            {"slot_id": "S002", "task": "모의고사 풀이"},
        ]
    }

    assert build_remove_slot_ids(
        case,
        2,
        {
            "operation": "remove",
            "target_selector": {"type": "duration", "value": "longest", "confidence": "low"},
            "target": "부담 큰 일정",
            "change": "제외",
            "tasks": [],
        },
        previous,
    ) == []


def test_remove_request_preserve_selector_blocks_mutation_target():
    base_case = load_mileday_multiturn_cases("tests/fixtures/mileday/test_api.json")[1]
    case = _case_with_turn_content(base_case, 2, "부담 큰 일정 하나는 빼줘. S002는 유지해줘.")
    previous = {
        "plan_items": [
            {"slot_id": "S001", "task": "개념 정리"},
            {"slot_id": "S002", "task": "모의고사 풀이"},
        ]
    }

    assert build_remove_slot_ids(
        case,
        2,
        {
            "operation": "remove",
            "target_selector": {"type": "slot_id", "value": "S002", "confidence": "high"},
            "preserve_selector": {"type": "slot_id", "value": "S002"},
            "target": "S002",
            "change": "제외",
            "tasks": [],
        },
        previous,
    ) == []


def test_remove_request_rejects_multi_slot_selector_for_db_safety():
    base_case = load_mileday_multiturn_cases("tests/fixtures/mileday/test_api.json")[2]
    previous = {
        "plan_items": [
            {"slot_id": "S001", "task": "자료 정리"},
            {"slot_id": "S002", "task": "화면 개선"},
            {"slot_id": "S003", "task": "최종 점검"},
        ]
    }

    assert build_remove_slot_ids(
        base_case,
        2,
        {
            "operation": "remove",
            "target_selector": {"type": "slot_id_list", "value": "S001, S002", "confidence": "high"},
            "target": "여러 일정",
            "change": "제외",
            "tasks": [],
        },
        previous,
    ) == []


def test_patch_request_uses_selector_for_rename_target():
    base_case = load_mileday_multiturn_cases("tests/fixtures/mileday/test_api.json")[2]
    case = _case_with_turn_content(base_case, 2, "첫 번째 작업 이름을 기존 자료 정리로 바꿔줘.")
    previous = {
        "plan_items": [
            {"slot_id": "S001", "task": "자료 수집"},
            {"slot_id": "S002", "task": "화면 개선"},
        ]
    }

    assert build_patch_items(
        case,
        2,
        {
            "operation": "rename",
            "target_selector": {"type": "slot_id", "value": "S002", "confidence": "high"},
            "target": "첫 번째 작업",
            "change": "기존 자료 정리",
            "tasks": ["기존 자료 정리"],
        },
        previous,
    ) == [{"slot_id": "S002", "task": "기존 자료 정리"}]


def test_patch_request_prefers_intent_task_over_change_keyword_fallback():
    base_case = load_mileday_multiturn_cases("tests/fixtures/mileday/test_api.json")[6]
    previous = {
        "plan_items": [
            {"slot_id": "S001", "task": "근력 운동"},
            {"slot_id": "S002", "task": "유산소 운동"},
        ]
    }

    assert build_patch_items(
        base_case,
        3,
        {
            "operation": "rename",
            "target_selector": {"type": "slot_id", "value": "S001", "confidence": "high"},
            "target": "첫 운동",
            "change": "남은 첫 운동 이름을 기본 체력 회복으로 바꿔줘.",
            "tasks": ["기본 체력 회복"],
        },
        previous,
    ) == [{"slot_id": "S001", "task": "기본 체력 회복"}]


def test_patch_request_rejects_multi_slot_selector_for_rename_safety():
    base_case = load_mileday_multiturn_cases("tests/fixtures/mileday/test_api.json")[2]
    previous = {
        "plan_items": [
            {"slot_id": "S001", "task": "자료 수집"},
            {"slot_id": "S002", "task": "화면 개선"},
        ]
    }

    assert build_patch_items(
        base_case,
        2,
        {
            "operation": "rename",
            "target_selector": {"type": "slot_id_list", "value": "S001, S002", "confidence": "high"},
            "target": "여러 작업",
            "change": "기존 자료 정리",
            "tasks": ["기존 자료 정리"],
        },
        previous,
    ) == []


def test_remove_request_scores_compact_task_similarity():
    base_case = load_mileday_multiturn_cases("tests/fixtures/mileday/test_api.json")[4]
    case = _case_with_turn_content(base_case, 2, "숙소비교 일정은 하나 빼줘.")
    previous = {
        "plan_items": [
            {"slot_id": "S001", "task": "항공권 확인"},
            {"slot_id": "S002", "task": "숙소 비교"},
            {"slot_id": "S003", "task": "여행 경비 정리"},
        ]
    }

    assert build_remove_slot_ids(case, 2, {"target": "숙소비교", "change": "제외", "tasks": []}, previous) == ["S002"]


def test_remove_request_does_not_overprotect_generic_preserve_phrase():
    base_case = load_mileday_multiturn_cases("tests/fixtures/mileday/test_api.json")[4]
    case = _case_with_turn_content(base_case, 2, "숙소 비교 일정은 하나 빼줘. 다른 준비 일정은 그대로 남겨줘.")
    previous = {
        "plan_items": [
            {"slot_id": "S001", "task": "항공권 준비"},
            {"slot_id": "S002", "task": "숙소 비교 준비"},
            {"slot_id": "S003", "task": "여행 경비 준비"},
        ]
    }

    assert build_remove_slot_ids(case, 2, {"target": "숙소 비교", "change": "제외", "tasks": []}, previous) == ["S002"]


def test_remove_request_scores_duplicate_candidate():
    base_case = load_mileday_multiturn_cases("tests/fixtures/mileday/test_api.json")[7]
    case = _case_with_turn_content(base_case, 3, "중복되는 점검 일정이 있으면 하나 빼줘. 새로 추가한 일정은 유지해줘.")
    previous = {
        "plan_items": [
            {"slot_id": "S001", "task": "출시 점검"},
            {"slot_id": "S002", "task": "품질 점검"},
            {"slot_id": "S003", "task": "스토어 등록 확인"},
        ]
    }

    assert build_remove_slot_ids(case, 3, {"target": "중복 점검", "change": "제외", "tasks": []}, previous) == ["S002"]


def test_ambiguous_add_or_remove_request_returns_no_remove_target():
    base_case = load_mileday_multiturn_cases("tests/fixtures/mileday/test_api.json")[14]
    previous = {
        "plan_items": [
            {"slot_id": "S001", "task": "회의 준비"},
            {"slot_id": "S002", "task": "역할 분담"},
        ]
    }

    assert build_remove_slot_ids(base_case, 2, {"target": "애매한 변경", "change": "추가하거나 삭제", "tasks": []}, previous) == []


def test_uncertain_remove_below_threshold_returns_no_target():
    base_case = load_mileday_multiturn_cases("tests/fixtures/mileday/test_api.json")[1]
    case = _case_with_turn_content(base_case, 2, "뭔가 하나 빼줘.")
    previous = {
        "plan_items": [
            {"slot_id": "S001", "task": "개념 정리"},
            {"slot_id": "S002", "task": "모의고사 풀이"},
        ]
    }

    assert build_remove_slot_ids(case, 2, {"target": "불명확", "change": "제외", "tasks": []}, previous) == []


def test_tied_remove_score_returns_no_target():
    base_case = load_mileday_multiturn_cases("tests/fixtures/mileday/test_api.json")[1]
    case = _case_with_turn_content(base_case, 2, "자료 일정 하나는 빼줘.")
    previous = {
        "plan_items": [
            {"slot_id": "S001", "task": "자료 정리"},
            {"slot_id": "S002", "task": "자료 검토"},
        ]
    }

    assert build_remove_slot_ids(case, 2, {"target": "자료 일정", "change": "제외", "tasks": []}, previous) == []
