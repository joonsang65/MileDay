from typing import Annotated

from fastapi import APIRouter, Depends, Path

from core.auth import require_current_user_id
from schemas.goal_schemas import (
    GoalCreateRequest,
    GoalDeleteResponse,
    GoalListResponse,
    GoalResponse,
    GoalUpdateRequest,
)
from services.goal_service import GoalService, get_goal_service


router = APIRouter(prefix="/goals", tags=["goals"])


@router.get(
    "",
    response_model=GoalListResponse,
    summary="목표 목록 조회",
    description="현재 사용자가 소유한 목표 목록을 조회합니다.",
)
def list_goals(
    user_id: str = Depends(require_current_user_id),
    goal_service: GoalService = Depends(get_goal_service),
):
    return {"success": True, "data": goal_service.list_goals(user_id=user_id)}


@router.get(
    "/{goal_id}",
    response_model=GoalResponse,
    summary="목표 상세 조회",
    description="현재 사용자가 소유한 특정 목표를 조회합니다.",
)
def get_goal(
    goal_id: Annotated[str, Path(description="목표 ID")],
    user_id: str = Depends(require_current_user_id),
    goal_service: GoalService = Depends(get_goal_service),
):
    return {
        "success": True,
        "data": goal_service.get_goal(goal_id=goal_id, user_id=user_id),
    }


@router.post(
    "",
    response_model=GoalResponse,
    summary="목표 생성",
    description="현재 사용자 기준으로 목표를 생성합니다.",
)
def create_goal(
    body: GoalCreateRequest,
    user_id: str = Depends(require_current_user_id),
    goal_service: GoalService = Depends(get_goal_service),
):
    return {
        "success": True,
        "data": goal_service.create_goal(user_id=user_id, body=body),
    }


@router.patch(
    "/{goal_id}",
    response_model=GoalResponse,
    summary="목표 수정",
    description="현재 사용자가 소유한 목표를 수정합니다.",
)
def update_goal(
    goal_id: Annotated[str, Path(description="목표 ID")],
    body: GoalUpdateRequest,
    user_id: str = Depends(require_current_user_id),
    goal_service: GoalService = Depends(get_goal_service),
):
    return {
        "success": True,
        "data": goal_service.update_goal(goal_id=goal_id, user_id=user_id, body=body),
    }


@router.delete(
    "/{goal_id}",
    response_model=GoalDeleteResponse,
    summary="목표 삭제",
    description="현재 사용자가 소유한 목표를 삭제합니다. 하위 마일스톤은 FK cascade로 함께 삭제됩니다.",
)
def delete_goal(
    goal_id: Annotated[str, Path(description="목표 ID")],
    user_id: str = Depends(require_current_user_id),
    goal_service: GoalService = Depends(get_goal_service),
):
    goal_service.delete_goal(goal_id=goal_id, user_id=user_id)
    return {"success": True, "message": "목표와 하위 마일스톤을 삭제했습니다."}
