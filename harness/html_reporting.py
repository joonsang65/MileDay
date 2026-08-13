from __future__ import annotations

import json
from collections import Counter, defaultdict
from html import escape
from pathlib import Path
from statistics import mean
from typing import Any

from harness.reporting import load_report_input
from harness.results import ResultStore
from harness.schemas import RequestResult, ResultStatus


def generate_mileday_multiturn_html_report(
    run_id: str,
    runs_dir: str | Path = Path("artifacts") / "runs",
) -> Path:
    """저장된 MileDay 멀티턴 run artifact를 사람이 검토하기 쉬운 HTML로 렌더링합니다."""

    store = ResultStore(runs_dir)
    report_input = load_report_input(run_id, store)
    html = render_mileday_multiturn_html_report(report_input.run_id, report_input.results)
    path = report_input.run_dir / "report.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8", newline="\n")
    return path


def generate_ai_draft_html_report(
    run_id: str,
    runs_dir: str | Path = Path("artifacts") / "runs",
) -> Path:
    """저장된 MileDay AI 일정 초안 run artifact를 HTML로 렌더링합니다."""

    store = ResultStore(runs_dir)
    report_input = load_report_input(run_id, store)
    html = render_ai_draft_html_report(report_input.run_id, report_input.results)
    path = report_input.run_dir / "report.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8", newline="\n")
    return path


def render_ai_draft_html_report(run_id: str, results: tuple[RequestResult, ...]) -> str:
    sorted_results = sorted(results, key=_result_sort_key)
    counts = Counter(result.status.value for result in sorted_results)
    judge_scores = [
        float(judge["score"])
        for result in sorted_results
        if isinstance(judge := result.parsed_output.get("draft_judge"), dict)
        and judge.get("error") is None
        and isinstance(judge.get("score"), int | float)
    ]
    validation_failures = _draft_validation_failure_counts(sorted_results)
    body = [
        "<!doctype html>",
        '<html lang="ko">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>MileDay AI 일정 초안 리포트 - {escape(run_id)}</title>",
        "<style>",
        _stylesheet(),
        "</style>",
        "</head>",
        "<body>",
        '<main class="page">',
        '<section class="hero">',
        "<div>",
        "<p>Harness HTML Report</p>",
        f"<h1>{escape(run_id)}</h1>",
        "</div>",
        f'<span class="status status-{_overall_status(counts)}">{escape(_overall_status_label(counts))}</span>',
        "</section>",
        _summary_grid(
            {
                "전체 case": len(sorted_results),
                "passed": counts.get(ResultStatus.PASSED.value, 0),
                "invalid": counts.get(ResultStatus.INVALID.value, 0),
                "failed": counts.get(ResultStatus.FAILED.value, 0),
                "skipped": counts.get(ResultStatus.SKIPPED.value, 0),
                "case pass": f"{counts.get(ResultStatus.PASSED.value, 0)} / {len(sorted_results)}",
                "judge 평균": _format_number(mean(judge_scores) if judge_scores else None),
                "평균 latency": _format_ms(_mean_metric(sorted_results, "latency_ms")),
            }
        ),
        _draft_failure_section(validation_failures, sorted_results),
        _draft_case_sections(sorted_results),
        "</main>",
        "</body>",
        "</html>",
    ]
    return "\n".join(body) + "\n"


