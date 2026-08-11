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
MULTITURN_DATASET_ID = "mileday-multiturn-schedule"
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
LOCALE_PATTERN = re.compile(r"^[a-z]{2}-[A-Z]{2}$")
TIME_PATTERN = re.compile(r"^\d{2}:\d{2}$")
DAY_OF_WEEK = Literal[
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
]
GOAL_DB_FIELDS = ["title", "deadline", "is_recurring", "recurrence_type", "color"]
MILESTONE_DB_FIELDS = ["title", "color", "scheduled_date"]


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


class AvailabilityWindow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    day_of_week: DAY_OF_WEEK
    start_time: str
    end_time: str

    @field_validator("start_time", "end_time")
    @classmethod
    def _validate_time(cls, value: str) -> str:
        stripped = value.strip()
        if not TIME_PATTERN.fullmatch(stripped):
            raise ValueError("time must use HH:MM")
        hour, minute = (int(part) for part in stripped.split(":"))
        if hour > 23 or minute > 59:
            raise ValueError("time must be a valid 24-hour clock value")
        return stripped

    @model_validator(mode="after")
    def _validate_time_order(self) -> "AvailabilityWindow":
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be later than start_time")
        return self


class MileDayMultiTurnGoalInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1)
    deadline: str
    is_recurring: bool = False
    recurrence_type: Literal["daily", "weekly", "monthly"] | None = None
    color: str = Field(min_length=1)

    @field_validator("title", "color")
    @classmethod
    def _strip_nonblank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("value must not be blank")
        return stripped

    @field_validator("deadline")
    @classmethod
    def _validate_deadline(cls, value: str) -> str:
        return _valid_date(value, field_name="input.initial_goal.deadline")

    @model_validator(mode="after")
    def _validate_recurrence(self) -> "MileDayMultiTurnGoalInput":
        if self.is_recurring and self.recurrence_type is None:
            raise ValueError("recurring goals require recurrence_type")
        if not self.is_recurring and self.recurrence_type is not None:
            raise ValueError("non-recurring goals must use null recurrence_type")
        return self


class ExistingMilestoneInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    fixture_milestone_id: str | None = None
    goal_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    color: str = Field(min_length=1)
    scheduled_date: str
    is_completed: bool = False

    @field_validator("scheduled_date")
    @classmethod
    def _validate_scheduled_date(cls, value: str) -> str:
        return _valid_date(value, field_name="existing_schedule.scheduled_date")


class MileDayMultiTurnInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    initial_goal: MileDayMultiTurnGoalInput
    availability: list[AvailabilityWindow] = Field(min_length=1)
    existing_schedule: list[ExistingMilestoneInput] = Field(default_factory=list)


