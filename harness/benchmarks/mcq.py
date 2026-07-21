from __future__ import annotations

import re
from collections import defaultdict
from enum import StrEnum
from typing import Iterable

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


VALID_LABELS = tuple("ABCDEFGHIJ")
ANSWER_PATTERN = re.compile(r"(?<![A-Za-z0-9])([A-Ja-j])(?![A-Za-z0-9])")


class MCQParseStatus(StrEnum):
    PARSED = "parsed"
    INVALID = "invalid"


class MCQChoice(BaseModel):
    label: str = Field(min_length=1, max_length=1)
    text: str = Field(min_length=1)

    @field_validator("label")
    @classmethod
    def _validate_label(cls, value: str) -> str:
        label = value.strip().upper()
        if label not in VALID_LABELS:
            raise ValueError("choice label must be A-J")
        return label

    @field_validator("text")
    @classmethod
    def _strip_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("choice text must not be blank")
        return stripped


class MCQQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    benchmark_id: str = Field(min_length=1)
    case_id: str = Field(min_length=1)
    question: str = Field(min_length=1)
    choices: list[MCQChoice] = Field(min_length=2, max_length=10)
    answer: str = Field(min_length=1, max_length=1)
    category: str | None = None

    @field_validator("answer")
    @classmethod
    def _validate_answer_label(cls, value: str) -> str:
        answer = value.strip().upper()
        if answer not in VALID_LABELS:
            raise ValueError("answer must be A-J")
        return answer

    @model_validator(mode="after")
    def _validate_choice_labels(self) -> MCQQuestion:
        labels = [choice.label for choice in self.choices]
        if len(labels) != len(set(labels)):
            raise ValueError("choice labels must be unique")
        if self.answer not in labels:
            raise ValueError("answer must match one of the choices")
        return self


class MCQParseResult(BaseModel):
    status: MCQParseStatus
    raw_output: str
    parsed_answer: str | None = None
    invalid_reason: str | None = None

    @property
    def is_valid(self) -> bool:
        return self.status == MCQParseStatus.PARSED


class MCQCaseResult(BaseModel):
    benchmark_id: str
    case_id: str
    category: str | None = None
    correct_answer: str
    raw_output: str
    parsed_answer: str | None
    is_correct: bool
    is_invalid: bool
    invalid_reason: str | None = None


class MCQAggregate(BaseModel):
    total: int
    correct: int
    invalid: int
    accuracy: float
    invalid_rate: float


class MCQAggregateReport(BaseModel):
    overall: MCQAggregate
    by_benchmark: dict[str, MCQAggregate]
    by_category: dict[str, MCQAggregate]


def build_mcq_prompt(question: MCQQuestion) -> str:
    choices = "\n".join(
        f"{choice.label}. {choice.text}" for choice in question.choices
    )
    return (
        f"Question:\n{question.question}\n\n"
        f"Choices:\n{choices}\n\n"
        "Answer with exactly one choice label from A to J."
    )


def parse_mcq_answer(raw_output: str) -> MCQParseResult:
    labels = [
        match.group(1).upper()
        for match in ANSWER_PATTERN.finditer(raw_output)
        if _looks_like_answer_marker(raw_output, match)
    ]
    distinct_labels = sorted(set(labels))

    if not distinct_labels:
        return MCQParseResult(
            status=MCQParseStatus.INVALID,
            raw_output=raw_output,
            invalid_reason="No A-J answer choice found.",
        )
    if len(distinct_labels) > 1:
        return MCQParseResult(
            status=MCQParseStatus.INVALID,
            raw_output=raw_output,
            invalid_reason="Multiple distinct answer choices found.",
        )
    return MCQParseResult(
        status=MCQParseStatus.PARSED,
        raw_output=raw_output,
        parsed_answer=distinct_labels[0],
    )


def _looks_like_answer_marker(raw_output: str, match: re.Match[str]) -> bool:
    label = match.group(1)
    start, end = match.span(1)

    next_char = raw_output[end] if end < len(raw_output) else ""
    if label == "I" and start == 0 and next_char == " ":
        return False
    return True


def score_mcq_response(question: MCQQuestion, raw_output: str) -> MCQCaseResult:
    parsed = parse_mcq_answer(raw_output)
    parsed_answer = parsed.parsed_answer if parsed.is_valid else None
    return MCQCaseResult(
        benchmark_id=question.benchmark_id,
        case_id=question.case_id,
        category=question.category,
        correct_answer=question.answer,
        raw_output=raw_output,
        parsed_answer=parsed_answer,
        is_correct=parsed_answer == question.answer,
        is_invalid=not parsed.is_valid,
        invalid_reason=parsed.invalid_reason,
    )


def aggregate_mcq_results(results: Iterable[MCQCaseResult]) -> MCQAggregateReport:
    items = list(results)
    by_benchmark: dict[str, list[MCQCaseResult]] = defaultdict(list)
    by_category: dict[str, list[MCQCaseResult]] = defaultdict(list)

    for item in items:
        by_benchmark[item.benchmark_id].append(item)
        by_category[item.category or "uncategorized"].append(item)

    return MCQAggregateReport(
        overall=_aggregate(items),
        by_benchmark={
            benchmark_id: _aggregate(group)
            for benchmark_id, group in sorted(by_benchmark.items())
        },
        by_category={
            category: _aggregate(group)
            for category, group in sorted(by_category.items())
        },
    )


def _aggregate(results: list[MCQCaseResult]) -> MCQAggregate:
    total = len(results)
    correct = sum(1 for result in results if result.is_correct)
    invalid = sum(1 for result in results if result.is_invalid)
    return MCQAggregate(
        total=total,
        correct=correct,
        invalid=invalid,
        accuracy=correct / total if total else 0.0,
        invalid_rate=invalid / total if total else 0.0,
    )
