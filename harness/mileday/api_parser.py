from __future__ import annotations

from typing import Any

from harness.mileday.api_constants import (
    MILEDAY_API_MULTITURN_PROMPT_VERSION,
    MILEDAY_MULTITURN_FIXTURE,
    MILEDAY_MULTITURN_PROMPT_VERSION,
)
from harness.mileday.api_intent import (
    extract_schedule_intent_block,
    fallback_schedule_intent,
    parse_schedule_intent_json,
    parse_schedule_intent_block,
)
from harness.mileday.api_plan_builder import (
    apply_plan_patch,
    build_add_items,
    build_patch_items,
    build_plan_items,
    build_remove_slot_ids,
    build_rule_based_user_message,
)
from harness.mileday.api_validation import validate_api_multiturn_plan_output
from harness.mileday.dataset import MileDayMultiTurnCase
from harness.mileday.explanation_judge import ExplanationJudge, skipped_explanation_judge_result
from harness.schemas import EvaluationError, FailureCategory, RequestResult, ResultStatus


def evaluate_api_multiturn_record(
    base_result: RequestResult,
    case: MileDayMultiTurnCase,
    turn_id: int,
    raw_output: str,
    *,
    previous_parsed: dict[str, Any] | None,
    explanation_judge: ExplanationJudge | None,
    prompt_version: str = MILEDAY_API_MULTITURN_PROMPT_VERSION,
    run_judge: bool = True,
) -> RequestResult:
    if base_result.error is not None:
        return base_result

    turn = case.turns[turn_id - 1]
    json_intent, json_parse_errors = parse_schedule_intent_json(raw_output)
    intent_block = None if json_intent is not None and not json_parse_errors else extract_schedule_intent_block(raw_output)
    contract: dict[str, Any] = {
        "type": "mileday_multiturn_intent_with_rule_based_payload",
        "structured_json_used": json_intent is not None and not json_parse_errors,
        "structured_json_parseable": json_intent is not None and not json_parse_errors,
        "has_schedule_intent_section": "[SCHEDULE_INTENT]" in raw_output or "[??_??]" in raw_output,
        "has_schedule_intent_end": "[/SCHEDULE_INTENT]" in raw_output or "[/??_??]" in raw_output,
        "intent_parseable": False,
        "required_fields_present": False,
        "db_payload_schema_valid": False,
        "requires_confirmation_valid": False,
    }
    base_metadata = {
        **base_result.parsed_output,
        "evaluation_family": "mileday_multiturn",
        "case_id": case.case_id,
        "turn_id": turn_id,
        "turn_count": len(case.turns),
        "expected_action": turn.expected_action,
        "prompt_version": prompt_version,
        "output_contract": contract,
    }

    if json_intent is not None and not json_parse_errors:
        intent = json_intent
        parse_errors = []
        contract["freeform_fallback_used"] = False
    elif intent_block is None:
        intent = fallback_schedule_intent(case, turn_id, raw_output)
        if intent is None:
            return _invalid_mileday_result(
                base_result,
                parsed_output={
                    **base_metadata,
                    "contract_errors": ["Missing JSON intent object or [SCHEDULE_INTENT] section."],
                    "json_parse_errors": json_parse_errors,
                },
                message="MileDay multiturn output must contain a JSON schedule intent object or the expected schedule intent block.",
            )
        parse_errors = []
        contract["freeform_fallback_used"] = True
    else:
        intent, parse_errors = parse_schedule_intent_block(intent_block)
        contract["freeform_fallback_used"] = False

    if parse_errors:
        has_invalid_explicit_action = bool(intent.get("action")) and any(
            "action must be create or partial_update." == error for error in parse_errors
        )
        if has_invalid_explicit_action:
            return _invalid_mileday_result(
                base_result,
                parsed_output={**base_metadata, "intent_parse_errors": parse_errors, "raw_intent": intent},
                message="MileDay multiturn SCHEDULE_INTENT block was not parseable.",
            )
        fallback_intent = fallback_schedule_intent(case, turn_id, raw_output)
        if fallback_intent is None:
            return _invalid_mileday_result(
                base_result,
                parsed_output={**base_metadata, "intent_parse_errors": parse_errors, "raw_intent": intent},
                message="MileDay multiturn SCHEDULE_INTENT block was not parseable.",
            )
        intent = fallback_intent
        contract["freeform_fallback_used"] = True
    else:
        contract.setdefault("freeform_fallback_used", False)

    contract["intent_parseable"] = True
    if turn.expected_action == "create":
        plan_items = build_plan_items(case, intent)
        patch_items: list[dict[str, str]] = []
        remove_slot_ids: list[str] = []
        add_items: list[dict[str, str]] = []
    else:
        patch_items = build_patch_items(case, turn_id, intent, previous_parsed)
        remove_slot_ids = build_remove_slot_ids(case, turn_id, intent, previous_parsed)
        add_items = build_add_items(case, turn_id, intent, previous_parsed)
        previous_plan_items = previous_parsed.get("plan_items") if isinstance(previous_parsed, dict) else []
        plan_items = apply_plan_patch(previous_plan_items if isinstance(previous_plan_items, list) else [], patch_items)
        if remove_slot_ids:
            plan_items = [item for item in plan_items if item.get("slot_id") not in set(remove_slot_ids)]
        plan_items.extend(add_items)

    parsed = {
        "action": turn.expected_action,
        "intent": intent,
        "freeform_fallback_used": bool(contract.get("freeform_fallback_used")),
        "user_message": "",
        "plan_items": plan_items,
        "patch_items": patch_items,
        "remove_slot_ids": remove_slot_ids,
        "add_items": add_items,
        "requires_confirmation": True,
    }
    validation = validate_api_multiturn_plan_output(case, turn_id, parsed, previous_parsed)
    contract.update(validation["contract"])
    parsed_for_judge = validation.get("effective_parsed_json", parsed)
    user_message = build_rule_based_user_message(case, turn_id, parsed_for_judge, previous_parsed)
    if isinstance(parsed_for_judge, dict):
        parsed_for_judge = {**parsed_for_judge, "user_message": user_message}
    parsed_output = {
        **base_metadata,
        "output_contract": contract,
        "explanation": user_message,
        "user_message": user_message,
        "parsed_json": parsed_for_judge,
        "raw_intent": intent,
        "raw_parsed_json": parsed,
        "multiturn_validation": validation,
        "semantic_score": validation["local_score"],
    }
    if validation["errors"]:
        failed_check_names = validation["deterministic_validation"]["failed_check_names"]
        failed_check_text = ", ".join(failed_check_names) if failed_check_names else "unknown"
        return _invalid_mileday_result(
            base_result,
            parsed_output=parsed_output,
            message=f"MileDay multiturn deterministic validation failed: {failed_check_text}.",
        )

    if not run_judge:
        skipped_judge = skipped_explanation_judge_result().model_dump(mode="json")
        skipped_judge["reason"] = "Turn-level judge skipped; accumulated case output will be judged once per case."
        skipped_judge["judge_scope"] = "case_pending"
        return base_result.model_copy(
            update={
                "status": ResultStatus.PASSED,
                "parsed_output": {
                    **parsed_output,
                    "judge_scope": "case_pending",
                    "explanation_judge": skipped_judge,
                },
            }
        )

    if explanation_judge is None:
        dependency_error = EvaluationError(
            category=FailureCategory.EXTERNAL_DEPENDENCY,
            message="Gemini multiturn judge is required but GEMINI_API_KEY is not configured.",
        )
        return base_result.model_copy(
            update={
                "status": ResultStatus.FAILED,
                "parsed_output": {
                    **parsed_output,
                    "explanation_judge": {
                        **skipped_explanation_judge_result().model_dump(mode="json"),
                        "error": dependency_error.model_dump(mode="json"),
                    },
                },
                "error": dependency_error,
            }
        )

    evaluate_multiturn = getattr(explanation_judge, "evaluate_multiturn", None)
    if evaluate_multiturn is None:
        dependency_error = EvaluationError(
            category=FailureCategory.CODE_ERROR,
            message="Configured explanation judge does not support MileDay multiturn evaluation.",
        )
        return base_result.model_copy(
            update={
                "status": ResultStatus.FAILED,
                "parsed_output": {
                    **parsed_output,
                    "explanation_judge": {
                        **skipped_explanation_judge_result().model_dump(mode="json"),
                        "error": dependency_error.model_dump(mode="json"),
                    },
                },
                "error": dependency_error,
            }
        )

    judge_result = evaluate_multiturn(case, turn_id, user_message, parsed_for_judge, previous_parsed)
    parsed_output["explanation_judge"] = judge_result.model_dump(mode="json")
    if judge_result.error is not None:
        return base_result.model_copy(
            update={
                "status": ResultStatus.FAILED,
                "parsed_output": parsed_output,
                "error": judge_result.error,
            }
        )
    if not judge_result.is_aligned:
        return _invalid_mileday_result(
            base_result,
            parsed_output=parsed_output,
            message="MileDay multiturn judge rejected the response.",
        )
    return base_result.model_copy(update={"status": ResultStatus.PASSED, "parsed_output": parsed_output})


def _invalid_mileday_result(
    base_result: RequestResult,
    *,
    parsed_output: dict[str, object],
    message: str,
) -> RequestResult:
    return base_result.model_copy(
        update={
            "status": ResultStatus.INVALID,
            "parsed_output": parsed_output,
            "error": EvaluationError(
                category=FailureCategory.PARSER_ERROR,
                message=message,
            ),
        }
    )
