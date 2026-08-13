from harness.mileday.api_db_payload import build_insert_sql_preview, build_sql_parameters
from harness.mileday.api_validation import validate_api_multiturn_plan_output
from harness.mileday.dataset import GOAL_DB_FIELDS, MILESTONE_DB_FIELDS, load_mileday_multiturn_cases


def test_validation_builds_db_payload_schema():
    case = load_mileday_multiturn_cases("tests/fixtures/mileday/multiturn_schedule.pretty.json")[0]
    parsed = {
        "action": "create",
        "plan_items": [
            {"slot_id": "S001", "task": "기초 정리"},
            {"slot_id": "S002", "task": "문제 풀이"},
            {"slot_id": "S003", "task": "오답 정리"},
        ],
        "patch_items": [],
        "add_items": [],
        "remove_slot_ids": [],
        "requires_confirmation": True,
    }

    result = validate_api_multiturn_plan_output(case, 1, parsed, None)
    payload = result["rule_based_db_payload"]

    assert result["errors"] == []
    assert set(payload["goal"]) == set(GOAL_DB_FIELDS)
    assert all(set(item) == set(MILESTONE_DB_FIELDS) for item in payload["milestones"])


def test_validation_rejects_intent_action_mismatch():
    case = load_mileday_multiturn_cases("tests/fixtures/mileday/test_api.json")[0]
    parsed = {
        "action": "create",
        "intent": {"action": "partial_update", "operation": "none"},
        "plan_items": [
            {"slot_id": "S001", "task": "기초 정리"},
            {"slot_id": "S002", "task": "문제 풀이"},
            {"slot_id": "S003", "task": "오답 정리"},
        ],
        "patch_items": [],
        "add_items": [],
        "remove_slot_ids": [],
        "requires_confirmation": True,
    }

    result = validate_api_multiturn_plan_output(case, 1, parsed, None)

    assert result["contract"]["intent_action_valid"] is False
    assert "intent_action_valid" in result["deterministic_validation"]["failed_check_names"]
    assert "INTENT_CONTRACT_ERROR" in result["deterministic_validation"]["failure_codes"]


def test_validation_rejects_intent_operation_mismatch():
    case = load_mileday_multiturn_cases("tests/fixtures/mileday/test_api.json")[0]
    previous = {
        "plan_items": [
            {"slot_id": "S001", "task": "기초 정리"},
            {"slot_id": "S002", "task": "문제 풀이"},
            {"slot_id": "S003", "task": "오답 복습"},
        ],
        "db_payload": {"milestones": []},
    }
    parsed = {
        "action": "partial_update",
        "intent": {"action": "partial_update", "operation": "remove"},
        "plan_items": [],
        "patch_items": [],
        "add_items": [{"slot_id": "S004", "task": "최종 점검"}],
        "remove_slot_ids": [],
        "requires_confirmation": True,
    }

    result = validate_api_multiturn_plan_output(case, 2, parsed, previous)

    assert result["contract"]["intent_operation_valid"] is False
    assert "intent_operation_valid" in result["deterministic_validation"]["failed_check_names"]


def test_validation_records_freeform_fallback_without_contract_failure():
    case = load_mileday_multiturn_cases("tests/fixtures/mileday/test_api.json")[0]
    parsed = {
        "action": "create",
        "freeform_fallback_used": True,
        "intent": {"action": "create", "operation": "", "source": "freeform_fallback"},
        "plan_items": [
            {"slot_id": "S001", "task": "기초 정리"},
            {"slot_id": "S002", "task": "문제 풀이"},
            {"slot_id": "S003", "task": "오답 복습"},
        ],
        "patch_items": [],
        "add_items": [],
        "remove_slot_ids": [],
        "requires_confirmation": True,
    }

    result = validate_api_multiturn_plan_output(case, 1, parsed, None)

    assert result["contract"]["fallback_used"] is True
    assert result["contract"]["intent_operation_valid"] is True
    assert result["state"]["fallback"]["used"] is True


