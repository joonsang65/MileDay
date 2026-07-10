from __future__ import annotations

from typing import Any

from core.supabase import get_supabase_admin_client


class CalendarRepository:
    def __init__(self, supabase_client: Any | None = None) -> None:
        # 캘린더 조회는 service 계층에서 현재 사용자 user_id로 제한한 뒤 서버 권한 client로 조회한다.
        self.client = supabase_client or get_supabase_admin_client()

    def list_goals_by_deadline_range(
        self,
        *,
        user_id: str,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, Any]]:
        response = (
            self.client.table("goals")
            .select("*")
            .eq("user_id", user_id)
            .gte("deadline", start_date)
            .lte("deadline", end_date)
            .order("deadline")
            .execute()
        )
        return list(response.data or [])

    def list_milestones_by_scheduled_date_range(
        self,
        *,
        user_id: str,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, Any]]:
        response = (
            self.client.table("milestones")
            .select("*, goals(title)")
            .eq("user_id", user_id)
            .gte("scheduled_date", start_date)
            .lte("scheduled_date", end_date)
            .order("scheduled_date")
            .execute()
        )
        return list(response.data or [])

    def list_goals_by_deadline(
        self,
        *,
        user_id: str,
        deadline: str,
    ) -> list[dict[str, Any]]:
        response = (
            self.client.table("goals")
            .select("*")
            .eq("user_id", user_id)
            .eq("deadline", deadline)
            .order("created_at")
            .execute()
        )
        return list(response.data or [])

    def list_milestones_by_scheduled_date(
        self,
        *,
        user_id: str,
        scheduled_date: str,
    ) -> list[dict[str, Any]]:
        response = (
            self.client.table("milestones")
            .select("*, goals(title)")
            .eq("user_id", user_id)
            .eq("scheduled_date", scheduled_date)
            .order("created_at")
            .execute()
        )
        return list(response.data or [])


def get_calendar_repository() -> CalendarRepository:
    return CalendarRepository()
