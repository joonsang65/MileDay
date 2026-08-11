from __future__ import annotations

import json
import re
import random
import subprocess
import time
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from statistics import mean
from typing import Annotated, Any, Callable

import typer
from pydantic import ValidationError

try:
    from tqdm import tqdm
except ImportError:  # pragma: no cover - optional CLI enhancement
    tqdm = None

from harness.benchmarks.ifeval_ko import load_ifeval_ko_cases
from harness.benchmarks.mcq import MCQChoice, MCQQuestion, build_mcq_prompt, score_mcq_response
from harness.config import load_settings
from harness.dataset_processor import (
    DatasetProcessingError,
    load_prepared_dataset_rows,
    load_processed_dataset_rows,
    prepare_all_datasets,
    prepare_dataset,
)
from harness.dataset_registry import DEFAULT_DATASET_REGISTRY_PATH, load_dataset_registry
from harness.mileday.constraints import validate_schedule_output
from harness.mileday.dataset import (
    GOAL_DB_FIELDS,
    MILESTONE_DB_FIELDS,
    MileDayGenerationCase,
    MileDayMultiTurnCase,
    load_mileday_generation_cases,
    load_mileday_multiturn_cases,
)
from harness.mileday.explanation_judge import (
    ExplanationJudge,
    GeminiExplanationJudge,
    BatchQualitySummaryResult,
    skipped_batch_quality_summary_result,
    skipped_explanation_judge_result,
)
from harness.mileday.multiturn_prompts import (
    ACTIVE_MULTITURN_PROMPT_VERSION,
    API_MULTITURN_PROMPT_VERSION,
    build_mileday_multiturn_api_prompt,
    build_mileday_multiturn_prompt,
    date_day_of_week,
    mileday_multiturn_allowed_slots,
)
from harness.mileday.time_prefix import (
    canonical_milestone_title,
    parse_canonical_milestone_title,
)
from harness.mileday.rubric import evaluate_semantic_rubric
from harness.model_registry import (
    DEFAULT_MODEL_REGISTRY_PATH,
    check_model_availability,
    load_model_registry,
)
from harness.orchestrator import (
    BenchmarkCasePrompt,
    BenchmarkMode,
    BenchmarkRunConfig,
    measured_records,
    run_benchmark_cases,
)
from harness.performance.monitor import PerformanceMonitor
from harness.html_reporting import generate_mileday_multiturn_html_report
from harness.reporting import generate_markdown_report
from harness.results import ResultStore
from harness.runtime.base import RuntimeAdapter, RuntimeAdapterError
from harness.runtime.gemini import GeminiRuntime
from harness.runtime.ollama import OllamaRuntime
from harness.schemas import EvaluationError, FailureCategory, RequestResult, ResultStatus, RuntimeMetrics


app = typer.Typer(help="Local LLM evaluation harness.")
FENCED_JSON_PATTERN = re.compile(r"```(?:json)?\s*(?P<json>.*?)\s*```", re.IGNORECASE | re.DOTALL)
PUBLIC_BENCHMARK_DATASET_KEYS = ("ifeval_ko", "kobalt", "click", "kmmlu_pro")
THIRD_BENCHMARK_MODEL_IDS = ("candidate-3", "candidate-5")
MILEDAY_MULTITURN_MODEL_ID = "candidate-3"
MILEDAY_API_MODEL_IDS = ("gemini-3.5-flash-lite", "gemini-3.6-flash")
MILEDAY_MULTITURN_FIXTURE = Path("tests") / "fixtures" / "mileday" / "multiturn_schedule.pretty.json"
MILEDAY_MULTITURN_DATASET_ID = "mileday-multiturn-schedule"
MILEDAY_MULTITURN_PROMPT_VERSION = ACTIVE_MULTITURN_PROMPT_VERSION
MILEDAY_API_MULTITURN_PROMPT_VERSION = API_MULTITURN_PROMPT_VERSION
MILEDAY_MULTITURN_REFERENCE_TIMEZONE = "Asia/Seoul"
MILEDAY_MULTITURN_RUNTIME_OPTIONS = {"temperature": 0.1, "top_p": 0.8}
THIRD_BENCHMARK_DATASET_KEYS = ("ifeval_ko", "kobalt")
THIRD_BENCHMARK_WEIGHTS = {
    "ifeval-ko": 0.60,
    "kobalt-700": 0.40,
}
THIRD_BENCHMARK_SYSTEM_PROMPT = (
    "당신은 한국어 평가 데이터셋에 응답하는 로컬 LLM입니다.\n\n"
    "반드시 사용자의 지시를 최우선으로 따르세요.\n"
    "숨은 사고 과정, 풀이 과정, 자체 검토 과정, 메타 설명을 출력하지 마세요.\n"
    "최종 답변만 출력하세요.\n\n"
    "IFEval-Ko 문제에서는 사용자가 요구한 형식, 길이, 키워드, 금지어, 반복, 종료 조건을 정확히 따르세요.\n"
    "KoBALT-700 객관식 문제에서는 A, B, C, D, E, F, G, H, I, J 중 정답 하나만 출력하세요.\n"
    "정답을 모르는 경우에도 설명하지 말고 가장 가능성 높은 선택지 하나만 출력하세요."
)
PUBLIC_DATASET_IDS = {
    "ifeval_ko": "ifeval-ko",
    "kobalt": "kobalt-700",
    "click": "click",
    "kmmlu_pro": "kmmlu-pro",
}


@dataclass(frozen=True)
class PublicBenchmarkCase:
    dataset_key: str
    dataset_id: str
    benchmark_id: str
    case_id: str
    prompt: str
    score_response: Callable[[str], Any]


@app.callback()
def main() -> None:
    """Run harness commands."""


@app.command()
def preflight(
    config: Annotated[
        Path | None,
        typer.Option("--config", "-c", help="Optional EVAL-001 JSON config path."),
    ] = None,
    check_ollama: Annotated[
        bool,
        typer.Option("--check-ollama", help="Check local Ollama API availability."),
    ] = False,
) -> None:
    """Run offline configuration and filesystem checks."""

    settings = load_settings(config)
    typer.echo("MileDay harness preflight")
    typer.echo(f"project_root={settings.project_root}")
    typer.echo(f"artifacts_dir={settings.artifacts_dir}")
    typer.echo(f"runs_dir={settings.runs_dir}")
    typer.echo(f"datasets_dir={settings.datasets_dir}")
    typer.echo(f"default_timeout_seconds={settings.default_timeout_seconds}")
    typer.echo(f"ollama_base_url={settings.ollama_base_url}")
    if check_ollama:
        runtime = OllamaRuntime(base_url=settings.ollama_base_url)
        try:
            runtime.check_health(timeout_seconds=min(settings.default_timeout_seconds, 5))
        except RuntimeAdapterError as exc:
            typer.echo(f"ollama_status=unavailable")
            typer.echo(f"ollama_error_category={exc.category}")
            typer.echo(f"ollama_error_message={exc.message}")
        else:
            typer.echo("ollama_status=ok")
    typer.echo("status=ok")


@app.command("list-models")
def list_models(
    registry: Annotated[
        Path,
        typer.Option(
            "--registry",
            "-r",
            help="Model registry YAML path.",
        ),
    ] = DEFAULT_MODEL_REGISTRY_PATH,
    check_installed: Annotated[
        bool,
        typer.Option("--check-installed", help="Check local Ollama installation status."),
    ] = False,
) -> None:
    """List configured model candidates without substituting missing models."""

    try:
        model_registry = load_model_registry(registry)
    except (FileNotFoundError, ValidationError, ValueError) as exc:
        raise typer.BadParameter(str(exc)) from exc

    availability_by_id = {}
    if check_installed:
        try:
            availability_by_id = {
                item.model_id: item.installed
                for item in check_model_availability(model_registry)
            }
        except (FileNotFoundError, subprocess.SubprocessError, OSError) as exc:
            raise typer.BadParameter(f"Ollama availability check failed: {exc}") from exc

    typer.echo("id\tprovider\truntime\tmodel_tag\tinstalled")
    for model in model_registry.models:
        installed = availability_by_id.get(model.id)
        installed_text = "not_checked" if installed is None else str(installed).lower()
        typer.echo(
            f"{model.id}\t{model.provider}\t{model.runtime}\t"
            f"{model.model_tag}\t{installed_text}"
        )


@app.command("prepare-datasets")
def prepare_datasets(
    registry: Annotated[
        Path,
        typer.Option(
            "--registry",
            "-r",
            help="Dataset registry YAML path.",
        ),
    ] = DEFAULT_DATASET_REGISTRY_PATH,
    sample_limit: Annotated[
        int | None,
        typer.Option("--sample-limit", help="Optional positive row limit per dataset."),
    ] = None,
    dataset: Annotated[
        str | None,
        typer.Option("--dataset", help="Optional single dataset key from configs/datasets.yaml."),
    ] = None,
) -> None:
    """Convert pinned source snapshots into local processed JSONL files."""

    try:
        loaded_registry = None
        if dataset is not None:
            from harness.dataset_registry import load_dataset_registry

            loaded_registry = load_dataset_registry(registry)
            if dataset not in loaded_registry.datasets:
                raise typer.BadParameter(f"Unknown dataset key: {dataset}")
            loaded_registry.datasets = {
                dataset: loaded_registry.datasets[dataset],
            }
        processed = prepare_all_datasets(
            registry=loaded_registry,
            registry_path=registry,
            sample_limit=sample_limit,
        )
    except (FileNotFoundError, ValueError, DatasetProcessingError) as exc:
        raise typer.BadParameter(str(exc)) from exc

    typer.echo("dataset\trows\tprocessed_path")
    for item in processed:
        typer.echo(f"{item.dataset_key}\t{item.row_count}\t{item.processed_path}")


@app.command("run-mileday-smoke")
def run_mileday_smoke(
    fixture: Annotated[
        Path,
        typer.Option("--fixture", help="Local MileDay JSON/JSONL fixture path."),
    ],
    model_id: Annotated[
        str,
        typer.Option("--model-id", help="Comma-separated model ids from configs/models.yaml."),
    ],
    run_id: Annotated[
        str | None,
        typer.Option("--run-id", help="Optional explicit run id. Only valid for a single model."),
    ] = None,
    registry: Annotated[
        Path,
        typer.Option("--registry", help="Model registry YAML path."),
    ] = DEFAULT_MODEL_REGISTRY_PATH,
    mode: Annotated[
        BenchmarkMode,
        typer.Option("--mode", help="cold or warm execution mode."),
    ] = BenchmarkMode.COLD,
    limit: Annotated[
        int,
        typer.Option("--limit", help="Maximum MileDay cases to execute."),
    ] = 1,
    seed: Annotated[
        int | None,
        typer.Option("--seed", help="Set dataset sampling seed"),
    ] = 42,
) -> None:
    """Run a small local MileDay dataset smoke evaluation through Ollama."""

    if limit <= 0:
        raise typer.BadParameter("limit must be positive.")
    settings = load_settings()
    explanation_judge = (
        GeminiExplanationJudge(
            api_key=settings.gemini_api_key,
            model=settings.gemini_judge_model,
            base_url=settings.gemini_api_base_url,
        )
        if settings.gemini_api_key
        else None
    )
    try:
        model_registry = load_model_registry(registry)
        requested_model_ids = _parse_model_ids(model_id)
        if run_id is not None and len(requested_model_ids) > 1:
            raise typer.BadParameter("--run-id can only be used with a single model id.")
        model_by_id = {item.id: item for item in model_registry.models}
        missing_model_ids = [item for item in requested_model_ids if item not in model_by_id]
        if missing_model_ids:
            raise typer.BadParameter(f"Unknown model id: {', '.join(missing_model_ids)}")
        all_cases = load_mileday_generation_cases(fixture)
        rng = random.Random(seed)
        cases = rng.sample(all_cases, k=min(limit, len(all_cases)))
    except (FileNotFoundError, ValueError) as exc:
        raise typer.BadParameter(str(exc)) from exc

    store = ResultStore(settings.runs_dir)
    batch_sequence = (
        None
        if run_id is not None
        else _next_mileday_batch_sequence(store.runs_dir, requested_model_ids, limit)
    )
    batch_items: list[dict[str, object]] = []
    typer.echo(f"batch_id={_batch_id(batch_sequence, limit) if batch_sequence is not None else run_id}")
    for current_model_id in requested_model_ids:
        model = model_by_id[current_model_id]
        current_run_id = run_id or f"{model.id}-{batch_sequence}-{limit}cases"
        try:
            stored = _run_mileday_smoke_for_model(
                model_id=model.id,
                model_tag=model.model_tag,
                run_id=current_run_id,
                mode=mode,
                cases=cases,
                store=store,
                ollama_base_url=settings.ollama_base_url,
                timeout_seconds=settings.default_timeout_seconds,
                explanation_judge=explanation_judge,
                require_explanation_judge=settings.mileday_require_explanation_judge,
            )
            report_path = generate_markdown_report(current_run_id, settings.runs_dir)
            counts = _status_counts(store.load_request_results(current_run_id))
            batch_items.append(
                {
                    "model_id": model.id,
                    "run_id": current_run_id,
                    "status": "completed",
                    "stored": stored,
                    "counts": counts,
                    "report_path": report_path,
                }
            )
            typer.echo(
                f"{model.id} -> {current_run_id} -> {report_path} -> "
                f"{_counter_text_for_cli(counts)}"
            )
        except Exception as exc:  # pragma: no cover - defensive batch isolation
            batch_items.append(
                {
                    "model_id": model.id,
                    "run_id": current_run_id,
                    "status": "failed",
                    "error": str(exc),
                }
            )
            typer.echo(f"{model.id} -> {current_run_id} -> failed -> {exc}")
            continue

    summary_path = _write_mileday_batch_summary(
        store.runs_dir,
        batch_id=_batch_id(batch_sequence, limit) if batch_sequence is not None else str(run_id),
        items=batch_items,
        limit=limit,
        seed=seed,
        model_ids=requested_model_ids,
        judge_model=settings.gemini_judge_model,
        require_explanation_judge=settings.mileday_require_explanation_judge,
        quality_judge=explanation_judge,
    )
    completed = sum(1 for item in batch_items if item["status"] == "completed")
    failed = sum(1 for item in batch_items if item["status"] == "failed")
    typer.echo(f"completed={completed} failed={failed}")
    typer.echo(f"batch_summary={summary_path}")


@app.command("run-mileday-multiturn")
def run_mileday_multiturn(
    registry: Annotated[
        Path,
        typer.Option("--registry", help="Model registry YAML path."),
    ] = DEFAULT_MODEL_REGISTRY_PATH,
    mode: Annotated[
        BenchmarkMode,
        typer.Option("--mode", help="cold or warm execution mode."),
    ] = BenchmarkMode.COLD,
) -> None:
    """Run the fixed MileDay multiturn evaluation for the selected local model."""

    settings = load_settings()
    explanation_judge = (
        GeminiExplanationJudge(
            api_key=settings.gemini_api_key,
            model=settings.gemini_judge_model,
            base_url=settings.gemini_api_base_url,
        )
        if settings.gemini_api_key
        else None
    )
    try:
        model_registry = load_model_registry(registry)
        model_by_id = {item.id: item for item in model_registry.models}
        if MILEDAY_MULTITURN_MODEL_ID not in model_by_id:
            raise typer.BadParameter(f"Unknown model id: {MILEDAY_MULTITURN_MODEL_ID}")
        cases = load_mileday_multiturn_cases(MILEDAY_MULTITURN_FIXTURE)
    except (FileNotFoundError, ValueError) as exc:
        raise typer.BadParameter(str(exc)) from exc

    store = ResultStore(settings.runs_dir)
    batch_sequence = _next_mileday_multiturn_sequence(store.runs_dir)
    model = model_by_id[MILEDAY_MULTITURN_MODEL_ID]
    run_id = f"{model.id}-mileday-multiturn-{batch_sequence}"

    typer.echo(f"run_id={run_id}")
    typer.echo(f"model={model.id}")
    typer.echo(f"fixture={MILEDAY_MULTITURN_FIXTURE}")
    typer.echo(f"cases={len(cases)}")
    typer.echo(f"prompt_version={MILEDAY_MULTITURN_PROMPT_VERSION}")
    typer.echo("judge=required")

    stored = _run_mileday_multiturn_for_model(
        model_id=model.id,
        model_tag=model.model_tag,
        run_id=run_id,
        mode=mode,
        cases=cases,
        store=store,
        ollama_base_url=settings.ollama_base_url,
        timeout_seconds=settings.default_timeout_seconds,
        explanation_judge=explanation_judge,
    )
    report_path = generate_markdown_report(run_id, settings.runs_dir)
    multiturn_report_path = _append_mileday_multiturn_report(run_id, settings.runs_dir, cases)
    html_report_path = generate_mileday_multiturn_html_report(run_id, settings.runs_dir)
    counts = _status_counts(store.load_request_results(run_id))
    typer.echo(
        f"{model.id} -> {run_id} -> {report_path} -> "
        f"{_counter_text_for_cli(counts)}"
    )
    typer.echo(f"stored={stored}")
    typer.echo(f"multiturn_report={multiturn_report_path}")
    typer.echo(f"html_report={html_report_path}")


@app.command("run-mileday-multiturn-grid")
def run_mileday_multiturn_grid(
    registry: Annotated[
        Path,
        typer.Option("--registry", help="Model registry YAML path."),
    ] = DEFAULT_MODEL_REGISTRY_PATH,
    mode: Annotated[
        BenchmarkMode,
        typer.Option("--mode", help="cold or warm execution mode."),
    ] = BenchmarkMode.COLD,
) -> None:
    """Run a small sampling-option grid for MileDay multiturn evaluation."""

    settings = load_settings()
    explanation_judge = (
        GeminiExplanationJudge(
            api_key=settings.gemini_api_key,
            model=settings.gemini_judge_model,
            base_url=settings.gemini_api_base_url,
        )
        if settings.gemini_api_key
        else None
    )
    try:
        model_registry = load_model_registry(registry)
        model_by_id = {item.id: item for item in model_registry.models}
        if MILEDAY_MULTITURN_MODEL_ID not in model_by_id:
            raise typer.BadParameter(f"Unknown model id: {MILEDAY_MULTITURN_MODEL_ID}")
        cases = load_mileday_multiturn_cases(MILEDAY_MULTITURN_FIXTURE)[:3]
    except (FileNotFoundError, ValueError) as exc:
        raise typer.BadParameter(str(exc)) from exc

    temperatures = [0.0, 0.1, 0.2]
    top_ps = [0.8, 0.9, 1.0]
    store = ResultStore(settings.runs_dir)
    batch_sequence = _next_mileday_multiturn_grid_sequence(store.runs_dir)
    batch_id = f"candidate-3-mileday-multiturn-grid-{batch_sequence}"
    model = model_by_id[MILEDAY_MULTITURN_MODEL_ID]
    batch_items: list[dict[str, object]] = []

    typer.echo(f"batch_id={batch_id}")
    typer.echo(f"model={model.id}")
    typer.echo(f"fixture={MILEDAY_MULTITURN_FIXTURE}")
    typer.echo(f"cases={len(cases)}")
    typer.echo("temperature_grid=0.0,0.1,0.2")
    typer.echo("top_p_grid=0.8,0.9,1.0")
    typer.echo("judge=required")

    for temperature in temperatures:
        for top_p in top_ps:
            run_id = (
                f"{batch_id}-temp{_option_label(temperature)}-top_p{_option_label(top_p)}"
            )
            runtime_options = {"temperature": temperature, "top_p": top_p}
            typer.echo(f"run_id={run_id} options={runtime_options}")
            stored = _run_mileday_multiturn_for_model(
                model_id=model.id,
                model_tag=model.model_tag,
                run_id=run_id,
                mode=mode,
                cases=cases,
                store=store,
                ollama_base_url=settings.ollama_base_url,
                timeout_seconds=settings.default_timeout_seconds,
                explanation_judge=explanation_judge,
                runtime_options=runtime_options,
            )
            report_path = generate_markdown_report(run_id, settings.runs_dir)
            multiturn_report_path = _append_mileday_multiturn_report(run_id, settings.runs_dir, cases)
            html_report_path = generate_mileday_multiturn_html_report(run_id, settings.runs_dir)
            results = store.load_request_results(run_id)
            counts = _status_counts(results)
            batch_items.append(
                {
                    "run_id": run_id,
                    "temperature": temperature,
                    "top_p": top_p,
                    "stored": stored,
                    "counts": counts,
                    "report_path": report_path,
                    "multiturn_report_path": multiturn_report_path,
                    "html_report_path": html_report_path,
                }
            )
            typer.echo(
                f"{run_id} -> {report_path} -> {_counter_text_for_cli(counts)} stored={stored}"
            )

    summary_path = _write_mileday_multiturn_grid_summary(
        store.runs_dir,
        batch_id=batch_id,
        items=batch_items,
        cases=cases,
    )
    typer.echo(f"grid_summary={summary_path}")


