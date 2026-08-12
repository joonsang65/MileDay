from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from statistics import mean

from harness.mileday.api_constants import (
    MILEDAY_API_MODEL_ID,
    MILEDAY_API_MULTITURN_PROMPT_VERSION,
    MILEDAY_MULTITURN_FIXTURE,
    MILEDAY_MULTITURN_PROMPT_VERSION,
)
from harness.mileday.dataset import MileDayMultiTurnCase
from harness.results import ResultStore
from harness.schemas import RequestResult, ResultStatus


def _next_prompt_test_sequence(runs_dir: Path) -> int:
    highest = 0
    if not runs_dir.exists():
        return 1
    pattern = re.compile(r"^prompt-test-(?P<sequence>\d+)(?:-summary\.md)?$")
    for path in runs_dir.iterdir():
        match = pattern.fullmatch(path.name)
        if match is not None:
            highest = max(highest, int(match.group("sequence")))
    return highest + 1


def _append_mileday_multiturn_report(
    run_id: str,
    runs_dir: Path,
    cases: list[MileDayMultiTurnCase],
    *,
    model_id: str = MILEDAY_API_MODEL_ID,
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
    fallback_count = _grid_fallback_used_count(results)
    self_check_mismatches = _grid_self_check_mismatch_count(results)
    time_difficulty_mismatches = _grid_failure_code_counts(results).get("TIME_DIFFICULTY_MISMATCH", 0)
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
        f"| schema_fallback_used | {fallback_count} |",
        f"| self_check_mismatches | {self_check_mismatches} |",
        f"| time_difficulty_mismatches | {time_difficulty_mismatches} |",
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


def _format_rate_from_counts(numerator: int, denominator: int) -> str:
    if denominator <= 0:
        return "없음"
    return f"{numerator / denominator:.1%}"


def _write_prompt_test_summary(
    runs_dir: Path,
    *,
    batch_id: str,
    item: dict[str, object],
    cases: list[MileDayMultiTurnCase],
) -> Path:
    path = runs_dir / f"{batch_id}-summary.md"
    store = ResultStore(runs_dir)
    run_id = str(item["run_id"])
    model_id = str(item["model_id"])
    results = store.load_request_results(run_id)
    counts = _status_counts(results)
    completed_cases = _mileday_multiturn_completed_cases(results, cases)
    all_turn_pass_cases = _mileday_multiturn_all_turn_pass_cases(results, cases)
    judge_rejects = _grid_judge_reject_count(results)
    failure_codes = _grid_failure_code_counts(results)
    self_check_mismatches = _grid_self_check_mismatch_count(results)
    fallback_count = _grid_fallback_used_count(results)
    time_difficulty_mismatches = failure_codes.get("TIME_DIFFICULTY_MISMATCH", 0)
    avg_latency = _grid_avg_latency_ms(results)
    lines = [
        f"# MileDay Prompt Test Summary: {batch_id}",
        "",
        "## Run",
        "",
        "- runtime: gemini",
        f"- model: {model_id}",
        f"- fixture: `{MILEDAY_MULTITURN_FIXTURE.as_posix()}`",
        f"- cases: {len(cases)}",
        f"- prompt version: {MILEDAY_API_MULTITURN_PROMPT_VERSION}",
        "- sampling: fixed full fixture",
        "",
        "## Result",
        "",
        "| model | passed | invalid | failed | skipped | case completion | all-turn-pass cases | judge rejects | schema fallback | self-check mismatches | time/difficulty mismatches | avg latency ms | top failure codes | report | html |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|",
        "| "
        + " | ".join(
            [
                model_id,
                str(counts.get("passed", 0)),
                str(counts.get("invalid", 0)),
                str(counts.get("failed", 0)),
                str(counts.get("skipped", 0)),
                _format_rate_from_counts(len(completed_cases), len(cases)),
                _format_rate_from_counts(len(all_turn_pass_cases), len(cases)),
                str(judge_rejects),
                str(fallback_count),
                str(self_check_mismatches),
                str(time_difficulty_mismatches),
                _format_optional_float(avg_latency),
                _dict_counter_text(dict(failure_codes.most_common(3))) if failure_codes else "none",
                f"`{Path(str(item.get('report_path', ''))).as_posix()}`",
                f"`{Path(str(item.get('html_report_path', ''))).as_posix()}`",
            ]
        )
        + " |",
        "",
        "## Assessment",
        "",
        f"- flash-lite tuning target: {model_id}",
        (
            f"- passed={counts.get('passed', 0)}, invalid={counts.get('invalid', 0)}, "
            f"failed={counts.get('failed', 0)}, skipped={counts.get('skipped', 0)}, "
            f"judge_rejects={judge_rejects}, schema_fallback={fallback_count}, "
            f"time_difficulty_mismatches={time_difficulty_mismatches}"
        ),
    ]
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


def _grid_self_check_mismatch_count(results: list[RequestResult]) -> int:
    count = 0
    for result in results:
        validation = result.parsed_output.get("multiturn_validation")
        if not isinstance(validation, dict):
            continue
        state = validation.get("state")
        if not isinstance(state, dict):
            continue
        self_check = state.get("mutation_safety_check")
        if isinstance(self_check, dict) and self_check.get("model") and self_check.get("matches") is False:
            count += 1
    return count


def _grid_fallback_used_count(results: list[RequestResult]) -> int:
    count = 0
    for result in results:
        validation = result.parsed_output.get("multiturn_validation")
        if isinstance(validation, dict):
            contract = validation.get("contract")
            if isinstance(contract, dict) and contract.get("fallback_used") is True:
                count += 1
                continue
        parsed_json = result.parsed_output.get("parsed_json")
        if isinstance(parsed_json, dict) and parsed_json.get("freeform_fallback_used") is True:
            count += 1
    return count


def _grid_avg_latency_ms(results: list[RequestResult]) -> float | None:
    values = [
        result.metrics.latency_ms
        for result in results
        if result.metrics is not None and result.metrics.latency_ms is not None
    ]
    if not values:
        return None
    return round(sum(values) / len(values), 3)


def _status_counts(results: list[RequestResult]) -> dict[str, int]:
    counts = {status.value: 0 for status in ResultStatus}
    for result in results:
        counts[result.status.value] = counts.get(result.status.value, 0) + 1
    return counts


def _counter_text_for_cli(counts: dict[str, int]) -> str:
    return " ".join(f"{key}={counts.get(key, 0)}" for key in ("passed", "invalid", "failed", "skipped"))


def _case_pass_text_for_cli(results: list[RequestResult], cases: list[MileDayMultiTurnCase]) -> str:
    return f"case_pass={len(_mileday_multiturn_all_turn_pass_cases(results, cases))}/{len(cases)}"


def _format_optional_float(value: float | None) -> str:
    if value is None:
        return "없음"
    return f"{value:.3f}"


def _dict_counter_text(counter: dict[str, int]) -> str:
    return ", ".join(f"{key}={counter[key]}" for key in sorted(counter))


def _escape_table(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")

def next_prompt_test_sequence(runs_dir: Path) -> int:
    return _next_prompt_test_sequence(runs_dir)


def append_mileday_multiturn_report(run_id: str, runs_dir: Path, cases: list[MileDayMultiTurnCase], *, model_id: str = MILEDAY_API_MODEL_ID) -> Path:
    return _append_mileday_multiturn_report(run_id, runs_dir, cases, model_id=model_id)


def write_prompt_test_summary(runs_dir: Path, *, batch_id: str, item: dict[str, object], cases: list[MileDayMultiTurnCase]) -> Path:
    return _write_prompt_test_summary(runs_dir, batch_id=batch_id, item=item, cases=cases)


def status_counts(results: list[RequestResult]) -> dict[str, int]:
    return _status_counts(results)


def counter_text_for_cli(counts: dict[str, int]) -> str:
    return _counter_text_for_cli(counts)


def case_pass_text_for_cli(results: list[RequestResult], cases: list[MileDayMultiTurnCase]) -> str:
    return _case_pass_text_for_cli(results, cases)
