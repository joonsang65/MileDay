from datetime import date

from pydantic import BaseModel

from schemas.goal_schemas import Goal
from schemas.milestone_schemas import Milestone


# 캘린더 날짜별 마일스톤 요약 DTO
class CalendarMilestoneSummary(BaseModel):
    id: str
    goal_id: str
    goal_title: str | None = None
    title: str
    color: str
    scheduled_date: date
    is_completed: bool


# 월간 캘린더의 하루 단위 요약 DTO
class CalendarDayData(BaseModel):
    date: date
    is_today: bool
    is_holiday: bool = False
    holiday_name: str | None = None
    goal_count: int
    milestone_count: int
    completed_milestone_count: int
    goals: list[Goal]
    milestones: list[CalendarMilestoneSummary]


# 날짜 상세 조회 데이터 DTO
class CalendarDateData(BaseModel):
    date: date
    is_today: bool
    goal_count: int
    milestone_count: int
    completed_milestone_count: int
    goals: list[Goal]
    milestones: list[CalendarMilestoneSummary]


# 날짜 상세 조회 응답 DTO
class CalendarDateResponse(BaseModel):
    success: bool
    data: CalendarDateData


# 월간 캘린더 조회 데이터 DTO
class CalendarMonthData(BaseModel):
    year: int
    month: int
    days: list[CalendarDayData]
    goals: list[Goal]
    milestones: list[Milestone]


# 월간 캘린더 조회 응답 DTO
class CalendarMonthResponse(BaseModel):
    success: bool
    data: CalendarMonthData


# 주간 캘린더 조회 데이터 DTO
class CalendarWeekData(BaseModel):
    start_date: date
    end_date: date
    days: list[CalendarDayData]
    goals: list[Goal]
    milestones: list[Milestone]


# 주간 캘린더 조회 응답 DTO
class CalendarWeekResponse(BaseModel):
    success: bool
    data: CalendarWeekData
