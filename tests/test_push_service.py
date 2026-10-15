from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from services.notification_content import build_daily_notification
from services.push_service import DEFAULT_NOTIFICATION_TIME, DEFAULT_TIMEZONE, PushService


class FakeRepository:
    def __init__(self):
        self.settings = None
        self.subscriptions = []
        self.deleted = []
        self.deleted_delivery_logs = []
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
        self.subscription_user_id = user_id
        return self.subscriptions

    def touch_subscription(self, *, subscription_id):
        self.touched.append(subscription_id)

    def delete_subscription_by_id(self, *, subscription_id):
        self.deleted.append({"subscription_id": subscription_id})

    def delete_delivery_log(self, **payload):
        self.deleted_delivery_logs.append(payload)


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


def test_push_service_resets_today_log_when_time_changes() -> None:
    repo = FakeRepository()
    repo.settings = {
        "user_id": "user-1",
        "enabled": True,
        "notification_time": "08:00",
        "timezone": "Asia/Seoul",
    }
    service = PushService(repository=repo)

    service.update_notification_settings(
        user_id="user-1",
        enabled=True,
        notification_time="09:30",
        timezone="Asia/Seoul",
    )

    assert repo.deleted_delivery_logs
    assert repo.deleted_delivery_logs[0]["user_id"] == "user-1"
    assert repo.deleted_delivery_logs[0]["notification_type"] == "daily_schedule"


def test_push_service_keeps_today_log_when_only_enabled_changes() -> None:
    repo = FakeRepository()
    repo.settings = {
        "user_id": "user-1",
        "enabled": False,
        "notification_time": "08:00",
        "timezone": "Asia/Seoul",
    }
    service = PushService(repository=repo)

    service.update_notification_settings(
        user_id="user-1",
        enabled=True,
        notification_time=None,
        timezone=None,
    )

    assert repo.deleted_delivery_logs == []


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


class FakeCalendarService:
    def __init__(self):
        self.calls = []
        self.data = {"goals": [], "milestones": []}

    def get_date_calendar(self, **payload):
        self.calls.append(payload)
        return self.data


def test_manual_push_resends_current_users_fresh_schedule_without_changing_daily_logs(monkeypatch) -> None:
    monkeypatch.setattr("services.push_service.utc_now", lambda: datetime(2026, 10, 15, 15, 30, tzinfo=UTC))
    repo = FakeRepository()
    repo.settings = {"enabled": False, "timezone": "Asia/Seoul", "notification_time": "08:00"}
    repo.subscriptions = [{"id": "sub-1", "endpoint": "https://push", "p256dh": "p256", "auth": "auth"}]
    calendar = FakeCalendarService()
    calendar.data = {"goals": [], "milestones": [
        {"id": str(i), "title": f"작업 {i}", "scheduled_date": "2026-10-16", "is_completed": False}
        for i in range(4)
    ]}
    service = PushService(repository=repo, calendar_service=calendar)
    sent = []
    monkeypatch.setattr(service, "_send_web_push", lambda **payload: sent.append(payload))

    for _ in range(2):
        assert service.send_test_push(user_id="current-user") == {"sent": 1, "removed": 0}
    assert sent[0]["payload"] == sent[1]["payload"] == build_daily_notification(calendar.data, date(2026, 10, 16))
    assert sent[0]["payload"]["body"] == "작업 0, 작업 1 외 2개"
    assert sent[0]["payload"]["url"] == "/#/today"
    assert calendar.calls == [{"user_id": "current-user", "target_date": date(2026, 10, 16)}] * 2
    assert repo.subscription_user_id == "current-user"
    assert repo.deleted_delivery_logs == []
    assert repo.settings["enabled"] is False

    calendar.data["milestones"][0]["is_completed"] = True
    service.send_test_push(user_id="current-user")
    assert sent[2]["payload"]["body"] == "작업 1, 작업 2 외 1개"
    assert len(calendar.calls) == 3


@pytest.mark.parametrize("timezone,expected_date", [
    ("Asia/Seoul", date(2026, 10, 16)),
    ("America/Los_Angeles", date(2026, 10, 15)),
    (None, date(2026, 10, 16)),
])
def test_manual_push_uses_notification_timezone(monkeypatch, timezone, expected_date) -> None:
    monkeypatch.setattr("services.push_service.utc_now", lambda: datetime(2026, 10, 15, 15, 30, tzinfo=UTC))
    repo = FakeRepository()
    repo.settings = {"timezone": timezone} if timezone else None
    calendar = FakeCalendarService()
    service = PushService(repository=repo, calendar_service=calendar)
    service.send_test_push(user_id="current-user")
    assert calendar.calls == [{"user_id": "current-user", "target_date": expected_date}]


@pytest.mark.parametrize("milestones", [
    [],
    [{"title": "완료", "scheduled_date": "2026-10-16", "is_completed": True}],
    [{"title": "다른 날짜", "scheduled_date": "2026-10-17", "is_completed": False}],
])
def test_manual_push_reports_no_incomplete_milestones(monkeypatch, milestones) -> None:
    monkeypatch.setattr("services.push_service.utc_now", lambda: datetime(2026, 10, 15, 15, 30, tzinfo=UTC))
    repo = FakeRepository()
    calendar = FakeCalendarService()
    calendar.data = {"goals": [{"id": "goal-only"}], "milestones": milestones}
    service = PushService(repository=repo, calendar_service=calendar)
    monkeypatch.setattr(service, "_send_web_push", lambda **payload: pytest.fail("Must not send an empty schedule"))
    assert service.send_test_push(user_id="current-user") == {"sent": 0, "removed": 0, "reason": "no_incomplete_milestones"}
    assert repo.deleted_delivery_logs == []


def test_manual_push_endpoint_uses_authenticated_user(client) -> None:
    from core.auth import require_current_user_id
    from services.push_service import get_push_service

    users = []

    class FakePushService:
        def send_test_push(self, *, user_id):
            users.append(user_id)
            return {"sent": 1, "removed": 0}

    client.app.dependency_overrides[get_push_service] = lambda: FakePushService()
    assert client.post("/push/test").status_code == 401
    assert users == []
    client.app.dependency_overrides[require_current_user_id] = lambda: "current-user"
    response = client.post("/push/test", json={"user_id": "another-user"})
    assert response.status_code == 200
    assert response.json()["data"]["sent"] == 1
    assert users == ["current-user"]
