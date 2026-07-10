from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, model_validator


RecurrenceType = Literal["daily", "weekly", "monthly"]


# 목표 공통 DTO
class GoalBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    deadline: date
    is_recurring: bool = False
    recurrence_type: Optional[RecurrenceType] = None
    color: str

    @model_validator(mode="after")
    def validate_recurrence(self) -> "GoalBase":
        if self.is_recurring and self.recurrence_type is None:
            raise ValueError("반복 목표에는 recurrence_type이 필요합니다.")
        if not self.is_recurring and self.recurrence_type is not None:
            raise ValueError("반복하지 않는 목표의 recurrence_type은 null이어야 합니다.")
        return self


# 목표 생성 요청 DTO
class GoalCreateRequest(GoalBase):
    pass


# 목표 수정 요청 DTO
class GoalUpdateRequest(BaseModel):
    title: Optional[str] = None
    deadline: Optional[date] = None
    is_recurring: Optional[bool] = None
    recurrence_type: Optional[RecurrenceType] = None
    color: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


# 목표 데이터 DTO
class Goal(GoalBase):
    id: str
    user_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# 목표 목록 조회 응답 DTO
class GoalListResponse(BaseModel):
    success: bool
    data: list[Goal]


# 목표 단건 조회/생성/수정 응답 DTO
class GoalResponse(BaseModel):
    success: bool
    data: Goal


# 목표 삭제 응답 DTO
class GoalDeleteResponse(BaseModel):
    success: bool
    message: str
