from __future__ import annotations

import time
from dataclasses import asdict
from typing import Any
from typing import Callable

import typer

from harness.config import HarnessSettings
from harness.html_reporting import generate_mileday_multiturn_html_report
from harness.mileday.api_constants import (
    MILEDAY_API_BASE_URL,
    MILEDAY_API_JUDGE_MODEL,
    MILEDAY_API_MODEL_ID,
    MILEDAY_API_MULTITURN_PROMPT_VERSION,
    MILEDAY_API_SLEEP_SECONDS,
    MILEDAY_MULTITURN_RUNTIME_OPTIONS,
)
from harness.mileday.api_db_client import ApiDbConfigError, ApiDbWriter
from harness.mileday.api_db_manifest import (
    api_db_manifest_path,
    append_api_db_manifest_record,
    load_api_db_manifest,
)
from harness.mileday.api_parser import evaluate_api_multiturn_record
from harness.mileday.api_prompt import (
    api_schedule_intent_response_schema,
    append_plan_targets_to_transcript,
    build_api_multiturn_prompt,
    turn_case_id,
)
from harness.mileday.api_summary import (
    append_mileday_multiturn_report,
    case_pass_text_for_cli,
    counter_text_for_cli,
    next_prompt_test_sequence,
    status_counts,
    write_prompt_test_summary,
)
from harness.mileday.dataset import load_mileday_multiturn_cases
from harness.mileday.explanation_judge import ExplanationJudge, GeminiExplanationJudge
from harness.orchestrator import BenchmarkCasePrompt, BenchmarkMode, BenchmarkRunConfig, measured_records, run_benchmark_cases
from harness.performance.monitor import PerformanceMonitor
from harness.reporting import generate_markdown_report
from harness.results import ResultStore
from harness.runtime.base import RuntimeAdapter
from harness.runtime.gemini import GeminiRuntime
from harness.runtime.ollama import OllamaRuntime
from harness.schemas import EvaluationError, FailureCategory, RequestResult, ResultStatus, RuntimeMetrics

try:
    from tqdm import tqdm
except ImportError:  # pragma: no cover - optional CLI enhancement
    tqdm = None


