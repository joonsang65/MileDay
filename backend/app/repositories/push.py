from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from core.supabase import execute_supabase_read, get_supabase_admin_client


PUSH_SUBSCRIPTION_COLUMNS = "id,user_id,endpoint,p256dh,auth,user_agent,created_at,updated_at,last_used_at"
NOTIFICATION_SETTINGS_COLUMNS = "user_id,enabled,notification_time,timezone,created_at,updated_at"


class PushRepository:
    def __init__(self, supabase_client: Any | None = None) -> None:
        self._uses_default_client = supabase_client is None
        self.client = supabase_client or get_supabase_admin_client()

    def _get_client(self) -> Any:
        if self._uses_default_client:
            self.client = get_supabase_admin_client()
        return self.client

    def upsert_subscription(
        self,
        *,
        user_id: str,
        endpoint: str,
        p256dh: str,
        auth: str,
        user_agent: str | None,
    ) -> dict[str, Any]:
        response = (
            self._get_client()
            .table("push_subscriptions")
            .upsert(
                {
                    "user_id": user_id,
                    "endpoint": endpoint,
                    "p256dh": p256dh,
                    "auth": auth,
                    "user_agent": user_agent,
                },
                on_conflict="user_id,endpoint",
            )
            .select(PUSH_SUBSCRIPTION_COLUMNS)
            .execute()
        )
        return _first_row(response.data)

    def delete_subscription(self, *, user_id: str, endpoint: str) -> None:
        (
            self._get_client()
            .table("push_subscriptions")
            .delete()
            .eq("user_id", user_id)
            .eq("endpoint", endpoint)
            .execute()
        )

    def list_user_subscriptions(self, *, user_id: str) -> list[dict[str, Any]]:
        response = execute_supabase_read(
            lambda: (
                self._get_client()
                .table("push_subscriptions")
                .select(PUSH_SUBSCRIPTION_COLUMNS)
                .eq("user_id", user_id)
                .execute()
            )
        )
        return list(response.data or [])

    def touch_subscription(self, *, subscription_id: str) -> None:
        (
            self._get_client()
            .table("push_subscriptions")
            .update({"last_used_at": datetime.now(UTC).isoformat()})
            .eq("id", subscription_id)
            .execute()
        )

    def delete_subscription_by_id(self, *, subscription_id: str) -> None:
        (
            self._get_client()
            .table("push_subscriptions")
            .delete()
            .eq("id", subscription_id)
            .execute()
        )

    def get_notification_settings(self, *, user_id: str) -> dict[str, Any] | None:
        response = execute_supabase_read(
            lambda: (
                self._get_client()
                .table("notification_settings")
                .select(NOTIFICATION_SETTINGS_COLUMNS)
                .eq("user_id", user_id)
                .limit(1)
                .execute()
            )
        )
        rows = list(response.data or [])
        return dict(rows[0]) if rows else None

    def upsert_notification_settings(
        self,
        *,
        user_id: str,
        enabled: bool,
        notification_time: str,
        timezone: str,
    ) -> dict[str, Any]:
        response = (
            self._get_client()
            .table("notification_settings")
            .upsert(
                {
                    "user_id": user_id,
                    "enabled": enabled,
                    "notification_time": notification_time,
                    "timezone": timezone,
                },
                on_conflict="user_id",
            )
            .select(NOTIFICATION_SETTINGS_COLUMNS)
            .execute()
        )
        return _first_row(response.data)

    def list_enabled_notification_settings(self) -> list[dict[str, Any]]:
        response = execute_supabase_read(
            lambda: (
                self._get_client()
                .table("notification_settings")
                .select(NOTIFICATION_SETTINGS_COLUMNS)
                .eq("enabled", True)
                .execute()
            )
        )
        return list(response.data or [])

    def try_create_delivery_log(
        self,
        *,
        user_id: str,
        delivery_date: date,
        notification_type: str,
    ) -> bool:
        try:
            (
                self._get_client()
                .table("notification_delivery_log")
                .insert(
                    {
                        "user_id": user_id,
                        "delivery_date": delivery_date.isoformat(),
                        "notification_type": notification_type,
                    }
                )
                .execute()
            )
            return True
        except Exception as exc:
            if "duplicate" in str(exc).lower() or "23505" in str(exc):
                return False
            raise


def get_push_repository() -> PushRepository:
    return PushRepository()


def _first_row(data: Any) -> dict[str, Any]:
    if isinstance(data, list):
        return dict(data[0]) if data else {}
    return dict(data or {})