def test_validation_accepts_create_subset_two_weekdays():
    case = load_mileday_multiturn_cases("tests/fixtures/mileday/test_api.json")[2]
    parsed = {
        "action": "create",
        "plan_items": [
            {"slot_id": "S001", "task": "기존 자료 정리"},
            {"slot_id": "S002", "task": "화면 개선"},
            {"slot_id": "S004", "task": "최종 점검"},
        ],
        "patch_items": [],
        "add_items": [],
        "remove_slot_ids": [],
        "requires_confirmation": True,
    }

    result = validate_api_multiturn_plan_output(case, 1, parsed, None)

    assert result["contract"]["create_subset_scope_valid"] is True
    assert result["state"]["create_subset_scope"]["expected_day_count"] == 2
    assert result["state"]["create_subset_scope"]["actual_day_count"] == 2


def test_validation_uses_case_min_milestone_count_for_create():
    case = load_mileday_multiturn_cases("tests/fixtures/mileday/test_api.json")[2]
    parsed = {
        "action": "create",
        "plan_items": [
            {"slot_id": "S001", "task": "기존 자료 정리"},
            {"slot_id": "S002", "task": "화면 개선"},
        ],
        "patch_items": [],
        "add_items": [],
        "remove_slot_ids": [],
        "requires_confirmation": True,
    }

    result = validate_api_multiturn_plan_output(case, 1, parsed, None)

    assert result["errors"] == []
    assert result["schedule_quality"]["milestone_count_valid"] is True


def test_validation_rejects_create_subset_using_too_many_weekdays():
    case = load_mileday_multiturn_cases("tests/fixtures/mileday/test_api.json")[2]
    parsed = {
        "action": "create",
        "plan_items": [
            {"slot_id": "S001", "task": "기존 자료 정리"},
            {"slot_id": "S002", "task": "화면 개선"},
            {"slot_id": "S003", "task": "최종 점검"},
        ],
        "patch_items": [],
        "add_items": [],
        "remove_slot_ids": [],
        "requires_confirmation": True,
    }

    result = validate_api_multiturn_plan_output(case, 1, parsed, None)

    assert result["contract"]["create_subset_scope_valid"] is False
    assert "create_subset_scope_valid" in result["deterministic_validation"]["failed_check_names"]
    assert "CREATE_SUBSET_SCOPE_MISMATCH" in result["deterministic_validation"]["failure_codes"]


def test_validation_rejects_short_long_create_without_duration_extremes():
    case = load_mileday_multiturn_cases("tests/fixtures/mileday/test_api.json")[1]
    parsed = {
        "action": "create",
        "plan_items": [
            {"slot_id": "S001", "task": "개념 정리"},
            {"slot_id": "S004", "task": "문제 풀이"},
        ],
        "patch_items": [],
        "add_items": [],
        "remove_slot_ids": [],
        "requires_confirmation": True,
    }

    result = validate_api_multiturn_plan_output(case, 1, parsed, None)

    assert result["contract"]["schedule_progression_valid"] is False
    assert "TIME_DIFFICULTY_MISMATCH" in result["deterministic_validation"]["failure_codes"]


def test_validation_accepts_short_long_create_with_duration_extremes():
    case = load_mileday_multiturn_cases("tests/fixtures/mileday/test_api.json")[1]
    parsed = {
        "action": "create",
        "plan_items": [
            {"slot_id": "S001", "task": "개념 정리"},
            {"slot_id": "S002", "task": "모의고사 풀이"},
        ],
        "patch_items": [],
        "add_items": [],
        "remove_slot_ids": [],
        "requires_confirmation": True,
    }

    result = validate_api_multiturn_plan_output(case, 1, parsed, None)

    assert result["contract"]["schedule_progression_valid"] is True
    assert "schedule_progression_valid" not in result["deterministic_validation"]["failed_check_names"]