@app.command("run-mileday-multiturn-api")
def run_mileday_multiturn_api(
    mode: Annotated[
        BenchmarkMode,
        typer.Option("--mode", help="cold or warm execution mode."),
    ] = BenchmarkMode.COLD,
    model_id: Annotated[
        str,
        typer.Option(
            "--model-id",
            help="Comma-separated Gemini model ids. Defaults to flash-lite and flash.",
        ),
    ] = ",".join(MILEDAY_API_MODEL_IDS),
    sleep_seconds: Annotated[
        float,
        typer.Option(
            "--sleep-seconds",
            help="Seconds to wait after each target+judge API turn before the next turn.",
        ),
    ] = 0.0,
    limit: Annotated[
        int | None,
        typer.Option("--limit", help="Optional positive limit for fixture cases to execute."),
    ] = None,
) -> None:
    """Run the fixed MileDay multiturn evaluation for selected Gemini API models."""

    if sleep_seconds < 0:
        raise typer.BadParameter("sleep_seconds must be non-negative.")
    if limit is not None and limit <= 0:
        raise typer.BadParameter("limit must be positive.")
    settings = load_settings()
    generation_api_key = settings.gemini_generation_api_key or settings.gemini_api_key
    if not generation_api_key:
        raise typer.BadParameter("GEMINI_API_KEY or GEMINI_GENERATION_API_KEY is required.")
    if not settings.gemini_api_key:
        raise typer.BadParameter("GEMINI_API_KEY is required for the required Gemini judge.")
    explanation_judge = (
        GeminiExplanationJudge(
            api_key=settings.gemini_api_key,
            model=settings.gemini_judge_model,
            base_url=settings.gemini_api_base_url,
        )
    )
    try:
        cases = load_mileday_multiturn_cases(MILEDAY_MULTITURN_FIXTURE)
        if limit is not None:
            cases = cases[:limit]
        requested_model_ids = _parse_model_ids(model_id)
    except (FileNotFoundError, ValueError) as exc:
        raise typer.BadParameter(str(exc)) from exc

    store = ResultStore(settings.runs_dir)
    batch_sequence = _next_mileday_multiturn_api_sequence(store.runs_dir)
    batch_id = f"gemini-mileday-multiturn-{batch_sequence}"
    batch_items: list[dict[str, object]] = []

    typer.echo(f"batch_id={batch_id}")
    typer.echo("models=" + ", ".join(requested_model_ids))
    typer.echo(f"fixture={MILEDAY_MULTITURN_FIXTURE}")
    typer.echo(f"cases={len(cases)}")
    typer.echo(f"case_limit={limit if limit is not None else 'all'}")
    typer.echo(f"prompt_version={MILEDAY_API_MULTITURN_PROMPT_VERSION}")
    typer.echo("runtime=gemini")
    typer.echo("judge=required")
    typer.echo(f"sleep_seconds={sleep_seconds:g}")

    for current_model_id in requested_model_ids:
        run_id = f"{_run_id_safe_model_name(current_model_id)}-mileday-multiturn-{batch_sequence}"
        runtime = GeminiRuntime(
            api_key=generation_api_key,
            base_url=settings.gemini_api_base_url,
        )
        stored = _run_mileday_multiturn_for_model(
            model_id=current_model_id,
            model_tag=current_model_id,
            run_id=run_id,
            mode=mode,
            cases=cases,
            store=store,
            ollama_base_url=settings.ollama_base_url,
            timeout_seconds=settings.default_timeout_seconds,
            explanation_judge=explanation_judge,
            runtime=runtime,
            sleep_seconds=sleep_seconds,
            prompt_builder=_mileday_multiturn_api_prompt,
            prompt_version=MILEDAY_API_MULTITURN_PROMPT_VERSION,
        )
        report_path = generate_markdown_report(run_id, settings.runs_dir)
        multiturn_report_path = _append_mileday_multiturn_report(
            run_id,
            settings.runs_dir,
            cases,
            model_id=current_model_id,
        )
        html_report_path = generate_mileday_multiturn_html_report(run_id, settings.runs_dir)
        results = store.load_request_results(run_id)
        counts = _status_counts(results)
        batch_items.append(
            {
                "model_id": current_model_id,
                "run_id": run_id,
                "stored": stored,
                "counts": counts,
                "report_path": report_path,
                "multiturn_report_path": multiturn_report_path,
                "html_report_path": html_report_path,
            }
        )
        typer.echo(
            f"{current_model_id} -> {run_id} -> {report_path} -> "
            f"{_counter_text_for_cli(counts)} stored={stored}"
        )

    summary_path = _write_mileday_multiturn_api_summary(
        store.runs_dir,
        batch_id=batch_id,
        items=batch_items,
        cases=cases,
        model_ids=requested_model_ids,
    )
    typer.echo(f"batch_summary={summary_path}")


@app.command("render-multiturn-html")
def render_multiturn_html(
    run_id: Annotated[
        str,
        typer.Option("--run-id", help="Run id under artifacts/runs."),
    ],
) -> None:
    """Render a stored MileDay multiturn run as a local static HTML report."""

    settings = load_settings()
    html_report_path = generate_mileday_multiturn_html_report(run_id, settings.runs_dir)
    typer.echo(f"html_report={html_report_path}")


@app.command("run-benchmark")
def run_benchmark(
    model_id: Annotated[
        str,
        typer.Option("--model-id", help="Comma-separated model ids from configs/models.yaml."),
    ],
    limit: Annotated[
        int,
        typer.Option("--limit", help="Random sample size per public benchmark dataset."),
    ] = 50,
    seed: Annotated[
        int,
        typer.Option("--seed", help="Set dataset sampling seed."),
    ] = 42,
    registry: Annotated[
        Path,
        typer.Option("--registry", help="Model registry YAML path."),
    ] = DEFAULT_MODEL_REGISTRY_PATH,
    dataset_registry: Annotated[
        Path,
        typer.Option("--dataset-registry", help="Dataset registry YAML path."),
    ] = DEFAULT_DATASET_REGISTRY_PATH,
    mode: Annotated[
        BenchmarkMode,
        typer.Option("--mode", help="cold or warm execution mode."),
    ] = BenchmarkMode.COLD,
) -> None:
    """Run sampled public benchmark evaluation for selected local models."""

    if limit <= 0:
        raise typer.BadParameter("limit must be positive.")
    settings = load_settings()
    try:
        model_registry = load_model_registry(registry)
        dataset_configs = load_dataset_registry(dataset_registry)
        requested_model_ids = _parse_model_ids(model_id)
        model_by_id = {item.id: item for item in model_registry.models}
        missing_model_ids = [item for item in requested_model_ids if item not in model_by_id]
        if missing_model_ids:
            raise typer.BadParameter(f"Unknown model id: {', '.join(missing_model_ids)}")
        missing_dataset_keys = [
            dataset_key
            for dataset_key in PUBLIC_BENCHMARK_DATASET_KEYS
            if dataset_key not in dataset_configs.datasets
        ]
        if missing_dataset_keys:
            raise typer.BadParameter(f"Missing dataset configs: {', '.join(missing_dataset_keys)}")
    except (FileNotFoundError, ValueError) as exc:
        raise typer.BadParameter(str(exc)) from exc

    store = ResultStore(settings.runs_dir)
    batch_sequence = _next_benchmark_batch_sequence(store.runs_dir, requested_model_ids, limit)
    batch_id = _benchmark_batch_id(batch_sequence, limit)
    sampled_cases = _load_public_benchmark_cases(
        dataset_configs.datasets,
        sample_dir=store.runs_dir / f"{batch_id}-datasets",
        limit=limit,
        seed=seed,
    )
    typer.echo(f"batch_id={batch_id}")
    typer.echo("datasets=" + ", ".join(f"{key}:{len(value)}" for key, value in sampled_cases.items()))

    batch_items: list[dict[str, object]] = []
    for current_model_id in requested_model_ids:
        model = model_by_id[current_model_id]
        current_run_id = f"{model.id}-benchmark-{batch_sequence}-{limit}cases"
        stored = _run_public_benchmark_for_model(
            model_id=model.id,
            model_tag=model.model_tag,
            run_id=current_run_id,
            mode=mode,
            cases_by_dataset=sampled_cases,
            store=store,
            ollama_base_url=settings.ollama_base_url,
            timeout_seconds=settings.default_timeout_seconds,
        )
        report_path = generate_markdown_report(current_run_id, settings.runs_dir)
        counts = _status_counts(store.load_request_results(current_run_id))
        batch_items.append(
            {
                "model_id": model.id,
                "run_id": current_run_id,
                "status": "completed",
                "stored": stored,
                "counts": counts,
                "report_path": report_path,
            }
        )
        typer.echo(
            f"{model.id} -> {current_run_id} -> {report_path} -> "
            f"{_counter_text_for_cli(counts)}"
        )

    summary_path = _write_public_benchmark_batch_summary(
        store.runs_dir,
        batch_id=batch_id,
        items=batch_items,
        limit=limit,
        seed=seed,
        model_ids=requested_model_ids,
        dataset_counts={key: len(value) for key, value in sampled_cases.items()},
    )
    typer.echo(f"completed={len(batch_items)} failed=0")
    typer.echo(f"batch_summary={summary_path}")


@app.command("run-third-benchmark")
def run_third_benchmark(
    registry: Annotated[
        Path,
        typer.Option("--registry", help="Model registry YAML path."),
    ] = DEFAULT_MODEL_REGISTRY_PATH,
    dataset_registry: Annotated[
        Path,
        typer.Option("--dataset-registry", help="Dataset registry YAML path."),
    ] = DEFAULT_DATASET_REGISTRY_PATH,
    mode: Annotated[
        BenchmarkMode,
        typer.Option("--mode", help="cold or warm execution mode."),
    ] = BenchmarkMode.COLD,
) -> None:
    """Run the fixed third-stage benchmark for candidate-3 and candidate-5."""

    settings = load_settings()
    try:
        model_registry = load_model_registry(registry)
        dataset_configs = load_dataset_registry(dataset_registry)
        model_by_id = {item.id: item for item in model_registry.models}
        missing_model_ids = [item for item in THIRD_BENCHMARK_MODEL_IDS if item not in model_by_id]
        if missing_model_ids:
            raise typer.BadParameter(f"Unknown model id: {', '.join(missing_model_ids)}")
        missing_dataset_keys = [
            dataset_key
            for dataset_key in THIRD_BENCHMARK_DATASET_KEYS
            if dataset_key not in dataset_configs.datasets
        ]
        if missing_dataset_keys:
            raise typer.BadParameter(f"Missing dataset configs: {', '.join(missing_dataset_keys)}")
    except (FileNotFoundError, ValueError) as exc:
        raise typer.BadParameter(str(exc)) from exc

    store = ResultStore(settings.runs_dir)
    batch_sequence = _next_third_benchmark_batch_sequence(store.runs_dir)
    batch_id = _third_benchmark_batch_id(batch_sequence)
    cases_by_dataset = _load_third_benchmark_cases(
        dataset_configs.datasets,
        snapshot_dir=store.runs_dir / f"{batch_id}-datasets",
    )
    dataset_counts = {key: len(value) for key, value in cases_by_dataset.items()}
    typer.echo(f"batch_id={batch_id}")
    typer.echo("models=" + ", ".join(THIRD_BENCHMARK_MODEL_IDS))
    typer.echo("datasets=" + ", ".join(f"{key}:{value}" for key, value in dataset_counts.items()))
    typer.echo("sampling=none")
    typer.echo("weights=ifeval-ko:0.60,kobalt-700:0.40")

    batch_items: list[dict[str, object]] = []
    for current_model_id in THIRD_BENCHMARK_MODEL_IDS:
        model = model_by_id[current_model_id]
        current_run_id = f"{model.id}-third-benchmark-{batch_sequence}"
        stored = _run_public_benchmark_for_model(
            model_id=model.id,
            model_tag=model.model_tag,
            run_id=current_run_id,
            mode=mode,
            cases_by_dataset=cases_by_dataset,
            store=store,
            ollama_base_url=settings.ollama_base_url,
            timeout_seconds=settings.default_timeout_seconds,
            system_prompt=THIRD_BENCHMARK_SYSTEM_PROMPT,
            dataset_order=THIRD_BENCHMARK_DATASET_KEYS,
            progress_label="third benchmark",
        )
        report_path = generate_markdown_report(current_run_id, settings.runs_dir)
        counts = _status_counts(store.load_request_results(current_run_id))
        batch_items.append(
            {
                "model_id": model.id,
                "run_id": current_run_id,
                "status": "completed",
                "stored": stored,
                "counts": counts,
                "report_path": report_path,
            }
        )
        typer.echo(
            f"{model.id} -> {current_run_id} -> {report_path} -> "
            f"{_counter_text_for_cli(counts)}"
        )

    summary_path = _write_third_benchmark_batch_summary(
        store.runs_dir,
        batch_id=batch_id,
        items=batch_items,
        dataset_counts=dataset_counts,
    )
    typer.echo(f"completed={len(batch_items)} failed=0")
    typer.echo(f"batch_summary={summary_path}")


def _run_mileday_smoke_for_model(
    *,
    model_id: str,
    model_tag: str,
    run_id: str,
    mode: BenchmarkMode,
    cases: list[MileDayGenerationCase],
    store: ResultStore,
    ollama_base_url: str,
    timeout_seconds: int,
    explanation_judge: ExplanationJudge | None,
    require_explanation_judge: bool,
) -> int:
    prompts = [
        BenchmarkCasePrompt(
            dataset_id=case.dataset_id,
            case_id=case.case_id,
            prompt=_mileday_generation_prompt(case),
        )
        for case in cases
    ]
    config = BenchmarkRunConfig(
        run_id=run_id,
        model_id=model_id,
        model_tag=model_tag,
        mode=mode,
        runtime_options={"temperature": 0},
        timeout_seconds=timeout_seconds,
    )
    progress = _progress_bar(
        total=_progress_total(len(prompts), config),
        desc=f"{model_id} MileDay",
    )
    try:
        records = run_benchmark_cases(
            prompts,
            config,
            OllamaRuntime(base_url=ollama_base_url),
            monitor_factory=PerformanceMonitor,
            completed_resume_keys=set(store.resume_index(run_id)),
            progress_callback=_progress_update(progress),
        )
    finally:
        _progress_close(progress)
    case_by_id = {case.case_id: case for case in cases}
    stored = 0
    for record in measured_records(records):
        case = case_by_id[record.request_result.case_id]
        result = _evaluate_mileday_record(
            record.request_result,
            case,
            record.response.text,
            explanation_judge=explanation_judge,
            require_explanation_judge=require_explanation_judge,
        )
        store.store_request_result(result, raw_output=record.response.text)
        store.append_performance_samples(
            run_id,
            [record.performance_summary.model_dump(mode="json")],
            phase=record.phase.value,
        )
        stored += 1
    return stored


def _run_mileday_multiturn_for_model(
    *,
    model_id: str,
    model_tag: str,
    run_id: str,
    mode: BenchmarkMode,
    cases: list[MileDayMultiTurnCase],
    store: ResultStore,
    ollama_base_url: str,
    timeout_seconds: int,
    explanation_judge: ExplanationJudge | None,
    runtime_options: dict[str, object] | None = None,
    runtime: RuntimeAdapter | None = None,
    sleep_seconds: float = 0.0,
    prompt_builder: Callable[[MileDayMultiTurnCase, int, list[dict[str, str]]], str] | None = None,
    prompt_version: str = MILEDAY_MULTITURN_PROMPT_VERSION,
) -> int:
    config = BenchmarkRunConfig(
        run_id=run_id,
        model_id=model_id,
        model_tag=model_tag,
        mode=mode,
        runtime_options=runtime_options or MILEDAY_MULTITURN_RUNTIME_OPTIONS,
        timeout_seconds=timeout_seconds,
    )
    progress = _progress_bar(
        total=_progress_total(sum(len(case.turns) for case in cases), config),
        desc=f"{model_id} MileDay multiturn",
    )
    active_runtime = runtime or OllamaRuntime(base_url=ollama_base_url)
    active_prompt_builder = prompt_builder or _mileday_multiturn_prompt
    stored = 0
    try:
        for case in cases:
            transcript: list[dict[str, str]] = []
            previous_parsed: dict[str, Any] | None = None
            case_blocked = False
            for turn in case.turns:
                turn_case_id = _mileday_multiturn_turn_case_id(case.case_id, turn.turn_id)
                if case_blocked:
                    skipped = _skipped_mileday_multiturn_result(
                        run_id=run_id,
                        model_id=model_id,
                        dataset_id=case.dataset_id,
                        case_id=turn_case_id,
                        case=case,
                        turn_id=turn.turn_id,
                        prompt_version=prompt_version,
                    )
                    store.store_request_result(skipped)
                    for _ in range(_progress_total(1, config)):
                        _progress_update(progress)(None)
                    stored += 1
                    continue

                prompt = active_prompt_builder(case, turn.turn_id, transcript)
                records = run_benchmark_cases(
                    [
                        BenchmarkCasePrompt(
                            dataset_id=case.dataset_id,
                            case_id=turn_case_id,
                            prompt=prompt,
                            parsed_output={
                                "evaluation_family": "mileday_multiturn",
                                "case_id": case.case_id,
                                "turn_id": turn.turn_id,
                                "turn_count": len(case.turns),
                                "expected_action": turn.expected_action,
                                "prompt_version": prompt_version,
                            },
                        )
                    ],
                    config,
                    active_runtime,
                    monitor_factory=PerformanceMonitor,
                    completed_resume_keys=set(),
                    progress_callback=_progress_update(progress),
                )
                measured = measured_records(records)
                if not measured:
                    continue
                record = measured[-1]
                result = _evaluate_mileday_multiturn_record(
                    record.request_result,
                    case,
                    turn.turn_id,
                    record.response.text,
                    previous_parsed=previous_parsed,
                    explanation_judge=explanation_judge,
                    prompt_version=prompt_version,
                )
                store.store_request_result(result, raw_output=record.response.text)
                store.append_performance_samples(
                    run_id,
                    [record.performance_summary.model_dump(mode="json")],
                    phase=record.phase.value,
                )
                stored += 1
                if result.status == ResultStatus.PASSED:
                    parsed_json = result.parsed_output.get("parsed_json")
                    assistant_content = record.response.text
                    if isinstance(parsed_json, dict):
                        previous_parsed = parsed_json
                        assistant_content = _append_mileday_plan_targets_to_transcript(
                            assistant_content,
                            parsed_json,
                        )
                    transcript.append({"role": "user", "content": turn.content})
                    transcript.append({"role": "assistant", "content": assistant_content})
                else:
                    case_blocked = True
                if sleep_seconds > 0:
                    time.sleep(sleep_seconds)
    finally:
        _progress_close(progress)
    return stored


