from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterable

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from harness.benchmarks.mcq import (
    MCQChoice,
    MCQQuestion,
    aggregate_mcq_results,
    build_mcq_prompt,
    score_mcq_response,
)
from harness.schemas import FailureCategory


BENCHMARK_ID = "kobalt-700"
DEFAULT_DATASET_ID = "kobalt-700-local"


class KoBALT700DatasetError(ValueError):
    def __init__(self, category: FailureCategory, message: str) -> None:
        super().__init__(message)
        self.category = category
        self.message = message


class KoBALT700FieldMapping(BaseModel):
    model_config = ConfigDict(frozen=True)

    case_id: str = "case_id"
    question: str = "question"
    answer: str = "answer"
    choices: dict[str, str] = Field(
        default_factory=lambda: {
            "A": "choice_a",
            "B": "choice_b",
            "C": "choice_c",
            "D": "choice_d",
        }
    )
    category: str | None = "category"
    metadata: dict[str, str] = Field(default_factory=dict)

    @field_validator("choices")
    @classmethod
    def _validate_choice_mapping(cls, value: dict[str, str]) -> dict[str, str]:
        if len(value) < 2:
            raise ValueError("choice mapping must include at least two choices")
        normalized: dict[str, str] = {}
        for label, field_name in value.items():
            choice_label = label.strip().upper()
            if choice_label not in tuple("ABCDEFGHIJ"):
                raise ValueError("choice mapping labels must be A-J")
            if not field_name.strip():
                raise ValueError("choice mapping field names must not be blank")
            normalized[choice_label] = field_name.strip()
        return dict(sorted(normalized.items()))


class KoBALT700Case(BaseModel):
    model_config = ConfigDict(extra="forbid")

    benchmark_id: str = BENCHMARK_ID
    dataset_id: str = DEFAULT_DATASET_ID
    case_id: str = Field(min_length=1)
    category: str | None = None
    question: str = Field(min_length=1)
    choices: list[MCQChoice] = Field(min_length=2, max_length=10)
    answer: str = Field(min_length=1, max_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("answer")
    @classmethod
    def _normalize_answer(cls, value: str) -> str:
        return value.strip().upper()

    @model_validator(mode="after")
    def _validate_answer_membership(self) -> KoBALT700Case:
        labels = {choice.label for choice in self.choices}
        if self.answer not in labels:
            raise ValueError("answer must match one of the choices")
        return self

    def to_mcq_question(self) -> MCQQuestion:
        return MCQQuestion(
            benchmark_id=self.benchmark_id,
            case_id=self.case_id,
            category=self.category,
            question=self.question,
            choices=self.choices,
            answer=self.answer,
        )

    def build_prompt(self) -> str:
        return build_mcq_prompt(self.to_mcq_question())

    def score_response(self, raw_output: str):
        return score_mcq_response(self.to_mcq_question(), raw_output)


def load_kobalt_700_cases(
    source_path: str | Path,
    *,
    dataset_id: str = DEFAULT_DATASET_ID,
    mapping: KoBALT700FieldMapping | None = None,
) -> list[KoBALT700Case]:
    path = Path(source_path)
    field_mapping = mapping or KoBALT700FieldMapping()
    rows = _load_rows(path)
    return [
        _normalize_row(row, dataset_id=dataset_id, mapping=field_mapping, row_number=index)
        for index, row in enumerate(rows, start=1)
    ]


def score_kobalt_700_responses(
    cases: Iterable[KoBALT700Case],
    raw_outputs_by_case_id: dict[str, str],
):
    results = [
        case.score_response(raw_outputs_by_case_id.get(case.case_id, ""))
        for case in cases
    ]
    return aggregate_mcq_results(results)


def _load_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists() or not path.is_file():
        raise KoBALT700DatasetError(
            FailureCategory.DATASET_UNAVAILABLE,
            f"KoBALT-700 dataset file does not exist or is not readable: {path}",
        )
    if path.suffix.lower() == ".jsonl":
        return _load_jsonl(path)
    if path.suffix.lower() == ".csv":
        return _load_csv(path)
    raise KoBALT700DatasetError(
        FailureCategory.DATASET_UNAVAILABLE,
        f"Unsupported KoBALT-700 dataset file extension: {path.suffix}",
    )


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise KoBALT700DatasetError(
                FailureCategory.DATASET_SCHEMA_CHANGED,
                f"Invalid JSONL at line {line_number}: {exc.msg}",
            ) from exc
        if not isinstance(row, dict):
            raise KoBALT700DatasetError(
                FailureCategory.DATASET_SCHEMA_CHANGED,
                f"JSONL line {line_number} must be an object.",
            )
        rows.append(row)
    return rows


def _load_csv(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def _normalize_row(
    row: dict[str, Any],
    *,
    dataset_id: str,
    mapping: KoBALT700FieldMapping,
    row_number: int,
) -> KoBALT700Case:
    _reject_unsupported_shape(row, mapping=mapping, row_number=row_number)
    case_id = _required_text(row, mapping.case_id, row_number)
    question = _required_text(row, mapping.question, row_number)
    answer = _required_text(row, mapping.answer, row_number).upper()
    choices = [
        MCQChoice(label=label, text=_required_text(row, field_name, row_number))
        for label, field_name in mapping.choices.items()
    ]
    category = (
        _optional_text(row, mapping.category)
        if mapping.category is not None
        else None
    )
    metadata = {
        name: row[field_name]
        for name, field_name in mapping.metadata.items()
        if field_name in row and row[field_name] not in (None, "")
    }

    try:
        return KoBALT700Case(
            dataset_id=dataset_id,
            case_id=case_id,
            category=category,
            question=question,
            choices=choices,
            answer=answer,
            metadata=metadata,
        )
    except ValueError as exc:
        raise KoBALT700DatasetError(
            FailureCategory.DATASET_SCHEMA_CHANGED,
            f"Invalid KoBALT-700 row {row_number}: {exc}",
        ) from exc


def _reject_unsupported_shape(
    row: dict[str, Any], *, mapping: KoBALT700FieldMapping, row_number: int
) -> None:
    required_fields = [mapping.case_id, mapping.question, mapping.answer, *mapping.choices.values()]
    missing_fields = [field_name for field_name in required_fields if field_name not in row]
    if missing_fields:
        raise KoBALT700DatasetError(
            FailureCategory.DATASET_SCHEMA_CHANGED,
            "KoBALT-700 row "
            f"{row_number} is not a supported mapped choice-answer row; "
            f"missing mapped fields: {', '.join(missing_fields)}.",
        )


def _required_text(row: dict[str, Any], field_name: str, row_number: int) -> str:
    value = row[field_name]
    if value is None or str(value).strip() == "":
        raise KoBALT700DatasetError(
            FailureCategory.DATASET_SCHEMA_CHANGED,
            f"KoBALT-700 row {row_number} has blank mapped field '{field_name}'.",
        )
    return str(value).strip()


def _optional_text(row: dict[str, Any], field_name: str | None) -> str | None:
    if field_name is None or field_name not in row:
        return None
    value = row[field_name]
    text = str(value).strip() if value is not None else ""
    return text or None
