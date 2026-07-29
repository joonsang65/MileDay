from __future__ import annotations

from collections.abc import Callable, Iterable
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from harness.performance.monitor import PeakPerformanceMetrics, PerformanceMonitor
from harness.runtime.base import RuntimeAdapter, RuntimeRequest, RuntimeResponse
from harness.schemas import RequestResult, ResultStatus


class BenchmarkMode(StrEnum):
    COLD = "cold"
    WARM = "warm"


class ExecutionPhase(StrEnum):
    COLD_MEASURED = "cold_measured"
    WARMUP = "warmup"
    WARM_MEASURED = "warm_measured"


class BenchmarkCasePrompt(BaseModel):
    model_config = ConfigDict(frozen=True)

    dataset_id: str
    case_id: str
    prompt: str
    parsed_output: dict[str, object] = Field(default_factory=dict)


class BenchmarkRunConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str
    model_id: str
    model_tag: str
    mode: BenchmarkMode = BenchmarkMode.COLD
    warmup_iterations: int = Field(default=1, ge=0)
    response_format: str | dict[str, object] | None = None
    runtime_options: dict[str, object] = Field(default_factory=dict)
    timeout_seconds: int = Field(default=120, gt=0)


class BenchmarkExecutionRecord(BaseModel):
    phase: ExecutionPhase
    request_result: RequestResult
    response: RuntimeResponse
    performance_summary: PeakPerformanceMetrics
    counted_for_resume: bool


def run_benchmark_cases(
    cases: Iterable[BenchmarkCasePrompt],
    config: BenchmarkRunConfig,
    runtime: RuntimeAdapter,
    *,
    monitor_factory: Callable[[], PerformanceMonitor],
    completed_resume_keys: set[tuple[str, str, str, str]] | None = None,
) -> list[BenchmarkExecutionRecord]:
    records: list[BenchmarkExecutionRecord] = []
    completed = completed_resume_keys or set()
    for case in cases:
        resume_key = (config.run_id, config.model_id, case.dataset_id, case.case_id)
        if resume_key in completed:
            continue
        if config.mode == BenchmarkMode.WARM:
            for _ in range(config.warmup_iterations):
                records.append(_execute_case(case, config, runtime, monitor_factory, ExecutionPhase.WARMUP))
            records.append(_execute_case(case, config, runtime, monitor_factory, ExecutionPhase.WARM_MEASURED))
        else:
            records.append(_execute_case(case, config, runtime, monitor_factory, ExecutionPhase.COLD_MEASURED))
    return records


def measured_records(records: Iterable[BenchmarkExecutionRecord]) -> list[BenchmarkExecutionRecord]:
    return [record for record in records if record.counted_for_resume]


def _execute_case(
    case: BenchmarkCasePrompt,
    config: BenchmarkRunConfig,
    runtime: RuntimeAdapter,
    monitor_factory: Callable[[], PerformanceMonitor],
    phase: ExecutionPhase,
) -> BenchmarkExecutionRecord:
    monitor = monitor_factory()
    response = runtime.generate(
        RuntimeRequest(
            model_tag=config.model_tag,
            prompt=case.prompt,
            response_format=config.response_format,
            options=config.runtime_options,
            timeout_seconds=config.timeout_seconds,
        )
    )
    samples = monitor.sample_for(0)
    status = ResultStatus.FAILED if response.error is not None else ResultStatus.PASSED
    counted = phase != ExecutionPhase.WARMUP
    result = RequestResult(
        run_id=config.run_id,
        model_id=config.model_id,
        dataset_id=case.dataset_id,
        case_id=case.case_id,
        status=status,
        parsed_output={
            **case.parsed_output,
            "phase": phase.value,
            "warmup": phase == ExecutionPhase.WARMUP,
        },
        metrics=response.metrics,
        error=response.error,
    )
    return BenchmarkExecutionRecord(
        phase=phase,
        request_result=result,
        response=response,
        performance_summary=PerformanceMonitor.summarize(samples),
        counted_for_resume=counted,
    )