def run_mileday_multiturn_for_model(
    *,
    model_id: str,
    model_tag: str,
    run_id: str,
    mode: BenchmarkMode,
    cases,
    store: ResultStore,
    ollama_base_url: str,
    timeout_seconds: int,
    explanation_judge: ExplanationJudge | None,
    runtime_options: dict[str, object] | None = None,
    runtime: RuntimeAdapter | None = None,
    sleep_seconds: float = 0.0,
    prompt_builder: Callable[[Any, int, list[dict[str, str]]], str] | None = None,
    prompt_version: str = MILEDAY_API_MULTITURN_PROMPT_VERSION,
    db_writer: ApiDbWriter | None = None,
    response_format: dict[str, object] | None = None,
) -> int:
    config = BenchmarkRunConfig(
        run_id=run_id,
        model_id=model_id,
        model_tag=model_tag,
        mode=mode,
        runtime_options=runtime_options or MILEDAY_MULTITURN_RUNTIME_OPTIONS,
        response_format=response_format,
        timeout_seconds=timeout_seconds,
    )
    progress = _progress_bar(
        total=_progress_total(sum(len(case.turns) for case in cases), config),
        desc=f"{model_id} MileDay multiturn",
    )
    active_runtime = runtime or OllamaRuntime(base_url=ollama_base_url)
    active_prompt_builder = prompt_builder or build_api_multiturn_prompt
    stored = 0
    try:
        for case in cases:
            transcript: list[dict[str, str]] = []
            previous_parsed: dict[str, Any] | None = None
            db_create_record: dict[str, Any] | None = None
            case_blocked = False
            for turn in case.turns:
                case_turn_id = turn_case_id(case.case_id, turn.turn_id)
                if case_blocked:
                    skipped = skipped_mileday_multiturn_result(
                        run_id=run_id,
                        model_id=model_id,
                        dataset_id=case.dataset_id,
                        case_id=case_turn_id,
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
                            case_id=case_turn_id,
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
                result = evaluate_api_multiturn_record(
                    record.request_result,
                    case,
                    turn.turn_id,
                    record.response.text,
                    previous_parsed=previous_parsed,
                    explanation_judge=explanation_judge,
                    prompt_version=prompt_version,
                )
                store.store_request_result(result, raw_output=record.response.text)
                if (
                    db_writer is not None
                    and result.status == ResultStatus.PASSED
                ):
                    parsed_json = result.parsed_output.get("parsed_json")
                    if isinstance(parsed_json, dict) and turn.expected_action == "create":
                        db_payload = parsed_json.get("db_payload")
                        plan_items = parsed_json.get("plan_items")
                        if not isinstance(db_payload, dict) or not isinstance(plan_items, list):
                            raise RuntimeError("Passed create result is missing db_payload or plan_items.")
                        db_record = db_writer.insert_create_payload(
                            run_id=run_id,
                            case_id=case_turn_id,
                            turn_id=turn.turn_id,
                            payload=db_payload,
                            plan_items=plan_items,
                        )
                        append_api_db_manifest_record(
                            api_db_manifest_path(store.run_dir(run_id)),
                            db_record,
                        )
                        db_create_record = asdict(db_record)
                    elif isinstance(parsed_json, dict) and turn.expected_action == "partial_update":
                        if db_create_record is None:
                            raise RuntimeError("Passed partial_update result requires a prior DB create record.")
                        db_record = db_writer.update_partial_payload(
                            run_id=run_id,
                            case_id=case_turn_id,
                            turn_id=turn.turn_id,
                            create_record=db_create_record,
                            parsed_json=parsed_json,
                        )
                        if db_record is not None:
                            append_api_db_manifest_record(
                                api_db_manifest_path(store.run_dir(run_id)),
                                db_record,
                            )
                            _apply_db_write_record_to_create_state(
                                db_create_record,
                                asdict(db_record),
                                parsed_json,
                            )
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
                        assistant_content = append_plan_targets_to_transcript(assistant_content, parsed_json)
                    transcript.append({"role": "user", "content": turn.content})
                    transcript.append({"role": "assistant", "content": assistant_content})
                else:
                    case_blocked = True
                if sleep_seconds > 0:
                    time.sleep(sleep_seconds)
    finally:
        _progress_close(progress)
    return stored


def _apply_db_write_record_to_create_state(
    create_record: dict[str, Any],
    write_record: dict[str, Any],
    parsed_json: dict[str, Any],
) -> None:
    milestone_slot_ids = create_record.get("milestone_slot_ids")
    milestone_titles = create_record.get("milestone_titles")
    if not isinstance(milestone_slot_ids, dict) or not isinstance(milestone_titles, dict):
        return

    remove_slot_ids = parsed_json.get("remove_slot_ids")
    if isinstance(remove_slot_ids, list):
        for slot_id in remove_slot_ids:
            if isinstance(slot_id, str):
                milestone_slot_ids.pop(slot_id, None)
                milestone_titles.pop(slot_id, None)

    written_slot_ids = write_record.get("milestone_slot_ids")
    if isinstance(written_slot_ids, dict):
        milestone_slot_ids.update(
            {
                str(slot_id): str(milestone_id)
                for slot_id, milestone_id in written_slot_ids.items()
                if slot_id not in set(remove_slot_ids or [])
            }
        )
    written_titles = write_record.get("milestone_titles")
    if isinstance(written_titles, dict):
        milestone_titles.update({str(slot_id): str(title) for slot_id, title in written_titles.items()})


def skipped_mileday_multiturn_result(
    *,
    run_id: str,
    model_id: str,
    dataset_id: str,
    case_id: str,
    case,
    turn_id: int,
    prompt_version: str = MILEDAY_API_MULTITURN_PROMPT_VERSION,
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


def run_prompt_test_api(
    *,
    settings: HarnessSettings,
    fixture,
    limit: int | None,
    write_db: bool,
    echo: Callable[[str], None] = typer.echo,
) -> None:
    if not settings.gemini_api_key:
        raise typer.BadParameter("GEMINI_API_KEY is required.")

    try:
        cases = load_mileday_multiturn_cases(fixture)
        if limit is not None:
            cases = cases[:limit]
    except (FileNotFoundError, ValueError) as exc:
        raise typer.BadParameter(str(exc)) from exc

    store = ResultStore(settings.runs_dir)
    batch_sequence = next_prompt_test_sequence(store.runs_dir)
    batch_id = f"prompt-test-{batch_sequence}"
    run_id = batch_id

    echo(f"batch_id={batch_id}")
    echo(f"model={MILEDAY_API_MODEL_ID}")
    echo(f"fixture={fixture}")
    echo(f"cases={len(cases)}")
    echo(f"case_limit={limit if limit is not None else 'all'}")
    echo(f"prompt_version={MILEDAY_API_MULTITURN_PROMPT_VERSION}")
    echo("runtime=gemini")
    echo("judge=required")
    echo(f"sleep_seconds={MILEDAY_API_SLEEP_SECONDS:g}")
    echo(f"db_write={'enabled' if write_db else 'disabled'}")

    db_writer = None
    if write_db:
        try:
            db_writer = ApiDbWriter.from_settings(settings)
        except ApiDbConfigError as exc:
            raise typer.BadParameter(str(exc)) from exc

    runtime = GeminiRuntime(
        api_key=settings.gemini_api_key,
        base_url=MILEDAY_API_BASE_URL,
    )
    explanation_judge = GeminiExplanationJudge(
        api_key=settings.gemini_api_key,
        model=MILEDAY_API_JUDGE_MODEL,
        base_url=MILEDAY_API_BASE_URL,
    )
    stored = run_mileday_multiturn_for_model(
        model_id=MILEDAY_API_MODEL_ID,
        model_tag=MILEDAY_API_MODEL_ID,
        run_id=run_id,
        mode=BenchmarkMode.COLD,
        cases=cases,
        store=store,
        ollama_base_url=settings.ollama_base_url,
        timeout_seconds=settings.default_timeout_seconds,
        explanation_judge=explanation_judge,
        runtime=runtime,
        sleep_seconds=MILEDAY_API_SLEEP_SECONDS,
        prompt_builder=build_api_multiturn_prompt,
        prompt_version=MILEDAY_API_MULTITURN_PROMPT_VERSION,
        db_writer=db_writer,
        response_format=api_schedule_intent_response_schema(),
    )
    report_path = generate_markdown_report(run_id, settings.runs_dir)
    multiturn_report_path = append_mileday_multiturn_report(
        run_id,
        settings.runs_dir,
        cases,
        model_id=MILEDAY_API_MODEL_ID,
    )
    html_report_path = generate_mileday_multiturn_html_report(run_id, settings.runs_dir)
    results = store.load_request_results(run_id)
    counts = status_counts(results)
    echo(
        f"{MILEDAY_API_MODEL_ID} -> {run_id} -> {report_path} -> "
        f"{case_pass_text_for_cli(results, cases)} {counter_text_for_cli(counts)} stored={stored}"
    )

    summary_path = write_prompt_test_summary(
        store.runs_dir,
        batch_id=batch_id,
        item={
            "model_id": MILEDAY_API_MODEL_ID,
            "run_id": run_id,
            "stored": stored,
            "counts": counts,
            "report_path": report_path,
            "multiturn_report_path": multiturn_report_path,
            "html_report_path": html_report_path,
        },
        cases=cases,
    )
    echo(f"batch_summary={summary_path}")


def cleanup_prompt_test_api(
    *,
    settings: HarnessSettings,
    run_id: str,
    echo: Callable[[str], None] = typer.echo,
) -> None:
    store = ResultStore(settings.runs_dir)
    manifest_path = api_db_manifest_path(store.run_dir(run_id))
    try:
        manifest = load_api_db_manifest(manifest_path)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    records = manifest.get("records", [])
    if not manifest_path.exists():
        raise typer.BadParameter(f"DB manifest not found: {manifest_path}")
    if not isinstance(records, list):
        raise typer.BadParameter(f"Invalid DB manifest records: {manifest_path}")
    try:
        db_writer = ApiDbWriter.from_settings(settings)
    except ApiDbConfigError as exc:
        raise typer.BadParameter(str(exc)) from exc

    deleted_goals = 0
    deleted_milestones = 0
    for record in reversed(records):
        if not isinstance(record, dict):
            continue
        counts = db_writer.cleanup_record(record)
        deleted_goals += counts["goals"]
        deleted_milestones += counts["milestones"]
    echo(f"cleanup_run_id={run_id}")
    echo(f"manifest={manifest_path}")
    echo(f"deleted_goals={deleted_goals}")
    echo(f"deleted_milestones={deleted_milestones}")
