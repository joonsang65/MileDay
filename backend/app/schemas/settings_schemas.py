from typing import Optional

from pydantic import BaseModel


# 사용자 설정 데이터 DTO
class UserSettings(BaseModel):
    calendar_view: str
    theme: str
    accent_color: str
    font_family: str
    font_size: int
    ai_suggestion: bool
    holiday_display: bool
    week_starts_on: str
    completed_milestones: bool
    default_goal_color: str
    default_milestone_color: str
    language: str
    timezone: str


# 사용자 설정 수정 요청 DTO
class SettingsUpdateRequest(BaseModel):
    calendar_view: Optional[str] = None
    theme: Optional[str] = None
    accent_color: Optional[str] = None
    font_family: Optional[str] = None
    font_size: Optional[int] = None
    ai_suggestion: Optional[bool] = None
    holiday_display: Optional[bool] = None
    week_starts_on: Optional[str] = None
    completed_milestones: Optional[bool] = None
    default_goal_color: Optional[str] = None
    default_milestone_color: Optional[str] = None
    language: Optional[str] = None
    timezone: Optional[str] = None


# 사용자 설정 조회/수정 응답 DTO
class SettingsResponse(BaseModel):
    success: bool
    data: UserSettings
