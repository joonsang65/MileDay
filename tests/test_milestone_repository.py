from __future__ import annotations

from repositories.milestones import MilestoneRepository


class FakeResponse:
    def __init__(self, data):
        self.data = data


class FakeMilestoneQuery:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []
        self.operation = None
        self.payload = None

    def select(self, value):
        self.calls.append(("select", value))
        return self

    def insert(self, payload):
        self.operation = "insert"
        self.payload = payload
        self.calls.append(("insert", payload))
        return self

    def update(self, payload):
        self.operation = "update"
        self.payload = payload
        self.calls.append(("update", payload))
        return self

    def delete(self):
        self.operation = "delete"
        self.calls.append(("delete", None))
        return self

    def eq(self, field, value):
        self.calls.append(("eq", field, value))
        return self

    def order(self, field):
        self.calls.append(("order", field))
        return self

    def limit(self, value):
        self.calls.append(("limit", value))
        return self

    def execute(self):
        return FakeResponse(self.rows)


class FakeSupabaseClient:
    def __init__(self, rows):
        self.rows = rows
        self.queries = []

    def table(self, name):
        query = FakeMilestoneQuery(self.rows)
        self.queries.append((name, query))
        return query


def latest_query(client):
    assert client.queries[-1][0] == "milestones"
    return client.queries[-1][1]


def test_milestone_repository_default_client_uses_admin_client(monkeypatch) -> None:
    admin_client = FakeSupabaseClient(rows=[])
    monkeypatch.setattr(
        "repositories.milestones.get_supabase_admin_client",
        lambda: admin_client,
    )

    repository = MilestoneRepository()

    assert repository.client is admin_client


def test_milestone_repository_applies_filters_to_reads() -> None:
    client = FakeSupabaseClient(rows=[{"id": "milestone-1"}])
    repository = MilestoneRepository(supabase_client=client)

    assert repository.list_by_goal(goal_id="goal-1", user_id="user-1") == [
        {"id": "milestone-1"}
    ]
    assert latest_query(client).calls == [
        ("select", "*"),
        ("eq", "goal_id", "goal-1"),
        ("eq", "user_id", "user-1"),
        ("order", "scheduled_date"),
    ]

    assert repository.list_by_scheduled_date(
        scheduled_date="2026-01-10",
        user_id="user-1",
    ) == [{"id": "milestone-1"}]
    assert latest_query(client).calls == [
        ("select", "*, goals(title)"),
        ("eq", "scheduled_date", "2026-01-10"),
        ("eq", "user_id", "user-1"),
        ("order", "created_at"),
    ]

    assert repository.get_by_id(milestone_id="milestone-1", user_id="user-1") == {
        "id": "milestone-1"
    }
    assert latest_query(client).calls == [
        ("select", "*"),
        ("eq", "id", "milestone-1"),
        ("eq", "user_id", "user-1"),
        ("limit", 1),
    ]


def test_milestone_repository_applies_filters_to_mutations() -> None:
    client = FakeSupabaseClient(rows=[{"id": "milestone-1"}])
    repository = MilestoneRepository(supabase_client=client)

    payload = {"title": "M4", "goal_id": "goal-1", "user_id": "user-1"}
    assert repository.create(payload=payload) == {"id": "milestone-1"}
    assert latest_query(client).calls == [("insert", payload)]

    payloads = [payload, {**payload, "title": "M4-2"}]
    assert repository.bulk_create(payloads=payloads) == [{"id": "milestone-1"}]
    assert latest_query(client).calls == [("insert", payloads)]

    assert repository.update(
        milestone_id="milestone-1",
        user_id="user-1",
        payload={"title": "수정"},
    ) == {"id": "milestone-1"}
    assert latest_query(client).calls == [
        ("update", {"title": "수정"}),
        ("eq", "id", "milestone-1"),
        ("eq", "user_id", "user-1"),
    ]

    assert repository.delete(milestone_id="milestone-1", user_id="user-1") is True
    assert latest_query(client).calls == [
        ("delete", None),
        ("eq", "id", "milestone-1"),
        ("eq", "user_id", "user-1"),
    ]


def test_milestone_repository_returns_empty_results() -> None:
    client = FakeSupabaseClient(rows=[])
    repository = MilestoneRepository(supabase_client=client)

    assert repository.get_by_id(milestone_id="missing", user_id="user-1") is None
    assert repository.create(payload={"title": "M4"}) is None
    assert repository.bulk_create(payloads=[]) == []
    assert repository.update(milestone_id="missing", user_id="user-1", payload={}) is None
    assert repository.delete(milestone_id="missing", user_id="user-1") is False
