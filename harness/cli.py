from __future__ import annotations

import json
import re
import random
import subprocess
from pathlib import Path
from typing import Annotated, Any

import typer
from pydantic import ValidationError

from harness.config import load_settings
from harness.dataset_processor import DatasetProcessingError, prepare_all_datasets
from harness.dataset_registry import DEFAULT_DATASET_REGISTRY_PATH
from harness.mileday.constraints import validate_schedule_output
from harness.mileday.dataset import MileDayGenerationCase, load_mileday_generation_cases
from harness.mileday.explanation_judge import (
    ExplanationJudge,
    GeminiExplanationJudge,
    BatchQualitySummaryResult,
    skipped_batch_quality_summary_result,
    skipped_explanation_judge_result,
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
from harness.reporting import generate_markdown_report
from harness.results import ResultStore
from harness.runtime.base import RuntimeAdapterError
from harness.runtime.ollama import OllamaRuntime
from harness.schemas import EvaluationError, FailureCategory, RequestResult, ResultStatus


app = typer.Typer(help="Local LLM evaluation harness.")
FENCED_JSON_PATTERN = re.compile(r"```(?:json)?\s*(?P<json>.*?)\s*```", re.IGNORECASE | re.DOTALL)


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
    records = run_benchmark_cases(
        prompts,
        BenchmarkRunConfig(
            run_id=run_id,
            model_id=model_id,
            model_tag=model_tag,
            mode=mode,
            runtime_options={"temperature": 0},
            timeout_seconds=timeout_seconds,
        ),
        OllamaRuntime(base_url=ollama_base_url),
        monitor_factory=PerformanceMonitor,
        completed_resume_keys=set(store.resume_index(run_id)),
    )
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
