from __future__ import annotations

import re
from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Any

from harness.mileday.ai_draft_schema import AI_DRAFT_MODEL_ID, AI_DRAFT_PROMPT_VERSION
from harness.mileday.dataset import AiScheduleDraftCase
from harness.results import ResultStore
from harness.schemas import RequestResult, ResultStatus


def next_prompt_draft_sequence(runs_dir: Path) -> int:
    highest = 0
    if not runs_dir.exists():
        return 1
    pattern = re.compile(r"^prompt-draft-(?P<sequence>\d+)(?:-summary\.md)?$")
    for path in runs_dir.iterdir():
        match = pattern.fullmatch(path.name)
        if match is not None:
            highest = max(highest, int(match.group("sequence")))
    return highest + 1


def status_counts(results: list[RequestResult]) -> dict[str, int]:
    counts = {status.value: 0 for status in ResultStatus}
    for result in results:
        counts[result.status.value] = counts.get(result.status.value, 0) + 1
    return counts


def write_ai_draft_summary(
    runs_dir: Path,
    *,
    run_id: str,
    cases: list[AiScheduleDraftCase],
    report_path: Path,
) -> Path:
    path = runs_dir / f"{run_id}-summary.md"
    results = ResultStore(runs_dir).load_request_results(run_id)
    counts = status_counts(results)
    validation_failures = Counter()
    judge_rejects = 0
    judge_scores: list[float] = []
    latencies = [result.metrics.latency_ms for result in results if result.metrics.latency_ms is not None]
    for result in results:
        validation = result.parsed_output.get("draft_validation")
        if isinstance(validation, dict):
            validation_failures.update(
                code
                for code in validation.get("failure_codes", [])
                if isinstance(code, str)
            )
        judge = result.parsed_output.get("draft_judge")
        if isinstance(judge, dict):
            if isinstance(judge.get("score"), int | float):
                judge_scores.append(float(judge["score"]))
            if judge.get("is_aligned") is False and judge.get("error") is None:
                judge_rejects += 1
    lines = [
        f"# MileDay AI Draft Summary: {run_id}",
        "",
        "## Run",
        "",
        "- runtime: gemini",
        f"- model: {AI_DRAFT_MODEL_ID}",
        "- fixture: `tests/fixtures/mileday/ai_schedule_draft.json`",
        f"- cases: {len(cases)}",
        f"- prompt version: {AI_DRAFT_PROMPT_VERSION}",
        "- db_write: disabled",
        "",
        "## Result",
        "",
        "| passed | invalid | failed | skipped | case pass | deterministic pass | judge rejects | avg judge score | avg latency ms | top validation failures | report |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|",
        "| "
        + " | ".join(
            [
                str(counts.get("passed", 0)),
                str(counts.get("invalid", 0)),
                str(counts.get("failed", 0)),
                str(counts.get("skipped", 0)),
                _rate(counts.get("passed", 0), len(cases)),
                _deterministic_pass_rate(results),
                str(judge_rejects),
                _float(mean(judge_scores) if judge_scores else None),
                _float(mean(latencies) if latencies else None),
                _counter_text(dict(validation_failures.most_common(3))) if validation_failures else "none",
                f"`{report_path.as_posix()}`",
            ]
        )
        + " |",
        "",
        "## Product Gate",
        "",
        "- minimum: case pass 24/30, deterministic pass 30/30, critical failure 0, avg judge score >= 0.85",
        "- target: case pass 27/30, deterministic pass 30/30, critical failure 0, avg judge score >= 0.90",
    ]
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8", newline="\n")
    return path


def append_ai_draft_report(
    run_id: str,
    runs_dir: Path,
    cases: list[AiScheduleDraftCase],
) -> Path:
    store = ResultStore(runs_dir)
    report_path = store.run_dir(run_id) / "report.md"
    results = store.load_request_results(run_id)
    existing = report_path.read_text(encoding="utf-8") if report_path.exists() else ""
    lines = [
        "",
        "## MileDay AI 일정 초안 평가",
        "",
        "### Case별 상태",
        "",
        "| case | status | validation | judge score | failure codes |",
        "|---|---|---|---:|---|",
    ]
    by_case = {result.case_id: result for result in results}
    for case in cases:
        result = by_case.get(case.case_id)
        if result is None:
            lines.append(f"| {case.case_id} | not_executed | 없음 | 없음 | 없음 |")
            continue
        validation = result.parsed_output.get("draft_validation")
        judge = result.parsed_output.get("draft_judge")
        lines.append(
            "| "
            + " | ".join(
                [
                    case.case_id,
                    result.status.value,
                    "valid" if isinstance(validation, dict) and validation.get("is_valid") else "invalid",
                    _float(judge.get("score") if isinstance(judge, dict) else None),
                    _failure_codes(validation),
                ]
            )
            + " |"
        )
    lines.append("")
    report_path.write_text(
        existing.rstrip() + "\n" + "\n".join(lines).rstrip() + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return report_path


def _deterministic_pass_rate(results: list[RequestResult]) -> str:
    passed = 0
    total = 0
    for result in results:
        validation = result.parsed_output.get("draft_validation")
        if isinstance(validation, dict):
            total += 1
            if validation.get("is_valid") is True:
                passed += 1
    return f"{passed}/{total}"


def _failure_codes(validation: Any) -> str:
    if not isinstance(validation, dict):
        return "없음"
    codes = validation.get("failure_codes")
    if not isinstance(codes, list) or not codes:
        return "없음"
    return ", ".join(str(code) for code in codes)


def _rate(numerator: int, denominator: int) -> str:
    if denominator <= 0:
        return "없음"
    return f"{numerator}/{denominator}"


def _float(value: object) -> str:
    if not isinstance(value, int | float):
        return "없음"
    return f"{float(value):.3f}"


def _counter_text(counter: dict[str, int]) -> str:
    return ", ".join(f"{key}={counter[key]}" for key in sorted(counter))
