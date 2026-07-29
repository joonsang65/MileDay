from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from statistics import mean

from harness.reporting import dataset_family
from harness.results import ResultStore
from harness.schemas import RequestResult, ResultStatus


MAX_INVALID_RATE = 0.20
MAX_FAILURE_RATE = 0.00
MAX_AVG_LATENCY_MS = 30_000.0
NEAR_TIE_SCORE_DELTA = 0.01

HARD_GATE_RULES = (
    "추천 대상 모델은 공개 benchmark 결과를 최소 1개 이상 가져야 합니다.",
    "추천 대상 모델은 MileDay deterministic validation 결과를 최소 1개 이상 가져야 합니다.",
    "추천 대상 모델은 MileDay semantic rubric 점수를 최소 1개 이상 가져야 합니다.",
    "추천 대상 모델은 latency, TTFT, throughput metric을 모두 가져야 합니다.",
    f"Invalid rate는 {MAX_INVALID_RATE:.2f} 이하여야 합니다.",
    f"Failure rate는 {MAX_FAILURE_RATE:.2f} 이하여야 합니다.",
    f"평균 latency는 {MAX_AVG_LATENCY_MS:.0f} ms 이하여야 합니다.",
)


@dataclass(frozen=True)
class ModelEvidence:
    model_id: str
    public_score: float | None
    mileday_valid_rate: float | None
    mileday_semantic_score: float | None
    avg_latency_ms: float | None
    avg_ttft_ms: float | None
    avg_tokens_per_second: float | None
    invalid_rate: float
    failure_rate: float
    result_count: int
    datasets: tuple[str, ...]
    artifact_paths: tuple[str, ...]
    blocked_reasons: tuple[str, ...]
    ranking_score: float | None


@dataclass(frozen=True)
class RecommendationSummary:
    run_id: str
    status: str
    recommended_model_id: str | None
    reason: str
    hard_gate_rules: tuple[str, ...]
    model_evidence: tuple[ModelEvidence, ...]
    tied_model_ids: tuple[str, ...] = ()


def summarize_recommendation(
    run_id: str,
    runs_dir: str | Path = Path("artifacts") / "runs",
) -> RecommendationSummary:
    store = ResultStore(runs_dir)
    results = store.load_request_results(run_id)
    evidence = tuple(_build_model_evidence(model_id, group) for model_id, group in _group_by_model(results))
    eligible = [item for item in evidence if not item.blocked_reasons and item.ranking_score is not None]
    if not results:
        return RecommendationSummary(
            run_id=run_id,
            status="insufficient_data",
            recommended_model_id=None,
            reason="저장된 request result가 없습니다.",
            hard_gate_rules=HARD_GATE_RULES,
            model_evidence=evidence,
        )
    if not eligible:
        return RecommendationSummary(
            run_id=run_id,
            status="no_recommendation",
            recommended_model_id=None,
            reason="모든 hard gate를 통과한 모델이 없습니다.",
            hard_gate_rules=HARD_GATE_RULES,
            model_evidence=evidence,
        )

    ranked = sorted(
        eligible,
        key=lambda item: (
            -(item.ranking_score or 0.0),
            item.avg_latency_ms if item.avg_latency_ms is not None else float("inf"),
            item.model_id,
        ),
    )
    if len(ranked) > 1 and abs((ranked[0].ranking_score or 0.0) - (ranked[1].ranking_score or 0.0)) <= NEAR_TIE_SCORE_DELTA:
        top_score = ranked[0].ranking_score or 0.0
        tied = tuple(
            item.model_id
            for item in ranked
            if abs((item.ranking_score or 0.0) - top_score) <= NEAR_TIE_SCORE_DELTA
        )
        return RecommendationSummary(
            run_id=run_id,
            status="no_recommendation",
            recommended_model_id=None,
            reason=f"{NEAR_TIE_SCORE_DELTA:.2f} 이내 near-tie입니다. deterministic 순서는 " + ", ".join(tied) + "입니다.",
            hard_gate_rules=HARD_GATE_RULES,
            model_evidence=evidence,
            tied_model_ids=tied,
        )

    winner = ranked[0]
    return RecommendationSummary(
        run_id=run_id,
        status="recommended",
        recommended_model_id=winner.model_id,
        reason="모든 hard gate를 통과한 모델 중 ranking score가 가장 높습니다.",
        hard_gate_rules=HARD_GATE_RULES,
        model_evidence=evidence,
    )


def render_recommendation_markdown(summary: RecommendationSummary) -> list[str]:
    lines = [
        "## 최종 추천 요약",
        "",
        f"- Run id: `{summary.run_id}`",
        f"- 상태: `{summary.status}`",
        f"- 추천 모델: `{summary.recommended_model_id or '없음'}`",
        f"- 사유: {summary.reason}",
        "",
        "### Hard Gate",
        "",
    ]
    lines.extend(f"- {rule}" for rule in summary.hard_gate_rules)
    lines.extend(
        [
            "",
            "### 추천 근거",
            "",
            "| 모델 | Rank score | 공개 점수 | MileDay 유효율 | MileDay semantic | Invalid rate | Failure rate | 평균 latency ms | 근거 path | Gate 결과 |",
            "|---|---:|---|---|---|---:|---:|---|---|---|",
        ]
    )
    for item in sorted(summary.model_evidence, key=lambda evidence: evidence.model_id):
        gate = "통과" if not item.blocked_reasons else "; ".join(item.blocked_reasons)
        lines.append(
            "| "
            + " | ".join(
                [
                    item.model_id,
                    _fmt(item.ranking_score),
                    _fmt(item.public_score),
                    _fmt(item.mileday_valid_rate),
                    _fmt(item.mileday_semantic_score),
                    f"{item.invalid_rate:.3f}",
                    f"{item.failure_rate:.3f}",
                    _fmt(item.avg_latency_ms),
                    "<br>".join(f"`{path}`" for path in item.artifact_paths) or "없음",
                    gate,
                ]
            )
            + " |"
        )
    lines.append("")
    if summary.tied_model_ids:
        lines.append("- 동률 모델: " + ", ".join(f"`{model_id}`" for model_id in summary.tied_model_ids))
        lines.append("")
    return lines


