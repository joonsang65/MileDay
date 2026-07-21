from harness.schemas import (
    EvaluationError,
    FailureCategory,
    RequestResult,
    ResultStatus,
    RuntimeMetrics,
)


def test_request_result_schema_matches_architecture_contract():
    result = RequestResult(
        run_id="run-001",
        model_id="model-a",
        dataset_id="dataset-a",
        case_id="case-001",
        status=ResultStatus.FAILED,
        parsed_output={"answer": "A"},
        metrics=RuntimeMetrics(ttft_ms=10, latency_ms=100, tokens_per_second=12.5),
        error=EvaluationError(
            category=FailureCategory.PARSER_ERROR,
            message="Could not parse answer.",
        ),
    )

    payload = result.model_dump(mode="json")

    assert payload["status"] == "failed"
    assert payload["metrics"]["ttft_ms"] == 10
    assert payload["error"]["category"] == "PARSER_ERROR"


def test_failure_categories_include_shared_not_executed_category():
    assert FailureCategory.NOT_EXECUTED == "NOT_EXECUTED"

