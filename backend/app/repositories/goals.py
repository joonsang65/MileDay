from __future__ import annotations

from typing import Any

from core.supabase import get_supabase_admin_client

GOAL_SELECT_COLUMNS = "id,user_id,title,deadline,is_completed,is_recurring,recurrence_type,color,created_at,updated_at"
GOAL_RESPONSE_COLUMNS = set(GOAL_SELECT_COLUMNS.split(","))


class GoalRepository:
    def __init__(self, supabase_client: Any | None = None) -> None:
        # FastAPI에서 현재 사용자 인증과 user_id 필터를 적용하므로 DB 접근은 서버 권한 client로 수행한다.
        self.client = supabase_client or get_supabase_admin_client()

    def list_by_user(self, *, user_id: str) -> list[dict[str, Any]]:
        response = (
            self.client.table("goals")
            .select(GOAL_SELECT_COLUMNS)
            .eq("user_id", user_id)
            .order("deadline")
            .execute()
        )
        return [self._goal_row(row) for row in response.data or []]

    def get_by_id(self, *, goal_id: str, user_id: str) -> dict[str, Any] | None:
        response = (
            self.client.table("goals")
            .select(GOAL_SELECT_COLUMNS)
            .eq("id", goal_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        rows = [self._goal_row(row) for row in response.data or []]
        return rows[0] if rows else None

    def create(self, *, payload: dict[str, Any]) -> dict[str, Any] | None:
        response = self.client.table("goals").insert(payload).execute()
        rows = [self._goal_row(row) for row in response.data or []]
        return rows[0] if rows else None

    def update(
        self,
        *,
        goal_id: str,
        user_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any] | None:
        response = (
            self.client.table("goals")
            .update(payload)
            .eq("id", goal_id)
            .eq("user_id", user_id)
            .execute()
        )
        rows = [self._goal_row(row) for row in response.data or []]
        return rows[0] if rows else None

    def delete(self, *, goal_id: str, user_id: str) -> bool:
        response = (
            self.client.table("goals")
            .delete()
            .eq("id", goal_id)
            .eq("user_id", user_id)
            .execute()
        )
        return bool(response.data)

    def _goal_row(self, row: dict[str, Any]) -> dict[str, Any]:
        goal = {key: value for key, value in row.items() if key in GOAL_RESPONSE_COLUMNS}
        goal.setdefault("is_completed", False)
        return goal


def get_goal_repository() -> GoalRepository:
    return GoalRepository()
