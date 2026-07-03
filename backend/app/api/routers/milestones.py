# 마일스톤 CRUD, 오늘 할 일 조회, 완료 상태 변경 API 제공
from typing import Annotated

from fastapi import APIRouter, Path

from schemas.milestone_schemas import (
    MilestoneCompleteRequest,
    MilestoneCreateRequest,
    MilestoneDeleteResponse,
    MilestoneListResponse,
    MilestoneResponse,
    MilestoneUpdateRequest,
)


router = APIRouter(tags=["milestones"])


# 마일스톤 API 명세용 예시 데이터
def milestone_data(goal_id: str = "uuid", milestone_id: str = "uuid") -> dict:
    return {
        "id": milestone_id,
        "goal_id": goal_id,
        "user_id": "uuid",
        "title": "Write resume draft",
        "color": "#F97316",
        "scheduled_date": "2026-07-05",
        "is_completed": False,
        "created_at": "2026-07-01T10:00:00+09:00",
        "updated_at": "2026-07-01T10:00:00+09:00",
    }


# 목표 하위 마일스톤 목록 조회 API
@router.get(
    "/goals/{goal_id}/milestones",
    response_model=MilestoneListResponse,
    summary="목표 하위 마일스톤 목록 조회",
    description="goal_id에 해당하는 목표의 하위 마일스톤 목록을 조회합니다.",
)
def list_goal_milestones(
    goal_id: Annotated[str, Path(description="마일스톤 목록을 조회할 목표 ID")],
):
    return {"success": True, "data": [milestone_data(goal_id=goal_id)]}


# 목표 하위 마일스톤 생성 API
@router.post(
    "/goals/{goal_id}/milestones",
    response_model=MilestoneResponse,
    summary="목표 하위 마일스톤 생성",
    description="goal_id에 해당하는 목표 하위에 새 마일스톤을 생성합니다.",
)
def create_milestone(
    goal_id: Annotated[str, Path(description="마일스톤을 생성할 목표 ID")],
    body: MilestoneCreateRequest,
):
    data = milestone_data(goal_id=goal_id)
    data.update(body.model_dump())
    return {"success": True, "data": data}


# 오늘 할 일 마일스톤 목록 조회 API
@router.get(
    "/milestones/today",
    response_model=MilestoneListResponse,
    summary="오늘 할 일 조회",
    description="오늘 수행 예정인 마일스톤 목록을 조회합니다.",
)
def list_today_milestones():
    return {"success": True, "data": [milestone_data()]}


# 마일스톤 상세 조회 API
@router.get(
    "/milestones/{milestone_id}",
    response_model=MilestoneResponse,
    summary="마일스톤 상세 조회",
    description="milestone_id에 해당하는 특정 마일스톤의 상세 정보를 조회합니다.",
)
def get_milestone(
    milestone_id: Annotated[str, Path(description="조회할 마일스톤 ID")],
):
    return {"success": True, "data": milestone_data(milestone_id=milestone_id)}


# 마일스톤 수정 API
@router.patch(
    "/milestones/{milestone_id}",
    response_model=MilestoneResponse,
    summary="마일스톤 수정",
    description="마일스톤의 제목, 색상, 수행일, 완료 여부를 수정합니다.",
)
def update_milestone(
    milestone_id: Annotated[str, Path(description="수정할 마일스톤 ID")],
    body: MilestoneUpdateRequest,
):
    data = milestone_data(milestone_id=milestone_id)
    data.update(body.model_dump(exclude_unset=True))
    return {"success": True, "data": data}


# 마일스톤 삭제 API
@router.delete(
    "/milestones/{milestone_id}",
    response_model=MilestoneDeleteResponse,
    summary="마일스톤 삭제",
    description="milestone_id에 해당하는 마일스톤을 삭제합니다.",
)
def delete_milestone(
    milestone_id: Annotated[str, Path(description="삭제할 마일스톤 ID")],
):
    return {"success": True, "message": "Milestone deleted."}


# 마일스톤 완료 상태 변경 API
@router.patch(
    "/milestones/{milestone_id}/complete",
    response_model=MilestoneResponse,
    summary="마일스톤 완료 처리",
    description="milestone_id에 해당하는 마일스톤의 완료 여부를 변경합니다.",
)
def complete_milestone(
    milestone_id: Annotated[str, Path(description="완료 여부를 변경할 마일스톤 ID")],
    body: MilestoneCompleteRequest,
):
    data = milestone_data(milestone_id=milestone_id)
    data["is_completed"] = body.is_completed
    return {"success": True, "data": data}
