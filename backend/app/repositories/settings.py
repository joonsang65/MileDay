from __future__ import annotations

from typing import Any

from core.supabase import get_supabase_admin_client


class SettingsRepository:
    def __init__(self, supabase_client: Any | None = None) -> None:
        # API 계층에서 JWT와 user_id 필터를 적용하므로 서버 권한 client로 DB 작업을 수행한다.
        self.client = supabase_client or get_supabase_admin_client()

    def get_by_user(self, *, user_id: str) -> dict[str, Any] | None:
        response = (
            self.client.table("user_settings")
            .select("*")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        rows = list(response.data or [])
        return rows[0] if rows else None

    def upsert_defaults(self, *, payload: dict[str, Any]) -> dict[str, Any] | None:
        response = (
            self.client.table("user_settings")
            .upsert(payload, on_conflict="user_id")
            .execute()
        )
        rows = list(response.data or [])
        return rows[0] if rows else None

    def update(self, *, user_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        response = (
            self.client.table("user_settings")
            .update(payload)
            .eq("user_id", user_id)
            .execute()
        )
        rows = list(response.data or [])
        return rows[0] if rows else None


def get_settings_repository() -> SettingsRepository:
    return SettingsRepository()
