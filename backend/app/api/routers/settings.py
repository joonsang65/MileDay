# 사용자 설정 조회/수정 API
from fastapi import APIRouter, Depends

from core.auth import require_current_user_id
from schemas.settings_schemas import SettingsResponse, SettingsUpdateRequest
from services.settings_service import SettingsService, get_settings_service


router = APIRouter(prefix="/settings", tags=["settings"])


@router.get(
    "",
    response_model=SettingsResponse,
    summary="사용자 설정 조회",
    description="현재 사용자의 계정 기준 앱 설정을 조회합니다.",
)
def get_settings(
    user_id: str = Depends(require_current_user_id),
    settings_service: SettingsService = Depends(get_settings_service),
):
    return {
        "success": True,
        "data": settings_service.get_settings(user_id=user_id),
    }


@router.patch(
    "",
    response_model=SettingsResponse,
    summary="사용자 설정 수정",
    description="현재 사용자의 계정 기준 앱 설정을 부분 수정합니다.",
)
def update_settings(
    body: SettingsUpdateRequest,
    user_id: str = Depends(require_current_user_id),
    settings_service: SettingsService = Depends(get_settings_service),
):
    return {
        "success": True,
        "data": settings_service.update_settings(user_id=user_id, body=body),
    }
