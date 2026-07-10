from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from core.auth import require_current_user_id
from schemas.calendar_schemas import (
    CalendarDateResponse,
    CalendarMonthResponse,
    CalendarWeekResponse,
)
from services.calendar_service import CalendarService, get_calendar_service


router = APIRouter(prefix="/calendar", tags=["calendar"])


@router.get(
    "/month",
    response_model=CalendarMonthResponse,
    summary="월간 캘린더 조회",
    description="현재 사용자의 목표 마감일과 마일스톤 예정일을 월 단위로 조회합니다.",
)
def get_month_calendar(
    year: Annotated[int, Query(description="조회할 연도", ge=1)],
    month: Annotated[int, Query(description="조회할 월", ge=1, le=12)],
    user_id: str = Depends(require_current_user_id),
    calendar_service: CalendarService = Depends(get_calendar_service),
):
    return {
        "success": True,
        "data": calendar_service.get_month_calendar(
            user_id=user_id,
            year=year,
            month=month,
        ),
    }


@router.get(
    "/week",
    response_model=CalendarWeekResponse,
    summary="주간 캘린더 조회",
    description="현재 사용자의 목표 마감일과 마일스톤 예정일을 7일 단위로 조회합니다.",
)
def get_week_calendar(
    start_date: Annotated[date, Query(description="조회할 주의 시작 날짜. YYYY-MM-DD 형식")],
    user_id: str = Depends(require_current_user_id),
    calendar_service: CalendarService = Depends(get_calendar_service),
):
    return {
        "success": True,
        "data": calendar_service.get_week_calendar(
            user_id=user_id,
            start_date=start_date,
        ),
    }


@router.get(
    "/date/{target_date}",
    response_model=CalendarDateResponse,
    summary="날짜 상세 조회",
    description="현재 사용자의 특정 날짜 목표와 마일스톤 상세 데이터를 조회합니다.",
)
def get_date_calendar(
    target_date: Annotated[date, Path(description="조회할 날짜. YYYY-MM-DD 형식")],
    user_id: str = Depends(require_current_user_id),
    calendar_service: CalendarService = Depends(get_calendar_service),
):
    return {
        "success": True,
        "data": calendar_service.get_date_calendar(
            user_id=user_id,
            target_date=target_date,
        ),
    }
