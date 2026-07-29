from harness.orchestrator import (
    BenchmarkCasePrompt,
    BenchmarkMode,
    BenchmarkRunConfig,
    ExecutionPhase,
    measured_records,
    run_benchmark_cases,
)
from harness.performance.monitor import PerformanceMonitor
from harness.runtime.base import RuntimeResponse
from harness.schemas import EvaluationError, FailureCategory, RuntimeMetrics


class MockRuntime:
    def __init__(self, error=None):
        self.error = error
        self.calls = 0
        self.requests = []

    def stream(self, request):
        return iter(())

    def generate(self, request):
        self.calls += 1
        self.requests.append(request)
        return RuntimeResponse(
            model_tag=request.model_tag,
            text="output",
            metrics=RuntimeMetrics(ttft_ms=5, latency_ms=50, tokens_per_second=10),
            error=self.error,
        )


def _monitor():
    return PerformanceMonitor(
        system_sampler=lambda: (1.0, 100, 10.0),
        ollama_rss_sampler=lambda process_name: None,
        vram_sampler=lambda: ("disabled", None, None, None),
    )


def _case():
    return BenchmarkCasePrompt(
        dataset_id="mileday-schedule",
        case_id="case-1",
        prompt="Generate milestones.",
    )


def test_cold_mode_runs_one_measured_record():
    records = run_benchmark_cases(
        [_case()],
        BenchmarkRunConfig(run_id="run-1", model_id="candidate-1", model_tag="local", mode=BenchmarkMode.COLD),
        MockRuntime(),
        monitor_factory=_monitor,
    )

    assert [record.phase for record in records] == [ExecutionPhase.COLD_MEASURED]
    assert records[0].counted_for_resume is True
    assert records[0].request_result.parsed_output["phase"] == "cold_measured"


def test_warm_mode_separates_warmup_from_measured_metrics():
    runtime = MockRuntime()

    records = run_benchmark_cases(
        [_case()],
        BenchmarkRunConfig(
            run_id="run-1",
            model_id="candidate-1",
            model_tag="local",
            mode=BenchmarkMode.WARM,
            warmup_iterations=2,
        ),
        runtime,
        monitor_factory=_monitor,
    )

    assert runtime.calls == 3
    assert [record.phase for record in records] == [
        ExecutionPhase.WARMUP,
        ExecutionPhase.WARMUP,
        ExecutionPhase.WARM_MEASURED,
    ]
    assert len(measured_records(records)) == 1
    assert records[0].counted_for_resume is False


def test_resume_skips_completed_measured_case_not_warmup_only_records():
    completed = {("run-1", "candidate-1", "mileday-schedule", "case-1")}

    records = run_benchmark_cases(
        [_case()],
        BenchmarkRunConfig(run_id="run-1", model_id="candidate-1", model_tag="local", mode=BenchmarkMode.WARM),
        MockRuntime(),
        monitor_factory=_monitor,
        completed_resume_keys=completed,
    )

    assert records == []


def test_runtime_failures_are_categorized_without_fabricated_metrics():
    error = EvaluationError(category=FailureCategory.OLLAMA_UNAVAILABLE, message="offline")

    records = run_benchmark_cases(
        [_case()],
        BenchmarkRunConfig(run_id="run-1", model_id="candidate-1", model_tag="local"),
        MockRuntime(error=error),
        monitor_factory=_monitor,
    )

    assert records[0].request_result.status == "failed"
    assert records[0].request_result.error is not None
    assert records[0].request_result.error.category == FailureCategory.OLLAMA_UNAVAILABLE


def test_run_config_passes_optional_response_format_and_runtime_options():
    runtime = MockRuntime()

    run_benchmark_cases(
        [_case()],
        BenchmarkRunConfig(
            run_id="run-1",
            model_id="candidate-1",
            model_tag="local",
            response_format="json",
            runtime_options={"temperature": 0},
        ),
        runtime,
        monitor_factory=_monitor,
    )

    assert runtime.requests[0].response_format == "json"
    assert runtime.requests[0].options == {"temperature": 0}