def render_mileday_multiturn_html_report(run_id: str, results: tuple[RequestResult, ...]) -> str:
    sorted_results = sorted(results, key=_result_sort_key)
    grouped = _group_by_case(sorted_results)
    counts = Counter(result.status.value for result in sorted_results)
    judge_scores = [
        float(judge["score"])
        for result in sorted_results
        if _is_completed_judge(judge := result.parsed_output.get("explanation_judge"))
        and isinstance(judge.get("score"), int | float)
    ]
    completed_cases = [
        case_id
        for case_id, group in grouped.items()
        if group and group[-1].status != ResultStatus.SKIPPED
    ]
    all_turn_pass_cases = [
        case_id
        for case_id, group in grouped.items()
        if group and all(result.status == ResultStatus.PASSED for result in group)
    ]
    invalid_results = [
        result
        for result in sorted_results
        if result.status in {ResultStatus.INVALID, ResultStatus.FAILED, ResultStatus.SKIPPED}
    ]
    failure_codes, safety_gate_rows = _failure_taxonomy(sorted_results)

    body = [
        "<!doctype html>",
        '<html lang="ko">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>MileDay 멀티턴 리포트 - {escape(run_id)}</title>",
        "<style>",
        _stylesheet(),
        "</style>",
        "</head>",
        "<body>",
        '<main class="page">',
        '<section class="hero">',
        "<div>",
        "<p>Harness HTML Report</p>",
        f"<h1>{escape(run_id)}</h1>",
        "</div>",
        f'<span class="status status-{_overall_status(counts)}">{escape(_overall_status_label(counts))}</span>',
        "</section>",
        _summary_grid(
            {
                "전체 turn": len(sorted_results),
                "passed": counts.get(ResultStatus.PASSED.value, 0),
                "invalid": counts.get(ResultStatus.INVALID.value, 0),
                "failed": counts.get(ResultStatus.FAILED.value, 0),
                "skipped": counts.get(ResultStatus.SKIPPED.value, 0),
                "마지막 turn 실행": f"{len(completed_cases)} / {len(grouped)}",
                "all-turn-pass case": f"{len(all_turn_pass_cases)} / {len(grouped)}",
                "judge 평균": _format_number(mean(judge_scores) if judge_scores else None),
                "평균 latency": _format_ms(_mean_metric(sorted_results, "latency_ms")),
            }
        ),
        _taxonomy_section(failure_codes, safety_gate_rows),
        _failure_section(invalid_results),
        _case_sections(grouped),
        "</main>",
        "</body>",
        "</html>",
    ]
    return "\n".join(body) + "\n"


def _summary_grid(items: dict[str, object]) -> str:
    cards = []
    for label, value in items.items():
        cards.append(
            '<article class="metric">'
            f"<span>{escape(str(label))}</span>"
            f"<strong>{escape(str(value))}</strong>"
            "</article>"
        )
    return '<section class="metrics">' + "\n".join(cards) + "</section>"


def _draft_failure_section(failure_codes: Counter[str], results: list[RequestResult]) -> str:
    invalid_rows = []
    for result in results:
        if result.status not in {ResultStatus.INVALID, ResultStatus.FAILED, ResultStatus.SKIPPED}:
            continue
        validation = result.parsed_output.get("draft_validation")
        judge = result.parsed_output.get("draft_judge")
        message = result.error.message if result.error is not None else ""
        if not message and isinstance(judge, dict):
            message = str(judge.get("reason", ""))
        invalid_rows.append(
            "<tr>"
            f"<td>{escape(result.case_id)}</td>"
            f'<td><span class="status status-{escape(result.status.value)}">{escape(result.status.value)}</span></td>'
            f"<td>{escape(_failure_codes(validation))}</td>"
            f"<td>{escape(message or '원인 없음')}</td>"
            "</tr>"
        )
    code_rows = "".join(
        f"<tr><td>{escape(code)}</td><td>{count}</td></tr>"
        for code, count in sorted(failure_codes.items())
    )
    if not code_rows:
        code_rows = '<tr><td colspan="2">없음</td></tr>'
    if not invalid_rows:
        invalid_rows.append('<tr><td colspan="4">invalid, failed, skipped 결과가 없습니다.</td></tr>')
    return (
        '<section class="panel">'
        "<h2>실패 분석</h2>"
        "<h3>Validation failure code</h3>"
        '<div class="table-wrap"><table>'
        "<thead><tr><th>failure code</th><th>건수</th></tr></thead>"
        f"<tbody>{code_rows}</tbody>"
        "</table></div>"
        "<h3>검토 대상 case</h3>"
        '<div class="table-wrap"><table>'
        "<thead><tr><th>case</th><th>상태</th><th>failure codes</th><th>사유</th></tr></thead>"
        f"<tbody>{''.join(invalid_rows)}</tbody>"
        "</table></div>"
        "</section>"
    )