def test_validation_rejects_invalid_slot_for_availability_gate():
    case = load_mileday_multiturn_cases("tests/fixtures/mileday/multiturn_schedule.pretty.json")[0]
    parsed = {
        "action": "create",
        "plan_items": [{"slot_id": "S999", "task": "기초 정리"}],
        "patch_items": [],
        "add_items": [],
        "remove_slot_ids": [],
        "requires_confirmation": True,
    }

    result = validate_api_multiturn_plan_output(case, 1, parsed, None)

    assert "plan_slot_valid" in result["deterministic_validation"]["failed_check_names"]
    assert "availability_alignment" in result["deterministic_validation"]["failed_check_names"]


def test_sql_preview_is_pure_and_parameterized():
    payload = {
        "goal": {
            "title": "시험",
            "deadline": "2026-09-01",
            "is_recurring": False,
            "recurrence_type": None,
            "color": "#4F46E5",
        },
        "milestones": [
            {
                "title": "[월 19:00-21:00] 기초 정리",
                "color": "#000000",
                "scheduled_date": "2026-08-17",
            }
        ],
    }

    preview = build_insert_sql_preview(payload)
    params = build_sql_parameters(payload, user_id="user-1")

    assert "Preview only" in preview
    assert "INSERT INTO public.goals" in preview
    assert "INSERT INTO public.milestones" in preview
    assert "inserted_goal.id" in preview
    assert ":user_id" in preview
    assert "is_completed" in preview
    assert "false" in preview
    assert ":milestone_1_title" in preview
    assert params == {
        "user_id": "user-1",
        "goal_title": "시험",
        "goal_deadline": "2026-09-01",
        "goal_is_recurring": False,
        "goal_recurrence_type": None,
        "goal_color": "#4F46E5",
        "milestone_1_title": "[월 19:00-21:00] 기초 정리",
        "milestone_1_color": "#000000",
        "milestone_1_scheduled_date": "2026-08-17",
    }


def test_validation_accepts_expected_remove_effect():
    case = load_mileday_multiturn_cases("tests/fixtures/mileday/test_api.json")[1]
    previous = {
        "plan_items": [
            {"slot_id": "S001", "task": "기출 개념 정리"},
            {"slot_id": "S002", "task": "핵심 문제 풀이"},
            {"slot_id": "S003", "task": "오답 복습"},
        ],
        "db_payload": {"milestones": []},
    }
    parsed = {
        "action": "partial_update",
        "plan_items": [],
        "patch_items": [],
        "add_items": [],
        "remove_slot_ids": ["S002"],
        "requires_confirmation": True,
    }

    result = validate_api_multiturn_plan_output(case, 2, parsed, previous)

    assert result["contract"]["operation_effect_valid"] is True
    assert "operation_effect_valid" not in result["deterministic_validation"]["failed_check_names"]
    assert result["state"]["operation_effect"]["explicit_remove_count"] == 1
    assert result["state"]["operation_effect"]["actual_removed_count"] == 1
    payload = result["rule_based_db_payload"]
    assert payload["operation"] == "remove"
    assert payload["mutations"]["requires_goal_id"] is True
    assert payload["mutations"]["requires_milestone_id"] is True
    assert payload["mutations"]["remove"] == [
        {
            "slot_id": "S002",
            "goal_id_required": True,
            "milestone_id_required": True,
        }
    ]


def test_validation_rejects_no_op_mutation():
    case = load_mileday_multiturn_cases("tests/fixtures/mileday/test_api.json")[14]
    previous = {
        "plan_items": [
            {"slot_id": "S001", "task": "회의 준비"},
            {"slot_id": "S002", "task": "역할 분담"},
            {"slot_id": "S003", "task": "최종 점검"},
        ],
        "db_payload": {"milestones": []},
    }
    parsed = {
        "action": "partial_update",
        "plan_items": [],
        "patch_items": [],
        "add_items": [{"slot_id": "S004", "task": "추가 회의"}],
        "remove_slot_ids": [],
        "requires_confirmation": True,
    }

    result = validate_api_multiturn_plan_output(case, 2, parsed, previous)

    assert result["contract"]["operation_effect_valid"] is False
    assert "operation_effect_valid" in result["deterministic_validation"]["failed_check_names"]
    assert "UNEXPECTED_MUTATION" in result["deterministic_validation"]["failure_codes"]


