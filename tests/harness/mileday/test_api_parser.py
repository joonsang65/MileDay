from harness.cli import MILEDAY_API_MULTITURN_PROMPT_VERSION
from harness.mileday.api_parser import evaluate_api_multiturn_record
from harness.mileday.dataset import load_mileday_multiturn_cases
from harness.mileday.explanation_judge import ExplanationJudgeResult
from harness.schemas import RequestResult, ResultStatus


class PassingJudge:
    def evaluate_multiturn(self, case, turn_id, explanation, parsed_output, previous_output):
        return ExplanationJudgeResult(is_aligned=True, score=0.95, reason="ok")


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
