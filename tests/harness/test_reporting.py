from harness.reporting import generate_markdown_report
from harness.results import ResultStore
from harness.schemas import EvaluationError, FailureCategory, RequestResult, ResultStatus, RuntimeMetrics


def _stored_result(
    store,
    *,
    run_id="run-report",
    model_id="model-a",
    dataset_id="kmmlu-pro",
    case_id="case-1",
    status=ResultStatus.PASSED,
    parsed_output=None,
    metrics=None,
    error=None,
    raw_output="raw output",
):
    result = RequestResult(
        run_id=run_id,
        model_id=model_id,
        dataset_id=dataset_id,
        case_id=case_id,
        status=status,
        parsed_output=parsed_output or {"score": 1.0},
        metrics=metrics or RuntimeMetrics(ttft_ms=10, latency_ms=100, tokens_per_second=20),
        error=error,
    )
    return store.store_request_result(result, raw_output=raw_output)


def test_report_covers_complete_results_with_separated_families_and_raw_links(tmp_path):
    store = ResultStore(tmp_path / "runs")
    _stored_result(store)
    _stored_result(
        store,
        dataset_id="mileday-schedule",
        case_id="case-2",
        parsed_output={"validation": {"is_valid": True}, "semantic_score": 0.8},
    )
    store.append_performance_samples(
        "run-report",
        [{"peak_cpu_percent": 50, "peak_ram_used_bytes": 1000, "peak_vram_used_bytes": 200, "vram_status": "ok"}],
    )

    path = generate_markdown_report("run-report", tmp_path / "runs")
    text = path.read_text(encoding="utf-8")

    assert path.name == "report.md"
    assert "공개 benchmark 결과: 1" in text
    assert "MileDay 생성 결과: 1" in text
    assert "Raw Artifact 참조" in text
    assert "raw output" not in text
    assert "Resource sample 수: 1" in text


def test_report_marks_missing_metrics_without_inference(tmp_path):
    store = ResultStore(tmp_path / "runs")
    _stored_result(store, metrics=RuntimeMetrics())

    text = generate_markdown_report("run-report", tmp_path / "runs").read_text(encoding="utf-8")

    assert "평균 latency ms" in text
    assert "| model-a | 1 | 1 | 0 | 0 | 0 | 1.000 | 없음 | 없음 | 없음 | 없음 | 없음 |" in text
    assert "Resource metric: 없음" in text


def test_report_analyzes_invalid_and_failed_results(tmp_path):
    store = ResultStore(tmp_path / "runs")
    _stored_result(
        store,
        status=ResultStatus.INVALID,
        error=EvaluationError(category=FailureCategory.PARSER_ERROR, message="bad json"),
    )
    _stored_result(
        store,
        model_id="model-b",
        case_id="case-2",
        status=ResultStatus.FAILED,
        error=EvaluationError(category=FailureCategory.TIMEOUT, message="timeout"),
    )

    text = generate_markdown_report("run-report", tmp_path / "runs").read_text(encoding="utf-8")

    assert "Invalid 출력: PARSER_ERROR=1" in text
    assert "Failed 출력: TIMEOUT=1" in text


def test_report_handles_partial_run_without_model_or_dataset_fabrication(tmp_path):
    path = generate_markdown_report("empty-run", tmp_path / "runs")
    text = path.read_text(encoding="utf-8")

    assert "저장된 request result가 없습니다: 미실행." in text
    assert "모델 요약" not in text


def test_report_output_is_deterministic_for_same_input(tmp_path):
    store = ResultStore(tmp_path / "runs")
    _stored_result(store, model_id="model-b")
    _stored_result(store, model_id="model-a", case_id="case-2")

    first = generate_markdown_report("run-report", tmp_path / "runs").read_text(encoding="utf-8")
    second = generate_markdown_report("run-report", tmp_path / "runs").read_text(encoding="utf-8")

    assert first == second