def _draft_case_sections(results: list[RequestResult]) -> str:
    sections = ['<section class="case-list">', "<h2>Case별 초안 상세</h2>"]
    for result in results:
        parsed = result.parsed_output
        draft = parsed.get("draft") if isinstance(parsed.get("draft"), dict) else {}
        validation = parsed.get("draft_validation")
        judge = parsed.get("draft_judge")
        goal = draft.get("goal") if isinstance(draft.get("goal"), dict) else {}
        milestones = draft.get("milestones") if isinstance(draft.get("milestones"), list) else []
        preference = (
            draft.get("planning_preference")
            if isinstance(draft.get("planning_preference"), dict)
            else {}
        )
        judge_score = judge.get("score") if isinstance(judge, dict) else None
        judge_reason = judge.get("reason") if isinstance(judge, dict) else ""
        raw_path = result.raw_output_path.as_posix() if result.raw_output_path is not None else ""
        sections.append(
            '<article class="case">'
            '<header class="case-head">'
            f"<h3>{escape(result.case_id)}</h3>"
            f'<span class="status status-{escape(result.status.value)}">{escape(result.status.value)}</span>'
            "</header>"
            '<div class="turn-grid">'
            f"<div><span>judge</span><strong>{escape(_format_number(judge_score))}</strong></div>"
            f"<div><span>latency</span><strong>{escape(_format_ms(result.metrics.latency_ms))}</strong></div>"
            f"<div><span>deadline</span><strong>{escape(str(goal.get('deadline') or '없음'))}</strong></div>"
            f"<div><span>milestones</span><strong>{len(milestones)}</strong></div>"
            "</div>"
            f'<p class="message"><b>Goal</b><br>{escape(str(goal.get("title") or "없음"))}</p>'
            f"{_draft_milestone_table(milestones)}"
            f"{_detail('Planning preference', _json_text(preference))}"
            f"{_tag_list('failure codes', _validation_codes(validation))}"
            f"{_detail('Judge reason', judge_reason)}"
            f"{_detail('Create payload preview', _json_text(parsed.get('create_payload_preview')))}"
            f"{_detail('SQL preview', parsed.get('sql_preview'))}"
            f"{_raw_link(raw_path)}"
            "</article>"
        )
    sections.append("</section>")
    return "\n".join(sections)


def _draft_milestone_table(milestones: list[Any]) -> str:
    if not milestones:
        return '<p class="muted">milestone 없음</p>'
    rows = []
    for item in milestones:
        if not isinstance(item, dict):
            continue
        rows.append(
            "<tr>"
            f"<td>{escape(str(item.get('scheduled_date') or ''))}</td>"
            f"<td>{escape(str(item.get('title') or ''))}</td>"
            "</tr>"
        )
    return (
        '<div class="table-wrap"><table>'
        "<thead><tr><th>date</th><th>milestone</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody>"
        "</table></div>"
    )


def _failure_section(results: list[RequestResult]) -> str:
    if not results:
        return '<section class="panel"><h2>실패 분석</h2><p class="muted">invalid, failed, skipped 결과가 없습니다.</p></section>'
    rows = []
    for result in results:
        judge = result.parsed_output.get("explanation_judge")
        judge_reason = judge.get("reason") if isinstance(judge, dict) else None
        message = result.error.message if result.error is not None else judge_reason
        rows.append(
            "<tr>"
            f"<td>{escape(result.case_id)}</td>"
            f'<td><span class="status status-{escape(result.status.value)}">{escape(result.status.value)}</span></td>'
            f"<td>{escape(result.error.category.value if result.error else 'judge')}</td>"
            f"<td>{escape(str(message or '원인 없음'))}</td>"
            "</tr>"
        )
    return (
        '<section class="panel">'
        "<h2>실패 분석</h2>"
        '<div class="table-wrap"><table>'
        "<thead><tr><th>turn</th><th>상태</th><th>분류</th><th>사유</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody>"
        "</table></div>"
        "</section>"
    )