def test_validation_builds_add_mutation_payload():
    case = load_mileday_multiturn_cases("tests/fixtures/mileday/test_api.json")[0]
    previous = {
        "plan_items": [
            {"slot_id": "S001", "task": "기초 정리"},
            {"slot_id": "S002", "task": "문제 풀이"},
            {"slot_id": "S003", "task": "오답 복습"},
        ],
        "db_payload": {"milestones": []},
    }
    parsed = {
        "action": "partial_update",
        "plan_items": [],
        "patch_items": [],
        "add_items": [{"slot_id": "S004", "task": "최종 점검"}],
        "remove_slot_ids": [],
        "requires_confirmation": True,
    }

    result = validate_api_multiturn_plan_output(case, 2, parsed, previous)

    payload = result["rule_based_db_payload"]
    assert result["contract"]["operation_effect_valid"] is True
    assert payload["operation"] == "add"
    assert payload["mutations"]["add"] == [
        {
            "slot_id": "S004",
            "goal_id_required": True,
            "milestone": {
                "title": payload["milestones"][-1]["title"],
                "color": case.input.initial_goal.color,
                "scheduled_date": payload["milestones"][-1]["scheduled_date"],
            },
        }
    ]


def test_validation_allows_add_to_exceed_case_max_milestone_count():
    case = load_mileday_multiturn_cases("tests/fixtures/mileday/test_api.json")[3]
    previous = {
        "plan_items": [
            {"slot_id": "S001", "task": "실제 작성 작업"},
            {"slot_id": "S002", "task": "실제 작성 작업"},
            {"slot_id": "S003", "task": "자료 확인"},
            {"slot_id": "S004", "task": "실제 작성 작업"},
            {"slot_id": "S005", "task": "실제 작성 작업"},
            {"slot_id": "S050", "task": "실제 작성 작업"},
        ],
        "db_payload": {"milestones": []},
    }
    parsed = {
        "action": "partial_update",
        "intent": {"action": "partial_update", "operation": "add"},
        "plan_items": [],
        "patch_items": [],
        "add_items": [{"slot_id": "S006", "task": "참고문헌 정리"}],
        "remove_slot_ids": [],
        "requires_confirmation": True,
    }

    result = validate_api_multiturn_plan_output(case, 2, parsed, previous)

    assert result["contract"]["operation_effect_valid"] is True
    assert result["schedule_quality"]["milestone_count_valid"] is True
    assert "milestone_count_valid" not in result["deterministic_validation"]["failed_check_names"]


def test_validation_rejects_add_outside_preserve_weekday_scope():
    case = load_mileday_multiturn_cases("tests/fixtures/mileday/test_api.json")[5]
    previous = {
        "plan_items": [{"slot_id": "S002", "task": "독서 진행"}],
        "db_payload": {"milestones": []},
    }
    parsed = {
        "action": "partial_update",
        "intent": {
            "action": "partial_update",
            "operation": "add",
            "preserve_selector": {"type": "weekday", "values": ["sunday"]},
        },
        "plan_items": [],
        "patch_items": [],
            "add_items": [{"slot_id": "S004", "task": "독서 메모 정리"}],
        "remove_slot_ids": [],
        "requires_confirmation": True,
    }

    result = validate_api_multiturn_plan_output(case, 2, parsed, previous)

    assert result["contract"]["add_preserve_scope_valid"] is False
    assert "PRESERVE_SCOPE_VIOLATION" in result["deterministic_validation"]["failure_codes"]


def test_validation_builds_rename_mutation_payload():
    case = load_mileday_multiturn_cases("tests/fixtures/mileday/multiturn_schedule.pretty.json")[0]
    previous = {
        "plan_items": [
            {"slot_id": "S001", "task": "기초 정리"},
            {"slot_id": "S002", "task": "문제 풀이"},
            {"slot_id": "S003", "task": "오답 복습"},
        ],
        "db_payload": {"milestones": []},
    }
    parsed = {
        "action": "partial_update",
        "plan_items": [],
        "patch_items": [{"slot_id": "S002", "task": "심화 문제 풀이"}],
        "add_items": [],
        "remove_slot_ids": [],
        "requires_confirmation": True,
    }

    result = validate_api_multiturn_plan_output(case, 2, parsed, previous)

    payload = result["rule_based_db_payload"]
    assert payload["operation"] == "rename"
    assert payload["mutations"]["rename"][0]["slot_id"] == "S002"
    assert payload["mutations"]["rename"][0]["milestone_id_required"] is True


