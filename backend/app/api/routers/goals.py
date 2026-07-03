# 목표 CRUD 및 목표 정보 조회 API 제공
from fastapi import APIRouter

from schemas.goal_schemas import (
    GoalCreateRequest,
    GoalDeleteResponse,
    GoalListResponse,
    GoalResponse,
    GoalUpdateRequest,
)


router = APIRouter(prefix="/goals", tags=["goals"])


# 목표 API 명세용 예시 데이터
def goal_data(goal_id: str = "uuid") -> dict:
    return {
        "id": goal_id,
        "user_id": "uuid",
        "title": "AI engineer job preparation",
        "deadline": "2026-09-30",
        "is_recurring": False,
        "recurrence_type": None,
        "color": "#4F46E5",
        "created_at": "2026-07-01T10:00:00+09:00",
        "updated_at": "2026-07-01T10:00:00+09:00",
    }


# 목표 목록 조회 API
@router.get("", response_model=GoalListResponse, summary="목표 목록 조회")
def list_goals():
    return {"success": True, "data": [goal_data()]}


# 목표 상세 조회 API
@router.get("/{goal_id}", response_model=GoalResponse, summary="목표 상세 조회")
def get_goal(goal_id: str):
    return {"success": True, "data": goal_data(goal_id)}


# 목표 생성 API
@router.post("", response_model=GoalResponse, summary="목표 생성")
def create_goal(body: GoalCreateRequest):
    data = goal_data()
    data.update(body.model_dump())
    return {"success": True, "data": data}


# 목표 수정 API
@router.patch("/{goal_id}", response_model=GoalResponse, summary="목표 수정")
def update_goal(goal_id: str, body: GoalUpdateRequest):
    data = goal_data(goal_id)
    data.update(body.model_dump(exclude_unset=True))
    return {"success": True, "data": data}


# 목표 삭제 API
@router.delete("/{goal_id}", response_model=GoalDeleteResponse, summary="목표 삭제")
def delete_goal(goal_id: str):
    return {"success": True, "message": "Goal deleted."}
