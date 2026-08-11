from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any, Iterable

from harness.results import ResultStore
from harness.schemas import RequestResult, ResultStatus


MISSING = "없음"
NOT_EXECUTED = "미실행"


@dataclass(frozen=True)
class ReportInput:
    run_id: str
    run_dir: Path
    results: tuple[RequestResult, ...]
    performance_samples: tuple[dict[str, Any], ...]


def generate_markdown_report(
    run_id: str,
    runs_dir: str | Path = Path("artifacts") / "runs",
) -> Path:
    """저장된 run artifact에서 deterministic Markdown 리포트를 생성합니다."""

    store = ResultStore(runs_dir)
    report_input = load_report_input(run_id, store)
    text = render_markdown_report(report_input)
    path = report_input.run_dir / "report.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


def load_report_input(run_id: str, store: ResultStore) -> ReportInput:
    return ReportInput(
        run_id=run_id,
        run_dir=store.run_dir(run_id),
        results=tuple(store.load_request_results(run_id)),
        performance_samples=tuple(_load_jsonl(store.run_dir(run_id) / "metrics" / "performance.jsonl")),
    )


def render_markdown_report(report_input: ReportInput) -> str:
    lines: list[str] = [
        f"# Harness 리포트: {report_input.run_id}",
        "",
        "## Artifact 참조",
        "",
        f"- Run 디렉터리: `{_display_path(report_input.run_dir)}`",
        f"- Parsed 결과: `{_display_path(report_input.run_dir / 'parsed' / 'results.jsonl')}`",
        f"- 성능 metric: `{_display_path(report_input.run_dir / 'metrics' / 'performance.jsonl')}`",
        "- 모델 응답 artifact는 저장된 `raw_output_path`로만 참조하며, 원문 전체는 리포트에 삽입하지 않습니다.",
        "",
    ]

    if not report_input.results:
        lines.extend(
            [
                "## 실행 요약",
                "",
                f"저장된 request result가 없습니다: {NOT_EXECUTED}.",
                "",
            ]
        )
    else:
        lines.extend(_execution_summary(report_input.results))
        lines.extend(_model_summary(report_input.results))
        lines.extend(_dataset_summary(report_input.results))
        lines.extend(_invalid_and_failure_summary(report_input.results))
        lines.extend(_metrics_summary(report_input.results, report_input.performance_samples))
        lines.extend(_raw_artifact_references(report_input.results))

    return "\n".join(lines).rstrip() + "\n"


def dataset_family(dataset_id: str, parsed_output: dict[str, Any] | None = None) -> str:
    parsed = parsed_output or {}
    explicit = parsed.get("evaluation_family") or parsed.get("family")
    if explicit in {"mileday_generation", "mileday_multiturn", "other"}:
        return str(explicit)
    lowered = dataset_id.lower()
    if lowered.startswith("mileday") or "mileday" in lowered or "validation" in parsed or "rubric" in parsed:
        return "mileday_generation"
    return "other"


def _execution_summary(results: Iterable[RequestResult]) -> list[str]:
    result_list = sorted(results, key=_result_key)
    status_counts = Counter(result.status.value for result in result_list)
    family_counts = Counter(dataset_family(result.dataset_id, result.parsed_output) for result in result_list)
    return [
        "## 실행 요약",
        "",
        f"- 전체 request result: {len(result_list)}",
        f"- 상태별 개수: {_counter_text(status_counts)}",
        f"- 기타 결과: {family_counts.get('other', 0)}",
        f"- MileDay 생성 결과: {family_counts.get('mileday_generation', 0)}",
        "",
    ]


def _model_summary(results: Iterable[RequestResult]) -> list[str]:
    by_model: dict[str, list[RequestResult]] = defaultdict(list)
    for result in results:
        by_model[result.model_id].append(result)

    lines = [
        "## 모델 요약",
        "",
        "| 모델 | 결과 수 | passed | invalid | failed | skipped | 기타 점수 | MileDay 유효율 | MileDay semantic | 평균 latency ms | 평균 TTFT ms | 평균 tok/s |",
        "|---|---:|---:|---:|---:|---:|---|---|---|---|---|---|",
    ]
    for model_id in sorted(by_model):
        group = by_model[model_id]
        counts = Counter(result.status.value for result in group)
        other_scores = [_generic_score(result) for result in group if dataset_family(result.dataset_id, result.parsed_output) == "other"]
        mileday_results = [result for result in group if dataset_family(result.dataset_id, result.parsed_output) == "mileday_generation"]
        semantic_scores = [_semantic_score(result) for result in mileday_results]
        lines.append(
            "| "
            + " | ".join(
                [
                    _escape(model_id),
                    str(len(group)),
                    str(counts.get(ResultStatus.PASSED.value, 0)),
                    str(counts.get(ResultStatus.INVALID.value, 0)),
                    str(counts.get(ResultStatus.FAILED.value, 0)),
                    str(counts.get(ResultStatus.SKIPPED.value, 0)),
                    _format_optional_mean(other_scores),
                    _format_rate(sum(1 for result in mileday_results if result.status == ResultStatus.PASSED), len(mileday_results)),
                    _format_optional_mean(semantic_scores),
                    _format_optional_mean(result.metrics.latency_ms for result in group),
                    _format_optional_mean(result.metrics.ttft_ms for result in group),
                    _format_optional_mean(result.metrics.tokens_per_second for result in group),
                ]
            )
            + " |"
        )
    lines.append("")
    return lines


