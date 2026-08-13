from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable

import typer

from harness.config import HarnessSettings
from harness.mileday.ai_draft_judge import GeminiAiDraftJudge
from harness.mileday.ai_draft_parser import parse_ai_schedule_draft_output
from harness.mileday.ai_draft_payload import (
    build_ai_draft_create_payload,
    build_ai_draft_create_sql_preview,
    build_ai_draft_sql_parameters,
)
from harness.mileday.ai_draft_prompt import build_ai_schedule_draft_prompt
from harness.mileday.ai_draft_schema import (
    AI_DRAFT_FIXTURE,
    AI_DRAFT_MODEL_ID,
    AI_DRAFT_PROMPT_VERSION,
    AI_DRAFT_RUNTIME_OPTIONS,
    ai_schedule_draft_response_schema,
)
from harness.mileday.ai_draft_summary import (
    append_ai_draft_report,
    next_prompt_draft_sequence,
    status_counts,
    write_ai_draft_summary,
)
from harness.mileday.api_constants import MILEDAY_API_BASE_URL, MILEDAY_API_SLEEP_SECONDS
from harness.mileday.dataset import AiScheduleDraftCase, load_ai_schedule_draft_cases
from harness.html_reporting import generate_ai_draft_html_report
from harness.orchestrator import BenchmarkCasePrompt, BenchmarkMode, BenchmarkRunConfig, measured_records, run_benchmark_cases
from harness.performance.monitor import PerformanceMonitor
from harness.reporting import generate_markdown_report
from harness.results import ResultStore
from harness.runtime.gemini import GeminiRuntime
from harness.schemas import EvaluationError, FailureCategory, RequestResult, ResultStatus

try:
    from tqdm import tqdm
except ImportError:  # pragma: no cover - optional CLI enhancement
    tqdm = None


def run_ai_schedule_draft_for_model(
    *,
    model_id: str,
    model_tag: str,
    run_id: str,
    cases: list[AiScheduleDraftCase],
    store: ResultStore,
    runtime: GeminiRuntime,
    judge: GeminiAiDraftJudge,
    timeout_seconds: int,
) -> int:
    config = BenchmarkRunConfig(
        run_id=run_id,
        model_id=model_id,
        model_tag=model_tag,
        mode=BenchmarkMode.COLD,
        runtime_options=AI_DRAFT_RUNTIME_OPTIONS,
        response_format=ai_schedule_draft_response_schema(),
        timeout_seconds=timeout_seconds,
    )
    progress = _progress_bar(
        total=len(cases),
        desc=f"{model_id} MileDay AI draft",
    )
    stored = 0
    try:
        for case in cases:
            records = run_benchmark_cases(
                [
                    BenchmarkCasePrompt(
                        dataset_id=case.dataset_id,
                        case_id=case.case_id,
                        prompt=build_ai_schedule_draft_prompt(case),
                        parsed_output={
                            "evaluation_family": "mileday_ai_draft",
                            "case_id": case.case_id,
                            "prompt_version": AI_DRAFT_PROMPT_VERSION,
                        },
                    )
                ],
                config,
                runtime,
                monitor_factory=PerformanceMonitor,
                completed_resume_keys=set(),
                progress_callback=_progress_update(progress),
            )
            measured = measured_records(records)
            if not measured:
                continue
            record = measured[-1]
            result = _evaluate_ai_draft_record(
                record.request_result,
                case,
                record.response.text,
                judge=judge,
            )
            stored_result = store.store_request_result(result, raw_output=record.response.text)
            store.append_performance_samples(
                run_id,
                [record.performance_summary.model_dump(mode="json")],
                phase=record.phase.value,
            )
            stored += 1 if stored_result is not None else 0
            if MILEDAY_API_SLEEP_SECONDS > 0:
                time.sleep(MILEDAY_API_SLEEP_SECONDS)
    finally:
        _progress_close(progress)
    return stored


def _evaluate_ai_draft_record(
    request_result: RequestResult,
    case: AiScheduleDraftCase,
    raw_output: str,
    *,
    judge: GeminiAiDraftJudge,
) -> RequestResult:
    if request_result.error is not None:
        return request_result
    try:
        draft = parse_ai_schedule_draft_output(raw_output)
    except ValueError as exc:
        return request_result.model_copy(
            update={
                "status": ResultStatus.INVALID,
                "parsed_output": {
                    **request_result.parsed_output,
                    "parse_error": str(exc),
                    "draft_validation": {"is_valid": False, "failure_codes": ["INVALID_JSON"]},
                },
                "error": EvaluationError(category=FailureCategory.PARSER_ERROR, message=str(exc)),
            }
        )

    from harness.mileday.ai_draft_validation import validate_ai_schedule_draft

    validation = validate_ai_schedule_draft(case, draft)
    parsed_output: dict[str, Any] = {
        **request_result.parsed_output,
        "draft": draft,
        "draft_validation": validation,
    }
    if not validation["is_valid"]:
        return request_result.model_copy(
            update={
                "status": ResultStatus.INVALID,
                "parsed_output": parsed_output,
                "error": EvaluationError(
                    category=FailureCategory.PARSER_ERROR,
                    message="AI draft failed deterministic validation.",
                ),
            }
        )

    create_payload = build_ai_draft_create_payload(draft)
    parsed_output["create_payload_preview"] = create_payload
    parsed_output["sql_preview"] = build_ai_draft_create_sql_preview(create_payload)
    parsed_output["sql_parameters"] = build_ai_draft_sql_parameters(create_payload)
    judge_result = judge.evaluate(case, draft)
    parsed_output["draft_judge"] = judge_result.model_dump(mode="json")
    if judge_result.error is not None:
        return request_result.model_copy(
            update={
                "status": ResultStatus.FAILED,
                "parsed_output": parsed_output,
                "error": judge_result.error,
            }
        )
    if not judge_result.is_aligned:
        return request_result.model_copy(
            update={
                "status": ResultStatus.INVALID,
                "parsed_output": parsed_output,
                "error": EvaluationError(
                    category=FailureCategory.PARSER_ERROR,
                    message="AI draft judge rejected the schedule draft.",
                ),
            }
        )
    return request_result.model_copy(update={"parsed_output": parsed_output})


