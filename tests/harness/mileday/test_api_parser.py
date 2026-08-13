from harness.cli import MILEDAY_API_MULTITURN_PROMPT_VERSION
from harness.mileday.api_parser import evaluate_api_multiturn_record
from harness.mileday.dataset import load_mileday_multiturn_cases
from harness.mileday.explanation_judge import ExplanationJudgeResult
from harness.schemas import RequestResult, ResultStatus


class PassingJudge:
    def evaluate_multiturn(self, case, turn_id, explanation, parsed_output, previous_output):
        return ExplanationJudgeResult(is_aligned=True, score=0.95, reason="ok")


class FailingIfCalledJudge:
    def evaluate_multiturn(self, case, turn_id, explanation, parsed_output, previous_output):
        raise AssertionError("turn-level judge must not run")


def _base_result(case_id: str) -> RequestResult:
    return RequestResult(
        run_id="prompt-test-1",
        model_id="gemini-3.5-flash-lite",
        dataset_id="mileday-multiturn-schedule",
        case_id=case_id,
        status=ResultStatus.PASSED,
    )


def _intent_response(*, action: str, target: str, tasks: list[str], change: str = "요청 반영") -> str:
    task_lines = "\n".join(f"- {task}" for task in tasks)
    return (
        "[일정_의도]\n"
        f"행동: {'생성' if action == 'create' else '부분수정'}\n"
        f"대상: {target}\n"
        f"변경: {change}\n"
        "작업:\n"
        f"{task_lines}\n"
        "[/일정_의도]"
    )


def test_api_parser_builds_rule_based_db_payload_for_create():
    case = load_mileday_multiturn_cases("tests/fixtures/mileday/multiturn_schedule.pretty.json")[0]

    result = evaluate_api_multiturn_record(
        _base_result("multiturn-001-turn-1"),
        case,
        1,
        _intent_response(
            action="create",
            target="전체 일정",
            tasks=["기초 범위 확인", "핵심 개념 정리", "문제 풀이", "오답 정리", "최종 점검"],
        ),
        previous_parsed=None,
        explanation_judge=PassingJudge(),
        prompt_version=MILEDAY_API_MULTITURN_PROMPT_VERSION,
    )

    assert result.status == ResultStatus.PASSED
    parsed = result.parsed_output["parsed_json"]
    assert parsed["action"] == "create"
    assert len(parsed["db_payload"]["milestones"]) == 5
    assert parsed["requires_confirmation"] is True


def test_api_parser_accepts_structured_json_output_for_create():
    case = load_mileday_multiturn_cases("tests/fixtures/mileday/test_api.json")[0]

    result = evaluate_api_multiturn_record(
        _base_result("multiturn-101-turn-1"),
        case,
        1,
        """
{
  "action": "create",
  "operation": "none",
  "target": "전체 일정",
  "target_selector_type": "ambiguous",
  "target_selector_value": "none",
  "target_selector_confidence": "high",
  "preserve_selector_type": "none",
  "preserve_selector_values": [],
  "requires_clarification": false,
  "selected_slot_ids": ["S001", "S002", "S003"],
  "change": "일정 생성",
  "tasks": ["자료 범위 확인", "분석 초안 작성", "최종 점검"],
  "mutation_safety_check": "create_scope_checked"
}
""".strip(),
        previous_parsed=None,
        explanation_judge=PassingJudge(),
        prompt_version=MILEDAY_API_MULTITURN_PROMPT_VERSION,
    )

    assert result.status == ResultStatus.PASSED
    parsed = result.parsed_output["parsed_json"]
    assert parsed["plan_items"] == [
        {"slot_id": "S001", "task": "자료 범위 확인"},
        {"slot_id": "S002", "task": "분석 초안 작성"},
        {"slot_id": "S003", "task": "최종 점검"},
    ]
    assert result.parsed_output["output_contract"]["structured_json_used"] is True