class MileDayConversationTurn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    turn_id: int = Field(ge=1)
    role: Literal["user"]
    content: str = Field(min_length=1)
    expected_action: Literal["create", "partial_update", "modify", "no_op", "clarify"]
    expected_operation: Literal["add", "remove", "rename", "reschedule", "soften", "none"] | None = None

    @field_validator("content")
    @classmethod
    def _strip_content(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("content must not be blank")
        return stripped


class MileDayMultiTurnConstraints(BaseModel):
    model_config = ConfigDict(extra="forbid")

    must_respect_availability: bool = True
    must_preserve_unmentioned_milestones: bool = True
    must_require_user_confirmation: bool = True
    min_milestones: int = Field(ge=1)
    max_milestones: int = Field(ge=1)
    latest_allowed_date: str

    @field_validator("latest_allowed_date")
    @classmethod
    def _validate_latest_allowed_date(cls, value: str) -> str:
        return _valid_date(value, field_name="expected.constraints.latest_allowed_date")

    @model_validator(mode="after")
    def _validate_milestone_bounds(self) -> "MileDayMultiTurnConstraints":
        if self.max_milestones < self.min_milestones:
            raise ValueError("max_milestones must be greater than or equal to min_milestones")
        return self


class MileDayExpectedEffect(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_milestone_ids: list[str] = Field(default_factory=list)
    preserved_milestone_ids: list[str] = Field(default_factory=list)
    protected_milestone_ids: list[str] = Field(default_factory=list)
    allowed_changed_fields: list[str] = Field(default_factory=list)
    forbidden_changed_fields: list[str] = Field(default_factory=list)
    expected_added_count: int | None = Field(default=None, ge=0)
    expected_removed_count: int | None = Field(default=None, ge=0)
    expected_no_op: bool = False
    expected_clarification: bool = False
    preserve_unmentioned: bool = True
    safety_gate_tags: list[str] = Field(default_factory=list)


class MileDayMultiTurnExpected(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response_sections: list[Literal["EXPLANATION", "JSON", "SCHEDULE_INTENT", "일정_의도"]]
    required_json_fields: list[str]
    db_goal_fields: list[str]
    db_milestone_fields: list[str]
    non_db_schedule_slot_fields: list[str] = Field(default_factory=list)
    allowed_actions: list[Literal["create", "partial_update", "modify", "no_op", "clarify"]]
    partial_update_only: Literal[True]
    requires_judge: Literal[True]
    constraints: MileDayMultiTurnConstraints
    effect: MileDayExpectedEffect = Field(default_factory=MileDayExpectedEffect)
    judge_rubric: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_schema_contract(self) -> "MileDayMultiTurnExpected":
        if self.response_sections not in (["EXPLANATION", "JSON"], ["SCHEDULE_INTENT"], ["일정_의도"]):
            raise ValueError("response_sections must match a supported multiturn output contract")
        if self.db_goal_fields != GOAL_DB_FIELDS:
            raise ValueError("db_goal_fields must match the current goal DB payload fields")
        if self.db_milestone_fields != MILESTONE_DB_FIELDS:
            raise ValueError("db_milestone_fields must match the current milestone DB payload fields")
        return self


class MileDayMultiTurnCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dataset_id: Literal["mileday-multiturn-schedule"]
    case_id: str = Field(min_length=1)
    locale: str
    timezone: str
    input: MileDayMultiTurnInput
    turns: list[MileDayConversationTurn] = Field(min_length=2, max_length=5)
    expected: MileDayMultiTurnExpected
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

    @model_validator(mode="after")
    def _validate_turn_sequence(self) -> "MileDayMultiTurnCase":
        turn_ids = [turn.turn_id for turn in self.turns]
        expected_turn_ids = list(range(1, len(self.turns) + 1))
        if turn_ids != expected_turn_ids:
            raise ValueError("turn_id values must be sequential from 1")
        return self


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


def load_mileday_multiturn_cases(source_path: str | Path) -> list[MileDayMultiTurnCase]:
    path = Path(source_path)
    rows = _load_rows(path)
    if not rows:
        raise MileDayDatasetError(
            FailureCategory.DATASET_SCHEMA_CHANGED,
            f"MileDay multiturn dataset file contains no cases: {path}",
        )
    cases: list[MileDayMultiTurnCase] = []
    for index, row in enumerate(rows, start=1):
        try:
            cases.append(MileDayMultiTurnCase.model_validate(row))
        except ValidationError as exc:
            raise MileDayDatasetError(
                FailureCategory.DATASET_SCHEMA_CHANGED,
                f"Invalid MileDay multiturn case at row {index}: {exc}",
            ) from exc
    return cases


class MileDayMultiTurnFixtureQuality(BaseModel):
    model_config = ConfigDict(frozen=True)

    case_count: int
    total_turns: int
    average_turns: float
    primary_group_counts: dict[str, int]
    required_tag_counts: dict[str, int]
    user_segment_counts: dict[str, int]
    domain_counts: dict[str, int]


REQUIRED_MULTITURN_PRIMARY_GROUP_COUNTS = {
    "basic_creation": 6,
    "partial_update": 7,
    "add_remove": 5,
    "conflict": 5,
    "state_preservation": 4,
    "ambiguous": 3,
}
REQUIRED_MULTITURN_TAG_MIN_COUNTS = {
    "target_not_found": 2,
    "completed_milestone_protection": 2,
    "availability_violation": 2,
    "deadline_violation": 2,
    "subset_slots": 2,
    "single_remove": 2,
    "single_add": 2,
    "rename_only": 2,
    "soften_only": 2,
    "preserve_unmentioned": 2,
    "reschedule_only": 2,
    "ambiguous_target": 2,
    "ambiguous_request": 3,
}


def summarize_mileday_multiturn_fixture_quality(
    cases: list[MileDayMultiTurnCase],
) -> MileDayMultiTurnFixtureQuality:
    from collections import Counter

    primary_groups = Counter()
    required_tags = Counter()
    user_segments = Counter()
    domains = Counter()
    for case in cases:
        metadata = case.metadata
        primary_group = metadata.get("primary_group")
        if isinstance(primary_group, str):
            primary_groups[primary_group] += 1
        user_segment = metadata.get("user_segment")
        if isinstance(user_segment, str):
            user_segments[user_segment] += 1
        domain = metadata.get("domain")
        if isinstance(domain, str):
            domains[domain] += 1
        tags = metadata.get("tags")
        if isinstance(tags, list):
            for tag in tags:
                if isinstance(tag, str):
                    required_tags[tag] += 1
    total_turns = sum(len(case.turns) for case in cases)
    average_turns = total_turns / len(cases) if cases else 0.0
    return MileDayMultiTurnFixtureQuality(
        case_count=len(cases),
        total_turns=total_turns,
        average_turns=round(average_turns, 3),
        primary_group_counts=dict(sorted(primary_groups.items())),
        required_tag_counts=dict(sorted(required_tags.items())),
        user_segment_counts=dict(sorted(user_segments.items())),
        domain_counts=dict(sorted(domains.items())),
    )


def validate_mileday_multiturn_fixture_quality(cases: list[MileDayMultiTurnCase]) -> None:
    quality = summarize_mileday_multiturn_fixture_quality(cases)
    if quality.case_count != 30:
        raise MileDayDatasetError(
            FailureCategory.DATASET_SCHEMA_CHANGED,
            f"MileDay multiturn fixture must contain exactly 30 cases: {quality.case_count}",
        )
    if not 85 <= quality.total_turns <= 95:
        raise MileDayDatasetError(
            FailureCategory.DATASET_SCHEMA_CHANGED,
            f"MileDay multiturn fixture total turns must be 85..95: {quality.total_turns}",
        )
    if not 2.8 <= quality.average_turns <= 3.2:
        raise MileDayDatasetError(
            FailureCategory.DATASET_SCHEMA_CHANGED,
            f"MileDay multiturn fixture average turns must be 2.8..3.2: {quality.average_turns}",
        )
    case_ids = [case.case_id for case in cases]
    if len(set(case_ids)) != len(case_ids):
        raise MileDayDatasetError(FailureCategory.DATASET_SCHEMA_CHANGED, "case_id values must be unique")
    turn_keys = [(case.case_id, turn.turn_id) for case in cases for turn in case.turns]
    if len(set(turn_keys)) != len(turn_keys):
        raise MileDayDatasetError(FailureCategory.DATASET_SCHEMA_CHANGED, "case_id/turn_id pairs must be unique")
    if any(len(case.turns) < 2 or len(case.turns) > 5 for case in cases):
        raise MileDayDatasetError(FailureCategory.DATASET_SCHEMA_CHANGED, "each case must contain 2..5 turns")
    for group, expected_count in REQUIRED_MULTITURN_PRIMARY_GROUP_COUNTS.items():
        actual = quality.primary_group_counts.get(group, 0)
        if actual != expected_count:
            raise MileDayDatasetError(
                FailureCategory.DATASET_SCHEMA_CHANGED,
                f"primary_group {group} must appear {expected_count} times: {actual}",
            )
    for tag, minimum_count in REQUIRED_MULTITURN_TAG_MIN_COUNTS.items():
        actual = quality.required_tag_counts.get(tag, 0)
        if actual < minimum_count:
            raise MileDayDatasetError(
                FailureCategory.DATASET_SCHEMA_CHANGED,
                f"tag {tag} must appear at least {minimum_count} times: {actual}",
            )


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
        lines = path.read_text(encoding="utf-8-sig").splitlines()
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
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
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
