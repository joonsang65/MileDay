from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


CalendarView = Literal["month", "week"]
HolidayDisplay = Literal["normal", "weekend_like", "hidden"]
Language = Literal["ko", "en"]


# 사용자 설정 데이터 DTO
class UserSettings(BaseModel):
    calendar_view: CalendarView
    holiday_display: HolidayDisplay
    week_starts_on: int = Field(ge=0, le=1)
    language: Language
    timezone: str
    gemini_data_consent: bool = False


# 부분 수정 요청 DTO, 전달된 필드만 갱신 대상
class SettingsUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    calendar_view: Optional[CalendarView] = None
    holiday_display: Optional[HolidayDisplay] = None
    week_starts_on: Optional[int] = Field(default=None, ge=0, le=1)
    language: Optional[Language] = None
    timezone: Optional[str] = None
    gemini_data_consent: Optional[bool] = None


# 사용자 설정 조회/수정 응답 DTO
class SettingsResponse(BaseModel):
    success: bool
    data: UserSettings
