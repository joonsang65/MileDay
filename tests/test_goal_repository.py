from __future__ import annotations

from repositories.goals import GoalRepository


class FakeResponse:
    def __init__(self, data):
        self.data = data


class FakeGoalQuery:
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
        query = FakeGoalQuery(self.rows)
        self.queries.append((name, query))
        return query


def latest_query(client):
    assert client.queries[-1][0] == "goals"
    return client.queries[-1][1]


def test_goal_repository_default_client_uses_admin_client(monkeypatch) -> None:
    admin_client = FakeSupabaseClient(rows=[])
    monkeypatch.setattr("repositories.goals.get_supabase_admin_client", lambda: admin_client)

    repository = GoalRepository()

    assert repository.client is admin_client


def test_goal_repository_applies_user_filters_to_reads() -> None:
    client = FakeSupabaseClient(rows=[{"id": "goal-1"}])
    repository = GoalRepository(supabase_client=client)

    assert repository.list_by_user(user_id="user-1") == [{"id": "goal-1"}]
    assert latest_query(client).calls == [
        ("select", "*"),
        ("eq", "user_id", "user-1"),
        ("order", "deadline"),
    ]

    assert repository.get_by_id(goal_id="goal-1", user_id="user-1") == {"id": "goal-1"}
    assert latest_query(client).calls == [
        ("select", "*"),
        ("eq", "id", "goal-1"),
        ("eq", "user_id", "user-1"),
        ("limit", 1),
    ]


def test_goal_repository_applies_user_filters_to_mutations() -> None:
    client = FakeSupabaseClient(rows=[{"id": "goal-1"}])
    repository = GoalRepository(supabase_client=client)

    payload = {"title": "M3", "user_id": "user-1"}
    assert repository.create(payload=payload) == {"id": "goal-1"}
    create_query = latest_query(client)
    assert create_query.operation == "insert"
    assert create_query.payload == payload

    assert repository.update(
        goal_id="goal-1",
        user_id="user-1",
        payload={"title": "Updated"},
    ) == {"id": "goal-1"}
    assert latest_query(client).calls == [
        ("update", {"title": "Updated"}),
        ("eq", "id", "goal-1"),
        ("eq", "user_id", "user-1"),
    ]

    assert repository.delete(goal_id="goal-1", user_id="user-1") is True
    assert latest_query(client).calls == [
        ("delete", None),
        ("eq", "id", "goal-1"),
        ("eq", "user_id", "user-1"),
    ]


def test_goal_repository_returns_none_or_false_for_empty_results() -> None:
    client = FakeSupabaseClient(rows=[])
    repository = GoalRepository(supabase_client=client)

    assert repository.get_by_id(goal_id="missing", user_id="user-1") is None
    assert repository.create(payload={"title": "M3"}) is None
    assert repository.update(goal_id="missing", user_id="user-1", payload={}) is None
    assert repository.delete(goal_id="missing", user_id="user-1") is False
