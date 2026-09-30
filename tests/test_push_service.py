from __future__ import annotations

import pytest

from services.push_service import DEFAULT_NOTIFICATION_TIME, DEFAULT_TIMEZONE, PushService


class FakeRepository:
    def __init__(self):
        self.settings = None
        self.subscriptions = []
        self.deleted = []
        self.touched = []

    def get_notification_settings(self, *, user_id):
        return self.settings

    def upsert_notification_settings(self, **payload):
        self.settings = payload
        return payload

    def upsert_subscription(self, **payload):
        return {"id": "sub-1", **payload}

    def delete_subscription(self, **payload):
        self.deleted.append(payload)

    def list_user_subscriptions(self, *, user_id):
        return self.subscriptions

    def touch_subscription(self, *, subscription_id):
        self.touched.append(subscription_id)

    def delete_subscription_by_id(self, *, subscription_id):
        self.deleted.append({"subscription_id": subscription_id})


def test_push_service_defaults_and_updates_settings() -> None:
    repo = FakeRepository()
    service = PushService(repository=repo)

    defaults = service.get_notification_settings(user_id="user-1")
    assert defaults["enabled"] is False
    assert defaults["notification_time"] == DEFAULT_NOTIFICATION_TIME
    assert defaults["timezone"] == DEFAULT_TIMEZONE

    updated = service.update_notification_settings(
        user_id="user-1",
        enabled=True,
        notification_time="09:30",
        timezone="Asia/Seoul",
    )
    assert updated["enabled"] is True
    assert updated["notification_time"] == "09:30"


def test_push_service_rejects_unknown_timezone() -> None:
    service = PushService(repository=FakeRepository())

    with pytest.raises(ValueError):
        service.update_notification_settings(
            user_id="user-1",
            enabled=True,
            notification_time="08:00",
            timezone="No/Such_Zone",
        )


def test_push_service_sends_to_all_subscriptions(monkeypatch) -> None:
    repo = FakeRepository()
    repo.subscriptions = [
        {"id": "sub-1", "endpoint": "https://push", "p256dh": "p256", "auth": "auth"}
    ]
    service = PushService(repository=repo)
    sent = []
    monkeypatch.setattr(service, "_send_web_push", lambda **payload: sent.append(payload))

    result = service.send_user_push(user_id="user-1", title="MileDay", body="Body", url="/today")

    assert result == {"sent": 1, "removed": 0}
    assert repo.touched == ["sub-1"]
    assert sent[0]["payload"]["url"] == "/today"
