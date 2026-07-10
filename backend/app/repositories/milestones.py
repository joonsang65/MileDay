from __future__ import annotations

from typing import Any

from core.supabase import get_supabase_admin_client


class MilestoneRepository:
    def __init__(self, supabase_client: Any | None = None) -> None:
        # FastAPI에서 목표 소유권과 user_id를 검증하므로 DB 접근은 서버 권한 client로 수행한다.
        self.client = supabase_client or get_supabase_admin_client()

    def list_by_goal(self, *, goal_id: str, user_id: str) -> list[dict[str, Any]]:
        response = (
            self.client.table("milestones")
            .select("*")
            .eq("goal_id", goal_id)
            .eq("user_id", user_id)
            .order("scheduled_date")
            .execute()
        )
        return list(response.data or [])

    def list_by_scheduled_date(
        self,
        *,
        scheduled_date: str,
        user_id: str,
    ) -> list[dict[str, Any]]:
        response = (
            self.client.table("milestones")
            .select("*, goals(title)")
            .eq("scheduled_date", scheduled_date)
            .eq("user_id", user_id)
            .order("created_at")
            .execute()
        )
        return list(response.data or [])

    def get_by_id(self, *, milestone_id: str, user_id: str) -> dict[str, Any] | None:
        response = (
            self.client.table("milestones")
            .select("*")
            .eq("id", milestone_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        rows = list(response.data or [])
        return rows[0] if rows else None

    def create(self, *, payload: dict[str, Any]) -> dict[str, Any] | None:
        response = self.client.table("milestones").insert(payload).execute()
        rows = list(response.data or [])
        return rows[0] if rows else None

    def bulk_create(self, *, payloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not payloads:
            return []
        response = self.client.table("milestones").insert(payloads).execute()
        return list(response.data or [])

    def update(
        self,
        *,
        milestone_id: str,
        user_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any] | None:
        response = (
            self.client.table("milestones")
            .update(payload)
            .eq("id", milestone_id)
            .eq("user_id", user_id)
            .execute()
        )
        rows = list(response.data or [])
        return rows[0] if rows else None

    def delete(self, *, milestone_id: str, user_id: str) -> bool:
        response = (
            self.client.table("milestones")
            .delete()
            .eq("id", milestone_id)
            .eq("user_id", user_id)
            .execute()
        )
        return bool(response.data)


def get_milestone_repository() -> MilestoneRepository:
    return MilestoneRepository()