def _taxonomy_section(failure_codes: Counter[str], safety_gate_rows: list[dict[str, str]]) -> str:
    code_rows = "".join(
        f"<tr><td>{escape(code)}</td><td>{count}</td></tr>"
        for code, count in sorted(failure_codes.items())
    )
    safety_rows = "".join(
        "<tr>"
        f"<td>{escape(row['case_id'])}</td>"
        f"<td>{escape(row['failure_code'])}</td>"
        f"<td>{escape(row['message'])}</td>"
        "</tr>"
        for row in safety_gate_rows
    )
    if not code_rows:
        code_rows = '<tr><td colspan="2">없음</td></tr>'
    if not safety_rows:
        safety_rows = '<tr><td colspan="3">Safety Gate 위반 없음</td></tr>'
    return (
        '<section class="panel">'
        "<h2>Failure Taxonomy / Safety Gate</h2>"
        "<h3>Failure code 집계</h3>"
        '<div class="table-wrap"><table>'
        "<thead><tr><th>failure code</th><th>건수</th></tr></thead>"
        f"<tbody>{code_rows}</tbody>"
        "</table></div>"
        "<h3>Safety Gate 위반</h3>"
        '<div class="table-wrap"><table>'
        "<thead><tr><th>turn</th><th>failure code</th><th>설명</th></tr></thead>"
        f"<tbody>{safety_rows}</tbody>"
        "</table></div>"
        "</section>"
    )


def _case_sections(grouped: dict[str, list[RequestResult]]) -> str:
    sections = ['<section class="case-list">', "<h2>Case별 상세</h2>"]
    for case_id, results in grouped.items():
        counts = Counter(result.status.value for result in results)
        final_status = results[-1].status.value if results else "not_executed"
        sections.append(
            '<article class="case">'
            '<header class="case-head">'
            f"<h3>{escape(case_id)}</h3>"
            f'<span class="status status-{escape(final_status)}">{escape(final_status)}</span>'
            "</header>"
            f'<p class="muted">turns={len(results)} · passed={counts.get("passed", 0)} · '
            f'invalid={counts.get("invalid", 0)} · failed={counts.get("failed", 0)} · skipped={counts.get("skipped", 0)}</p>'
            + "".join(_turn_card(result) for result in results)
            + "</article>"
        )
    sections.append("</section>")
    return "\n".join(sections)


def _turn_card(result: RequestResult) -> str:
    parsed = result.parsed_output
    judge = parsed.get("explanation_judge")
    validation = parsed.get("multiturn_validation")
    db_payload = _nested(parsed, "parsed_json", "db_payload") or _nested(validation, "rule_based_db_payload")
    failed_checks = _nested(validation, "deterministic_validation", "failed_check_names") or []
    failure_codes = _nested(validation, "deterministic_validation", "failure_codes") or []
    raw_path = result.raw_output_path.as_posix() if result.raw_output_path is not None else ""
    user_message = parsed.get("user_message") or parsed.get("explanation") or ""
    judge_score = judge.get("score") if _is_completed_judge(judge) else None
    judge_reason = judge.get("reason") if _is_completed_judge(judge) else ""
    return (
        '<section class="turn">'
        '<div class="turn-head">'
        f"<h4>{escape(result.case_id)}</h4>"
        f'<span class="status status-{escape(result.status.value)}">{escape(result.status.value)}</span>'
        "</div>"
        '<div class="turn-grid">'
        f"<div><span>judge</span><strong>{escape(_format_number(judge_score))}</strong></div>"
        f"<div><span>latency</span><strong>{escape(_format_ms(result.metrics.latency_ms))}</strong></div>"
        f"<div><span>TTFT</span><strong>{escape(_format_ms(result.metrics.ttft_ms))}</strong></div>"
        f"<div><span>tok/s</span><strong>{escape(_format_number(result.metrics.tokens_per_second))}</strong></div>"
        "</div>"
        f'<p class="message">{escape(str(user_message or "사용자 메시지 없음"))}</p>'
        f"{_tag_list('failed checks', failed_checks)}"
        f"{_tag_list('failure codes', failure_codes)}"
        f"{_detail('Judge reason', judge_reason)}"
        f"{_detail('DB payload', _json_text(db_payload))}"
        f"{_raw_link(raw_path)}"
        "</section>"
    )


