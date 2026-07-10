from typing import Annotated

from fastapi import APIRouter, Depends, Path

from core.auth import require_current_user_id
from schemas.milestone_schemas import (
    MilestoneCompleteRequest,
    MilestoneCreateRequest,
    MilestoneDeleteResponse,
    MilestoneListResponse,
    MilestoneResponse,
    MilestoneUpdateRequest,
)
from services.milestone_service import MilestoneService, get_milestone_service


router = APIRouter(tags=["milestones"])


@router.get(
    "/goals/{goal_id}/milestones",
    response_model=MilestoneListResponse,
    summary="목표 하위 마일스톤 목록 조회",
    description="현재 사용자가 소유한 목표의 하위 마일스톤 목록을 조회합니다.",
)
def list_goal_milestones(
    goal_id: Annotated[str, Path(description="마일스톤 목록을 조회할 목표 ID")],
    user_id: str = Depends(require_current_user_id),
    milestone_service: MilestoneService = Depends(get_milestone_service),
):
    return {
        "success": True,
        "data": milestone_service.list_goal_milestones(
            goal_id=goal_id,
            user_id=user_id,
        ),
    }


@router.post(
    "/goals/{goal_id}/milestones",
    response_model=MilestoneResponse,
    summary="목표 하위 마일스톤 생성",
    description="현재 사용자가 소유한 목표 하위에 새 마일스톤을 생성합니다.",
)
def create_milestone(
    goal_id: Annotated[str, Path(description="마일스톤을 생성할 목표 ID")],
    body: MilestoneCreateRequest,
    user_id: str = Depends(require_current_user_id),
    milestone_service: MilestoneService = Depends(get_milestone_service),
):
    return {
        "success": True,
        "data": milestone_service.create_milestone(
            goal_id=goal_id,
            user_id=user_id,
            body=body,
        ),
    }


@router.get(
    "/milestones/today",
    response_model=MilestoneListResponse,
    summary="오늘 할 일 조회",
    description="오늘 수행 예정인 현재 사용자의 마일스톤 목록을 조회합니다.",
)
def list_today_milestones(
    user_id: str = Depends(require_current_user_id),
    milestone_service: MilestoneService = Depends(get_milestone_service),
):
    return {
        "success": True,
        "data": milestone_service.list_today_milestones(user_id=user_id),
    }


@router.get(
    "/milestones/{milestone_id}",
    response_model=MilestoneResponse,
    summary="마일스톤 상세 조회",
    description="현재 사용자가 소유한 특정 마일스톤의 상세 정보를 조회합니다.",
)
def get_milestone(
    milestone_id: Annotated[str, Path(description="조회할 마일스톤 ID")],
    user_id: str = Depends(require_current_user_id),
    milestone_service: MilestoneService = Depends(get_milestone_service),
):
    return {
        "success": True,
        "data": milestone_service.get_milestone(
            milestone_id=milestone_id,
            user_id=user_id,
        ),
    }


@router.patch(
    "/milestones/{milestone_id}",
    response_model=MilestoneResponse,
    summary="마일스톤 수정",
    description="현재 사용자가 소유한 마일스톤의 제목, 색상, 수행일, 완료 여부를 수정합니다.",
)
def update_milestone(
    milestone_id: Annotated[str, Path(description="수정할 마일스톤 ID")],
    body: MilestoneUpdateRequest,
    user_id: str = Depends(require_current_user_id),
    milestone_service: MilestoneService = Depends(get_milestone_service),
):
    return {
        "success": True,
        "data": milestone_service.update_milestone(
            milestone_id=milestone_id,
            user_id=user_id,
            body=body,
        ),
    }


@router.delete(
    "/milestones/{milestone_id}",
    response_model=MilestoneDeleteResponse,
    summary="마일스톤 삭제",
    description="현재 사용자가 소유한 마일스톤을 삭제합니다.",
)
def delete_milestone(
    milestone_id: Annotated[str, Path(description="삭제할 마일스톤 ID")],
    user_id: str = Depends(require_current_user_id),
    milestone_service: MilestoneService = Depends(get_milestone_service),
):
    milestone_service.delete_milestone(milestone_id=milestone_id, user_id=user_id)
    return {"success": True, "message": "마일스톤을 삭제했습니다."}


@router.patch(
    "/milestones/{milestone_id}/complete",
    response_model=MilestoneResponse,
    summary="마일스톤 완료 처리",
    description="현재 사용자가 소유한 마일스톤의 완료 여부를 변경합니다.",
)
def complete_milestone(
    milestone_id: Annotated[str, Path(description="완료 여부를 변경할 마일스톤 ID")],
    body: MilestoneCompleteRequest,
    user_id: str = Depends(require_current_user_id),
    milestone_service: MilestoneService = Depends(get_milestone_service),
):
    return {
        "success": True,
        "data": milestone_service.complete_milestone(
            milestone_id=milestone_id,
            user_id=user_id,
            body=body,
        ),
    }