def run_prompt_test_draft(
    *,
    settings: HarnessSettings,
    fixture: str | Path = AI_DRAFT_FIXTURE,
    limit: int | None,
    echo: Callable[[str], None] = typer.echo,
) -> None:
    if not settings.gemini_api_key:
        raise typer.BadParameter("GEMINI_API_KEY is required.")
    try:
        cases = load_ai_schedule_draft_cases(fixture)
        if limit is not None:
            cases = cases[:limit]
    except (FileNotFoundError, ValueError) as exc:
        raise typer.BadParameter(str(exc)) from exc

    store = ResultStore(settings.runs_dir)
    run_id = f"prompt-draft-{next_prompt_draft_sequence(store.runs_dir)}"
    echo(_draft_startup_table(run_id=run_id, fixture=str(fixture), case_count=len(cases), limit=limit))

    runtime = GeminiRuntime(api_key=settings.gemini_api_key, base_url=MILEDAY_API_BASE_URL)
    judge = GeminiAiDraftJudge(api_key=settings.gemini_api_key, base_url=MILEDAY_API_BASE_URL)
    stored = run_ai_schedule_draft_for_model(
        model_id=AI_DRAFT_MODEL_ID,
        model_tag=AI_DRAFT_MODEL_ID,
        run_id=run_id,
        cases=cases,
        store=store,
        runtime=runtime,
        judge=judge,
        timeout_seconds=settings.default_timeout_seconds,
    )
    report_path = generate_markdown_report(run_id, settings.runs_dir)
    report_path = append_ai_draft_report(run_id, settings.runs_dir, cases)
    html_report_path = generate_ai_draft_html_report(run_id, settings.runs_dir)
    summary_path = write_ai_draft_summary(
        settings.runs_dir,
        run_id=run_id,
        cases=cases,
        report_path=report_path,
    )
    counts = status_counts(store.load_request_results(run_id))
    echo(
        _draft_result_table(
            run_id=run_id,
            report_path=str(report_path),
            html_report_path=str(html_report_path),
            summary_path=str(summary_path),
            case_pass=f"{counts.get('passed', 0)}/{len(cases)}",
            counts=counts,
            stored=stored,
        )
    )


def _draft_startup_table(
    *,
    run_id: str,
    fixture: str,
    case_count: int,
    limit: int | None,
) -> str:
    rows = [
        ("run_id", run_id),
        ("model", AI_DRAFT_MODEL_ID),
        ("fixture", fixture),
        ("cases", str(case_count)),
        ("case_limit", str(limit) if limit is not None else "all"),
        ("prompt_version", AI_DRAFT_PROMPT_VERSION),
        ("runtime", "gemini"),
        ("judge", "case-level"),
        ("sleep_seconds", f"{MILEDAY_API_SLEEP_SECONDS:g}"),
        ("db_write", "disabled"),
    ]
    return _table(rows)


def _draft_result_table(
    *,
    run_id: str,
    report_path: str,
    html_report_path: str,
    summary_path: str,
    case_pass: str,
    counts: dict[str, int],
    stored: int,
) -> str:
    rows = [
        ("model", AI_DRAFT_MODEL_ID),
        ("run_id", run_id),
        ("case_pass", case_pass),
        ("passed", str(counts.get("passed", 0))),
        ("invalid", str(counts.get("invalid", 0))),
        ("failed", str(counts.get("failed", 0))),
        ("skipped", str(counts.get("skipped", 0))),
        ("stored", str(stored)),
        ("report_md", report_path),
        ("report_html", html_report_path),
        ("summary", summary_path),
    ]
    return _table(rows)


def _table(rows: list[tuple[str, str]]) -> str:
    key_width = max(len(key) for key, _value in rows)
    value_width = max(len(value) for _key, value in rows)
    divider = f"+-{'-' * key_width}-+-{'-' * value_width}-+"
    lines = [divider]
    lines.extend(f"| {key:<{key_width}} | {value:<{value_width}} |" for key, value in rows)
    lines.append(divider)
    return "\n".join(lines)


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