def _group_by_model(results: list[RequestResult]) -> list[tuple[str, list[RequestResult]]]:
    grouped: dict[str, list[RequestResult]] = {}
    for result in results:
        grouped.setdefault(result.model_id, []).append(result)
    return [(model_id, grouped[model_id]) for model_id in sorted(grouped)]


def _build_model_evidence(model_id: str, results: list[RequestResult]) -> ModelEvidence:
    public_results = [
        result for result in results if dataset_family(result.dataset_id, result.parsed_output) == "public_benchmark"
    ]
    mileday_results = [
        result for result in results if dataset_family(result.dataset_id, result.parsed_output) == "mileday_generation"
    ]
    public_scores = [_public_score(result) for result in public_results]
    semantic_scores = [_semantic_score(result) for result in mileday_results]
    latencies = [result.metrics.latency_ms for result in results if result.metrics.latency_ms is not None]
    ttfts = [result.metrics.ttft_ms for result in results if result.metrics.ttft_ms is not None]
    throughputs = [
        result.metrics.tokens_per_second
        for result in results
        if result.metrics.tokens_per_second is not None
    ]
    invalid_rate = _rate(sum(1 for result in results if result.status == ResultStatus.INVALID), len(results))
    failure_rate = _rate(sum(1 for result in results if result.status == ResultStatus.FAILED), len(results))
    mileday_valid_rate = _rate(sum(1 for result in mileday_results if result.status == ResultStatus.PASSED), len(mileday_results)) if mileday_results else None
    public_score = _avg(public_scores)
    semantic_score = _avg(semantic_scores)
    avg_latency = _avg(latencies)
    avg_ttft = _avg(ttfts)
    avg_tps = _avg(throughputs)
    blocked = _blocked_reasons(
        public_score=public_score,
        mileday_valid_rate=mileday_valid_rate,
        semantic_score=semantic_score,
        avg_latency=avg_latency,
        avg_ttft=avg_ttft,
        avg_tps=avg_tps,
        invalid_rate=invalid_rate,
        failure_rate=failure_rate,
    )
    ranking_score = None if blocked else _ranking_score(public_score, mileday_valid_rate, semantic_score, avg_latency, avg_tps)
    return ModelEvidence(
        model_id=model_id,
        public_score=public_score,
        mileday_valid_rate=mileday_valid_rate,
        mileday_semantic_score=semantic_score,
        avg_latency_ms=avg_latency,
        avg_ttft_ms=avg_ttft,
        avg_tokens_per_second=avg_tps,
        invalid_rate=invalid_rate,
        failure_rate=failure_rate,
        result_count=len(results),
        datasets=tuple(sorted({result.dataset_id for result in results})),
        artifact_paths=tuple(
            sorted({Path(result.raw_output_path).as_posix() for result in results if result.raw_output_path is not None})
        ),
        blocked_reasons=tuple(blocked),
        ranking_score=ranking_score,
    )


def _blocked_reasons(
    *,
    public_score: float | None,
    mileday_valid_rate: float | None,
    semantic_score: float | None,
    avg_latency: float | None,
    avg_ttft: float | None,
    avg_tps: float | None,
    invalid_rate: float,
    failure_rate: float,
) -> list[str]:
    blocked: list[str] = []
    if public_score is None:
        blocked.append("공개 benchmark 근거 없음")
    if mileday_valid_rate is None:
        blocked.append("MileDay deterministic 근거 없음")
    if semantic_score is None:
        blocked.append("MileDay semantic 근거 없음")
    if avg_latency is None or avg_ttft is None or avg_tps is None:
        blocked.append("성능 metric 없음")
    if invalid_rate > MAX_INVALID_RATE:
        blocked.append("invalid rate gate 실패")
    if failure_rate > MAX_FAILURE_RATE:
        blocked.append("failure rate gate 실패")
    if avg_latency is not None and avg_latency > MAX_AVG_LATENCY_MS:
        blocked.append("latency gate 실패")
    return blocked


def _ranking_score(
    public_score: float | None,
    mileday_valid_rate: float | None,
    semantic_score: float | None,
    avg_latency: float | None,
    avg_tps: float | None,
) -> float:
    assert public_score is not None
    assert mileday_valid_rate is not None
    assert semantic_score is not None
    assert avg_latency is not None
    assert avg_tps is not None
    latency_score = max(0.0, 1.0 - (avg_latency / MAX_AVG_LATENCY_MS))
    throughput_score = min(avg_tps / 50.0, 1.0)
    performance_score = (latency_score + throughput_score) / 2
    return (public_score * 0.35) + (mileday_valid_rate * 0.25) + (semantic_score * 0.30) + (performance_score * 0.10)


def _public_score(result: RequestResult) -> float | None:
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


def _avg(values: list[float | int | None]) -> float | None:
    present = [float(value) for value in values if value is not None]
    return mean(present) if present else None


def _rate(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def _fmt(value: float | None) -> str:
    return "없음" if value is None else f"{value:.3f}"