def _dataset_summary(results: Iterable[RequestResult]) -> list[str]:
    by_dataset: dict[str, list[RequestResult]] = defaultdict(list)
    for result in results:
        by_dataset[result.dataset_id].append(result)

    lines = [
        "## 데이터셋 요약",
        "",
        "| 데이터셋 | 계열 | 결과 수 | passed | invalid | failed | 점수 / 유효율 |",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    for dataset_id in sorted(by_dataset):
        group = by_dataset[dataset_id]
        counts = Counter(result.status.value for result in group)
        family = dataset_family(dataset_id, group[0].parsed_output if group else {})
        if family == "other":
            score = _format_optional_mean(_generic_score(result) for result in group)
        else:
            score = _format_rate(sum(1 for result in group if result.status == ResultStatus.PASSED), len(group))
        lines.append(
            f"| {_escape(dataset_id)} | {family} | {len(group)} | "
            f"{counts.get(ResultStatus.PASSED.value, 0)} | {counts.get(ResultStatus.INVALID.value, 0)} | "
            f"{counts.get(ResultStatus.FAILED.value, 0)} | {score} |"
        )
    lines.append("")
    return lines


def _invalid_and_failure_summary(results: Iterable[RequestResult]) -> list[str]:
    invalid_reasons = Counter()
    failure_categories = Counter()
    for result in results:
        if result.status == ResultStatus.INVALID:
            invalid_reasons[_error_label(result)] += 1
        if result.status == ResultStatus.FAILED:
            failure_categories[_error_label(result)] += 1

    lines = ["## Invalid 출력 및 실패 분석", ""]
    lines.append(f"- Invalid 출력: {_counter_text(invalid_reasons) if invalid_reasons else '없음'}")
    lines.append(f"- Failed 출력: {_counter_text(failure_categories) if failure_categories else '없음'}")
    lines.append("")
    return lines


def _metrics_summary(results: Iterable[RequestResult], performance_samples: Iterable[dict[str, Any]]) -> list[str]:
    result_list = list(results)
    samples = list(performance_samples)
    lines = ["## 성능 요약", ""]
    if not result_list:
        lines.append(f"- Request metric: {MISSING}")
    else:
        lines.append(f"- 평균 latency ms: {_format_optional_mean(result.metrics.latency_ms for result in result_list)}")
        lines.append(f"- 평균 TTFT ms: {_format_optional_mean(result.metrics.ttft_ms for result in result_list)}")
        lines.append(f"- 평균 throughput tok/s: {_format_optional_mean(result.metrics.tokens_per_second for result in result_list)}")
    if not samples:
        lines.append(f"- Resource metric: {MISSING}")
    else:
        lines.append(f"- Resource sample 수: {len(samples)}")
        lines.append(f"- Peak CPU percent: {_format_optional_mean(_metric(sample, 'peak_cpu_percent', 'cpu_percent') for sample in samples)}")
        lines.append(f"- Peak RAM bytes: {_format_optional_mean(_metric(sample, 'peak_ram_used_bytes', 'ram_used_bytes') for sample in samples)}")
        lines.append(f"- Peak VRAM bytes: {_format_optional_mean(_metric(sample, 'peak_vram_used_bytes', 'vram_used_bytes') for sample in samples)}")
        vram_statuses = Counter(str(sample.get("vram_status", MISSING)) for sample in samples)
        lines.append(f"- VRAM 상태: {_counter_text(vram_statuses)}")
    lines.append("")
    return lines


def _raw_artifact_references(results: Iterable[RequestResult]) -> list[str]:
    lines = [
        "## Raw Artifact 참조",
        "",
        "| 모델 | 데이터셋 | 케이스 | 상태 | Raw output path |",
        "|---|---|---|---|---|",
    ]
    for result in sorted(results, key=_result_key):
        raw_path = _display_path(result.raw_output_path) if result.raw_output_path is not None else MISSING
        lines.append(
            f"| {_escape(result.model_id)} | {_escape(result.dataset_id)} | {_escape(result.case_id)} | "
            f"{result.status.value} | `{raw_path}` |"
        )
    lines.append("")
    return lines


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _generic_score(result: RequestResult) -> float | None:
    parsed = result.parsed_output
    for key in ("score", "accuracy", "strict_accuracy", "prompt_level_strict_accuracy"):
        value = parsed.get(key)
        if isinstance(value, int | float):
            return float(value)
    if isinstance(parsed.get("is_correct"), bool):
        return 1.0 if parsed["is_correct"] else 0.0
    return None


def _semantic_score(result: RequestResult) -> float | None:
    parsed = result.parsed_output
    if isinstance(parsed.get("semantic_score"), int | float):
        return float(parsed["semantic_score"])
    rubric = parsed.get("rubric")
    if isinstance(rubric, dict) and isinstance(rubric.get("aggregate_score"), int | float):
        return float(rubric["aggregate_score"])
    return None


def _format_optional_mean(values: Iterable[float | int | None]) -> str:
    present = [float(value) for value in values if value is not None]
    if not present:
        return MISSING
    return f"{mean(present):.3f}"


def _format_rate(numerator: int, denominator: int) -> str:
    if denominator <= 0:
        return MISSING
    return f"{numerator / denominator:.3f}"


def _metric(sample: dict[str, Any], *keys: str) -> float | int | None:
    for key in keys:
        value = sample.get(key)
        if isinstance(value, int | float):
            return value
    return None


def _counter_text(counter: Counter[str]) -> str:
    if not counter:
        return MISSING
    return ", ".join(f"{key}={counter[key]}" for key in sorted(counter))


def _error_label(result: RequestResult) -> str:
    if result.error is None:
        return MISSING
    return result.error.category.value


def _result_key(result: RequestResult) -> tuple[str, str, str, str]:
    return (result.model_id, result.dataset_id, result.case_id, result.status.value)


def _display_path(path: Path | str | None) -> str:
    if path is None:
        return MISSING
    return Path(path).as_posix()


def _escape(value: str) -> str:
    return value.replace("|", "\\|")