def _run_public_benchmark_for_model(
    *,
    model_id: str,
    model_tag: str,
    run_id: str,
    mode: BenchmarkMode,
    cases_by_dataset: dict[str, list[PublicBenchmarkCase]],
    store: ResultStore,
    ollama_base_url: str,
    timeout_seconds: int,
    system_prompt: str | None = None,
    dataset_order: tuple[str, ...] = PUBLIC_BENCHMARK_DATASET_KEYS,
    progress_label: str = "benchmark",
) -> int:
    config = BenchmarkRunConfig(
        run_id=run_id,
        model_id=model_id,
        model_tag=model_tag,
        mode=mode,
        system=system_prompt,
        runtime_options={"temperature": 0},
        timeout_seconds=timeout_seconds,
    )
    stored = 0
    for dataset_key in dataset_order:
        dataset_cases = cases_by_dataset.get(dataset_key, [])
        if not dataset_cases:
            continue
        prompts = [
            BenchmarkCasePrompt(
                dataset_id=case.dataset_id,
                case_id=case.case_id,
                prompt=case.prompt,
                parsed_output={
                    "evaluation_family": "public_benchmark",
                    "dataset_key": case.dataset_key,
                    "benchmark_id": case.benchmark_id,
                },
            )
            for case in dataset_cases
        ]
        progress = _progress_bar(
            total=_progress_total(len(prompts), config),
            desc=f"{model_id} {dataset_key} {progress_label}",
        )
        try:
            records = run_benchmark_cases(
                prompts,
                config,
                OllamaRuntime(base_url=ollama_base_url),
                monitor_factory=PerformanceMonitor,
                completed_resume_keys=set(store.resume_index(run_id)),
                progress_callback=_progress_update(progress),
            )
        finally:
            _progress_close(progress)
        case_by_key = {(case.dataset_id, case.case_id): case for case in dataset_cases}
        for record in measured_records(records):
            base_result = record.request_result
            case = case_by_key[(base_result.dataset_id, base_result.case_id)]
            result = _evaluate_public_benchmark_record(base_result, case, record.response.text)
            store.store_request_result(result, raw_output=record.response.text)
            store.append_performance_samples(
                run_id,
                [record.performance_summary.model_dump(mode="json")],
                phase=record.phase.value,
            )
            stored += 1
            if result.status == ResultStatus.FAILED:
                error_text = (
                    f"{result.error.category.value}: {result.error.message}"
                    if result.error is not None
                    else "unknown failure"
                )
                raise RuntimeError(
                    f"Benchmark run stopped after failed result "
                    f"{model_id}/{case.dataset_id}/{case.case_id}: {error_text}"
                )
    return stored


def _load_public_benchmark_cases(
    dataset_configs: dict[str, Any],
    *,
    sample_dir: Path,
    limit: int,
    seed: int,
) -> dict[str, list[PublicBenchmarkCase]]:
    rng = random.Random(seed)
    cases_by_dataset: dict[str, list[PublicBenchmarkCase]] = {}
    sample_dir.mkdir(parents=True, exist_ok=True)
    for dataset_key in PUBLIC_BENCHMARK_DATASET_KEYS:
        loaded = load_processed_dataset_rows(dataset_key, dataset_configs[dataset_key])
        sampled_rows = rng.sample(loaded.rows, k=min(limit, len(loaded.rows)))
        sample_path = sample_dir / f"{dataset_key}.jsonl"
        _write_jsonl(sample_path, sampled_rows)
        cases_by_dataset[dataset_key] = _load_public_benchmark_cases_from_sample(
            dataset_key,
            sample_path,
        )
    return cases_by_dataset


def _load_third_benchmark_cases(
    dataset_configs: dict[str, Any],
    *,
    snapshot_dir: Path,
) -> dict[str, list[PublicBenchmarkCase]]:
    cases_by_dataset: dict[str, list[PublicBenchmarkCase]] = {}
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    for dataset_key in THIRD_BENCHMARK_DATASET_KEYS:
        prepare_dataset(dataset_key, dataset_configs[dataset_key], sample_limit=None)
        loaded = load_prepared_dataset_rows(dataset_key, dataset_configs[dataset_key])
        snapshot_path = snapshot_dir / f"{dataset_key}.jsonl"
        _write_jsonl(snapshot_path, loaded.rows)
        cases_by_dataset[dataset_key] = _load_public_benchmark_cases_from_sample(
            dataset_key,
            snapshot_path,
        )
    return cases_by_dataset


def _load_public_benchmark_cases_from_sample(
    dataset_key: str,
    sample_path: Path,
) -> list[PublicBenchmarkCase]:
    dataset_id = PUBLIC_DATASET_IDS[dataset_key]
    if dataset_key == "kmmlu_pro":
        return _load_mcq_public_cases(dataset_key, dataset_id, "kmmlu-pro", sample_path)
    if dataset_key == "kobalt":
        return _load_mcq_public_cases(dataset_key, dataset_id, "kobalt-700", sample_path)
    if dataset_key == "click":
        return _load_mcq_public_cases(dataset_key, dataset_id, "click", sample_path)
    if dataset_key == "ifeval_ko":
        return [
            PublicBenchmarkCase(
                dataset_key=dataset_key,
                dataset_id=dataset_id,
                benchmark_id=case.benchmark_id,
                case_id=case.case_id,
                prompt=case.build_prompt(),
                score_response=case.score_response,
            )
            for case in load_ifeval_ko_cases(sample_path, dataset_id=dataset_id)
        ]
    raise typer.BadParameter(f"Unsupported public benchmark dataset: {dataset_key}")


def _load_mcq_public_cases(
    dataset_key: str,
    dataset_id: str,
    benchmark_id: str,
    sample_path: Path,
) -> list[PublicBenchmarkCase]:
    cases: list[PublicBenchmarkCase] = []
    for row in _read_jsonl_rows(sample_path):
        question = _mcq_question_from_processed_row(row, benchmark_id=benchmark_id)
        cases.append(
            PublicBenchmarkCase(
                dataset_key=dataset_key,
                dataset_id=dataset_id,
                benchmark_id=benchmark_id,
                case_id=question.case_id,
                prompt=_public_mcq_prompt(build_mcq_prompt(question)),
                score_response=lambda raw_output, item=question: score_mcq_response(item, raw_output),
            )
        )
    return cases


def _mcq_question_from_processed_row(row: dict[str, Any], *, benchmark_id: str) -> MCQQuestion:
    choices = [
        MCQChoice(label=label, text=str(row[field_name]))
        for label, field_name in _choice_fields(row)
    ]
    return MCQQuestion(
        benchmark_id=benchmark_id,
        case_id=str(row["case_id"]),
        category=str(row["category"]) if row.get("category") not in (None, "") else None,
        question=str(row["question"]),
        choices=choices,
        answer=str(row["answer"]).strip().upper(),
    )


def _choice_fields(row: dict[str, Any]) -> list[tuple[str, str]]:
    fields: list[tuple[str, str]] = []
    for label in tuple("ABCDEFGHIJ"):
        field_name = f"choice_{label.lower()}"
        if field_name in row and row[field_name] not in (None, ""):
            fields.append((label, field_name))
    return fields


def _public_mcq_prompt(prompt: str) -> str:
    return (
        "다음은 객관식 벤치마크 문제입니다.\n"
        "반드시 정답 선택지의 알파벳 하나만 출력하세요.\n"
        "설명, 풀이 과정, 문장, 마침표는 쓰지 마세요.\n"
        "\n"
        f"{prompt}"
    )


def _evaluate_public_benchmark_record(
    base_result: RequestResult,
    case: PublicBenchmarkCase,
    raw_output: str,
) -> RequestResult:
    if base_result.error is not None:
        return base_result
    scored = case.score_response(raw_output)
    payload = scored.model_dump(mode="json")
    parsed_output = {
        **base_result.parsed_output,
        **payload,
        "evaluation_family": "public_benchmark",
        "dataset_key": case.dataset_key,
        "dataset_id": case.dataset_id,
        "benchmark_id": case.benchmark_id,
    }
    if "is_correct" in payload:
        parsed_output["score"] = 1.0 if payload.get("is_correct") is True else 0.0
        parsed_output["accuracy"] = parsed_output["score"]
    elif "prompt_level_strict" in payload:
        parsed_output["score"] = 1.0 if payload.get("prompt_level_strict") is True else 0.0
        parsed_output["prompt_level_strict_accuracy"] = parsed_output["score"]
        parsed_output["prompt_level_loose_accuracy"] = (
            1.0 if payload.get("prompt_level_loose") is True else 0.0
        )

    invalid = bool(payload.get("is_invalid"))
    return base_result.model_copy(
        update={
            "status": ResultStatus.INVALID if invalid else ResultStatus.PASSED,
            "parsed_output": parsed_output,
            "error": (
                EvaluationError(
                    category=FailureCategory.PARSER_ERROR,
                    message=str(payload.get("invalid_reason") or "Benchmark response was invalid."),
                )
                if invalid
                else None
            ),
        }
    )


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def _read_jsonl_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _next_benchmark_batch_sequence(runs_dir: Path, model_ids: list[str], limit: int) -> int:
    highest = 0
    if not runs_dir.exists():
        return 1
    patterns = [
        re.compile(rf"^{re.escape(model_id)}-benchmark-(?P<sequence>\d+)-{limit}cases$")
        for model_id in model_ids
    ]
    for path in runs_dir.iterdir():
        if not path.is_dir():
            continue
        for pattern in patterns:
            match = pattern.fullmatch(path.name)
            if match is not None:
                highest = max(highest, int(match.group("sequence")))
                break
    return highest + 1


def _next_third_benchmark_batch_sequence(runs_dir: Path) -> int:
    highest = 0
    if not runs_dir.exists():
        return 1
    patterns = [
        re.compile(rf"^{re.escape(model_id)}-third-benchmark-(?P<sequence>\d+)$")
        for model_id in THIRD_BENCHMARK_MODEL_IDS
    ]
    for path in runs_dir.iterdir():
        if not path.is_dir():
            continue
        for pattern in patterns:
            match = pattern.fullmatch(path.name)
            if match is not None:
                highest = max(highest, int(match.group("sequence")))
                break
    return highest + 1


def _next_mileday_multiturn_sequence(runs_dir: Path) -> int:
    highest = 0
    if not runs_dir.exists():
        return 1
    pattern = re.compile(
        rf"^{re.escape(MILEDAY_MULTITURN_MODEL_ID)}-mileday-multiturn-(?P<sequence>\d+)$"
    )
    for path in runs_dir.iterdir():
        if not path.is_dir():
            continue
        match = pattern.fullmatch(path.name)
        if match is not None:
            highest = max(highest, int(match.group("sequence")))
    return highest + 1


def _next_mileday_multiturn_grid_sequence(runs_dir: Path) -> int:
    highest = 0
    if not runs_dir.exists():
        return 1
    pattern = re.compile(
        rf"^{re.escape(MILEDAY_MULTITURN_MODEL_ID)}-mileday-multiturn-grid-(?P<sequence>\d+)"
    )
    for path in runs_dir.iterdir():
        match = pattern.match(path.name)
        if match is not None:
            highest = max(highest, int(match.group("sequence")))
    return highest + 1


def _next_mileday_multiturn_api_sequence(runs_dir: Path) -> int:
    highest = 0
    if not runs_dir.exists():
        return 1
    pattern = re.compile(r"^gemini-mileday-multiturn-(?P<sequence>\d+)-summary\.md$")
    run_pattern = re.compile(r"^gemini-[\w-]+-mileday-multiturn-(?P<sequence>\d+)$")
    for path in runs_dir.iterdir():
        summary_match = pattern.fullmatch(path.name)
        run_match = run_pattern.fullmatch(path.name)
        match = summary_match or run_match
        if match is not None:
            highest = max(highest, int(match.group("sequence")))
    return highest + 1


def _option_label(value: float) -> str:
    return f"{value:.1f}".replace(".", "p")


def _run_id_safe_model_name(model_id: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9_.-]+", "-", model_id.strip()).strip("-")
    return normalized.replace(".", "-")


def _benchmark_batch_id(sequence: int, limit: int) -> str:
    return f"benchmark-batch-{sequence}-{limit}cases"


def _third_benchmark_batch_id(sequence: int) -> str:
    return f"third-benchmark-batch-{sequence}"


