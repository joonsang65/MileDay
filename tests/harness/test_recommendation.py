from harness.recommendation import render_recommendation_markdown, summarize_recommendation
from harness.results import ResultStore
from harness.schemas import EvaluationError, FailureCategory, RequestResult, ResultStatus, RuntimeMetrics


def _add_model(
    store,
    model_id,
    *,
    run_id="run-rec",
    public_score=0.8,
    mileday_semantic=0.8,
    latency=100,
    ttft=10,
    tps=20,
    mileday_status=ResultStatus.PASSED,
    public_status=ResultStatus.PASSED,
    public_error=None,
    mileday_error=None,
):
    metrics = RuntimeMetrics(ttft_ms=ttft, latency_ms=latency, tokens_per_second=tps)
    public = RequestResult(
        run_id=run_id,
        model_id=model_id,
        dataset_id="kmmlu-pro",
        case_id="public-1",
        status=public_status,
        parsed_output={"score": public_score},
        metrics=metrics,
        error=public_error,
    )
    mileday = RequestResult(
        run_id=run_id,
        model_id=model_id,
        dataset_id="mileday-schedule",
        case_id="mileday-1",
        status=mileday_status,
        parsed_output={"validation": {"is_valid": mileday_status == ResultStatus.PASSED}, "semantic_score": mileday_semantic},
        metrics=metrics,
        error=mileday_error,
    )
    store.store_request_result(public, raw_output=f"{model_id} public")
    store.store_request_result(mileday, raw_output=f"{model_id} mileday")


def test_recommendation_selects_clear_winner_with_traceable_evidence(tmp_path):
    store = ResultStore(tmp_path / "runs")
    _add_model(store, "model-a", public_score=0.7, mileday_semantic=0.7)
    _add_model(store, "model-b", public_score=0.9, mileday_semantic=0.9)

    summary = summarize_recommendation("run-rec", tmp_path / "runs")
    text = "\n".join(render_recommendation_markdown(summary))

    assert summary.status == "recommended"
    assert summary.recommended_model_id == "model-b"
    assert "run-rec" in text
    assert "model-b__kmmlu-pro__public-1.txt" in text


def test_recommendation_returns_insufficient_data_for_empty_run(tmp_path):
    summary = summarize_recommendation("missing-run", tmp_path / "runs")

    assert summary.status == "insufficient_data"
    assert summary.recommended_model_id is None


def test_recommendation_blocks_missing_mileday_results(tmp_path):
    store = ResultStore(tmp_path / "runs")
    result = RequestResult(
        run_id="run-rec",
        model_id="model-a",
        dataset_id="kmmlu-pro",
        case_id="public-1",
        status=ResultStatus.PASSED,
        parsed_output={"score": 1.0},
        metrics=RuntimeMetrics(ttft_ms=10, latency_ms=100, tokens_per_second=20),
    )
    store.store_request_result(result, raw_output="raw")

    summary = summarize_recommendation("run-rec", tmp_path / "runs")

    assert summary.status == "no_recommendation"
    assert "MileDay deterministic 근거 없음" in summary.model_evidence[0].blocked_reasons


def test_recommendation_blocks_missing_performance_metrics(tmp_path):
    store = ResultStore(tmp_path / "runs")
    _add_model(store, "model-a", latency=None, ttft=None, tps=None)

    summary = summarize_recommendation("run-rec", tmp_path / "runs")

    assert summary.status == "no_recommendation"
    assert "성능 metric 없음" in summary.model_evidence[0].blocked_reasons


def test_recommendation_blocks_high_invalid_rate(tmp_path):
    store = ResultStore(tmp_path / "runs")
    _add_model(
        store,
        "model-a",
        mileday_status=ResultStatus.INVALID,
        mileday_error=EvaluationError(category=FailureCategory.PARSER_ERROR, message="invalid"),
    )

    summary = summarize_recommendation("run-rec", tmp_path / "runs")

    assert summary.status == "no_recommendation"
    assert "invalid rate gate 실패" in summary.model_evidence[0].blocked_reasons


def test_recommendation_blocks_failed_model_runs(tmp_path):
    store = ResultStore(tmp_path / "runs")
    _add_model(
        store,
        "model-a",
        public_status=ResultStatus.FAILED,
        public_error=EvaluationError(category=FailureCategory.TIMEOUT, message="timeout"),
    )

    summary = summarize_recommendation("run-rec", tmp_path / "runs")

    assert summary.status == "no_recommendation"
    assert "failure rate gate 실패" in summary.model_evidence[0].blocked_reasons


def test_recommendation_tie_handling_is_deterministic(tmp_path):
    store = ResultStore(tmp_path / "runs")
    _add_model(store, "model-b", public_score=0.8, mileday_semantic=0.8)
    _add_model(store, "model-a", public_score=0.8, mileday_semantic=0.8)

    first = summarize_recommendation("run-rec", tmp_path / "runs")
    second = summarize_recommendation("run-rec", tmp_path / "runs")

    assert first == second
    assert first.status == "no_recommendation"
    assert first.tied_model_ids == ("model-a", "model-b")