def _failure_taxonomy(results: list[RequestResult]) -> tuple[Counter[str], list[dict[str, str]]]:
    failure_codes: Counter[str] = Counter()
    safety_rows: list[dict[str, str]] = []
    for result in results:
        validation = result.parsed_output.get("multiturn_validation")
        if isinstance(validation, dict):
            deterministic = validation.get("deterministic_validation")
            if isinstance(deterministic, dict):
                for code in deterministic.get("failure_codes", []):
                    failure_codes[str(code)] += 1
            safety_gate = validation.get("safety_gate")
            if isinstance(safety_gate, dict):
                for violation in safety_gate.get("violations", []):
                    if not isinstance(violation, dict):
                        continue
                    safety_rows.append(
                        {
                            "case_id": result.case_id,
                            "failure_code": str(violation.get("failure_code", "UNKNOWN")),
                            "message": str(violation.get("message", "")),
                        }
                    )
        judge = result.parsed_output.get("explanation_judge")
        if _is_completed_judge(judge) and judge.get("is_aligned") is False:
            failure_codes["JUDGE_REJECTION"] += 1
    return failure_codes, safety_rows


def _draft_validation_failure_counts(results: list[RequestResult]) -> Counter[str]:
    counter: Counter[str] = Counter()
    for result in results:
        validation = result.parsed_output.get("draft_validation")
        if isinstance(validation, dict):
            counter.update(
                code
                for code in validation.get("failure_codes", [])
                if isinstance(code, str)
            )
    return counter


def _is_completed_judge(judge: Any) -> bool:
    return isinstance(judge, dict) and judge.get("skipped") is not True and judge.get("error") is None


def _tag_list(label: str, values: list[Any]) -> str:
    if not values:
        return ""
    tags = "".join(f"<span>{escape(str(value))}</span>" for value in values)
    return f'<div class="tags"><b>{escape(label)}</b>{tags}</div>'


def _validation_codes(validation: object) -> list[Any]:
    if not isinstance(validation, dict):
        return []
    codes = validation.get("failure_codes")
    return codes if isinstance(codes, list) else []


def _failure_codes(validation: object) -> str:
    codes = _validation_codes(validation)
    if not codes:
        return "없음"
    return ", ".join(str(code) for code in codes)


def _detail(summary: str, text: object) -> str:
    if text is None or text == "":
        return ""
    return (
        "<details>"
        f"<summary>{escape(summary)}</summary>"
        f"<pre>{escape(str(text))}</pre>"
        "</details>"
    )


def _raw_link(raw_path: str) -> str:
    if not raw_path:
        return ""
    return f'<p class="raw">raw: <code>{escape(raw_path)}</code></p>'


def _group_by_case(results: list[RequestResult]) -> dict[str, list[RequestResult]]:
    grouped: dict[str, list[RequestResult]] = defaultdict(list)
    for result in results:
        case_id = str(result.parsed_output.get("case_id") or result.case_id.rsplit("-turn-", maxsplit=1)[0])
        grouped[case_id].append(result)
    return dict(sorted(grouped.items()))


def _result_sort_key(result: RequestResult) -> tuple[str, int, str]:
    return (
        str(result.parsed_output.get("case_id") or result.case_id),
        int(result.parsed_output.get("turn_id", 0) or 0),
        result.case_id,
    )


