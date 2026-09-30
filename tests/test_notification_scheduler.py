from __future__ import annotations

from datetime import UTC, datetime

from services.notification_scheduler import NotificationScheduler


class FakeRepository:
    def __init__(self):
        self.settings = []
        self.log_result = True
        self.subscriptions = [{"id": "sub-1"}]

    def list_enabled_notification_settings(self):
        return self.settings

    def try_create_delivery_log(self, **payload):
        self.last_log = payload
        return self.log_result

    def list_user_subscriptions(self, *, user_id):
        return self.subscriptions


class FakeCalendarService:
    def __init__(self, count):
        self.count = count

    def get_date_calendar(self, **payload):
        self.last_payload = payload
        return {
            "goals": [{"id": str(index)} for index in range(self.count)],
            "milestones": [],
        }


class FakePushService:
    def __init__(self):
        self.sent = []

    def send_user_push(self, **payload):
        self.sent.append(payload)
        return {"sent": 1, "removed": 0}


def test_scheduler_sends_due_daily_notification_once() -> None:
    repo = FakeRepository()
    repo.settings = [
        {
            "user_id": "user-1",
            "enabled": True,
            "notification_time": "08:00:00",
            "timezone": "Asia/Seoul",
        }
    ]
    calendar = FakeCalendarService(count=2)
    push = FakePushService()
    scheduler = NotificationScheduler(repository=repo, calendar_service=calendar, push_service=push)

    result = scheduler.run_once(now=datetime(2026, 9, 29, 23, 0, tzinfo=UTC))

    assert result == {"checked": 1, "sent_users": 1, "skipped": 0}
    assert repo.last_log["delivery_date"].isoformat() == "2026-09-30"
    assert push.sent[0]["body"] == "오늘 일정이 2개 있습니다."


def test_scheduler_skips_not_due_duplicate_and_empty_days() -> None:
    repo = FakeRepository()
    repo.settings = [
        {"user_id": "not-due", "notification_time": "08:00", "timezone": "Asia/Seoul"},
    ]
    scheduler = NotificationScheduler(
        repository=repo,
        calendar_service=FakeCalendarService(count=1),
        push_service=FakePushService(),
    )
    assert scheduler.run_once(now=datetime(2026, 9, 29, 22, 59, tzinfo=UTC))["skipped"] == 1

    repo.log_result = False
    repo.settings = [{"user_id": "dup", "notification_time": "08:00", "timezone": "Asia/Seoul"}]
    assert scheduler.run_once(now=datetime(2026, 9, 29, 23, 0, tzinfo=UTC))["skipped"] == 1

    repo.log_result = True
    push = FakePushService()
    scheduler = NotificationScheduler(
        repository=repo,
        calendar_service=FakeCalendarService(count=0),
        push_service=push,
    )
    assert scheduler.run_once(now=datetime(2026, 9, 29, 23, 0, tzinfo=UTC))["skipped"] == 1
    assert push.sent == []

    repo.subscriptions = []
    scheduler = NotificationScheduler(
        repository=repo,
        calendar_service=FakeCalendarService(count=1),
        push_service=push,
    )
    assert scheduler.run_once(now=datetime(2026, 9, 29, 23, 0, tzinfo=UTC))["skipped"] == 1
