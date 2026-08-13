from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


Weekday = Literal[
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
]
PlanningIntensity = Literal["relaxed", "balanced", "intensive"]


class AiScheduleAvailability(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date: date
    available_minutes: int = Field(gt=0)


class AiScheduleDraftRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt: str = Field(min_length=1, max_length=2000)
    today: date
    timezone: str = Field(default="Asia/Seoul", min_length=1, max_length=80)
    availability: list[AiScheduleAvailability] = Field(min_length=1, max_length=90)


class AiScheduleDraftGoal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1)
    deadline: date


class AiScheduleDraftMilestone(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_id: str
    title: str = Field(min_length=1)
    scheduled_date: date
    selected: bool = True


class AiSchedulePlanningPreference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intensity: PlanningIntensity
    preferred_days: list[Weekday] = Field(default_factory=list)


class AiScheduleDraftValidation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_valid: bool
    failure_codes: list[str]
    warnings: list[str]


class AiCreateGoalPayloadPreview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    goal: dict
    milestones: list[dict]
    write_policy: Literal["user_confirmation_required"]


class AiScheduleDraftData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    goal: AiScheduleDraftGoal
    milestones: list[AiScheduleDraftMilestone]
    planning_preference: AiSchedulePlanningPreference
    validation: AiScheduleDraftValidation
    create_goal_payload: AiCreateGoalPayloadPreview


class AiScheduleDraftResponse(BaseModel):
    success: bool
    data: AiScheduleDraftData
