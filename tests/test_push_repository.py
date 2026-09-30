from __future__ import annotations

from datetime import date

from repositories.push import PushRepository


class FakeResponse:
    def __init__(self, data):
        self.data = data


class FakeQuery:
    def __init__(self, rows=None, fail=None):
        self.rows = rows or []
        self.fail = fail
        self.calls = []

    def select(self, value):
        self.calls.append(("select", value))
        return self

    def eq(self, field, value):
        self.calls.append(("eq", field, value))
        return self

    def limit(self, value):
        self.calls.append(("limit", value))
        return self

    def upsert(self, payload, on_conflict=None):
        self.calls.append(("upsert", payload, on_conflict))
        return self

    def delete(self):
        self.calls.append(("delete",))
        return self

    def update(self, payload):
        self.calls.append(("update", payload))
        return self

    def insert(self, payload):
        self.calls.append(("insert", payload))
        return self

    def execute(self):
        if self.fail:
            raise self.fail
        return FakeResponse(self.rows)


class FakeClient:
    def __init__(self):
        self.queries = []
        self.next_rows = []
        self.next_fail = None

    def table(self, name):
        query = FakeQuery(self.next_rows, self.next_fail)
        self.queries.append((name, query))
        self.next_rows = []
        self.next_fail = None
        return query


def latest(client: FakeClient):
    return client.queries[-1]


def test_push_repository_subscriptions_and_settings() -> None:
    client = FakeClient()
    repo = PushRepository(supabase_client=client)

    client.next_rows = [{"id": "sub-1", "endpoint": "https://push"}]
    assert repo.upsert_subscription(
        user_id="user-1",
        endpoint="https://push",
        p256dh="p256",
        auth="auth",
        user_agent="agent",
    )["id"] == "sub-1"
    table, query = latest(client)
    assert table == "push_subscriptions"
    assert query.calls[0][0] == "upsert"
    assert query.calls[0][2] == "user_id,endpoint"

    repo.delete_subscription(user_id="user-1", endpoint="https://push")
    assert latest(client)[1].calls == [
        ("delete",),
        ("eq", "user_id", "user-1"),
        ("eq", "endpoint", "https://push"),
    ]

    client.next_rows = [{"user_id": "user-1", "enabled": True}]
    assert repo.get_notification_settings(user_id="user-1") == {"user_id": "user-1", "enabled": True}

    client.next_rows = [{"user_id": "user-1", "enabled": False}]
    assert repo.upsert_notification_settings(
        user_id="user-1",
        enabled=False,
        notification_time="08:00",
        timezone="Asia/Seoul",
    )["enabled"] is False


def test_push_repository_delivery_log_duplicate_returns_false() -> None:
    client = FakeClient()
    repo = PushRepository(supabase_client=client)

    assert repo.try_create_delivery_log(
        user_id="user-1",
        delivery_date=date(2026, 9, 30),
        notification_type="daily_schedule",
    )

    client.next_fail = Exception("duplicate key value violates unique constraint 23505")
    assert not repo.try_create_delivery_log(
        user_id="user-1",
        delivery_date=date(2026, 9, 30),
        notification_type="daily_schedule",
    )
