# 사용자 설정 조회/수정 API
from fastapi import APIRouter

from schemas.settings_schemas import SettingsResponse, SettingsUpdateRequest


router = APIRouter(prefix="/settings", tags=["settings"])


# M1 API 명세 검증용 임시 설정 데이터
def settings_data() -> dict:
    return {
        "calendar_view": "month",
        "theme": "system",
        "accent_color": "#4F46E5",
        "font_family": "system",
        "font_size": 14,
        "ai_suggestion": False,
        "holiday_display": "normal",
        "week_starts_on": 1,
        "completed_milestones": True,
        "default_goal_color": "#4F46E5",
        "default_milestone_color": "#F97316",
        "language": "ko",
        "timezone": "Asia/Seoul",
    }


# 저장소 연결 전 기본 설정 조회
@router.get(
    "",
    response_model=SettingsResponse,
    summary="사용자 설정 조회",
    description="사용자의 계정 기준 앱 설정 조회",
)
def get_settings():
    return {"success": True, "data": settings_data()}


# 저장소 연결 전 요청 값 병합 응답
@router.patch(
    "",
    response_model=SettingsResponse,
    summary="사용자 설정 수정",
    description="사용자의 계정 기준 앱 설정 수정",
)
def update_settings(body: SettingsUpdateRequest):
    data = settings_data()
    data.update(body.model_dump(exclude_unset=True))
    return {"success": True, "data": data}
