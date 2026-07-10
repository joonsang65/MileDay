from typing import Literal, Optional

from pydantic import BaseModel, Field


CalendarView = Literal["month", "week"]
HolidayDisplay = Literal["normal", "weekend_like", "hidden"]
Language = Literal["ko", "en"]


# 사용자 설정 데이터 DTO
class UserSettings(BaseModel):
    calendar_view: CalendarView
    theme: str
    accent_color: str
    font_family: str
    font_size: int
    ai_suggestion: bool
    holiday_display: HolidayDisplay
    week_starts_on: int = Field(ge=0, le=1)
    completed_milestones: bool
    default_goal_color: str
    default_milestone_color: str
    language: Language
    timezone: str


# 부분 수정 요청 DTO, 전달된 필드만 갱신 대상
class SettingsUpdateRequest(BaseModel):
    calendar_view: Optional[CalendarView] = None
    theme: Optional[str] = None
    accent_color: Optional[str] = None
    font_family: Optional[str] = None
    font_size: Optional[int] = None
    ai_suggestion: Optional[bool] = None
    holiday_display: Optional[HolidayDisplay] = None
    week_starts_on: Optional[int] = Field(default=None, ge=0, le=1)
    completed_milestones: Optional[bool] = None
    default_goal_color: Optional[str] = None
    default_milestone_color: Optional[str] = None
    language: Optional[Language] = None
    timezone: Optional[str] = None


# 사용자 설정 조회/수정 응답 DTO
class SettingsResponse(BaseModel):
    success: bool
    data: UserSettings
