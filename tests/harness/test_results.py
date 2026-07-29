import json

from harness.performance.monitor import PerformanceSample
from harness.results import ResultStore, ResultStoreError
from harness.schemas import (
    EvaluationError,
    FailureCategory,
    RequestResult,
    ResultStatus,
    RuntimeMetrics,
)


def _result(tmp_path, status=ResultStatus.PASSED, raw_output_path=None):
    return RequestResult(
        run_id="run-1",
        model_id="model:1",
        dataset_id="mileday/schedule",
        case_id="case 1",
        status=status,
        raw_output_path=raw_output_path,
        parsed_output={"score": 1.0},
        metrics=RuntimeMetrics(ttft_ms=10, latency_ms=100, tokens_per_second=12.5),
    )


def test_raw_first_store_writes_deterministic_windows_safe_path(tmp_path):
    store = ResultStore(tmp_path / "runs")

    stored = store.store_request_result(_result(tmp_path), raw_output="raw model output")

    assert stored.raw_output_path is not None
    assert stored.raw_output_path.exists()
    assert "model-1__mileday-schedule__case-1.txt" in str(stored.raw_output_path)
    assert (store.run_dir("run-1") / "parsed" / "results.jsonl").exists()
    assert (store.run_dir("run-1") / "parsed" / "results.pretty.json").exists()


def test_append_behavior_and_resume_lookup(tmp_path):
    store = ResultStore(tmp_path / "runs")
    store.store_request_result(_result(tmp_path), raw_output="raw")
    invalid = _result(tmp_path, status=ResultStatus.INVALID)
    invalid = invalid.model_copy(update={"case_id": "case-2"})
    store.store_request_result(invalid, raw_output="bad raw")

    loaded = store.load_request_results("run-1")
    index = store.resume_index("run-1")

    assert len(loaded) == 2
    assert ("run-1", "model:1", "mileday/schedule", "case 1") in index
    assert store.is_completed("run-1", "model:1", "mileday/schedule", "case-2") is True

    pretty_path = store.run_dir("run-1") / "parsed" / "results.pretty.json"
    pretty = json.loads(pretty_path.read_text(encoding="utf-8"))
    assert len(pretty) == 2
    assert pretty[0]["case_id"] == "case 1"
    assert "\n  {" in pretty_path.read_text(encoding="utf-8")


def test_failed_result_is_stored_with_error(tmp_path):
    store = ResultStore(tmp_path / "runs")
    failed = _result(tmp_path, status=ResultStatus.FAILED).model_copy(
        update={
            "error": EvaluationError(
                category=FailureCategory.TIMEOUT,
                message="timed out",
            )
        }
    )

    store.store_request_result(failed, raw_output="")

    loaded = store.load_request_results("run-1")
    assert loaded[0].status == ResultStatus.FAILED
    assert loaded[0].error is not None
    assert loaded[0].error.category == FailureCategory.TIMEOUT


def test_missing_raw_output_path_is_rejected(tmp_path):
    store = ResultStore(tmp_path / "runs")
    result = _result(tmp_path, raw_output_path=tmp_path / "missing.txt")

    try:
        store.append_request_result(result)
    except ResultStoreError as exc:
        assert exc.category == FailureCategory.CODE_ERROR
    else:
        raise AssertionError("Expected missing raw path to fail")


def test_config_snapshot_and_performance_samples_are_written(tmp_path):
    store = ResultStore(tmp_path / "runs")
    config_path = store.write_config_snapshot("run-1", {"model": "candidate-1"})
    metrics_path = store.append_performance_samples(
        "run-1",
        [
            PerformanceSample(
                timestamp_s=1,
                cpu_percent=10,
                ram_used_bytes=100,
                ram_percent=20,
                ollama_rss_bytes=None,
                vram_used_bytes=None,
                vram_total_bytes=None,
                vram_status="unavailable",
            )
        ],
        phase="warm_measured",
    )

    assert config_path.exists()
    assert metrics_path.exists()
    assert "warm_measured" in metrics_path.read_text(encoding="utf-8")
