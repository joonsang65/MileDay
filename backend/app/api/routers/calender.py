# 월간 캘린더 및 날짜별 상세 조회 API 제공
from fastapi import APIRouter

from schemas.calendar_schemas import CalendarDateResponse, CalendarMonthResponse


router = APIRouter(prefix="/calendar", tags=["calendar"])


# 캘린더 API 명세용 목표 예시 데이터
def goal_data() -> dict:
    return {
        "id": "uuid",
        "user_id": "uuid",
        "title": "AI engineer job preparation",
        "deadline": "2026-09-30",
        "is_recurring": False,
        "recurrence_type": None,
        "color": "#4F46E5",
        "created_at": "2026-07-01T10:00:00+09:00",
        "updated_at": "2026-07-01T10:00:00+09:00",
    }


# 캘린더 API 명세용 마일스톤 예시 데이터
def milestone_data() -> dict:
    return {
        "id": "uuid",
        "goal_id": "uuid",
        "user_id": "uuid",
        "title": "Write resume draft",
        "color": "#F97316",
        "scheduled_date": "2026-07-05",
        "is_completed": False,
        "created_at": "2026-07-01T10:00:00+09:00",
        "updated_at": "2026-07-01T10:00:00+09:00",
    }


# 월간 캘린더 조회 API
@router.get("/month", response_model=CalendarMonthResponse, summary="월간 캘린더 조회")
def get_month_calendar(year: int, month: int):
    return {
        "success": True,
        "data": {
            "year": year,
            "month": month,
            "goals": [goal_data()],
            "milestones": [milestone_data()],
        },
    }


# 날짜 상세 조회 API
@router.get("/date/{date}", response_model=CalendarDateResponse, summary="날짜 상세 조회")
def get_date_calendar(date: str):
    return {
        "success": True,
        "data": {
            "date": date,
            "milestones": [
                {
                    "id": "uuid",
                    "goal_id": "uuid",
                    "goal_title": "AI engineer job preparation",
                    "title": "Write resume draft",
                    "color": "#F97316",
                    "is_completed": False,
                }
            ],
        },
    }