def test_api_parser_can_skip_turn_level_judge_for_case_level_evaluation():
    case = load_mileday_multiturn_cases("tests/fixtures/mileday/test_api.json")[0]

    result = evaluate_api_multiturn_record(
        _base_result("multiturn-101-turn-1"),
        case,
        1,
        """
{
  "action": "create",
  "operation": "none",
  "target": "?꾩껜 ?쇱젙",
  "target_selector_type": "ambiguous",
  "target_selector_value": "none",
  "target_selector_confidence": "high",
  "preserve_selector_type": "none",
  "preserve_selector_values": [],
  "requires_clarification": false,
  "selected_slot_ids": ["S001", "S002", "S003"],
  "change": "?쇱젙 ?앹꽦",
  "tasks": ["?먮즺 踰붿쐞 ?뺤씤", "遺꾩꽍 珥덉븞 ?묒꽦", "理쒖쥌 ?먭?"],
  "mutation_safety_check": "create_scope_checked"
}
""".strip(),
        previous_parsed=None,
        explanation_judge=FailingIfCalledJudge(),
        prompt_version=MILEDAY_API_MULTITURN_PROMPT_VERSION,
        run_judge=False,
    )

    assert result.status == ResultStatus.PASSED
    judge = result.parsed_output["explanation_judge"]
    assert judge["skipped"] is True
    assert judge["judge_scope"] == "case_pending"


def test_api_parser_rejects_structured_json_action_mismatch():
    case = load_mileday_multiturn_cases("tests/fixtures/mileday/test_api.json")[0]

    result = evaluate_api_multiturn_record(
        _base_result("multiturn-101-turn-1"),
        case,
        1,
        """
{
  "action": "partial_update",
  "operation": "none",
  "target": "전체 일정",
  "target_selector_type": "ambiguous",
  "target_selector_value": "none",
  "target_selector_confidence": "high",
  "preserve_selector_type": "none",
  "preserve_selector_values": [],
  "requires_clarification": false,
  "selected_slot_ids": ["S001", "S002", "S003"],
  "change": "create selected milestones",
  "tasks": ["자료 범위 확인", "기초 통계 분석", "최종 점검"],
  "mutation_safety_check": "create_scope_checked"
}
""".strip(),
        previous_parsed=None,
        explanation_judge=PassingJudge(),
        prompt_version=MILEDAY_API_MULTITURN_PROMPT_VERSION,
    )

    assert result.status == ResultStatus.INVALID
    validation = result.parsed_output["multiturn_validation"]
    assert "intent_action_valid" in validation["deterministic_validation"]["failed_check_names"]


def test_api_parser_limits_single_target_partial_update_to_one_patch():
    case = load_mileday_multiturn_cases("tests/fixtures/mileday/multiturn_schedule.pretty.json")[0]
    previous_parsed = {
        "plan_items": [
            {"slot_id": "S001", "task": "기초 범위 확인"},
            {"slot_id": "S002", "task": "핵심 개념 정리"},
        ],
        "db_payload": {
            "goal": {
                "title": case.input.initial_goal.title,
                "deadline": case.input.initial_goal.deadline,
                "is_recurring": False,
                "recurrence_type": None,
                "color": case.input.initial_goal.color,
            },
            "milestones": [],
        },
    }

    result = evaluate_api_multiturn_record(
        _base_result("multiturn-001-turn-2"),
        case,
        2,
        _intent_response(
            action="partial_update",
            target="S002",
            change="일정 중 하나만 더 구체화",
            tasks=["핵심 개념별 예제 풀이"],
        ),
        previous_parsed=previous_parsed,
        explanation_judge=PassingJudge(),
        prompt_version=MILEDAY_API_MULTITURN_PROMPT_VERSION,
    )

    assert result.status == ResultStatus.PASSED
    assert result.parsed_output["parsed_json"]["patch_items"] == [
        {"slot_id": "S002", "task": "핵심 개념별 예제 풀이"}
    ]