def _nested(value: Any, *keys: str) -> Any:
    current = value
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _json_text(value: Any) -> str:
    if value is None:
        return ""
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)


def _mean_metric(results: list[RequestResult], field_name: str) -> float | None:
    values = [
        float(value)
        for result in results
        if (value := getattr(result.metrics, field_name)) is not None
    ]
    return mean(values) if values else None


def _format_number(value: object) -> str:
    if isinstance(value, int | float):
        return f"{float(value):.3f}"
    return "없음"


def _format_ms(value: object) -> str:
    if isinstance(value, int | float):
        return f"{float(value):.0f} ms"
    return "없음"


def _overall_status(counts: Counter[str]) -> str:
    if counts.get(ResultStatus.FAILED.value, 0):
        return "failed"
    if counts.get(ResultStatus.INVALID.value, 0):
        return "invalid"
    if counts.get(ResultStatus.SKIPPED.value, 0):
        return "skipped"
    return "passed"


def _overall_status_label(counts: Counter[str]) -> str:
    return {
        "passed": "전체 통과",
        "invalid": "검토 필요",
        "failed": "실행 실패 포함",
        "skipped": "스킵 포함",
    }[_overall_status(counts)]


def _stylesheet() -> str:
    return """
:root {
  color-scheme: light;
  --bg: #f6f7f9;
  --text: #1f2937;
  --muted: #6b7280;
  --line: #d9dee7;
  --panel: #ffffff;
  --passed: #0f7a4f;
  --invalid: #b45309;
  --failed: #b91c1c;
  --skipped: #64748b;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font-family: "Segoe UI", "Malgun Gothic", Arial, sans-serif;
  line-height: 1.55;
}
.page { max-width: 1180px; margin: 0 auto; padding: 32px 20px 48px; }
.hero {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 20px;
  padding-bottom: 20px;
  border-bottom: 1px solid var(--line);
}
.hero p, .muted { color: var(--muted); }
.hero p { margin: 0 0 4px; font-size: 13px; }
h1, h2, h3, h4 { margin: 0; letter-spacing: 0; }
h1 { font-size: 28px; }
h2 { margin-bottom: 14px; font-size: 20px; }
h3 { font-size: 18px; }
h4 { font-size: 15px; }
.metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 10px;
  margin: 20px 0;
}
.metric, .panel, .case, .turn {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 8px;
}
.metric { padding: 14px; }
.metric span, .turn-grid span { display: block; color: var(--muted); font-size: 12px; }
.metric strong { display: block; margin-top: 4px; font-size: 22px; }
.panel { padding: 18px; margin: 20px 0; }
.table-wrap { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: 14px; }
th, td { padding: 10px; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; }
.case-list { margin-top: 20px; }
.case { padding: 18px; margin: 14px 0; }
.case-head, .turn-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.turn { padding: 14px; margin-top: 12px; }
.turn-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 10px;
  margin: 12px 0;
}
.turn-grid div { padding: 10px; border: 1px solid var(--line); border-radius: 6px; }
.message { padding: 12px; background: #f8fafc; border-radius: 6px; white-space: pre-wrap; }
.status {
  display: inline-flex;
  align-items: center;
  min-height: 26px;
  padding: 3px 9px;
  border-radius: 999px;
  color: #fff;
  font-size: 12px;
  font-weight: 700;
}
.status-passed { background: var(--passed); }
.status-invalid { background: var(--invalid); }
.status-failed { background: var(--failed); }
.status-skipped { background: var(--skipped); }
details { margin-top: 10px; }
summary { cursor: pointer; font-weight: 700; }
pre {
  overflow-x: auto;
  padding: 12px;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: #0f172a;
  color: #e5e7eb;
  font-size: 12px;
}
.tags { display: flex; align-items: center; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
.tags span { padding: 3px 8px; border-radius: 999px; background: #fee2e2; color: #991b1b; font-size: 12px; }
.raw { color: var(--muted); font-size: 12px; }
code { word-break: break-all; }
"""
