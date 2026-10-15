from __future__ import annotations

from datetime import UTC, datetime

from services.notification_content import milestone_notification_body
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
            "milestones": [
                {"id": str(index), "title": f"작업 {index + 1}", "scheduled_date": payload["target_date"].isoformat(), "is_completed": False}
                for index in range(self.count)
            ],
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
    assert push.sent[0]["body"] == "작업 1, 작업 2"
    assert push.sent[0]["title"] == "MileDay · 오늘의 마일스톤"
    assert push.sent[0]["url"] == "/#/today"
    assert calendar.last_payload["target_date"].isoformat() == "2026-09-30"


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


def test_summary_is_stable_and_bounded() -> None:
    milestones = [{"id": str(i), "title": "가" * 200} for i in range(4)]
    body = milestone_notification_body(milestones)
    assert body == milestone_notification_body(list(reversed(milestones)))
    assert body.endswith(" 외 2개")
    assert len(body) <= 80
    assert "…" in body


def test_scheduler_only_includes_incomplete_milestones_for_local_today() -> None:
    repo = FakeRepository()
    repo.settings = [{"user_id": "u", "notification_time": "08:00", "timezone": "America/Los_Angeles"}]
    push = FakePushService()
    calendar = FakeCalendarService(count=0)
    rows = [
        {"id": "1", "title": "완료", "scheduled_date": "2026-09-30", "is_completed": True},
        {"id": "2", "title": "내일", "scheduled_date": "2026-10-01", "is_completed": False},
        {"id": "3", "title": "오늘 할 일", "scheduled_date": "2026-09-30", "is_completed": False},
    ]
    calendar.get_date_calendar = lambda **kwargs: {"goals": [{"id": "goal"}], "milestones": rows}
    scheduler = NotificationScheduler(repository=repo, calendar_service=calendar, push_service=push)
    assert scheduler.run_once(now=datetime(2026, 9, 30, 15, 0, tzinfo=UTC))["sent_users"] == 1
    assert push.sent[0]["body"] == "오늘 할 일"
    rows.pop()
    assert scheduler.run_once(now=datetime(2026, 9, 30, 15, 0, tzinfo=UTC))["skipped"] == 1
    rows.clear()
    assert scheduler.run_once(now=datetime(2026, 9, 30, 15, 0, tzinfo=UTC))["skipped"] == 1
