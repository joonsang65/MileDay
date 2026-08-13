from fastapi import APIRouter, Depends

from core.auth import require_current_user_id
from schemas.ai_schedule_schemas import (
    AiScheduleDraftRequest,
    AiScheduleDraftResponse,
)
from services.ai_schedule_service import AiScheduleService, get_ai_schedule_service


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
):
    return {
        "success": True,
        "data": ai_schedule_service.create_draft(user_id=user_id, body=body),
    }
