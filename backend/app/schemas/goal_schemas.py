from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel


# 목표 공통 DTO
class GoalBase(BaseModel):
    title: str
    deadline: date
    is_recurring: bool = False
    recurrence_type: Optional[str] = None
    color: str


# 목표 생성 요청 DTO
class GoalCreateRequest(GoalBase):
    pass


# 목표 수정 요청 DTO
class GoalUpdateRequest(BaseModel):
    title: Optional[str] = None
    deadline: Optional[date] = None
    is_recurring: Optional[bool] = None
    recurrence_type: Optional[str] = None
    color: Optional[str] = None


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