def test_api_parser_adds_new_task_to_next_unused_slot():
    base_case = load_mileday_multiturn_cases("tests/fixtures/mileday/multiturn_schedule.pretty.json")[2]
    turns = list(base_case.turns)
    turns[2] = turns[2].model_copy(
        update={
            "content": "기술 블로그 글 작성 일정을 하나 추가해줘. 나머지는 그대로 둬.",
            "expected_operation": "add",
        }
    )
    case = base_case.model_copy(update={"turns": turns})
    previous_parsed = {
        "plan_items": [
            {"slot_id": "S001", "task": "이력서 초안 작성"},
            {"slot_id": "S002", "task": "포트폴리오 구조 정리"},
            {"slot_id": "S003", "task": "프로젝트 설명 보완"},
        ],
        "db_payload": {
            "goal": {
                "title": case.input.initial_goal.title,
                "deadline": case.input.initial_goal.deadline,
                "is_recurring": False,
                "recurrence_type": None,
                "color": case.input.initial_goal.color,
            },
            "milestones": [],
        },
    }

    result = evaluate_api_multiturn_record(
        _base_result("multiturn-003-turn-3"),
        case,
        3,
        _intent_response(
            action="partial_update",
            target="추가",
            change="기술 블로그 글 작성 일정 추가",
            tasks=["기술 블로그 글 작성"],
        ),
        previous_parsed=previous_parsed,
        explanation_judge=PassingJudge(),
        prompt_version=MILEDAY_API_MULTITURN_PROMPT_VERSION,
    )

    assert result.status == ResultStatus.PASSED
    parsed = result.parsed_output["parsed_json"]
    assert parsed["add_items"] == [{"slot_id": "S004", "task": "기술 블로그 글 작성"}]
    assert parsed["plan_items"][-1] == {"slot_id": "S004", "task": "기술 블로그 글 작성"}


def test_api_parser_removes_target_from_new_fixture_by_rule_scoring():
    case = load_mileday_multiturn_cases("tests/fixtures/mileday/test_api.json")[1]
    previous_parsed = {
        "plan_items": [
            {"slot_id": "S001", "task": "개념 정리"},
            {"slot_id": "S002", "task": "모의고사 풀이"},
            {"slot_id": "S003", "task": "가벼운 복습"},
        ],
        "db_payload": {
            "goal": {
                "title": case.input.initial_goal.title,
                "deadline": case.input.initial_goal.deadline,
                "is_recurring": False,
                "recurrence_type": None,
                "color": case.input.initial_goal.color,
            },
            "milestones": [],
        },
    }

    result = evaluate_api_multiturn_record(
        _base_result("multiturn-102-turn-2"),
        case,
        2,
        _intent_response(
            action="partial_update",
            target="부담 큰 일정",
            change="일정 하나 제외",
            tasks=[],
        ),
        previous_parsed=previous_parsed,
        explanation_judge=PassingJudge(),
        prompt_version=MILEDAY_API_MULTITURN_PROMPT_VERSION,
    )

    assert result.status == ResultStatus.PASSED
    parsed = result.parsed_output["parsed_json"]
    assert parsed["remove_slot_ids"] == ["S001"]
    assert [item["slot_id"] for item in parsed["plan_items"]] == ["S002", "S003"]


def test_api_parser_keeps_ambiguous_add_remove_request_as_no_op():
    case = load_mileday_multiturn_cases("tests/fixtures/mileday/test_api.json")[14]
    previous_parsed = {
        "plan_items": [
            {"slot_id": "S001", "task": "회의 준비"},
            {"slot_id": "S002", "task": "역할 분담"},
            {"slot_id": "S003", "task": "최종 점검"},
        ],
        "db_payload": {
            "goal": {
                "title": case.input.initial_goal.title,
                "deadline": case.input.initial_goal.deadline,
                "is_recurring": False,
                "recurrence_type": None,
                "color": case.input.initial_goal.color,
            },
            "milestones": [],
        },
    }

    result = evaluate_api_multiturn_record(
        _base_result("multiturn-115-turn-2"),
        case,
        2,
        _intent_response(
            action="partial_update",
            target="확인 필요",
            change="임의 변경 없음",
            tasks=[],
        ),
        previous_parsed=previous_parsed,
        explanation_judge=PassingJudge(),
        prompt_version=MILEDAY_API_MULTITURN_PROMPT_VERSION,
    )

    assert result.status == ResultStatus.PASSED
    parsed = result.parsed_output["parsed_json"]
    assert parsed["patch_items"] == []
    assert parsed["add_items"] == []
    assert parsed["remove_slot_ids"] == []
    assert parsed["plan_items"] == previous_parsed["plan_items"]
