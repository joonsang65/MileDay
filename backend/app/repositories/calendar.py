from __future__ import annotations

from typing import Any

from core.supabase import execute_supabase_read, get_supabase_admin_client

GOAL_SELECT_COLUMNS = "id,user_id,title,deadline,is_recurring,recurrence_type,color,created_at,updated_at"
MILESTONE_SELECT_COLUMNS = (
    "id,goal_id,user_id,title,color,scheduled_date,is_completed,created_at,updated_at,goals(title)"
)


class CalendarRepository:
    def __init__(self, supabase_client: Any | None = None) -> None:
        self._uses_default_client = supabase_client is None
        self.client = supabase_client or get_supabase_admin_client()

    def _get_client(self) -> Any:
        if self._uses_default_client:
            self.client = get_supabase_admin_client()
        return self.client

    def list_goals_by_deadline_range(
        self,
        *,
        user_id: str,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, Any]]:
        response = execute_supabase_read(
            lambda: (
                self._get_client()
                .table("goals")
                .select(GOAL_SELECT_COLUMNS)
                .eq("user_id", user_id)
                .gte("deadline", start_date)
                .lte("deadline", end_date)
                .order("deadline")
                .execute()
            ),
        )
        return list(response.data or [])

    def list_milestones_by_scheduled_date_range(
        self,
        *,
        user_id: str,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, Any]]:
        response = execute_supabase_read(
            lambda: (
                self._get_client()
                .table("milestones")
                .select(MILESTONE_SELECT_COLUMNS)
                .eq("user_id", user_id)
                .gte("scheduled_date", start_date)
                .lte("scheduled_date", end_date)
                .order("scheduled_date")
                .execute()
            ),
        )
        return list(response.data or [])

    def list_goals_by_deadline(
        self,
        *,
        user_id: str,
        deadline: str,
    ) -> list[dict[str, Any]]:
        response = execute_supabase_read(
            lambda: (
                self._get_client()
                .table("goals")
                .select(GOAL_SELECT_COLUMNS)
                .eq("user_id", user_id)
                .eq("deadline", deadline)
                .order("created_at")
                .execute()
            ),
        )
        return list(response.data or [])

    def list_milestones_by_scheduled_date(
        self,
        *,
        user_id: str,
        scheduled_date: str,
    ) -> list[dict[str, Any]]:
        response = execute_supabase_read(
            lambda: (
                self._get_client()
                .table("milestones")
                .select(MILESTONE_SELECT_COLUMNS)
                .eq("user_id", user_id)
                .eq("scheduled_date", scheduled_date)
                .order("created_at")
                .execute()
            ),
        )
        return list(response.data or [])


def get_calendar_repository() -> CalendarRepository:
    return CalendarRepository()
