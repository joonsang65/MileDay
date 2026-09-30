from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from core.config import get_settings
from repositories.push import PushRepository, get_push_repository


DEFAULT_NOTIFICATION_TIME = "08:00"
DEFAULT_TIMEZONE = "Asia/Seoul"


class PushConfigurationError(RuntimeError):
    pass


class PushService:
    def __init__(self, repository: PushRepository | None = None) -> None:
        self.repository = repository or get_push_repository()

    def get_public_config(self) -> dict[str, Any]:
        settings = get_settings()
        return {
            "vapid_public_key": settings.vapid_public_key,
            "configured": bool(settings.vapid_public_key),
        }

    def subscribe(
        self,
        *,
        user_id: str,
        endpoint: str,
        p256dh: str,
        auth: str,
        user_agent: str | None,
    ) -> dict[str, Any]:
        return self.repository.upsert_subscription(
            user_id=user_id,
            endpoint=endpoint,
            p256dh=p256dh,
            auth=auth,
            user_agent=user_agent,
        )

    def unsubscribe(self, *, user_id: str, endpoint: str) -> None:
        self.repository.delete_subscription(user_id=user_id, endpoint=endpoint)

    def get_notification_settings(self, *, user_id: str) -> dict[str, Any]:
        row = self.repository.get_notification_settings(user_id=user_id)
        if row:
            return row
        return {
            "user_id": user_id,
            "enabled": False,
            "notification_time": DEFAULT_NOTIFICATION_TIME,
            "timezone": DEFAULT_TIMEZONE,
        }

    def update_notification_settings(
        self,
        *,
        user_id: str,
        enabled: bool | None,
        notification_time: str | None,
        timezone: str | None,
    ) -> dict[str, Any]:
        current = self.get_notification_settings(user_id=user_id)
        next_timezone = timezone or current["timezone"] or DEFAULT_TIMEZONE
        self._validate_timezone(next_timezone)
        return self.repository.upsert_notification_settings(
            user_id=user_id,
            enabled=current["enabled"] if enabled is None else enabled,
            notification_time=notification_time or current["notification_time"] or DEFAULT_NOTIFICATION_TIME,
            timezone=next_timezone,
        )

    def send_test_push(self, *, user_id: str) -> dict[str, Any]:
        return self.send_user_push(
            user_id=user_id,
            title="MileDay",
            body="Test notification from MileDay.",
            url="/today",
        )

    def send_user_push(self, *, user_id: str, title: str, body: str, url: str) -> dict[str, Any]:
        subscriptions = self.repository.list_user_subscriptions(user_id=user_id)
        sent = 0
        removed = 0
        for subscription in subscriptions:
            try:
                self._send_web_push(
                    subscription_info={
                        "endpoint": subscription["endpoint"],
                        "keys": {
                            "p256dh": subscription["p256dh"],
                            "auth": subscription["auth"],
                        },
                    },
                    payload={
                        "title": title,
                        "body": body,
                        "url": url,
                    },
                )
                sent += 1
                self.repository.touch_subscription(subscription_id=subscription["id"])
            except Exception as exc:
                status_code = getattr(getattr(exc, "response", None), "status_code", None)
                if status_code in {404, 410}:
                    self.repository.delete_subscription_by_id(subscription_id=subscription["id"])
                    removed += 1
                    continue
                raise
        return {"sent": sent, "removed": removed}

    def _send_web_push(self, *, subscription_info: dict[str, Any], payload: dict[str, str]) -> None:
        settings = get_settings()
        if not settings.vapid_public_key or not settings.vapid_private_key or not settings.vapid_claims_email:
            raise PushConfigurationError("VAPID settings are required to send Web Push.")

        try:
            from pywebpush import WebPushException, webpush
        except ImportError as exc:
            raise PushConfigurationError("pywebpush is not installed.") from exc

        claims = {"sub": f"mailto:{settings.vapid_claims_email}"}
        try:
            webpush(
                subscription_info=subscription_info,
                data=_json_payload(payload),
                vapid_private_key=settings.vapid_private_key,
                vapid_claims=claims,
            )
        except WebPushException:
            raise

    def _validate_timezone(self, timezone: str) -> None:
        try:
            ZoneInfo(timezone)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"Unsupported timezone: {timezone}") from exc


def get_push_service() -> PushService:
    return PushService()


def _json_payload(payload: dict[str, str]) -> str:
    import json

    return json.dumps(payload, ensure_ascii=False)


def utc_now() -> datetime:
    return datetime.now(UTC)