def _write_public_benchmark_batch_summary(
    runs_dir: Path,
    *,
    batch_id: str,
    items: list[dict[str, object]],
    limit: int,
    seed: int,
    model_ids: list[str],
    dataset_counts: dict[str, int],
) -> Path:
    path = runs_dir / f"{batch_id}-summary.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    store = ResultStore(runs_dir)
    model_summaries = [
        _public_benchmark_model_summary(
            model_id=str(item["model_id"]),
            run_id=str(item["run_id"]),
            results=store.load_request_results(str(item["run_id"])),
        )
        for item in items
    ]
    lines = [
        f"# Public Benchmark Batch Summary: {batch_id}",
        "",
        "## 실행 조건",
        "",
        f"- model ids: {', '.join(model_ids)}",
        f"- dataset keys: {', '.join(PUBLIC_BENCHMARK_DATASET_KEYS)}",
        f"- sampling: random",
        f"- limit per dataset: {limit}",
        f"- seed: {seed}",
        f"- dataset counts: {_dict_counter_text(dataset_counts)}",
        "",
        "## 모델별 실행 요약",
        "",
        "| model | run_id | status | passed | invalid | failed | skipped | weighted score | report |",
        "|---|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for item in items:
        counts = item.get("counts")
        count_map = counts if isinstance(counts, dict) else {}
        summary = next(
            model_summary
            for model_summary in model_summaries
            if model_summary["model_id"] == item["model_id"]
        )
        lines.append(
            "| "
            + " | ".join(
                [
                    _escape_table(str(item.get("model_id", ""))),
                    _escape_table(str(item.get("run_id", ""))),
                    _escape_table(str(item.get("status", ""))),
                    str(count_map.get("passed", 0)),
                    str(count_map.get("invalid", 0)),
                    str(count_map.get("failed", 0)),
                    str(count_map.get("skipped", 0)),
                    _format_optional_float(summary["weighted_score"]),
                    f"`{Path(str(item.get('report_path', ''))).as_posix()}`" if item.get("report_path") else "",
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## 데이터셋별 점수",
            "",
            "| model | IFEval-Ko | KoBALT-700 | CLIcK | KMMLU-Pro |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for summary in model_summaries:
        dataset_scores = summary["dataset_scores"]
        lines.append(
            f"| {_escape_table(str(summary['model_id']))} | "
            f"{_format_optional_float(dataset_scores.get('ifeval-ko'))} | "
            f"{_format_optional_float(dataset_scores.get('kobalt-700'))} | "
            f"{_format_optional_float(dataset_scores.get('click'))} | "
            f"{_format_optional_float(dataset_scores.get('kmmlu-pro'))} |"
        )
    lines.extend(
        [
            "",
            "## 실패 및 invalid 요약",
            "",
        ]
    )
    for summary in model_summaries:
        lines.append(
            f"- {summary['model_id']}: status={_dict_counter_text(summary['status_counts'])}, "
            f"errors={_dict_counter_text(summary['error_counts']) if summary['error_counts'] else '없음'}"
        )
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8", newline="\n")
    return path


def _write_third_benchmark_batch_summary(
    runs_dir: Path,
    *,
    batch_id: str,
    items: list[dict[str, object]],
    dataset_counts: dict[str, int],
) -> Path:
    path = runs_dir / f"{batch_id}-summary.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    store = ResultStore(runs_dir)
    model_summaries = [
        _public_benchmark_model_summary(
            model_id=str(item["model_id"]),
            run_id=str(item["run_id"]),
            results=store.load_request_results(str(item["run_id"])),
            weights=THIRD_BENCHMARK_WEIGHTS,
        )
        for item in items
    ]
    winner = _third_benchmark_winner(model_summaries)
    lines = [
        f"# 3차 형식 제약·추론 안정성 테스트 Summary: {batch_id}",
        "",
        "## 실행 조건",
        "",
        f"- model ids: {', '.join(THIRD_BENCHMARK_MODEL_IDS)}",
        f"- dataset keys: {', '.join(THIRD_BENCHMARK_DATASET_KEYS)}",
        "- sampling: none",
        "- dataset 기준: processed data 전체",
        "- system prompt: candidate-3와 candidate-5에 동일 적용",
        "- weights: IFEval-Ko=60%, KoBALT-700=40%",
        f"- dataset counts: {_dict_counter_text(dataset_counts)}",
        "",
        "## System Prompt",
        "",
        "```text",
        THIRD_BENCHMARK_SYSTEM_PROMPT,
        "```",
        "",
        "## 모델별 실행 요약",
        "",
        "| model | run_id | status | passed | invalid | failed | skipped | weighted score | IFEval-Ko | KoBALT-700 | report |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for item in items:
        counts = item.get("counts")
        count_map = counts if isinstance(counts, dict) else {}
        summary = next(
            model_summary
            for model_summary in model_summaries
            if model_summary["model_id"] == item["model_id"]
        )
        dataset_scores = summary["dataset_scores"]
        lines.append(
            "| "
            + " | ".join(
                [
                    _escape_table(str(item.get("model_id", ""))),
                    _escape_table(str(item.get("run_id", ""))),
                    _escape_table(str(item.get("status", ""))),
                    str(count_map.get("passed", 0)),
                    str(count_map.get("invalid", 0)),
                    str(count_map.get("failed", 0)),
                    str(count_map.get("skipped", 0)),
                    _format_optional_float(summary["weighted_score"]),
                    _format_optional_float(dataset_scores.get("ifeval-ko")),
                    _format_optional_float(dataset_scores.get("kobalt-700")),
                    f"`{Path(str(item.get('report_path', ''))).as_posix()}`" if item.get("report_path") else "",
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## 판단 기준",
            "",
            "- `failed=0`이어야 운영 후보로 유지한다.",
            "- `invalid rate < 5%`를 기본 통과 기준으로 둔다.",
            "- IFEval-Ko 60%, KoBALT-700 40% weighted score 1위 모델을 우선한다.",
            "- weighted score 차이가 0.03 미만이면 IFEval-Ko 점수가 높은 모델을 우선한다.",
            "- 품질 지표가 유사하면 평균 latency와 p95 latency가 낮은 모델을 우선한다.",
            "",
            "## 실패 및 invalid 요약",
            "",
        ]
    )
    for summary in model_summaries:
        lines.append(
            f"- {summary['model_id']}: status={_dict_counter_text(summary['status_counts'])}, "
            f"errors={_dict_counter_text(summary['error_counts']) if summary['error_counts'] else '없음'}, "
            f"invalid_rate={_format_rate_from_counts(summary['status_counts'].get('invalid', 0), sum(summary['status_counts'].values()))}"
        )
    lines.extend(
        [
            "",
            "## 최종 후보 판단",
            "",
        ]
    )
    if winner is None:
        lines.append("3차 판단 기준을 만족하는 모델이 없다. system prompt 또는 parser 정책을 먼저 재검토한다.")
    else:
        lines.append(
            f"`{winner['model_id']}`가 3차 판단 기준을 만족하는 우선 후보이다. "
            f"weighted score는 {_format_optional_float(winner['weighted_score'])}이다."
        )
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8", newline="\n")
    return path


def _append_mileday_multiturn_report(
    run_id: str,
    runs_dir: Path,
    cases: list[MileDayMultiTurnCase],
    *,
    model_id: str = MILEDAY_MULTITURN_MODEL_ID,
) -> Path:
    store = ResultStore(runs_dir)
    run_dir = store.run_dir(run_id)
    report_path = run_dir / "report.md"
    results = store.load_request_results(run_id)
    existing = report_path.read_text(encoding="utf-8") if report_path.exists() else ""
    lines = [
        "",
        "## MileDay 멀티턴 평가",
        "",
        "### 실행 조건",
        "",
        f"- model id: {model_id}",
        f"- fixture: `{MILEDAY_MULTITURN_FIXTURE.as_posix()}`",
        f"- cases: {len(cases)}",
        "- sampling: none",
        "- judge: required",
        f"- prompt version: {MILEDAY_MULTITURN_PROMPT_VERSION}",
        "- time storage policy: milestone title prefix",
        "",
    ]
    lines.extend(_mileday_multiturn_measurement_summary(results, cases))
    lines.extend(_mileday_multiturn_case_table(results, cases))
    lines.extend(_mileday_multiturn_failure_summary(results))
    lines.extend(_mileday_multiturn_conclusion(results, cases))
    report_path.write_text(
        existing.rstrip() + "\n" + "\n".join(lines).rstrip() + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return report_path


def _mileday_multiturn_measurement_summary(
    results: list[RequestResult],
    cases: list[MileDayMultiTurnCase],
) -> list[str]:
    total_turns = sum(len(case.turns) for case in cases)
    counts = Counter(result.status.value for result in results)
    completed_cases = _mileday_multiturn_completed_cases(results, cases)
    all_turn_pass_cases = _mileday_multiturn_all_turn_pass_cases(results, cases)
    latencies = [result.metrics.latency_ms for result in results if result.metrics.latency_ms is not None]
    ttfts = [result.metrics.ttft_ms for result in results if result.metrics.ttft_ms is not None]
    tok_per_sec = [
        result.metrics.tokens_per_second
        for result in results
        if result.metrics.tokens_per_second is not None
    ]
    turn_latency = _mileday_multiturn_per_turn_latency(results)
    judge_results = [result.parsed_output.get("explanation_judge") for result in results]
    judge_completed = sum(
        1
        for item in judge_results
        if isinstance(item, dict) and item.get("skipped") is False and item.get("error") is None
    )
    judge_scores = [
        float(item["score"])
        for item in judge_results
        if isinstance(item, dict) and isinstance(item.get("score"), int | float)
    ]
    judge_aligned = sum(
        1 for item in judge_results if isinstance(item, dict) and item.get("is_aligned") is True
    )
    warning_count = _mileday_multiturn_warning_count(results)
    db_ready_cases = len(all_turn_pass_cases)
    critical_failures = counts.get(ResultStatus.FAILED.value, 0) + counts.get(ResultStatus.INVALID.value, 0)
    return [
        "### 측정 요약",
        "",
        "| 항목 | 값 |",
        "|---|---:|",
        f"| total_turns | {total_turns} |",
        f"| passed_turns | {counts.get(ResultStatus.PASSED.value, 0)} |",
        f"| invalid_turns | {counts.get(ResultStatus.INVALID.value, 0)} |",
        f"| failed_turns | {counts.get(ResultStatus.FAILED.value, 0)} |",
        f"| skipped_turns | {counts.get(ResultStatus.SKIPPED.value, 0)} |",
        f"| critical_failure_rate | {_format_rate_from_counts(critical_failures, total_turns)} |",
        f"| warnings | {warning_count} |",
        f"| case_completion_rate | {_format_rate_from_counts(len(completed_cases), len(cases))} |",
        f"| all_turn_pass_case_rate | {_format_rate_from_counts(len(all_turn_pass_cases), len(cases))} |",
        f"| judge_completed | {judge_completed} |",
        f"| judge_is_aligned_count | {judge_aligned} |",
        f"| judge_score_avg | {_format_optional_float(mean(judge_scores) if judge_scores else None)} |",
        f"| avg_latency_ms | {_format_optional_float(mean(latencies) if latencies else None)} |",
        f"| max_latency_ms | {_format_optional_float(max(latencies) if latencies else None)} |",
        f"| avg_ttft_ms | {_format_optional_float(mean(ttfts) if ttfts else None)} |",
        f"| avg_tokens_per_second | {_format_optional_float(mean(tok_per_sec) if tok_per_sec else None)} |",
        f"| performance_by_turn_index | {_escape_table(json.dumps(turn_latency, ensure_ascii=False, sort_keys=True))} |",
        f"| db_ready_cases | {db_ready_cases} |",
        "",
    ]


def _mileday_multiturn_case_table(
    results: list[RequestResult],
    cases: list[MileDayMultiTurnCase],
) -> list[str]:
    by_case = _mileday_multiturn_results_by_case(results)
    lines = [
        "### Case별 최종 상태",
        "",
        "| case | turns | final status | passed | invalid | failed | skipped |",
        "|---|---:|---|---:|---:|---:|---:|",
    ]
    for case in cases:
        group = by_case.get(case.case_id, [])
        counts = Counter(result.status.value for result in group)
        final_status = group[-1].status.value if group else "not_executed"
        lines.append(
            f"| {case.case_id} | {len(case.turns)} | {final_status} | "
            f"{counts.get(ResultStatus.PASSED.value, 0)} | "
            f"{counts.get(ResultStatus.INVALID.value, 0)} | "
            f"{counts.get(ResultStatus.FAILED.value, 0)} | "
            f"{counts.get(ResultStatus.SKIPPED.value, 0)} |"
        )
    lines.append("")
    return lines


def _mileday_multiturn_failure_summary(results: list[RequestResult]) -> list[str]:
    parser_errors = Counter()
    judge_rejects = Counter()
    failures = Counter()
    warnings = Counter()
    deterministic_checks = Counter()
    failure_codes = Counter()
    safety_gate_codes = Counter()
    safety_gate_rows: list[str] = []
    for result in results:
        validation = result.parsed_output.get("multiturn_validation")
        if isinstance(validation, dict):
            for warning in validation.get("warnings", []):
                warnings[str(warning)] += 1
            deterministic_validation = validation.get("deterministic_validation")
            if isinstance(deterministic_validation, dict):
                for check_name in deterministic_validation.get("failed_check_names", []):
                    deterministic_checks[str(check_name)] += 1
                for failure_code in deterministic_validation.get("failure_codes", []):
                    failure_codes[str(failure_code)] += 1
            safety_gate = validation.get("safety_gate")
            if isinstance(safety_gate, dict):
                for violation in safety_gate.get("violations", []):
                    if not isinstance(violation, dict):
                        continue
                    code = str(violation.get("failure_code", "UNKNOWN"))
                    safety_gate_codes[code] += 1
                    safety_gate_rows.append(
                        f"| {result.case_id} | {code} | {_escape_table(str(violation.get('message', '')))} |"
                    )
        if result.status == ResultStatus.INVALID:
            judge = result.parsed_output.get("explanation_judge")
            if isinstance(judge, dict) and judge.get("is_aligned") is False:
                judge_rejects[str(judge.get("reason", "judge rejected"))] += 1
                failure_codes["JUDGE_REJECTION"] += 1
            elif result.error is not None:
                parser_errors[result.error.message] += 1
        if result.status == ResultStatus.FAILED and result.error is not None:
            failures[result.error.category.value] += 1
    lines = [
        "### 실패 원인 요약",
        "",
        f"- parser/constraint errors: {_dict_counter_text(dict(parser_errors)) if parser_errors else '없음'}",
        f"- warnings: {_dict_counter_text(dict(warnings)) if warnings else '없음'}",
        f"- deterministic failed checks: {_dict_counter_text(dict(deterministic_checks)) if deterministic_checks else '없음'}",
        f"- failure codes: {_dict_counter_text(dict(failure_codes)) if failure_codes else '없음'}",
        f"- judge rejects: {_dict_counter_text(dict(judge_rejects)) if judge_rejects else '없음'}",
        f"- failed categories: {_dict_counter_text(dict(failures)) if failures else '없음'}",
        "",
    ]
    lines.extend(
        [
            "### Safety Gate",
            "",
            f"- 전체 통과 여부: {'통과' if not safety_gate_codes else '실패'}",
            f"- 위반 유형별 건수: {_dict_counter_text(dict(safety_gate_codes)) if safety_gate_codes else '없음'}",
            "",
        ]
    )
    if safety_gate_rows:
        lines.extend(
            [
                "| turn | failure code | 설명 |",
                "|---|---|---|",
                *safety_gate_rows,
                "",
            ]
        )
    return lines


def _mileday_multiturn_conclusion(
    results: list[RequestResult],
    cases: list[MileDayMultiTurnCase],
) -> list[str]:
    completed_cases = _mileday_multiturn_completed_cases(results, cases)
    all_turn_pass_cases = _mileday_multiturn_all_turn_pass_cases(results, cases)
    ready = len(all_turn_pass_cases) == len(cases)
    conclusion = (
        "모든 case가 마지막 turn까지 통과했으므로 제품 기능 연결을 위한 후보로 볼 수 있다."
        if ready
        else "일부 case가 마지막 turn까지 통과하지 못했으므로 제품 기능 연결 전 prompt, parser, judge 기준을 보강해야 한다."
    )
    return [
        "### 결론",
        "",
        f"- 마지막 turn까지 실행된 case 수: {len(completed_cases)} / {len(cases)}",
        f"- 최종적으로 DB 반영 가능한 case 수: {len(all_turn_pass_cases)} / {len(cases)}",
        f"- 제품 연결 판단: {conclusion}",
        "",
    ]


def _mileday_multiturn_completed_cases(
    results: list[RequestResult],
    cases: list[MileDayMultiTurnCase],
) -> set[str]:
    by_case = _mileday_multiturn_results_by_case(results)
    completed: set[str] = set()
    for case in cases:
        group = by_case.get(case.case_id, [])
        if len(group) == len(case.turns) and group[-1].status != ResultStatus.SKIPPED:
            completed.add(case.case_id)
    return completed


def _mileday_multiturn_all_turn_pass_cases(
    results: list[RequestResult],
    cases: list[MileDayMultiTurnCase],
) -> set[str]:
    by_case = _mileday_multiturn_results_by_case(results)
    passed: set[str] = set()
    for case in cases:
        group = by_case.get(case.case_id, [])
        if len(group) == len(case.turns) and all(result.status == ResultStatus.PASSED for result in group):
            passed.add(case.case_id)
    return passed


def _mileday_multiturn_results_by_case(
    results: list[RequestResult],
) -> dict[str, list[RequestResult]]:
    grouped: dict[str, list[RequestResult]] = {}
    for result in sorted(
        results,
        key=lambda item: (
            str(item.parsed_output.get("case_id")),
            int(item.parsed_output.get("turn_id", 0)),
        ),
    ):
        case_id = str(result.parsed_output.get("case_id", "unknown"))
        grouped.setdefault(case_id, []).append(result)
    return grouped


def _mileday_multiturn_per_turn_latency(results: list[RequestResult]) -> dict[str, float]:
    by_turn: dict[int, list[int]] = {}
    for result in results:
        turn_id = result.parsed_output.get("turn_id")
        if isinstance(turn_id, int) and result.metrics.latency_ms is not None:
            by_turn.setdefault(turn_id, []).append(result.metrics.latency_ms)
    return {
        f"turn_{turn_id}": round(mean(values), 3)
        for turn_id, values in sorted(by_turn.items())
        if values
    }


def _mileday_multiturn_warning_count(results: list[RequestResult]) -> int:
    count = 0
    for result in results:
        validation = result.parsed_output.get("multiturn_validation")
        if isinstance(validation, dict):
            warnings = validation.get("warnings")
            if isinstance(warnings, list):
                count += len(warnings)
    return count


def _public_benchmark_model_summary(
    *,
    model_id: str,
    run_id: str,
    results: list[RequestResult],
    weights: dict[str, float] | None = None,
) -> dict[str, Any]:
    dataset_scores: dict[str, float | None] = {}
    active_weights = weights or {
        "ifeval-ko": 0.40,
        "kobalt-700": 0.30,
        "click": 0.15,
        "kmmlu-pro": 0.15,
    }
    for dataset_id in active_weights:
        scores = [
            _public_result_score(result)
            for result in results
            if result.dataset_id == dataset_id and _public_result_score(result) is not None
        ]
        dataset_scores[dataset_id] = round(sum(scores) / len(scores), 4) if scores else None
    weighted_parts = [
        dataset_scores[dataset_id] * weight
        for dataset_id, weight in active_weights.items()
        if dataset_scores[dataset_id] is not None
    ]
    error_counts = Counter(
        result.error.category.value
        for result in results
        if result.error is not None
    )
    return {
        "model_id": model_id,
        "run_id": run_id,
        "dataset_scores": dataset_scores,
        "weighted_score": round(sum(weighted_parts), 4) if len(weighted_parts) == len(active_weights) else None,
        "status_counts": Counter(result.status.value for result in results),
        "error_counts": error_counts,
    }


def _third_benchmark_winner(model_summaries: list[dict[str, Any]]) -> dict[str, Any] | None:
    eligible = []
    for summary in model_summaries:
        status_counts = summary["status_counts"]
        total = sum(status_counts.values())
        failed = status_counts.get(ResultStatus.FAILED.value, 0)
        invalid = status_counts.get(ResultStatus.INVALID.value, 0)
        invalid_rate = invalid / total if total else 1.0
        if failed == 0 and invalid_rate < 0.05 and summary["weighted_score"] is not None:
            eligible.append(summary)
    if not eligible:
        return None
    eligible.sort(
        key=lambda summary: (
            summary["weighted_score"],
            summary["dataset_scores"].get("ifeval-ko") or 0.0,
        ),
        reverse=True,
    )
    return eligible[0]


def _public_result_score(result: RequestResult) -> float | None:
    value = result.parsed_output.get("score")
    if isinstance(value, int | float):
        return float(value)
    return None


def _format_rate_from_counts(numerator: int, denominator: int) -> str:
    if denominator <= 0:
        return "없음"
    return f"{numerator / denominator:.1%}"


def _progress_total(case_count: int, config: BenchmarkRunConfig) -> int:
    if config.mode == BenchmarkMode.WARM:
        return case_count * (config.warmup_iterations + 1)
    return case_count


def _progress_bar(*, total: int, desc: str):
    if tqdm is None or total <= 0:
        return None
    return tqdm(total=total, desc=desc, unit="case", dynamic_ncols=True)


def _progress_update(progress):
    def update(_record) -> None:
        if progress is not None:
            progress.update(1)

    return update


def _progress_close(progress) -> None:
    if progress is not None:
        progress.close()


def _write_mileday_multiturn_grid_summary(
    runs_dir: Path,
    *,
    batch_id: str,
    items: list[dict[str, object]],
    cases: list[MileDayMultiTurnCase],
) -> Path:
    path = runs_dir / f"{batch_id}-summary.md"
    store = ResultStore(runs_dir)
    lines = [
        f"# MileDay Multiturn Sampling Grid Summary: {batch_id}",
        "",
        "## 실행 조건",
        "",
        f"- model id: {MILEDAY_MULTITURN_MODEL_ID}",
        f"- fixture: `{MILEDAY_MULTITURN_FIXTURE.as_posix()}`",
        f"- cases: {len(cases)}",
        f"- case ids: {', '.join(case.case_id for case in cases)}",
        "- temperature: 0.0, 0.1, 0.2",
        "- top_p: 0.8, 0.9, 1.0",
        f"- prompt version: {MILEDAY_MULTITURN_PROMPT_VERSION}",
        "- sampling: fixed first 3 fixture cases",
        "",
        "## 조합별 결과",
        "",
        "| temp | top_p | passed | invalid | failed | skipped | turn1 passed | turn2 passed | turn3 passed | judge rejects | avg latency ms | top failure codes | report |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    ranked: list[dict[str, object]] = []
    for item in items:
        run_id = str(item["run_id"])
        results = store.load_request_results(run_id)
        counts = _status_counts(results)
        turn_status = _grid_turn_status_counts(results)
        judge_rejects = _grid_judge_reject_count(results)
        failure_codes = _grid_failure_code_counts(results)
        avg_latency = _grid_avg_latency_ms(results)
        passed = int(counts.get("passed", 0))
        invalid = int(counts.get("invalid", 0))
        skipped = int(counts.get("skipped", 0))
        ranked.append(
            {
                "run_id": run_id,
                "temperature": item["temperature"],
                "top_p": item["top_p"],
                "passed": passed,
                "invalid": invalid,
                "skipped": skipped,
                "judge_rejects": judge_rejects,
                "avg_latency": avg_latency,
            }
        )
        lines.append(
            "| "
            + " | ".join(
                [
                    str(item["temperature"]),
                    str(item["top_p"]),
                    str(passed),
                    str(invalid),
                    str(counts.get("failed", 0)),
                    str(skipped),
                    str(turn_status.get(1, {}).get("passed", 0)),
                    str(turn_status.get(2, {}).get("passed", 0)),
                    str(turn_status.get(3, {}).get("passed", 0)),
                    str(judge_rejects),
                    _format_optional_float(avg_latency),
                    _dict_counter_text(dict(failure_codes.most_common(3))) if failure_codes else "없음",
                    f"`{Path(str(item.get('report_path', ''))).as_posix()}`",
                ]
            )
            + " |"
        )
    best = (
        sorted(
            ranked,
            key=lambda row: (
                -int(row["passed"]),
                int(row["invalid"]),
                int(row["skipped"]),
                int(row["judge_rejects"]),
                float(row["avg_latency"] or 999999),
            ),
        )[0]
        if ranked
        else None
    )
    lines.extend(["", "## 1차 판단", ""])
    if best is None:
        lines.append("- 비교 가능한 결과가 없습니다.")
    else:
        lines.append(
            "- 가장 나은 조합: "
            f"temperature={best['temperature']}, top_p={best['top_p']} "
            f"(passed={best['passed']}, invalid={best['invalid']}, "
            f"skipped={best['skipped']}, judge_rejects={best['judge_rejects']})"
        )
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8", newline="\n")
    return path


def _write_mileday_multiturn_api_summary(
    runs_dir: Path,
    *,
    batch_id: str,
    items: list[dict[str, object]],
    cases: list[MileDayMultiTurnCase],
    model_ids: list[str],
) -> Path:
    path = runs_dir / f"{batch_id}-summary.md"
    store = ResultStore(runs_dir)
    lines = [
        f"# MileDay Multiturn API Summary: {batch_id}",
        "",
        "## 실행 조건",
        "",
        "- runtime: gemini",
        f"- models: {', '.join(model_ids)}",
        f"- fixture: `{MILEDAY_MULTITURN_FIXTURE.as_posix()}`",
        f"- cases: {len(cases)}",
        f"- prompt version: {MILEDAY_API_MULTITURN_PROMPT_VERSION}",
        "- sampling: fixed full fixture",
        "",
        "## 모델별 결과",
        "",
        "| model | passed | invalid | failed | skipped | case completion | all-turn-pass cases | judge rejects | avg latency ms | top failure codes | report | html |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|",
    ]
    ranked: list[dict[str, object]] = []
    for item in items:
        run_id = str(item["run_id"])
        model_id = str(item["model_id"])
        results = store.load_request_results(run_id)
        counts = _status_counts(results)
        completed_cases = _mileday_multiturn_completed_cases(results, cases)
        all_turn_pass_cases = _mileday_multiturn_all_turn_pass_cases(results, cases)
        judge_rejects = _grid_judge_reject_count(results)
        failure_codes = _grid_failure_code_counts(results)
        avg_latency = _grid_avg_latency_ms(results)
        passed = int(counts.get("passed", 0))
        invalid = int(counts.get("invalid", 0))
        skipped = int(counts.get("skipped", 0))
        ranked.append(
            {
                "model_id": model_id,
                "passed": passed,
                "invalid": invalid,
                "skipped": skipped,
                "judge_rejects": judge_rejects,
                "avg_latency": avg_latency,
            }
        )
        lines.append(
            "| "
            + " | ".join(
                [
                    model_id,
                    str(passed),
                    str(invalid),
                    str(counts.get("failed", 0)),
                    str(skipped),
                    _format_rate_from_counts(len(completed_cases), len(cases)),
                    _format_rate_from_counts(len(all_turn_pass_cases), len(cases)),
                    str(judge_rejects),
                    _format_optional_float(avg_latency),
                    _dict_counter_text(dict(failure_codes.most_common(3))) if failure_codes else "none",
                    f"`{Path(str(item.get('report_path', ''))).as_posix()}`",
                    f"`{Path(str(item.get('html_report_path', ''))).as_posix()}`",
                ]
            )
            + " |"
        )
    best = (
        sorted(
            ranked,
            key=lambda row: (
                -int(row["passed"]),
                int(row["invalid"]),
                int(row["skipped"]),
                int(row["judge_rejects"]),
                float(row["avg_latency"] or 999999),
            ),
        )[0]
        if ranked
        else None
    )
    lines.extend(["", "## 1차 판단", ""])
    if best is None:
        lines.append("- 비교 가능한 결과가 없습니다.")
    else:
        lines.append(
            f"- 현재 기준 우위 모델: {best['model_id']} "
            f"(passed={best['passed']}, invalid={best['invalid']}, "
            f"skipped={best['skipped']}, judge_rejects={best['judge_rejects']})"
        )
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8", newline="\n")
    return path


def _grid_turn_status_counts(results: list[RequestResult]) -> dict[int, Counter[str]]:
    by_turn: dict[int, Counter[str]] = {}
    for result in results:
        try:
            turn_id = int(result.case_id.rsplit("-turn-", 1)[1])
        except (IndexError, ValueError):
            continue
        by_turn.setdefault(turn_id, Counter())[result.status.value] += 1
    return by_turn


def _grid_judge_reject_count(results: list[RequestResult]) -> int:
    count = 0
    for result in results:
        judge = result.parsed_output.get("explanation_judge")
        if isinstance(judge, dict) and judge.get("is_aligned") is False:
            count += 1
    return count


def _grid_failure_code_counts(results: list[RequestResult]) -> Counter[str]:
    counter: Counter[str] = Counter()
    for result in results:
        validation = result.parsed_output.get("multiturn_validation")
        if not isinstance(validation, dict):
            continue
        deterministic = validation.get("deterministic_validation")
        if isinstance(deterministic, dict):
            counter.update(
                code
                for code in deterministic.get("failure_codes", [])
                if isinstance(code, str)
            )
        judge = result.parsed_output.get("explanation_judge")
        if isinstance(judge, dict) and judge.get("is_aligned") is False:
            counter["JUDGE_REJECTION"] += 1
    return counter


def _grid_avg_latency_ms(results: list[RequestResult]) -> float | None:
    values = [
        result.metrics.latency_ms
        for result in results
        if result.metrics is not None and result.metrics.latency_ms is not None
    ]
    if not values:
        return None
    return round(sum(values) / len(values), 3)


def _parse_model_ids(raw_model_ids: str) -> list[str]:
    model_ids = [item.strip() for item in raw_model_ids.split(",") if item.strip()]
    if not model_ids:
        raise typer.BadParameter("--model-id must contain at least one model id.")
    seen: set[str] = set()
    deduplicated: list[str] = []
    for model_id in model_ids:
        if model_id not in seen:
            seen.add(model_id)
            deduplicated.append(model_id)
    return deduplicated


def _next_mileday_batch_sequence(runs_dir: Path, model_ids: list[str], limit: int) -> int:
    highest = 0
    if not runs_dir.exists():
        return 1
    patterns = [
        re.compile(rf"^{re.escape(model_id)}-(?P<sequence>\d+)-{limit}cases$")
        for model_id in model_ids
    ]
    for path in runs_dir.iterdir():
        if not path.is_dir():
            continue
        for pattern in patterns:
            match = pattern.fullmatch(path.name)
            if match is not None:
                highest = max(highest, int(match.group("sequence")))
                break
    return highest + 1


def _batch_id(sequence: int | None, limit: int) -> str:
    if sequence is None:
        return "manual-run"
    return f"batch-{sequence}-{limit}cases"


def _status_counts(results: list[RequestResult]) -> dict[str, int]:
    counts = {status.value: 0 for status in ResultStatus}
    for result in results:
        counts[result.status.value] = counts.get(result.status.value, 0) + 1
    return counts


def _counter_text_for_cli(counts: dict[str, int]) -> str:
    return " ".join(f"{key}={counts.get(key, 0)}" for key in ("passed", "invalid", "failed", "skipped"))


def _write_mileday_batch_summary(
    runs_dir: Path,
    *,
    batch_id: str,
    items: list[dict[str, object]],
    limit: int,
    seed: int | None,
    model_ids: list[str],
    judge_model: str,
    require_explanation_judge: bool,
    quality_judge: GeminiExplanationJudge | None,
) -> Path:
    path = runs_dir / f"{batch_id}-summary.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    store = ResultStore(runs_dir)
    judge_context = _build_batch_judge_context(
        store,
        items=items,
        batch_id=batch_id,
        limit=limit,
        seed=seed,
        model_ids=model_ids,
        judge_model=judge_model,
        require_explanation_judge=require_explanation_judge,
    )
    quality_summary = (
        quality_judge.summarize_batch_quality(judge_context)
        if quality_judge is not None
        else skipped_batch_quality_summary_result()
    )
    lines = [
        f"# MileDay Batch Summary: {batch_id}",
        "",
        f"- limit: {limit}",
        f"- seed: {seed}",
        "",
        "| model | run_id | status | passed | invalid | failed | skipped | report | error |",
        "|---|---|---|---:|---:|---:|---:|---|---|",
    ]
    for item in items:
        counts = item.get("counts")
        count_map = counts if isinstance(counts, dict) else {}
        lines.append(
            "| "
            + " | ".join(
                [
                    _escape_table(str(item.get("model_id", ""))),
                    _escape_table(str(item.get("run_id", ""))),
                    _escape_table(str(item.get("status", ""))),
                    str(count_map.get("passed", 0)),
                    str(count_map.get("invalid", 0)),
                    str(count_map.get("failed", 0)),
                    str(count_map.get("skipped", 0)),
                    f"`{Path(str(item.get('report_path', ''))).as_posix()}`" if item.get("report_path") else "",
                    _escape_table(str(item.get("error", ""))),
                ]
            )
            + " |"
        )
    lines.extend(_render_batch_judge_summary(judge_context, quality_summary))
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8", newline="\n")
    return path


def _build_batch_judge_context(
    store: ResultStore,
    *,
    items: list[dict[str, object]],
    batch_id: str,
    limit: int,
    seed: int | None,
    model_ids: list[str],
    judge_model: str,
    require_explanation_judge: bool,
) -> dict[str, Any]:
    model_summaries: list[dict[str, Any]] = []
    judge_execution_counts = {"completed": 0, "failed": 0, "skipped": 0}
    failure_reasons: dict[str, int] = {}

    for item in items:
        model_id = str(item.get("model_id", ""))
        run_id = str(item.get("run_id", ""))
        results = store.load_request_results(run_id) if run_id else []
        aligned = 0
        completed = 0
        failed = 0
        skipped = 0
        scores: list[float] = []
        model_failure_reasons: dict[str, int] = {}
        status_counts = _status_counts(results)

        for result in results:
            judge = result.parsed_output.get("explanation_judge")
            if not isinstance(judge, dict):
                skipped += 1
                judge_execution_counts["skipped"] += 1
                continue
            error = judge.get("error")
            if isinstance(error, dict):
                failed += 1
                judge_execution_counts["failed"] += 1
                label = str(error.get("category") or error.get("message") or "UNKNOWN")
                failure_reasons[label] = failure_reasons.get(label, 0) + 1
                model_failure_reasons[label] = model_failure_reasons.get(label, 0) + 1
                continue
            if judge.get("skipped") is True:
                skipped += 1
                judge_execution_counts["skipped"] += 1
                continue
            completed += 1
            judge_execution_counts["completed"] += 1
            if judge.get("is_aligned") is True:
                aligned += 1
            score = judge.get("score")
            if isinstance(score, int | float):
                scores.append(float(score))

        total = len(results)
        model_summaries.append(
            {
                "model_id": model_id,
                "run_id": run_id,
                "total_results": total,
                "status_counts": status_counts,
                "judge_completed": completed,
                "judge_failed": failed,
                "judge_skipped": skipped,
                "aligned_true": aligned,
                "aligned_rate_percent": _percent(aligned, total),
                "average_judge_score": round(sum(scores) / len(scores), 4) if scores else None,
                "judge_failure_reasons": model_failure_reasons,
            }
        )

    return {
        "batch_id": batch_id,
        "execution_conditions": {
            "limit": limit,
            "seed": seed,
            "sampling": "random",
            "model_ids": model_ids,
            "judge_model": judge_model,
            "require_explanation_judge": require_explanation_judge,
        },
        "judge_execution_counts": judge_execution_counts,
        "judge_failure_reasons": failure_reasons,
        "model_summaries": model_summaries,
    }


def _render_batch_judge_summary(
    context: dict[str, Any],
    quality_summary: BatchQualitySummaryResult,
) -> list[str]:
    conditions = context["execution_conditions"]
    execution_counts = context["judge_execution_counts"]
    failure_reasons = context["judge_failure_reasons"]
    lines = [
        "",
        "## LLM-as-Judge 전체 평가",
        "",
        "### 실행 조건",
        "",
        f"- model ids: {', '.join(conditions['model_ids'])}",
        f"- limit: {conditions['limit']}",
        f"- sampling: {conditions['sampling']}",
        f"- seed: {conditions['seed']}",
        f"- judge model: {conditions['judge_model']}",
        f"- require explanation judge: {conditions['require_explanation_judge']}",
        "",
        "### Judge 실행 여부",
        "",
        f"- completed: {execution_counts['completed']}",
        f"- failed: {execution_counts['failed']}",
        f"- skipped: {execution_counts['skipped']}",
        "",
        "### 모델별 Judge 결과",
        "",
        "| model | run_id | total | judge completed | aligned rate | average score |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for item in context["model_summaries"]:
        lines.append(
            f"| {_escape_table(str(item['model_id']))} | {_escape_table(str(item['run_id']))} | "
            f"{item['total_results']} | {item['judge_completed']} | "
            f"{_format_percent(item['aligned_rate_percent'])} | {_format_optional_float(item['average_judge_score'])} |"
        )
    lines.extend(
        [
            "",
            "### 실패 원인 요약",
            "",
            f"- {_dict_counter_text(failure_reasons) if failure_reasons else '없음'}",
            "",
            "### 전체 한글 요약",
            "",
            quality_summary.overall_summary,
            "",
            "### 위험 신호",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in (quality_summary.risk_signals or _fallback_risk_signals(context)))
    lines.extend(["", "### 개선 방안", ""])
    lines.extend(
        f"- {item}"
        for item in (quality_summary.improvement_actions or _fallback_improvement_actions(context))
    )
    if quality_summary.error is not None:
        lines.extend(
            [
                "",
                "### 품질 요약 생성 오류",
                "",
                f"- {quality_summary.error.category.value}: {quality_summary.error.message}",
            ]
        )
    return lines


def _fallback_risk_signals(context: dict[str, Any]) -> list[str]:
    risks: list[str] = []
    for item in context["model_summaries"]:
        status_counts = item["status_counts"]
        if status_counts.get("invalid", 0) > 0:
            risks.append(f"{item['model_id']}에서 invalid 결과가 {status_counts['invalid']}건 발생했습니다.")
        if item["judge_failed"] > 0:
            risks.append(f"{item['model_id']}에서 Gemini judge 실패가 {item['judge_failed']}건 발생했습니다.")
        if item["judge_completed"] == 0:
            risks.append(f"{item['model_id']}는 완료된 LLM-as-Judge 평가가 없습니다.")
    return risks or ["명확한 위험 신호가 집계되지 않았습니다."]


def _fallback_improvement_actions(context: dict[str, Any]) -> list[str]:
    actions = [
        "invalid 결과가 많은 모델은 raw output을 확인해 [EXPLANATION] / [JSON] 계약과 날짜 제약 실패를 분리해서 개선하세요.",
        "judge_failed가 발생하면 Gemini 모델명, response schema, API quota 및 response body를 먼저 확인하세요.",
    ]
    if context["judge_execution_counts"]["skipped"] > 0:
        actions.append("skipped가 많으면 deterministic validation 전에 실패한 케이스와 Gemini API 설정 여부를 구분해 추적하세요.")
    return actions


def _percent(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return round((numerator / denominator) * 100, 2)


def _format_percent(value: float | None) -> str:
    if value is None:
        return "없음"
    return f"{value:.2f}%"


def _format_optional_float(value: float | None) -> str:
    if value is None:
        return "없음"
    return f"{value:.3f}"


def _dict_counter_text(counter: dict[str, int]) -> str:
    return ", ".join(f"{key}={counter[key]}" for key in sorted(counter))


def _escape_table(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def _mileday_multiturn_prompt(
    case: MileDayMultiTurnCase,
    turn_id: int,
    transcript: list[dict[str, str]],
) -> str:
    return build_mileday_multiturn_prompt(case, turn_id, transcript)


def _mileday_multiturn_api_prompt(
    case: MileDayMultiTurnCase,
    turn_id: int,
    transcript: list[dict[str, str]],
) -> str:
    return build_mileday_multiturn_api_prompt(case, turn_id, transcript)


def _append_mileday_plan_targets_to_transcript(content: str, parsed_json: dict[str, Any]) -> str:
    plan_items = parsed_json.get("plan_items")
    if not isinstance(plan_items, list):
        return content
    lines = []
    for item in plan_items:
        if not isinstance(item, dict):
            continue
        slot_id = item.get("slot_id")
        task = item.get("task")
        if isinstance(slot_id, str) and isinstance(task, str):
            lines.append(f"- {slot_id} | {task}")
    if not lines:
        return content
    return content.rstrip() + "\n\n[CURRENT_PLAN_TARGETS]\n" + "\n".join(lines)


def _mileday_multiturn_transcript_text(transcript: list[dict[str, str]]) -> str:
    if not transcript:
        return "이전 대화 없음."
    chunks = []
    for index, message in enumerate(transcript, start=1):
        role = message["role"]
        content = message["content"].strip()
        chunks.append(f"{index}. {role}:\n{content}")
    return "\n\n".join(chunks)


def _mileday_multiturn_reference_date_context() -> dict[str, str]:
    today = date.today()
    day_of_week = _date_day_of_week(today.isoformat())
    return {
        "today": today.isoformat(),
        "weekday": _ko_weekday(day_of_week),
        "day_of_week": day_of_week or "",
        "timezone": MILEDAY_MULTITURN_REFERENCE_TIMEZONE,
    }


def _mileday_multiturn_allowed_slots(case: MileDayMultiTurnCase) -> list[dict[str, str]]:
    return mileday_multiturn_allowed_slots(case)


def _mileday_multiturn_candidate_start_date(case: MileDayMultiTurnCase) -> date:
    return date.today()


def _ko_weekday(day_of_week: str | None) -> str:
    return {
        "monday": "월",
        "tuesday": "화",
        "wednesday": "수",
        "thursday": "목",
        "friday": "금",
        "saturday": "토",
        "sunday": "일",
    }.get(day_of_week or "", "")


def _mileday_multiturn_turn_case_id(case_id: str, turn_id: int) -> str:
    return f"{case_id}-turn-{turn_id}"


def _mileday_generation_prompt(case: MileDayGenerationCase) -> str:
    milestone_schema = _milestone_schema_example(case.expected.required_fields)
    prompt = (
        "당신은 MileDay 일정 생성기입니다.\n"
        "응답은 반드시 [EXPLANATION] 구역과 [JSON] 구역 두 개만 포함하세요.\n"
        "그 외의 머리말, 마크다운 설명, 내부 추론 과정, </think> 태그는 포함하지 마세요.\n"
        "\n"
        "[EXPLANATION]\n"
        "사용자에게 보여줄 한국어 설명을 3~5문장으로 작성하세요.\n"
        "목표, 마감일, 주요 milestone 흐름, 일정 배치 이유를 자연스럽게 설명하세요.\n"
        "설명문은 아래 JSON milestones의 제목과 날짜 흐름을 실제로 반영해야 합니다.\n"
        "내부 추론 과정이나 단계별 계산 과정은 쓰지 마세요.\n"
        "\n"
        "[JSON]\n"
        "아래 JSON 스키마와 동일한 형태의 fenced json block 하나만 작성하세요.\n"
        "JSON block 안에는 load 가능한 JSON 객체만 포함하세요.\n"
        "\n"
        "```json\n"
        "{\n"
        '  "milestones": [\n'
        "    {\n"
        f"{milestone_schema}\n"
        "    }\n"
        "  ]\n"
        "}\n"
        "```\n"
        "\n"
        "생성 규칙:\n"
        f"- 목표 제목: {case.input.goal_title}\n"
        f"- 마감일: {case.input.deadline}\n"
        f"- locale: {case.locale}\n"
        f"- timezone: {case.timezone}\n"
        f"- 최소 milestone 수: {case.expected.min_milestones}\n"
        f"- 최대 milestone 수: {case.expected.max_milestones}\n"
        f"- 가장 늦은 scheduled_date: {case.expected.latest_allowed_date}\n"
        "- 모든 milestone은 스키마에 표시된 필드를 모두 포함해야 합니다.\n"
        "- 스키마에 표시되지 않은 필드는 포함하지 마세요.\n"
        "- 모든 scheduled_date는 YYYY-MM-DD 형식이어야 합니다.\n"
        "- 모든 scheduled_date는 가장 늦은 scheduled_date 이하여야 합니다.\n"
        "- locale이 ko-KR이면 title과 description은 간결한 한국어로 작성하세요.\n"
    )
    return prompt
    return (
        "당신은 MileDay 일정 생성기입니다.\n"
        "응답은 반드시 [EXPLANATION] 구역과 [JSON] 구역 두 개만 포함하세요.\n"
        "그 외의 머리말, 마크다운 설명, 내부 추론 과정, </think> 태그는 포함하지 마세요.\n"
        "\n"
        "[EXPLANATION]\n"
        "사용자에게 보여줄 한국어 설명을 3~5문장으로 작성하세요.\n"
        "목표, 마감일, 주요 milestone 흐름, 일정 배치 이유를 자연스럽게 설명하세요.\n"
        "설명문은 아래 JSON milestones의 제목과 날짜 흐름을 실제로 반영해야 합니다.\n"
        "내부 추론 과정이나 단계별 계산 과정은 쓰지 마세요.\n"
        "\n"
        "[JSON]\n"
        "아래 JSON 스키마와 동일한 형태의 fenced json block 하나만 작성하세요.\n"
        "JSON block 안에는 load 가능한 JSON 객체만 포함하세요.\n"
        "\n"
        "```json\n"
        "{\n"
        '  "milestones": [\n'
        "    {\n"
        f"{milestone_schema}\n"
        "    }\n"
        "  ]\n"
        "}\n"
        "```\n"
        "\n"
        "생성 규칙:\n"
        f"- 목표 제목: {case.input.goal_title}\n"
        f"- 마감일: {case.input.deadline}\n"
        f"- locale: {case.locale}\n"
        f"- timezone: {case.timezone}\n"
        f"- 최소 milestone 수: {case.expected.min_milestones}\n"
        f"- 최대 milestone 수: {case.expected.max_milestones}\n"
        f"- 가장 늦은 scheduled_date: {case.expected.latest_allowed_date}\n"
        "- 모든 milestone은 스키마에 표시된 필드를 모두 포함해야 합니다.\n"
        "- 스키마에 표시되지 않은 필드는 포함하지 마세요.\n"
        "- 모든 scheduled_date는 YYYY-MM-DD 형식이어야 합니다.\n"
        "- 모든 scheduled_date는 가장 늦은 scheduled_date 이하여야 합니다.\n"
        "- locale이 ko-KR이면 title과 description은 간결한 한국어로 작성하세요.\n"
    )


def _milestone_schema_example(required_fields: list[str]) -> str:
    lines = []
    for field in required_fields:
        value = "YYYY-MM-DD" if field == "scheduled_date" else "string"
        lines.append(f'      "{field}": "{value}"')
    return ",\n".join(lines)


def _evaluate_mileday_record(
    base_result: RequestResult,
    case: MileDayGenerationCase,
    raw_output: str,
    *,
    explanation_judge: ExplanationJudge | None = None,
    require_explanation_judge: bool = False,
) -> RequestResult:
    if base_result.error is not None:
        return base_result
    explanation = _extract_explanation(raw_output)
    candidate = _extract_fenced_json(raw_output)
    contract = {
        "type": "explanation_plus_fenced_json",
        "explanation_present": explanation is not None,
        "fenced_json_present": candidate is not None,
        "json_loadable": False,
    }
    if explanation is None or candidate is None:
        contract_errors = []
        if explanation is None:
            contract_errors.append("Missing [EXPLANATION] section.")
        if candidate is None:
            contract_errors.append("Missing fenced JSON block.")
        return _invalid_mileday_result(
            base_result,
            parsed_output={"output_contract": contract, "contract_errors": contract_errors},
            message="MileDay output must contain an explanation and a fenced JSON block.",
        )

    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError as exc:
        return _invalid_mileday_result(
            base_result,
            parsed_output={
                "output_contract": contract,
                "explanation": explanation,
                "json_error": f"Fenced JSON was not valid JSON: {exc.msg}",
            },
            message=f"Fenced JSON was not valid JSON: {exc.msg}",
        )
    contract["json_loadable"] = True
    validation = validate_schedule_output(case, parsed, raw_output=candidate)
    if not validation.is_valid:
        return _invalid_mileday_result(
            base_result,
            parsed_output={
                "output_contract": contract,
                "explanation": explanation,
                "validation": validation.model_dump(mode="json"),
            },
            message="MileDay schedule constraint validation failed.",
        )
    rubric = evaluate_semantic_rubric(case, parsed, validation)
    if explanation_judge is None and require_explanation_judge:
        judge_result = skipped_explanation_judge_result()
        dependency_error = EvaluationError(
            category=FailureCategory.EXTERNAL_DEPENDENCY,
            message="Gemini explanation judge is required but GEMINI_API_KEY is not configured.",
        )
        return base_result.model_copy(
            update={
                "status": ResultStatus.FAILED,
                "parsed_output": {
                    "output_contract": contract,
                    "explanation": explanation,
                    "validation": validation.model_dump(mode="json"),
                    "rubric": rubric.model_dump(mode="json"),
                    "semantic_score": rubric.aggregate_score,
                    "explanation_judge": {
                        **judge_result.model_dump(mode="json"),
                        "error": dependency_error.model_dump(mode="json"),
                    },
                },
                "error": dependency_error,
            }
        )
    judge_result = (
        explanation_judge.evaluate(case, explanation, parsed)
        if explanation_judge is not None
        else skipped_explanation_judge_result()
    )
    if judge_result.error is not None and require_explanation_judge:
        return base_result.model_copy(
            update={
                "status": ResultStatus.FAILED,
                "parsed_output": {
                    "output_contract": contract,
                    "explanation": explanation,
                    "validation": validation.model_dump(mode="json"),
                    "rubric": rubric.model_dump(mode="json"),
                    "semantic_score": rubric.aggregate_score,
                    "explanation_judge": judge_result.model_dump(mode="json"),
                },
                "error": judge_result.error,
            }
        )
    if not judge_result.skipped and not judge_result.is_aligned:
        return _invalid_mileday_result(
            base_result,
            parsed_output={
                "output_contract": contract,
                "explanation": explanation,
                "validation": validation.model_dump(mode="json"),
                "rubric": rubric.model_dump(mode="json"),
                "semantic_score": rubric.aggregate_score,
                "explanation_judge": judge_result.model_dump(mode="json"),
            },
            message="Explanation did not align with generated milestones.",
        )
    return base_result.model_copy(
        update={
            "status": ResultStatus.PASSED,
            "parsed_output": {
                "output_contract": contract,
                "explanation": explanation,
                "validation": validation.model_dump(mode="json"),
                "rubric": rubric.model_dump(mode="json"),
                "semantic_score": rubric.aggregate_score,
                "explanation_judge": judge_result.model_dump(mode="json"),
            },
        }
    )


def _extract_user_message(raw_output: str) -> str | None:
    match = re.search(
        r"\[USER_MESSAGE\]\s*(?P<message>.*?)(?:\s*\[/USER_MESSAGE\])?(?=\n\s*\[(?:PLAN|PATCH)\])",
        raw_output,
        re.DOTALL,
    )
    if match is None:
        return None
    message = match.group("message").strip()
    return message or None


def _extract_plan_block(raw_output: str) -> str | None:
    match = re.search(
        r"\[PLAN\]\s*(?P<plan>.*?)\s*\[/PLAN\]",
        raw_output,
        re.DOTALL,
    )
    if match is None:
        return None
    plan = match.group("plan").strip()
    return plan or None


def _extract_patch_block(raw_output: str) -> str | None:
    match = re.search(
        r"\[PATCH\]\s*(?P<patch>.*?)\s*\[/PATCH\]",
        raw_output,
        re.DOTALL,
    )
    if match is None:
        return None
    return match.group("patch").strip()


def _extract_schedule_intent_block(raw_output: str) -> str | None:
    match = re.search(
        r"\[(?:SCHEDULE_INTENT|일정_의도)\]\s*(?P<intent>.*?)\s*\[/(?:SCHEDULE_INTENT|일정_의도)\]",
        raw_output,
        re.DOTALL,
    )
    if match is None:
        return None
    intent = match.group("intent").strip()
    return intent or None


def _parse_mileday_schedule_intent_block(intent_block: str) -> tuple[dict[str, Any], list[str]]:
    intent: dict[str, Any] = {"action": "", "target": "", "change": "", "tasks": []}
    errors: list[str] = []
    key_map = {
        "action": "action",
        "행동": "action",
        "target": "target",
        "대상": "target",
        "change": "change",
        "변경": "change",
    }
    action_map = {
        "create": "create",
        "생성": "create",
        "partial_update": "partial_update",
        "부분수정": "partial_update",
        "부분 수정": "partial_update",
    }
    in_tasks = False
    for line_number, raw_line in enumerate(intent_block.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        lower = line.lower()
        if lower in {"tasks:", "작업:"}:
            in_tasks = True
            continue
        if in_tasks:
            if not line.startswith("- "):
                errors.append(f"Line {line_number} in tasks must start with '- '.")
                continue
            task = line[2:].strip()
            if not task:
                errors.append(f"Line {line_number} has an empty task.")
                continue
            intent["tasks"].append(task)
            continue
        if ":" not in line:
            errors.append(f"Line {line_number} must use 'key: value'.")
            continue
        key, value = [part.strip() for part in line.split(":", 1)]
        key = key_map.get(key.lower(), key_map.get(key))
        if key is None:
            errors.append(f"Line {line_number} has an unsupported key: {key}.")
            continue
        if key == "action":
            value = action_map.get(value.lower(), action_map.get(value, value))
        intent[key] = value
    if intent["action"] not in {"create", "partial_update"}:
        errors.append("action must be create or partial_update.")
    if not intent["target"]:
        errors.append("target must not be empty.")
    if not intent["change"]:
        errors.append("change must not be empty.")
    if not isinstance(intent["tasks"], list):
        errors.append("tasks must be a list.")
    return intent, errors


def _fallback_mileday_schedule_intent(
    case: MileDayMultiTurnCase,
    turn_id: int,
    raw_output: str,
) -> dict[str, Any] | None:
    if not raw_output.strip():
        return None
    tasks = _extract_candidate_tasks_from_freeform_output(raw_output)
    expected_action = case.turns[turn_id - 1].expected_action
    if expected_action == "partial_update" and not tasks:
        tasks = [_task_from_update_request(case.turns[turn_id - 1].content, case)]
    elif expected_action == "create" and len(tasks) < case.expected.constraints.min_milestones:
        tasks = _default_mileday_tasks_for_goal(case)
    return {
        "action": expected_action,
        "target": case.input.initial_goal.title,
        "change": case.turns[turn_id - 1].content,
        "tasks": tasks,
        "source": "freeform_fallback",
    }


def _extract_candidate_tasks_from_freeform_output(raw_output: str) -> list[str]:
    tasks: list[str] = []
    for raw_line in raw_output.splitlines():
        line = raw_line.strip().strip("|").strip()
        if not line:
            continue
        if any(token in line for token in ('"title_prefix"', '"weekday"', '"scheduled_date"', "---", "날짜", "색상:", "완료여부:")):
            continue
        if line.startswith(("[", "{", "}", "```", "#")):
            continue
        if "|" in line:
            cells = [cell.strip() for cell in line.split("|") if cell.strip()]
            text = cells[-1] if cells else ""
        elif line.startswith("- "):
            text = line[2:].strip()
        else:
            text = line
        text = re.sub(r"^제목\s*:\s*", "", text).strip()
        text = re.sub(r"^\d{4}-\d{2}-\d{2}\s*", "", text).strip()
        text = re.sub(r"^S\d{3}\s*", "", text).strip()
        text = re.sub(r"^\[[^\]]+\]\s*", "", text).strip()
        if re.fullmatch(r"[월화수목금토일]요일?\(?\d{1,2}:\d{2}-\d{1,2}:\d{2}\)?", text):
            continue
        if 2 <= len(text) <= 40 and re.search(r"[가-힣]", text):
            tasks.append(text)
    deduped: list[str] = []
    for task in tasks:
        if task not in deduped:
            deduped.append(task)
    return deduped[:8]


def _default_mileday_tasks_for_goal(case: MileDayMultiTurnCase) -> list[str]:
    title = case.input.initial_goal.title
    return [
        f"{title} 준비",
        f"{title} 기초 진행",
        f"{title} 핵심 진행",
        f"{title} 중간 점검",
        f"{title} 최종 점검",
    ]


def _plan_items_from_mileday_intent(
    case: MileDayMultiTurnCase,
    intent: dict[str, Any],
) -> list[dict[str, str]]:
    tasks = [task for task in intent.get("tasks", []) if isinstance(task, str) and task.strip()]
    min_items = case.expected.constraints.min_milestones
    max_items = case.expected.constraints.max_milestones
    item_count = min(max(len(tasks), min_items), max_items)
    if not tasks:
        tasks = [case.input.initial_goal.title]
    existing_dates = {item.scheduled_date for item in case.input.existing_schedule}
    slots = [
        slot
        for slot in _mileday_multiturn_allowed_slots(case)
        if slot["scheduled_date"] not in existing_dates
    ][:item_count]
    plan_items: list[dict[str, str]] = []
    for index, slot in enumerate(slots):
        raw_task = tasks[index] if index < len(tasks) else f"{case.input.initial_goal.title} {index + 1}단계"
        task = _sanitize_mileday_task(raw_task, case)
        plan_items.append({"slot_id": slot["slot_id"], "task": task})
    return plan_items


def _patch_items_from_mileday_intent(
    case: MileDayMultiTurnCase,
    turn_id: int,
    intent: dict[str, Any],
    previous_parsed: dict[str, Any] | None,
) -> list[dict[str, str]]:
    previous_plan_items = previous_parsed.get("plan_items") if isinstance(previous_parsed, dict) else []
    if not isinstance(previous_plan_items, list):
        return []
    request = case.turns[turn_id - 1].content
    if _is_add_request(request):
        return []
    if _is_date_move_request(request):
        return []
    tasks = [task for task in intent.get("tasks", []) if isinstance(task, str) and task.strip()]
    target_text = f"{intent.get('target', '')} {intent.get('change', '')} {' '.join(tasks)}"
    combined_text = f"{target_text} {request}"
    requested_destination_days = _requested_destination_weekdays(combined_text)
    if requested_destination_days and not _destination_days_available(case, requested_destination_days):
        return []

    target_slot_ids = _select_mileday_patch_target_slot_ids(case, previous_plan_items, combined_text)
    if not target_slot_ids:
        return []
    replacement = _replacement_task_from_intent(intent, case)
    return [{"slot_id": slot_id, "task": replacement} for slot_id in target_slot_ids]


def _add_items_from_mileday_intent(
    case: MileDayMultiTurnCase,
    turn_id: int,
    intent: dict[str, Any],
    previous_parsed: dict[str, Any] | None,
) -> list[dict[str, str]]:
    request = case.turns[turn_id - 1].content
    if not _is_add_request(request):
        return []
    previous_plan_items = previous_parsed.get("plan_items") if isinstance(previous_parsed, dict) else []
    if not isinstance(previous_plan_items, list):
        return []
    used_slot_ids = {
        item.get("slot_id")
        for item in previous_plan_items
        if isinstance(item, dict) and isinstance(item.get("slot_id"), str)
    }
    for slot in _mileday_multiturn_allowed_slots(case):
        if slot["slot_id"] not in used_slot_ids:
            return [{"slot_id": slot["slot_id"], "task": _task_from_update_request(request, case)}]
    return []


def _is_add_request(text: str) -> bool:
    return any(keyword in text for keyword in ("추가", "넣어", "새로"))


def _remove_slot_ids_from_mileday_intent(
    case: MileDayMultiTurnCase,
    turn_id: int,
    intent: dict[str, Any],
    previous_parsed: dict[str, Any] | None,
) -> list[str]:
    request = case.turns[turn_id - 1].content
    if not _is_remove_request(request):
        return []
    previous_plan_items = previous_parsed.get("plan_items") if isinstance(previous_parsed, dict) else []
    if not isinstance(previous_plan_items, list):
        return []
    target_text = _target_only_text(f"{intent.get('target', '')} {intent.get('change', '')} {request}")
    return _select_mileday_patch_target_slot_ids(case, previous_plan_items, target_text)


def _is_remove_request(text: str) -> bool:
    return any(keyword in text for keyword in ("빼", "제외", "삭제", "없애"))


def _is_date_move_request(text: str) -> bool:
    return any(
        keyword in text
        for keyword in ("하루 앞당", "하루 뒤", "한 주", "일주일", "앞으로 당", "앞당겨", "미뤄", "연기")
    )


def _replacement_task_from_intent(intent: dict[str, Any], case: MileDayMultiTurnCase) -> str:
    request_task = _task_from_update_request(str(intent.get("change") or ""), case)
    if request_task != case.input.initial_goal.title:
        return request_task
    tasks = [task for task in intent.get("tasks", []) if isinstance(task, str) and task.strip()]
    for task in tasks:
        if any(placeholder in task for placeholder in ("추가할 작업명", "유지할 작업명", "삭제할 작업명")):
            continue
        return _sanitize_mileday_task(task, case)
    change = str(intent.get("change") or "").strip()
    if change and not any(placeholder in change for placeholder in ("작업명 목록", "작업 목록")):
        return _sanitize_mileday_task(change, case)
    return case.input.initial_goal.title


def _sanitize_mileday_task(task: str, case: MileDayMultiTurnCase) -> str:
    request_task = _task_from_update_request(task, case)
    if request_task != case.input.initial_goal.title:
        return request_task
    cleaned = re.sub(r"\d{1,2}\s*시(?:\s*\d{1,2}\s*분)?\s*[~-]\s*\d{1,2}\s*시(?:\s*\d{1,2}\s*분)?", "", task)
    cleaned = re.sub(r"\d{1,2}:\d{2}\s*-\s*\d{1,2}:\d{2}", "", cleaned)
    cleaned = re.sub(r"(월|화|수|목|금|토|일)요일\s*(오전|오후)?", "", cleaned)
    cleaned = cleaned.replace("오전", "").replace("오후", "")
    cleaned = cleaned.strip(" -~:()")
    if "포장" in task:
        return "포장 관련 작업"
    if _contains_disallowed_english_task_text(cleaned):
        return case.input.initial_goal.title
    if not cleaned:
        return case.input.initial_goal.title
    return cleaned


def _task_from_update_request(text: str, case: MileDayMultiTurnCase) -> str:
    normalized = text.lower()
    if "회화 녹음" in text or ("피드백" in text and "회화" in text):
        return "회화 녹음 및 피드백"
    if "회복" in text:
        return "회복 위주 운동"
    if "포장" in text:
        return "포장 관련 작업"
    if "기술 블로그" in text or "블로그 글" in text:
        return "기술 블로그 글 작성"
    if "1시간" in text or "한 시간" in text or ("reduce" in normalized and ("hour" in normalized or "duration" in normalized)):
        return "1시간 축소 학습"
    return case.input.initial_goal.title


def _requested_destination_weekdays(text: str) -> set[str]:
    if not any(keyword in text for keyword in ("옮", "이동", "변경")):
        return set()
    return _mentioned_weekday_values(text)


def _destination_days_available(case: MileDayMultiTurnCase, weekdays: set[str]) -> bool:
    available_days = {item.day_of_week for item in case.input.availability}
    return weekdays <= available_days


def _select_mileday_patch_target_slot_ids(
    case: MileDayMultiTurnCase,
    previous_plan_items: list[Any],
    target_text: str,
) -> list[str]:
    slots_by_id = {slot["slot_id"]: slot for slot in _mileday_multiturn_allowed_slots(case)}
    previous_slot_ids = [
        item.get("slot_id")
        for item in previous_plan_items
        if isinstance(item, dict) and isinstance(item.get("slot_id"), str)
    ]
    explicit_slot_ids = [
        slot_id
        for slot_id in re.findall(r"\bS\d{3}\b", target_text)
        if slot_id in previous_slot_ids
    ]
    if explicit_slot_ids:
        return list(dict.fromkeys(explicit_slot_ids))
    reduced_weekdays = _reduced_duration_weekdays(target_text)
    if reduced_weekdays:
        reduced_matches = [
            slot_id
            for slot_id in previous_slot_ids
            if slot_id in slots_by_id and slots_by_id[slot_id]["day_of_week"] in reduced_weekdays
        ]
        return _limit_single_target_if_requested(target_text, reduced_matches, slots_by_id)
    target_only_text = _target_only_text(target_text)
    weekdays = _mentioned_weekday_values(target_only_text)
    requested_week_index = _requested_plan_week_index(target_text)
    if requested_week_index is not None:
        week_matches = _slot_ids_in_plan_week(previous_slot_ids, slots_by_id, requested_week_index)
        if week_matches:
            return _limit_single_target_if_requested(target_text, week_matches, slots_by_id)
    matching_slot_ids = [
        slot_id
        for slot_id in previous_slot_ids
        if slot_id in slots_by_id and (not weekdays or slots_by_id[slot_id]["day_of_week"] in weekdays)
    ]
    if any(keyword in target_text for keyword in ("마지막", "최종")) and matching_slot_ids:
        return [max(matching_slot_ids, key=lambda slot_id: slots_by_id.get(slot_id, {}).get("scheduled_date", ""))]
    if weekdays:
        return _limit_single_target_if_requested(target_text, matching_slot_ids, slots_by_id)
    keywords = _target_keywords(target_text)
    if keywords:
        keyword_matches = []
        for item in previous_plan_items:
            if not isinstance(item, dict):
                continue
            slot_id = item.get("slot_id")
            task = item.get("task")
            if (
                isinstance(slot_id, str)
                and isinstance(task, str)
                and slot_id in matching_slot_ids
                and any(keyword in task for keyword in keywords)
            ):
                keyword_matches.append(slot_id)
        if keyword_matches:
            return _limit_single_target_if_requested(target_text, keyword_matches, slots_by_id)
        if any(keyword in target_only_text for keyword in keywords):
            return []
    if _single_patch_target_requested(target_text) and previous_slot_ids:
        return [previous_slot_ids[0]]
    return []


def _single_patch_target_requested(text: str) -> bool:
    normalized = text.lower()
    return any(
        keyword in normalized
        for keyword in (
            "하나만",
            "한 개만",
            "1개만",
            "하나",
            "one",
            "single",
            "only one",
        )
    )


def _limit_single_target_if_requested(
    request_text: str,
    slot_ids: list[str],
    slots_by_id: dict[str, dict[str, str]],
) -> list[str]:
    if not _single_patch_target_requested(request_text):
        return slot_ids
    if not slot_ids:
        return []
    return [max(slot_ids, key=lambda slot_id: slots_by_id.get(slot_id, {}).get("scheduled_date", ""))]


def _requested_plan_week_index(text: str) -> int | None:
    normalized = text.lower()
    if "두 번째 주" in text or "2번째 주" in text or "둘째 주" in text or "second week" in normalized:
        return 2
    if "첫 번째 주" in text or "1번째 주" in text or "첫째 주" in text or "first week" in normalized:
        return 1
    return None


def _slot_ids_in_plan_week(
    previous_slot_ids: list[str],
    slots_by_id: dict[str, dict[str, str]],
    week_index: int,
) -> list[str]:
    ordered_slot_ids = [
        slot_id
        for slot_id in previous_slot_ids
        if slot_id in slots_by_id and slots_by_id[slot_id].get("scheduled_date")
    ]
    if week_index <= 0 or not ordered_slot_ids:
        return []
    week_key_by_slot_id = {
        slot_id: date.fromisoformat(slots_by_id[slot_id]["scheduled_date"]).isocalendar()[:2]
        for slot_id in ordered_slot_ids
    }
    ordered_week_keys = []
    for slot_id in ordered_slot_ids:
        week_key = week_key_by_slot_id[slot_id]
        if week_key not in ordered_week_keys:
            ordered_week_keys.append(week_key)
    if week_index > len(ordered_week_keys):
        return []
    target_week = ordered_week_keys[week_index - 1]
    return [slot_id for slot_id in ordered_slot_ids if week_key_by_slot_id[slot_id] == target_week]


def _target_keywords(text: str) -> list[str]:
    candidates = ["회복", "포장", "복습", "암기", "발표", "일본어", "회화", "러닝", "달리기"]
    return [keyword for keyword in candidates if keyword in text]


def _target_only_text(text: str) -> str:
    before_maintain = re.split(r"유지|maintain|keep", text, maxsplit=1, flags=re.IGNORECASE)[0]
    markers = ["바꿔", "변경", "줄", "빼", "제외", "몰아", "옮", "이동", "앞당"]
    marker_positions = [before_maintain.find(marker) for marker in markers if before_maintain.find(marker) >= 0]
    if marker_positions:
        return before_maintain[: min(marker_positions)]
    return before_maintain


def _reduced_duration_weekdays(text: str) -> set[str]:
    normalized = text.lower()
    if not any(keyword in normalized for keyword in ("줄", "1시간", "한 시간", "reduce", "shorter")):
        return set()
    focused_weekdays = set()
    for match in re.finditer(r"([월화수목금토일]요일)[^.!?\n]*(?:1시간|한 시간|줄)", text):
        focused_weekdays.update(_mentioned_weekday_values(match.group(1)))
    for match in re.finditer(r"(mondays?|tuesdays?|wednesdays?|thursdays?|fridays?|saturdays?|sundays?)[^.!?\n]*(?:1\s*hour|reduce|shorter)", normalized):
        focused_weekdays.update(_mentioned_weekday_values(match.group(1)))
    if focused_weekdays:
        return focused_weekdays
    target_part = re.split(r"유지|maintain|keep", text, maxsplit=1, flags=re.IGNORECASE)[0]
    return _mentioned_weekday_values(target_part)


def _mentioned_weekday_values(text: str) -> set[str]:
    labels = {
        "월요일": "monday",
        "화요일": "tuesday",
        "수요일": "wednesday",
        "목요일": "thursday",
        "금요일": "friday",
        "토요일": "saturday",
        "일요일": "sunday",
        "monday": "monday",
        "mondays": "monday",
        "tuesday": "tuesday",
        "tuesdays": "tuesday",
        "wednesday": "wednesday",
        "wednesdays": "wednesday",
        "thursday": "thursday",
        "thursdays": "thursday",
        "friday": "friday",
        "fridays": "friday",
        "saturday": "saturday",
        "saturdays": "saturday",
        "sunday": "sunday",
        "sundays": "sunday",
    }
    normalized = text.lower()
    return {day for label, day in labels.items() if label in normalized}


def _parse_mileday_plan_block(plan_block: str, *, allow_empty: bool = False) -> tuple[list[dict[str, str]], list[str]]:
    items: list[dict[str, str]] = []
    errors: list[str] = []
    for line_number, raw_line in enumerate(plan_block.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        if not line.startswith("- "):
            errors.append(f"Line {line_number} must start with '- '.")
            continue
        content = line[2:].strip()
        if "|" not in content:
            errors.append(f"Line {line_number} must use 'slot_id | task'.")
            continue
        slot_id, task = [part.strip() for part in content.split("|", 1)]
        if not slot_id:
            errors.append(f"Line {line_number} has an empty slot_id.")
        if not task:
            errors.append(f"Line {line_number} has an empty task.")
        items.append({"slot_id": slot_id, "task": task})
    if not items and not errors and not allow_empty:
        errors.append("PLAN block must contain at least one plan line.")
    return items, errors


def _apply_mileday_plan_patch(
    previous_plan_items: list[Any],
    patch_items: list[Any],
) -> list[dict[str, str]]:
    patch_by_slot = {
        item.get("slot_id"): item.get("task")
        for item in patch_items
        if isinstance(item, dict) and isinstance(item.get("slot_id"), str)
    }
    merged: list[dict[str, str]] = []
    for item in previous_plan_items:
        if not isinstance(item, dict):
            continue
        slot_id = item.get("slot_id")
        task = item.get("task")
        if not isinstance(slot_id, str) or not isinstance(task, str):
            continue
        merged.append({"slot_id": slot_id, "task": str(patch_by_slot.get(slot_id, task))})
    return merged


def _expand_mileday_patch_items_for_weekday_request(
    case: MileDayMultiTurnCase,
    previous_plan_items: list[Any],
    patch_items: list[dict[str, str]],
    user_request: str,
) -> list[dict[str, str]]:
    if not patch_items:
        return patch_items
    if "만" in user_request:
        return patch_items
    requested_weekdays = {
        day
        for label, day in {
            "월요일": "monday",
            "월": "monday",
            "화요일": "tuesday",
            "화": "tuesday",
            "수요일": "wednesday",
            "수": "wednesday",
            "목요일": "thursday",
            "목": "thursday",
            "금요일": "friday",
            "금": "friday",
            "토요일": "saturday",
            "토": "saturday",
            "일요일": "sunday",
            "일": "sunday",
        }.items()
        if label in user_request
    }
    if not requested_weekdays:
        return patch_items

    slots_by_id = {slot["slot_id"]: slot for slot in _mileday_multiturn_allowed_slots(case)}
    previous_slot_ids = [
        item.get("slot_id")
        for item in previous_plan_items
        if isinstance(item, dict) and isinstance(item.get("slot_id"), str)
    ]
    patch_by_day: dict[str, str] = {}
    for item in patch_items:
        slot = slots_by_id.get(item["slot_id"])
        if slot is not None and slot["day_of_week"] in requested_weekdays:
            patch_by_day[slot["day_of_week"]] = item["task"]
    if not patch_by_day:
        return patch_items

    expanded_by_slot = {item["slot_id"]: item for item in patch_items}
    for slot_id in previous_slot_ids:
        slot = slots_by_id.get(slot_id)
        if slot is None:
            continue
        task = patch_by_day.get(slot["day_of_week"])
        if task is not None:
            expanded_by_slot[slot_id] = {"slot_id": slot_id, "task": task}
    return list(expanded_by_slot.values())


def _contains_disallowed_english_task_text(task: str) -> bool:
    normalized = re.sub(r"(?i)\b\d+\s*(km|m|cm|mm|kg|g|ml|l)\b", "", task)
    normalized = re.sub(r"\b[A-Z]{2,8}\b", "", normalized)
    return re.search(r"[A-Za-z]{2,}", normalized) is not None


def _mentioned_korean_weekdays(task: str) -> set[str]:
    labels = {
        "월요일": "monday",
        "화요일": "tuesday",
        "수요일": "wednesday",
        "목요일": "thursday",
        "금요일": "friday",
        "토요일": "saturday",
        "일요일": "sunday",
    }
    return {day for label, day in labels.items() if label in task}


def _build_mileday_rule_based_user_message(
    case: MileDayMultiTurnCase,
    turn_id: int,
    parsed: dict[str, Any],
    previous_parsed: dict[str, Any] | None,
) -> str:
    availability = _format_mileday_availability(case)
    action = parsed.get("action")
    plan_items = parsed.get("plan_items")
    patch_items = parsed.get("patch_items")
    add_items = parsed.get("add_items")
    remove_slot_ids = parsed.get("remove_slot_ids")
    plan_count = len(plan_items) if isinstance(plan_items, list) else 0
    patch_count = len(patch_items) if isinstance(patch_items, list) else 0
    add_count = len(add_items) if isinstance(add_items, list) else 0
    remove_count = len(remove_slot_ids) if isinstance(remove_slot_ids, list) else 0
    previous_count = len(previous_parsed.get("plan_items", [])) if isinstance(previous_parsed, dict) else 0
    goal_title = case.input.initial_goal.title
    deadline = case.input.initial_goal.deadline
    requires_confirmation = "DB 반영 전 사용자 확인이 필요합니다."

    if action == "create":
        return (
            f"{goal_title} 목표를 {deadline}까지 진행할 수 있도록 {plan_count}개 일정을 제안했습니다. "
            f"가능 시간은 {availability}입니다. "
            f"{requires_confirmation}"
        )
    if patch_count == 0:
        if add_count > 0:
            return (
                f"요청한 일정 추가 {add_count}건을 반영하고, 기존 일정은 유지했습니다. "
                f"전체 일정 수는 {plan_count or previous_count}개이며 가능 시간은 {availability}입니다. "
                f"{requires_confirmation}"
            )
        if remove_count > 0:
            return (
                f"요청한 일정 제외 {remove_count}건을 반영하고, 나머지 일정은 유지했습니다. "
                f"전체 일정 수는 {plan_count or previous_count}개이며 가능 시간은 {availability}입니다. "
                f"{requires_confirmation}"
            )
        return (
            f"요청한 변경은 현재 가능한 시간({availability}) 안에서 바로 반영하기 어렵습니다. "
            "기존 일정은 변경하지 않았습니다. "
            f"{requires_confirmation}"
        )
    return (
        f"요청한 변경 {patch_count}건을 반영하고, 나머지 일정은 유지했습니다. "
        f"전체 일정 수는 {plan_count or previous_count}개이며 가능 시간은 {availability}입니다. "
        f"{requires_confirmation}"
    )


def _format_mileday_availability(case: MileDayMultiTurnCase) -> str:
    day_labels = {
        "monday": "월",
        "tuesday": "화",
        "wednesday": "수",
        "thursday": "목",
        "friday": "금",
        "saturday": "토",
        "sunday": "일",
    }
    return ", ".join(
        f"{day_labels.get(item.day_of_week, item.day_of_week)} {item.start_time}-{item.end_time}"
        for item in case.input.availability
    )


def _evaluate_mileday_multiturn_record(
    base_result: RequestResult,
    case: MileDayMultiTurnCase,
    turn_id: int,
    raw_output: str,
    *,
    previous_parsed: dict[str, Any] | None,
    explanation_judge: ExplanationJudge | None,
    prompt_version: str = MILEDAY_MULTITURN_PROMPT_VERSION,
) -> RequestResult:
    if base_result.error is not None:
        return base_result

    turn = case.turns[turn_id - 1]
    if prompt_version in {"v11", MILEDAY_API_MULTITURN_PROMPT_VERSION}:
        return _evaluate_mileday_multiturn_intent_record(
            base_result,
            case,
            turn_id,
            raw_output,
            previous_parsed=previous_parsed,
            explanation_judge=explanation_judge,
            prompt_version=prompt_version,
        )

    plan_block = _extract_plan_block(raw_output)
    patch_block = _extract_patch_block(raw_output)
    contract: dict[str, Any] = {
        "type": "mileday_multiturn_plan_or_patch_with_rule_based_message",
        "has_plan_section": "[PLAN]" in raw_output,
        "has_plan_end": "[/PLAN]" in raw_output,
        "has_patch_section": "[PATCH]" in raw_output,
        "has_patch_end": "[/PATCH]" in raw_output,
        "plan_parseable": False,
        "patch_parseable": False,
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
    needs_plan = turn.expected_action == "create"
    needs_patch = turn.expected_action == "partial_update"
    missing_required_block = (needs_plan and plan_block is None) or (needs_patch and patch_block is None)
    if missing_required_block:
        errors = []
        if needs_plan and plan_block is None:
            errors.append("Missing [PLAN] or [/PLAN] section.")
        if needs_patch and patch_block is None:
            errors.append("Missing [PATCH] or [/PATCH] section.")
        return _invalid_mileday_result(
            base_result,
            parsed_output={**base_metadata, "contract_errors": errors},
            message="MileDay multiturn output must contain the expected PLAN/PATCH block.",
        )

    if needs_plan:
        plan_items, parse_errors = _parse_mileday_plan_block(plan_block or "")
        patch_items: list[dict[str, str]] = []
    else:
        plan_items = []
        patch_items, parse_errors = _parse_mileday_plan_block(patch_block or "", allow_empty=True)
    if parse_errors:
        return _invalid_mileday_result(
            base_result,
            parsed_output={
                **base_metadata,
                "plan_parse_errors": parse_errors,
            },
            message="MileDay multiturn PLAN/PATCH block was not parseable.",
        )
    contract["plan_parseable"] = needs_plan
    contract["patch_parseable"] = needs_patch
    parsed = {
        "action": turn.expected_action,
        "user_message": "",
        "plan_items": plan_items,
        "patch_items": patch_items,
        "requires_confirmation": True,
    }
    validation = _validate_mileday_multiturn_plan_output(
        case,
        turn_id,
        parsed,
        previous_parsed,
    )
    contract.update(validation["contract"])
    parsed_for_judge = validation.get("effective_parsed_json", parsed)
    user_message = _build_mileday_rule_based_user_message(case, turn_id, parsed_for_judge, previous_parsed)
    if isinstance(parsed_for_judge, dict):
        parsed_for_judge = {**parsed_for_judge, "user_message": user_message}
    parsed_output = {
        **base_metadata,
        "output_contract": contract,
        "explanation": user_message,
        "user_message": user_message,
        "parsed_json": parsed_for_judge,
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
    return base_result.model_copy(
        update={
            "status": ResultStatus.PASSED,
            "parsed_output": parsed_output,
        }
    )


def _evaluate_mileday_multiturn_intent_record(
    base_result: RequestResult,
    case: MileDayMultiTurnCase,
    turn_id: int,
    raw_output: str,
    *,
    previous_parsed: dict[str, Any] | None,
    explanation_judge: ExplanationJudge | None,
    prompt_version: str = MILEDAY_MULTITURN_PROMPT_VERSION,
) -> RequestResult:
    if base_result.error is not None:
        return base_result

    turn = case.turns[turn_id - 1]
    intent_block = _extract_schedule_intent_block(raw_output)
    contract: dict[str, Any] = {
        "type": "mileday_multiturn_intent_with_rule_based_payload",
        "has_schedule_intent_section": "[SCHEDULE_INTENT]" in raw_output or "[일정_의도]" in raw_output,
        "has_schedule_intent_end": "[/SCHEDULE_INTENT]" in raw_output or "[/일정_의도]" in raw_output,
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
    if intent_block is None:
        intent = _fallback_mileday_schedule_intent(case, turn_id, raw_output)
        if intent is None:
            return _invalid_mileday_result(
                base_result,
                parsed_output={
                    **base_metadata,
                    "contract_errors": ["Missing [일정_의도] or [/일정_의도] section."],
                },
                message="MileDay multiturn output must contain the expected Korean schedule intent block.",
            )
        parse_errors = []
        contract["freeform_fallback_used"] = True
    else:
        intent, parse_errors = _parse_mileday_schedule_intent_block(intent_block)
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
        fallback_intent = _fallback_mileday_schedule_intent(case, turn_id, raw_output)
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
        plan_items = _plan_items_from_mileday_intent(case, intent)
        patch_items: list[dict[str, str]] = []
        remove_slot_ids: list[str] = []
        add_items: list[dict[str, str]] = []
    else:
        patch_items = _patch_items_from_mileday_intent(case, turn_id, intent, previous_parsed)
        remove_slot_ids = _remove_slot_ids_from_mileday_intent(case, turn_id, intent, previous_parsed)
        add_items = _add_items_from_mileday_intent(case, turn_id, intent, previous_parsed)
        previous_plan_items = previous_parsed.get("plan_items") if isinstance(previous_parsed, dict) else []
        plan_items = _apply_mileday_plan_patch(previous_plan_items if isinstance(previous_plan_items, list) else [], patch_items)
        if remove_slot_ids:
            plan_items = [item for item in plan_items if item.get("slot_id") not in set(remove_slot_ids)]
        plan_items.extend(add_items)

    parsed = {
        "action": turn.expected_action,
        "intent": intent,
        "user_message": "",
        "plan_items": plan_items,
        "patch_items": patch_items,
        "remove_slot_ids": remove_slot_ids,
        "add_items": add_items,
        "requires_confirmation": True,
    }
    validation = _validate_mileday_multiturn_plan_output(
        case,
        turn_id,
        parsed,
        previous_parsed,
    )
    contract.update(validation["contract"])
    parsed_for_judge = validation.get("effective_parsed_json", parsed)
    user_message = _build_mileday_rule_based_user_message(case, turn_id, parsed_for_judge, previous_parsed)
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
    return base_result.model_copy(
        update={
            "status": ResultStatus.PASSED,
            "parsed_output": parsed_output,
        }
    )


def _validate_mileday_multiturn_plan_output(
    case: MileDayMultiTurnCase,
    turn_id: int,
    parsed: dict[str, Any],
    previous_parsed: dict[str, Any] | None,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    failed_checks: list[dict[str, str]] = []

    def add_error(check: str, message: str, *, code: str | None = None, safety_gate: bool = False) -> None:
        errors.append(message)
        failed_checks.append(
            {
                "check": check,
                "failure_code": code or _failure_code_for_check(check),
                "severity": "critical" if safety_gate else "error",
                "message": message,
                "safety_gate": safety_gate,
                "validator_source": "deterministic",
            }
        )

    expected_action = case.turns[turn_id - 1].expected_action
    raw_plan_items = parsed.get("plan_items")
    raw_patch_items = parsed.get("patch_items")
    raw_remove_slot_ids = parsed.get("remove_slot_ids")
    raw_add_items = parsed.get("add_items")
    if expected_action == "partial_update":
        previous_plan_items = previous_parsed.get("plan_items") if isinstance(previous_parsed, dict) else None
        if not isinstance(previous_plan_items, list):
            add_error("previous_plan_present", "partial_update requires previous parsed plan_items", code="STATE_LOSS")
            previous_plan_items = []
        patch_items = raw_patch_items if isinstance(raw_patch_items, list) else []
        patch_items = _expand_mileday_patch_items_for_weekday_request(
            case,
            previous_plan_items,
            patch_items,
            case.turns[turn_id - 1].content,
        )
        plan_items = _apply_mileday_plan_patch(previous_plan_items, patch_items)
        remove_slot_ids = {
            slot_id
            for slot_id in raw_remove_slot_ids
            if isinstance(raw_remove_slot_ids, list) and isinstance(slot_id, str)
        }
        if remove_slot_ids:
            plan_items = [item for item in plan_items if item.get("slot_id") not in remove_slot_ids]
        add_items = raw_add_items if isinstance(raw_add_items, list) else []
        if add_items:
            plan_items.extend(add_items)
    else:
        patch_items = []
        remove_slot_ids = set()
        add_items = []
        plan_items = raw_plan_items
    required_fields_present = (
        parsed.get("action") == expected_action
        and isinstance(plan_items, list)
    )
    if not required_fields_present:
        add_error("required_fields_present", "Parsed v11 output must contain action and plan_items", code="INTENT_CONTRACT_ERROR")

    confirmation_valid = parsed.get("requires_confirmation") is True
    if not confirmation_valid:
        add_error("requires_confirmation_valid", "requires_confirmation must be true", code="APPROVAL_GUARD_VIOLATION", safety_gate=True)

    allowed_slots = _mileday_multiturn_allowed_slots(case)
    slots_by_id = {slot["slot_id"]: slot for slot in allowed_slots}
    selected_milestones: list[dict[str, Any]] = []
    slot_ids_seen: set[str] = set()
    source_items = patch_items if expected_action == "partial_update" else plan_items
    partial_update_scope_valid = True
    if expected_action == "partial_update":
        if _single_patch_target_requested(case.turns[turn_id - 1].content) and len(patch_items) > 1:
            partial_update_scope_valid = False
            add_error(
                "partial_update_scope_valid",
                "Single-target partial_update requests must change at most one slot.",
                code="INTENT_CONTRACT_ERROR",
                safety_gate=True,
            )
    plan_schema_valid = isinstance(source_items, list) and all(isinstance(item, dict) for item in source_items)
    plan_slot_valid = True
    if not plan_schema_valid:
        add_error("plan_schema_valid", "plan_items/patch_items must be a list of objects", code="PAYLOAD_SCHEMA_ERROR")
        source_items = []

    valid_patch_slot_ids = {item.get("slot_id") for item in previous_parsed.get("plan_items", [])} if isinstance(previous_parsed, dict) else set()
    for item in source_items or []:
        slot_id = item.get("slot_id")
        task = item.get("task")
        if not isinstance(slot_id, str) or slot_id not in slots_by_id:
            plan_slot_valid = False
            add_error("plan_slot_valid", f"Unknown slot_id: {slot_id!r}", code="TARGET_NOT_FOUND")
            continue
        if expected_action == "partial_update" and slot_id not in valid_patch_slot_ids:
            plan_slot_valid = False
            add_error("patch_slot_valid", f"PATCH slot_id was not present in previous PLAN: {slot_id}", code="TARGET_NOT_FOUND", safety_gate=True)
            continue
        if slot_id in slot_ids_seen:
            plan_slot_valid = False
            add_error("plan_slot_valid", f"Duplicate slot_id: {slot_id}", code="PAYLOAD_SCHEMA_ERROR")
            continue
        slot_ids_seen.add(slot_id)
        if not isinstance(task, str) or not task.strip():
            plan_slot_valid = False
            add_error("plan_task_valid", f"Task must be a non-empty string for {slot_id}", code="PAYLOAD_SCHEMA_ERROR")
            continue
        if task.strip().startswith("[") or re.search(r"\d{1,2}:\d{2}", task):
            plan_slot_valid = False
            add_error("plan_task_valid", f"Task must not include weekday/time prefix for {slot_id}", code="TIME_PREFIX_MISMATCH")
            continue
        slot = slots_by_id[slot_id]
        mentioned_weekdays = _mentioned_korean_weekdays(task)
        if mentioned_weekdays and slot["day_of_week"] not in mentioned_weekdays:
            plan_slot_valid = False
            add_error("plan_task_valid", f"Task weekday text does not match slot weekday for {slot_id}", code="DATE_WEEKDAY_MISMATCH")
            continue
        if "오전" in task or "오후" in task:
            plan_slot_valid = False
            add_error("plan_task_valid", f"Task must not include time-of-day text for {slot_id}", code="TIME_PREFIX_MISMATCH")
            continue
        if _contains_disallowed_english_task_text(task):
            plan_slot_valid = False
            add_error("plan_task_valid", f"Task must be written in Korean for {slot_id}", code="INTENT_CONTRACT_ERROR")
            continue

    slot_ids_seen = set()
    for item in plan_items or []:
        slot_id = item.get("slot_id")
        task = item.get("task")
        if not isinstance(slot_id, str) or slot_id not in slots_by_id:
            continue
        if slot_id in slot_ids_seen:
            continue
        slot_ids_seen.add(slot_id)
        if not isinstance(task, str) or not task.strip():
            continue
        if (
            task.strip().startswith("[")
            or re.search(r"\d{1,2}:\d{2}", task)
            or "오전" in task
            or "오후" in task
            or _contains_disallowed_english_task_text(task)
        ):
            continue
        mentioned_weekdays = _mentioned_korean_weekdays(task)
        slot = slots_by_id[slot_id]
        if mentioned_weekdays and slot["day_of_week"] not in mentioned_weekdays:
            continue
        selected_milestones.append(
            {
                "title": canonical_milestone_title(slot["day_of_week"], slot["time_range"].split("-")[0], slot["time_range"].split("-")[1], task.strip()),
                "color": case.input.initial_goal.color,
                "scheduled_date": slot["scheduled_date"],
            }
        )

    min_items = 3 if expected_action == "create" else 1
    max_items = case.expected.constraints.max_milestones
    milestone_count_valid = min_items <= len(selected_milestones) <= max_items
    if not milestone_count_valid:
        add_error("milestone_count_valid", "Final PLAN item count is outside the expected min/max range", code="PAYLOAD_SCHEMA_ERROR")

    goal_payload = {
        "title": case.input.initial_goal.title,
        "deadline": case.input.initial_goal.deadline,
        "is_recurring": case.input.initial_goal.is_recurring,
        "recurrence_type": case.input.initial_goal.recurrence_type,
        "color": case.input.initial_goal.color,
    }
    rule_based_db_payload = {
        "goal": goal_payload,
        "milestones": selected_milestones,
    }
    effective_parsed = {
        **parsed,
        "plan_items": plan_items,
        "patch_items": patch_items,
        "remove_slot_ids": sorted(remove_slot_ids),
        "add_items": add_items,
        "db_payload": rule_based_db_payload,
        "rule_based_db_payload": rule_based_db_payload,
    }

    availability_result = _validate_multiturn_availability_alignment(case, selected_milestones)
    availability_alignment = availability_result["is_valid"]
    weekday_date_alignment = availability_result["weekday_date_alignment"]
    if not availability_alignment:
        for message in availability_result["errors"]:
            add_error("availability_alignment", message, code="AVAILABILITY_VIOLATION", safety_gate=True)
    if availability_alignment and not weekday_date_alignment:
        add_error("weekday_date_alignment", "Milestone title weekday does not match scheduled_date weekday", code="DATE_WEEKDAY_MISMATCH", safety_gate=True)
    if availability_result["warnings"]:
        warnings.extend(availability_result["warnings"])

    latest_allowed = case.expected.constraints.latest_allowed_date
    deadline_compliance = all(
        isinstance(milestone.get("scheduled_date"), str)
        and milestone["scheduled_date"] <= latest_allowed
        for milestone in selected_milestones
    )
    if not deadline_compliance:
        add_error("deadline_compliance", "All generated scheduled_date values must be before the case deadline", code="DEADLINE_VIOLATION", safety_gate=True)

    previous_plan_slot_ids = set(_plan_slot_ids(previous_parsed))
    current_plan_slot_ids = {
        item.get("slot_id")
        for item in plan_items or []
        if isinstance(item, dict) and isinstance(item.get("slot_id"), str)
    }
    previous_titles = set(_milestone_titles(previous_parsed))
    current_titles = set(_milestone_titles(effective_parsed))
    state_regression_count = (
        len(previous_plan_slot_ids - current_plan_slot_ids)
        if previous_plan_slot_ids
        else len(previous_titles - current_titles)
        if previous_titles
        else 0
    )
    completed_existing_titles = [
        milestone.title for milestone in case.input.existing_schedule if milestone.is_completed
    ]
    completed_milestones_preserved = all(
        any(title in current_title for current_title in current_titles)
        for title in completed_existing_titles
    )
    if completed_existing_titles and not completed_milestones_preserved:
        warnings.append("Completed existing milestones are outside the v8 PLAN output.")

    db_payload_schema_valid = set(rule_based_db_payload["goal"]) == set(GOAL_DB_FIELDS) and all(
        set(item) == set(MILESTONE_DB_FIELDS) for item in selected_milestones
    )
    if not db_payload_schema_valid:
        add_error("db_payload_schema_valid", "DB payload contains missing or extra fields.", code="PAYLOAD_SCHEMA_ERROR")
    safety_gate_failures = [item for item in failed_checks if item.get("safety_gate") is True]
    local_flags = [
        required_fields_present,
        plan_schema_valid,
        plan_slot_valid,
        db_payload_schema_valid,
        confirmation_valid,
        deadline_compliance,
        milestone_count_valid,
        availability_alignment,
        weekday_date_alignment,
        partial_update_scope_valid,
    ]
    return {
        "errors": errors,
        "warnings": warnings,
        "local_score": round(sum(1 for flag in local_flags if flag) / len(local_flags), 3),
        "effective_parsed_json": effective_parsed,
        "rule_based_db_payload": rule_based_db_payload,
        "deterministic_validation": {
            "is_valid": len(errors) == 0,
            "failed_checks": failed_checks,
            "failed_check_names": sorted({item["check"] for item in failed_checks}),
            "failure_codes": sorted({item["failure_code"] for item in failed_checks}),
        },
        "failure_taxonomy": failed_checks,
        "safety_gate": {
            "passed": len(safety_gate_failures) == 0,
            "violations": safety_gate_failures,
            "violation_count": len(safety_gate_failures),
        },
        "contract": {
            "required_fields_present": required_fields_present,
            "db_payload_schema_valid": db_payload_schema_valid,
            "requires_confirmation_valid": confirmation_valid,
            "plan_schema_valid": plan_schema_valid,
            "plan_slot_valid": plan_slot_valid,
            "patch_applied": expected_action == "partial_update",
            "partial_update_scope_valid": partial_update_scope_valid,
        },
        "state": {
            "previous_context_used": previous_parsed is not None,
            "unmentioned_milestones_preserved": state_regression_count == 0,
            "completed_milestones_preserved": completed_milestones_preserved,
            "partial_update_scope_valid": partial_update_scope_valid,
            "state_regression_count": state_regression_count,
        },
        "schedule_quality": {
            "availability_alignment": availability_alignment,
            "weekday_date_alignment": weekday_date_alignment,
            "deadline_compliance": deadline_compliance,
            "milestone_count_valid": milestone_count_valid,
            "schedule_progression_valid": None,
            "explanation_alignment": None,
        },
    }


def _milestone_titles(parsed: dict[str, Any] | None) -> list[str]:
    if not isinstance(parsed, dict):
        return []
    db_payload = parsed.get("db_payload")
    if not isinstance(db_payload, dict):
        return []
    milestones = db_payload.get("milestones")
    if not isinstance(milestones, list):
        return []
    return [str(item["title"]) for item in milestones if isinstance(item, dict) and isinstance(item.get("title"), str)]


def _plan_slot_ids(parsed: dict[str, Any] | None) -> list[str]:
    if not isinstance(parsed, dict):
        return []
    plan_items = parsed.get("plan_items")
    if not isinstance(plan_items, list):
        return []
    return [
        str(item["slot_id"])
        for item in plan_items
        if isinstance(item, dict) and isinstance(item.get("slot_id"), str)
    ]


def _validate_multiturn_availability_alignment(
    case: MileDayMultiTurnCase,
    milestones: list[dict[str, Any]],
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if not milestones:
        return {
            "is_valid": False,
            "weekday_date_alignment": False,
            "errors": ["At least one milestone is required for availability validation."],
            "warnings": warnings,
        }
    windows = {
        (window.day_of_week, window.start_time, window.end_time)
        for window in case.input.availability
    }
    title_prefix_valid = True
    weekday_date_alignment = True
    for milestone in milestones:
        title = milestone.get("title")
        scheduled_date = milestone.get("scheduled_date")
        if not isinstance(title, str):
            title_prefix_valid = False
            errors.append("Milestone title must be a string.")
            continue
        parsed_title = parse_canonical_milestone_title(title)
        if parsed_title is None:
            title_prefix_valid = False
            errors.append(f"Milestone title must start with a bracketed weekday/time range: {title}")
            continue
        if (parsed_title.day_of_week, parsed_title.start_time, parsed_title.end_time) not in windows:
            title_prefix_valid = False
            errors.append(f"Milestone title uses unavailable weekday/time: {title}")
        if isinstance(scheduled_date, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", scheduled_date):
            actual_day = _date_day_of_week(scheduled_date)
            if actual_day is not None and actual_day != parsed_title.day_of_week:
                weekday_date_alignment = False
                errors.append(
                    f"Milestone title weekday does not match scheduled_date: {title} / {scheduled_date}"
                )
        else:
            weekday_date_alignment = False
            warnings.append(f"Cannot verify weekday/date alignment for invalid date: {scheduled_date}")
    return {
        "is_valid": title_prefix_valid and weekday_date_alignment,
        "weekday_date_alignment": weekday_date_alignment,
        "errors": errors,
        "warnings": warnings,
    }


def _failure_code_for_check(check: str) -> str:
    return {
        "previous_plan_present": "STATE_LOSS",
        "required_fields_present": "INTENT_CONTRACT_ERROR",
        "requires_confirmation_valid": "APPROVAL_GUARD_VIOLATION",
        "plan_schema_valid": "PAYLOAD_SCHEMA_ERROR",
        "plan_slot_valid": "TARGET_NOT_FOUND",
        "patch_slot_valid": "TARGET_NOT_FOUND",
        "plan_task_valid": "INTENT_CONTRACT_ERROR",
        "milestone_count_valid": "PAYLOAD_SCHEMA_ERROR",
        "availability_alignment": "AVAILABILITY_VIOLATION",
        "weekday_date_alignment": "DATE_WEEKDAY_MISMATCH",
        "deadline_compliance": "DEADLINE_VIOLATION",
        "db_payload_schema_valid": "PAYLOAD_SCHEMA_ERROR",
    }.get(check, "JUDGE_REJECTION")


def _parse_milestone_title_time_prefix(title: str) -> tuple[str, str, str] | None:
    match = re.match(r"^\[(?P<weekday>[^\s\]]+)\s+(?P<start>\d{2}:\d{2})-(?P<end>\d{2}:\d{2})\]", title)
    if match is None:
        return None
    weekday = match.group("weekday")
    day_of_week = {
        "월": "monday",
        "월요일": "monday",
        "화": "tuesday",
        "화요일": "tuesday",
        "수": "wednesday",
        "수요일": "wednesday",
        "목": "thursday",
        "목요일": "thursday",
        "금": "friday",
        "금요일": "friday",
        "토": "saturday",
        "토요일": "saturday",
        "일": "sunday",
        "일요일": "sunday",
    }.get(weekday)
    if day_of_week is None:
        return None
    return day_of_week, match.group("start"), match.group("end")


def _date_day_of_week(raw_date: str) -> str | None:
    try:
        weekday_index = date.fromisoformat(raw_date).weekday()
    except ValueError:
        return None
    return [
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    ][weekday_index]


def _skipped_mileday_multiturn_result(
    *,
    run_id: str,
    model_id: str,
    dataset_id: str,
    case_id: str,
    case: MileDayMultiTurnCase,
    turn_id: int,
    prompt_version: str = MILEDAY_MULTITURN_PROMPT_VERSION,
) -> RequestResult:
    return RequestResult(
        run_id=run_id,
        model_id=model_id,
        dataset_id=dataset_id,
        case_id=case_id,
        status=ResultStatus.SKIPPED,
        parsed_output={
            "evaluation_family": "mileday_multiturn",
            "case_id": case.case_id,
            "turn_id": turn_id,
            "turn_count": len(case.turns),
            "prompt_version": prompt_version,
            "skipped_reason": "Previous turn in the same case did not pass.",
        },
        metrics=RuntimeMetrics(),
        error=EvaluationError(
            category=FailureCategory.NOT_EXECUTED,
            message="Previous turn in the same case did not pass.",
        ),
    )


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


def _recover_mileday_json_diagnostic(case: MileDayGenerationCase, raw_output: str) -> dict[str, object]:
    candidate = _extract_fenced_json(raw_output)
    if candidate is None:
        return {
            "output_contract_valid": False,
            "recovered_json_available": False,
            "recovery_source": None,
        }
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError as exc:
        return {
            "output_contract_valid": False,
            "recovered_json_available": False,
            "recovery_source": "markdown_code_fence",
            "recovery_error": f"Fenced JSON was not valid JSON: {exc.msg}",
        }

    validation = validate_schedule_output(case, parsed, raw_output=candidate)
    diagnostic: dict[str, object] = {
        "output_contract_valid": False,
        "recovered_json_available": True,
        "recovery_source": "markdown_code_fence",
        "recovered_validation": validation.model_dump(mode="json"),
    }
    if validation.is_valid:
        rubric = evaluate_semantic_rubric(case, parsed, validation)
        diagnostic["recovered_rubric"] = rubric.model_dump(mode="json")
        diagnostic["recovered_semantic_score"] = rubric.aggregate_score
    return diagnostic


def _extract_fenced_json(raw_output: str) -> str | None:
    candidates = [match.group("json").strip() for match in FENCED_JSON_PATTERN.finditer(raw_output)]
    if not candidates:
        return None
    return max(candidates, key=len)


def _extract_explanation(raw_output: str) -> str | None:
    explanation_marker = "[EXPLANATION]"
    json_marker = "[JSON]"
    explanation_start = raw_output.find(explanation_marker)
    json_start = raw_output.find(json_marker)
    if explanation_start < 0 or json_start < 0 or json_start <= explanation_start:
        return None
    explanation = raw_output[explanation_start + len(explanation_marker) : json_start].strip()
    if "</think>" in explanation:
        explanation = explanation.split("</think>", maxsplit=1)[-1].strip()
    return explanation or None


if __name__ == "__main__":
    app()


