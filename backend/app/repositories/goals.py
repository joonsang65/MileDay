from __future__ import annotations

from typing import Any

from core.supabase import get_supabase_admin_client


class GoalRepository:
    def __init__(self, supabase_client: Any | None = None) -> None:
        # FastAPI에서 현재 사용자 인증과 user_id 필터를 적용하므로 DB 접근은 서버 권한 client로 수행한다.
        self.client = supabase_client or get_supabase_admin_client()

    def list_by_user(self, *, user_id: str) -> list[dict[str, Any]]:
        response = (
            self.client.table("goals")
            .select("*")
            .eq("user_id", user_id)
            .order("deadline")
            .execute()
        )
        return list(response.data or [])

    def get_by_id(self, *, goal_id: str, user_id: str) -> dict[str, Any] | None:
        response = (
            self.client.table("goals")
            .select("*")
            .eq("id", goal_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        rows = list(response.data or [])
        return rows[0] if rows else None

    def create(self, *, payload: dict[str, Any]) -> dict[str, Any] | None:
        response = self.client.table("goals").insert(payload).execute()
        rows = list(response.data or [])
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
        rows = list(response.data or [])
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


def get_goal_repository() -> GoalRepository:
    return GoalRepository()