def test_validation_records_mutation_safety_check_mismatch_without_failing():
    case = load_mileday_multiturn_cases("tests/fixtures/mileday/test_api.json")[0]
    previous = {
        "plan_items": [
            {"slot_id": "S001", "task": "기초 정리"},
            {"slot_id": "S002", "task": "문제 풀이"},
            {"slot_id": "S003", "task": "오답 복습"},
        ],
        "db_payload": {"milestones": []},
    }
    parsed = {
        "action": "partial_update",
        "intent": {"mutation_safety_check": "no_target_matched"},
        "plan_items": [],
        "patch_items": [],
        "add_items": [{"slot_id": "S004", "task": "최종 점검"}],
        "remove_slot_ids": [],
        "requires_confirmation": True,
    }

    result = validate_api_multiturn_plan_output(case, 2, parsed, previous)

    assert result["errors"] == []
    assert result["state"]["mutation_safety_check"] == {
        "model": "no_target_matched",
        "actual": "single_target_matched",
        "matches": False,
    }


def test_validation_builds_no_op_payload_without_mutations():
    case = load_mileday_multiturn_cases("tests/fixtures/mileday/test_api.json")[14]
    previous = {
        "plan_items": [
            {"slot_id": "S001", "task": "회의 준비"},
            {"slot_id": "S002", "task": "역할 분담"},
            {"slot_id": "S003", "task": "최종 점검"},
        ],
        "db_payload": {"milestones": []},
    }
    parsed = {
        "action": "partial_update",
        "plan_items": [],
        "patch_items": [],
        "add_items": [],
        "remove_slot_ids": [],
        "requires_confirmation": True,
    }

    result = validate_api_multiturn_plan_output(case, 2, parsed, previous)

    payload = result["rule_based_db_payload"]
    assert payload["operation"] == "none"
    assert payload["mutations"]["no_op"] is True
    assert payload["mutations"]["add"] == []
    assert payload["mutations"]["remove"] == []
    assert payload["mutations"]["rename"] == []


def test_sql_preview_covers_add_remove_rename_and_none_operations():
    add_payload = {
        "operation": "add",
        "mutations": {
            "add": [
                {
                    "slot_id": "S003",
                    "milestone": {
                        "title": "[수 19:00-21:00] 오답 정리",
                        "color": "#4F46E5",
                        "scheduled_date": "2026-08-19",
                    },
                }
            ],
            "remove": [],
            "rename": [],
        },
    }
    remove_payload = {
        "operation": "remove",
        "mutations": {
            "add": [],
            "remove": [{"slot_id": "S002"}],
            "rename": [],
        },
    }
    rename_payload = {
        "operation": "rename",
        "mutations": {
            "add": [],
            "remove": [],
            "rename": [
                {
                    "slot_id": "S002",
                    "milestone": {"title": "[화 19:00-21:00] 심화 문제 풀이"},
                }
            ],
        },
    }
    none_payload = {"operation": "none", "mutations": {"add": [], "remove": [], "rename": []}}

    add_preview = build_insert_sql_preview(add_payload)
    remove_preview = build_insert_sql_preview(remove_payload)
    rename_preview = build_insert_sql_preview(rename_payload)
    none_preview = build_insert_sql_preview(none_payload)

    assert "INSERT INTO public.milestones" in add_preview
    assert ":goal_id" in add_preview
    assert "DELETE FROM public.milestones" in remove_preview
    assert "AND user_id = :user_id" in remove_preview
    assert "UPDATE public.milestones" in rename_preview
    assert "updated_at = now()" in rename_preview
    assert "No DB mutation" in none_preview
