from __future__ import annotations

from typing import Any

from core.supabase import execute_supabase_read, get_supabase_admin_client


class SettingsRepository:
    def __init__(self, supabase_client: Any | None = None) -> None:
        self._uses_default_client = supabase_client is None
        self.client = supabase_client or get_supabase_admin_client()

    def _get_client(self) -> Any:
        if self._uses_default_client:
            self.client = get_supabase_admin_client()
        return self.client

    def get_by_user(self, *, user_id: str) -> dict[str, Any] | None:
        response = execute_supabase_read(
            lambda: (
                self._get_client()
                .table("user_settings")
                .select("*")
                .eq("user_id", user_id)
                .limit(1)
                .execute()
            ),
        )
        rows = list(response.data or [])
        return rows[0] if rows else None

    def upsert_defaults(self, *, payload: dict[str, Any]) -> dict[str, Any] | None:
        response = (
            self._get_client()
            .table("user_settings")
            .upsert(payload, on_conflict="user_id")
            .execute()
        )
        rows = list(response.data or [])
        return rows[0] if rows else None

    def update(self, *, user_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        response = (
            self._get_client()
            .table("user_settings")
            .update(payload)
            .eq("user_id", user_id)
            .execute()
        )
        rows = list(response.data or [])
        return rows[0] if rows else None


def get_settings_repository() -> SettingsRepository:
    return SettingsRepository()
