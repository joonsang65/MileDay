# 마일스톤 CRUD, 오늘 할 일 조회, 완료 상태 변경 API 제공
from fastapi import APIRouter

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
)
def list_goal_milestones(goal_id: str):
    return {"success": True, "data": [milestone_data(goal_id=goal_id)]}


# 목표 하위 마일스톤 생성 API
@router.post(
    "/goals/{goal_id}/milestones",
    response_model=MilestoneResponse,
    summary="목표 하위 마일스톤 생성",
)
def create_milestone(goal_id: str, body: MilestoneCreateRequest):
    data = milestone_data(goal_id=goal_id)
    data.update(body.model_dump())
    return {"success": True, "data": data}


# 오늘 할 일 마일스톤 목록 조회 API
@router.get(
    "/milestones/today",
    response_model=MilestoneListResponse,
    summary="오늘 할 일 조회",
)
def list_today_milestones():
    return {"success": True, "data": [milestone_data()]}


# 마일스톤 상세 조회 API
@router.get(
    "/milestones/{milestone_id}",
    response_model=MilestoneResponse,
    summary="마일스톤 상세 조회",
)
def get_milestone(milestone_id: str):
    return {"success": True, "data": milestone_data(milestone_id=milestone_id)}


# 마일스톤 수정 API
@router.patch(
    "/milestones/{milestone_id}",
    response_model=MilestoneResponse,
    summary="마일스톤 수정",
)
def update_milestone(milestone_id: str, body: MilestoneUpdateRequest):
    data = milestone_data(milestone_id=milestone_id)
    data.update(body.model_dump(exclude_unset=True))
    return {"success": True, "data": data}


# 마일스톤 삭제 API
@router.delete(
    "/milestones/{milestone_id}",
    response_model=MilestoneDeleteResponse,
    summary="마일스톤 삭제",
)
def delete_milestone(milestone_id: str):
    return {"success": True, "message": "Milestone deleted."}


# 마일스톤 완료 상태 변경 API
@router.patch(
    "/milestones/{milestone_id}/complete",
    response_model=MilestoneResponse,
    summary="마일스톤 완료 상태 변경",
)
def complete_milestone(milestone_id: str, body: MilestoneCompleteRequest):
    data = milestone_data(milestone_id=milestone_id)
    data["is_completed"] = body.is_completed
    return {"success": True, "data": data}
