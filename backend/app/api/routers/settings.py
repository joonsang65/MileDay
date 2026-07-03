# 사용자 설정 조회 및 수정 API 제공
from fastapi import APIRouter

from schemas.settings_schemas import SettingsResponse, SettingsUpdateRequest


router = APIRouter(prefix="/settings", tags=["settings"])


# 설정 API 명세용 예시 데이터
def settings_data() -> dict:
    return {
        "calendar_view": "month",
        "theme": "system",
        "accent_color": "#4F46E5",
        "font_family": "system",
        "font_size": 14,
        "ai_suggestion": False,
        "holiday_display": True,
        "week_starts_on": "monday",
        "completed_milestones": True,
        "default_goal_color": "#4F46E5",
        "default_milestone_color": "#F97316",
        "language": "ko",
        "timezone": "Asia/Seoul",
    }


# 사용자 설정 조회 API
@router.get(
    "",
    response_model=SettingsResponse,
    summary="사용자 설정 조회",
    description="현재 로그인한 사용자의 계정 기준 앱 설정을 조회합니다.",
)
def get_settings():
    return {"success": True, "data": settings_data()}


# 사용자 설정 수정 API
@router.patch(
    "",
    response_model=SettingsResponse,
    summary="사용자 설정 수정",
    description="현재 로그인한 사용자의 계정 기준 앱 설정을 수정합니다.",
)
def update_settings(body: SettingsUpdateRequest):
    data = settings_data()
    data.update(body.model_dump(exclude_unset=True))
    return {"success": True, "data": data}
