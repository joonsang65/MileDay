from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


# 마일스톤 공통 DTO
class MilestoneBase(BaseModel):
    title: str
    color: str
    scheduled_date: date


# 마일스톤 생성 요청 DTO
class MilestoneCreateRequest(MilestoneBase):
    pass


# 마일스톤 수정 요청 DTO
class MilestoneUpdateRequest(BaseModel):
    title: Optional[str] = None
    color: Optional[str] = None
    scheduled_date: Optional[date] = None
    is_completed: Optional[bool] = None


# 마일스톤 완료 처리 요청 DTO
class MilestoneCompleteRequest(BaseModel):
    is_completed: bool = True


# 마일스톤 데이터 DTO
class Milestone(MilestoneBase):
    id: str
    goal_id: str
    user_id: str
    is_completed: bool
    created_at: datetime
    updated_at: datetime


# 마일스톤 목록 조회 응답 DTO
class MilestoneListResponse(BaseModel):
    success: bool
    data: list[Milestone]


# 마일스톤 단건 조회/생성/수정/완료 응답 DTO
class MilestoneResponse(BaseModel):
    success: bool
    data: Milestone


# 마일스톤 삭제 응답 DTO
class MilestoneDeleteResponse(BaseModel):
    success: bool
    message: str
