from datetime import date

from pydantic import BaseModel

from schemas.goal_schemas import Goal
from schemas.milestone_schemas import Milestone


# 캘린더 날짜별 마일스톤 요약 DTO
class CalendarMilestoneSummary(BaseModel):
    id: str
    goal_id: str
    goal_title: str
    title: str
    color: str
    is_completed: bool


# 날짜 상세 조회 데이터 DTO
class CalendarDateData(BaseModel):
    date: date
    milestones: list[CalendarMilestoneSummary]


# 날짜 상세 조회 응답 DTO
class CalendarDateResponse(BaseModel):
    success: bool
    data: CalendarDateData


# 월간 캘린더 조회 데이터 DTO
class CalendarMonthData(BaseModel):
    year: int
    month: int
    goals: list[Goal]
    milestones: list[Milestone]


# 월간 캘린더 조회 응답 DTO
class CalendarMonthResponse(BaseModel):
    success: bool
    data: CalendarMonthData
