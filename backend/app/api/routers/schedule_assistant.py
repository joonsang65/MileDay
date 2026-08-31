from fastapi import APIRouter, Depends

from core.auth import require_current_user_id
from exceptions.common import BadRequestError
from schemas.ai_schedule_schemas import (
    AiScheduleDraftRequest,
    AiScheduleDraftResponse,
)
from services.ai_schedule_service import AiScheduleService, get_ai_schedule_service
from services.settings_service import SettingsService, get_settings_service


router = APIRouter(prefix="/ai", tags=["ai"])


@router.post(
    "/schedule/draft",
    response_model=AiScheduleDraftResponse,
    summary="AI 일정 초안 생성",
    description="사용자 자연어 요청과 가능한 날짜를 바탕으로 저장 전 편집 가능한 일정 초안을 생성합니다.",
)
def create_schedule_draft(
    body: AiScheduleDraftRequest,
    user_id: str = Depends(require_current_user_id),
    ai_schedule_service: AiScheduleService = Depends(get_ai_schedule_service),
    settings_service: SettingsService = Depends(get_settings_service),
):
    settings = settings_service.get_settings(user_id=user_id)
    if not settings.get("gemini_data_consent"):
        raise BadRequestError(
            message="Gemini 전송 동의가 필요합니다.",
            detail={"code": "GEMINI_DATA_CONSENT_REQUIRED"},
        )
    return {
        "success": True,
        "data": ai_schedule_service.create_draft(user_id=user_id, body=body),
    }
