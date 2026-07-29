from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field

from harness.mileday.constraints import ScheduleValidationResult
from harness.mileday.dataset import MileDayGenerationCase
from harness.schemas import EvaluationError, FailureCategory


RUBRIC_DOCUMENTATION = {
    "goal_alignment": "Milestones should clearly support the fixture goal.",
    "actionability": "Milestones should be concrete enough for a user to act on.",
    "schedule_balance": "Milestones should be spread across the available time window.",
}


class SemanticJudge(Protocol):
    def evaluate(
        self,
        case: MileDayGenerationCase,
        parsed_output: dict[str, Any],
    ) -> dict[str, float]:
        """Return optional rubric dimension scores in the 0.0-1.0 range."""


class RubricDimensionScore(BaseModel):
    name: str
    score: float = Field(ge=0.0, le=1.0)
    note: str


class SemanticRubricResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    dataset_id: str
    case_id: str
    is_valid: bool
    skipped: bool = False
    dimension_scores: list[RubricDimensionScore] = Field(default_factory=list)
    aggregate_score: float | None = None
    notes: list[str] = Field(default_factory=list)
    raw_output: str | None = None
    error: EvaluationError | None = None


def evaluate_semantic_rubric(
    case: MileDayGenerationCase,
    parsed_output: dict[str, Any],
    validation: ScheduleValidationResult,
    *,
    judge: SemanticJudge | None = None,
    require_judge: bool = False,
) -> SemanticRubricResult:
    if not validation.is_valid:
        return SemanticRubricResult(
            dataset_id=case.dataset_id,
            case_id=case.case_id,
            is_valid=False,
            skipped=True,
            aggregate_score=None,
            notes=["Deterministic validation failed; semantic rubric was not applied."],
            raw_output=validation.raw_output,
        )

    if require_judge and judge is None:
        return SemanticRubricResult(
            dataset_id=case.dataset_id,
            case_id=case.case_id,
            is_valid=True,
            skipped=True,
            aggregate_score=None,
            notes=["Semantic judge is required but unavailable."],
            raw_output=validation.raw_output,
            error=EvaluationError(
                category=FailureCategory.EXTERNAL_DEPENDENCY,
                message="Semantic judge dependency is unavailable.",
            ),
        )

    scores = _deterministic_scores(case, parsed_output)
    if judge is not None:
        scores.update(_clamp_scores(judge.evaluate(case, parsed_output)))

    dimensions = [
        RubricDimensionScore(
            name=name,
            score=score,
            note=RUBRIC_DOCUMENTATION.get(name, "Judge-provided rubric dimension."),
        )
        for name, score in sorted(scores.items())
    ]
    aggregate = sum(item.score for item in dimensions) / len(dimensions) if dimensions else 0.0
    return SemanticRubricResult(
        dataset_id=case.dataset_id,
        case_id=case.case_id,
        is_valid=True,
        dimension_scores=dimensions,
        aggregate_score=round(aggregate, 4),
        notes=["Semantic rubric applied after deterministic validation passed."],
        raw_output=validation.raw_output,
    )


def _deterministic_scores(
    case: MileDayGenerationCase,
    parsed_output: dict[str, Any],
) -> dict[str, float]:
    milestones = parsed_output.get("milestones", [])
    goal_terms = {
        token.lower()
        for token in case.input.goal_title.replace("-", " ").split()
        if len(token) >= 4
    }
    milestone_text = " ".join(
        str(milestone.get("title", "")) + " " + str(milestone.get("description", ""))
        for milestone in milestones
        if isinstance(milestone, dict)
    ).lower()
    goal_alignment = 1.0 if any(term in milestone_text for term in goal_terms) else 0.5
    actionable = sum(
        1
        for milestone in milestones
        if isinstance(milestone, dict) and str(milestone.get("title", "")).strip()
    )
    actionability = actionable / len(milestones) if milestones else 0.0
    unique_dates = {
        milestone.get("scheduled_date")
        for milestone in milestones
        if isinstance(milestone, dict) and milestone.get("scheduled_date")
    }
    schedule_balance = len(unique_dates) / len(milestones) if milestones else 0.0
    return {
        "actionability": round(actionability, 4),
        "goal_alignment": goal_alignment,
        "schedule_balance": round(schedule_balance, 4),
    }


def _clamp_scores(scores: dict[str, float]) -> dict[str, float]:
    return {
        name: min(1.0, max(0.0, float(score)))
        for name, score in scores.items()
    }
