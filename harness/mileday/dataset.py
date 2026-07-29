from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Any, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from harness.schemas import FailureCategory


DEFAULT_DATASET_ID = "mileday-schedule"
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
LOCALE_PATTERN = re.compile(r"^[a-z]{2}-[A-Z]{2}$")


class MileDayDatasetError(ValueError):
    def __init__(self, category: FailureCategory, message: str) -> None:
        super().__init__(message)
        self.category = category
        self.message = message


class MileDayGenerationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    goal_title: str = Field(min_length=1)
    deadline: str
    constraints: dict[str, Any]

    @field_validator("goal_title")
    @classmethod
    def _strip_goal_title(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("goal_title must not be blank")
        return stripped

    @field_validator("deadline")
    @classmethod
    def _validate_deadline(cls, value: str) -> str:
        return _valid_date(value, field_name="input.deadline")


class MileDayGenerationExpected(BaseModel):
    model_config = ConfigDict(extra="forbid")

    min_milestones: int = Field(ge=1)
    max_milestones: int = Field(ge=1)
    latest_allowed_date: str
    required_fields: list[str]

    @field_validator("latest_allowed_date")
    @classmethod
    def _validate_latest_allowed_date(cls, value: str) -> str:
        return _valid_date(value, field_name="expected.latest_allowed_date")

    @field_validator("required_fields")
    @classmethod
    def _validate_required_fields(cls, value: list[str]) -> list[str]:
        normalized = [item.strip() for item in value]
        if any(not item for item in normalized):
            raise ValueError("required_fields must not contain blank values")
        return normalized

    @model_validator(mode="after")
    def _validate_milestone_bounds(self) -> MileDayGenerationExpected:
        if self.max_milestones < self.min_milestones:
            raise ValueError("max_milestones must be greater than or equal to min_milestones")
        return self


class MileDayGenerationCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dataset_id: Literal["mileday-schedule"]
    case_id: str = Field(min_length=1)
    locale: str
    timezone: str
    input: MileDayGenerationInput
    expected: MileDayGenerationExpected
    metadata: dict[str, Any]

    @field_validator("case_id")
    @classmethod
    def _strip_case_id(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("case_id must not be blank")
        return stripped

    @field_validator("locale")
    @classmethod
    def _validate_locale(cls, value: str) -> str:
        stripped = value.strip()
        if not LOCALE_PATTERN.fullmatch(stripped):
            raise ValueError("locale must use language-region format such as ko-KR")
        return stripped

    @field_validator("timezone")
    @classmethod
    def _validate_timezone(cls, value: str) -> str:
        stripped = value.strip()
        try:
            ZoneInfo(stripped)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"timezone is not available: {stripped}") from exc
        return stripped


def load_mileday_generation_cases(source_path: str | Path) -> list[MileDayGenerationCase]:
    path = Path(source_path)
    rows = _load_rows(path)
    if not rows:
        raise MileDayDatasetError(
            FailureCategory.DATASET_SCHEMA_CHANGED,
            f"MileDay dataset file contains no cases: {path}",
        )
    cases: list[MileDayGenerationCase] = []
    for index, row in enumerate(rows, start=1):
        try:
            cases.append(MileDayGenerationCase.model_validate(row))
        except ValidationError as exc:
            raise MileDayDatasetError(
                FailureCategory.DATASET_SCHEMA_CHANGED,
                f"Invalid MileDay generation case at row {index}: {exc}",
            ) from exc
    return cases


def _load_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists() or not path.is_file():
        raise MileDayDatasetError(
            FailureCategory.DATASET_UNAVAILABLE,
            f"MileDay dataset file does not exist or is not readable: {path}",
        )
    if path.suffix.lower() == ".jsonl":
        return _load_jsonl(path)
    if path.suffix.lower() == ".json":
        return _load_json(path)
    raise MileDayDatasetError(
        FailureCategory.DATASET_UNAVAILABLE,
        f"Unsupported MileDay dataset file extension: {path.suffix}",
    )


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise MileDayDatasetError(
            FailureCategory.DATASET_UNAVAILABLE,
            f"MileDay dataset file is not readable: {path}",
        ) from exc
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise MileDayDatasetError(
                FailureCategory.DATASET_SCHEMA_CHANGED,
                f"Invalid JSONL at line {line_number}: {exc.msg}",
            ) from exc
        if not isinstance(row, dict):
            raise MileDayDatasetError(
                FailureCategory.DATASET_SCHEMA_CHANGED,
                f"JSONL line {line_number} must be an object.",
            )
        rows.append(row)
    return rows


def _load_json(path: Path) -> list[dict[str, Any]]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise MileDayDatasetError(
            FailureCategory.DATASET_UNAVAILABLE,
            f"MileDay dataset file is not readable: {path}",
        ) from exc
    except json.JSONDecodeError as exc:
        raise MileDayDatasetError(
            FailureCategory.DATASET_SCHEMA_CHANGED,
            f"Invalid JSON at {path}: {exc.msg}",
        ) from exc
    if isinstance(raw, dict):
        raw = [raw]
    if not isinstance(raw, list) or not all(isinstance(row, dict) for row in raw):
        raise MileDayDatasetError(
            FailureCategory.DATASET_SCHEMA_CHANGED,
            f"Expected a JSON object or JSON array of objects: {path}",
        )
    return raw


def _valid_date(value: str, *, field_name: str) -> str:
    stripped = value.strip()
    if not DATE_PATTERN.fullmatch(stripped):
        raise ValueError(f"{field_name} must use YYYY-MM-DD")
    try:
        date.fromisoformat(stripped)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be a valid calendar date") from exc
    return stripped
