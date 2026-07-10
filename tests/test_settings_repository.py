from __future__ import annotations

from repositories.settings import SettingsRepository


class FakeResponse:
    def __init__(self, data):
        self.data = data


class FakeSettingsQuery:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []
        self.operation = None
        self.payload = None

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
        self.operation = "upsert"
        self.payload = payload
        self.calls.append(("upsert", payload, on_conflict))
        return self

    def update(self, payload):
        self.operation = "update"
        self.payload = payload
        self.calls.append(("update", payload))
        return self

    def execute(self):
        return FakeResponse(self.rows)


class FakeSupabaseClient:
    def __init__(self, rows):
        self.rows = rows
        self.queries = []

    def table(self, name):
        query = FakeSettingsQuery(self.rows)
        self.queries.append((name, query))
        return query


def latest_query(client):
    assert client.queries[-1][0] == "user_settings"
    return client.queries[-1][1]


def test_settings_repository_default_client_uses_admin_client(monkeypatch) -> None:
    admin_client = FakeSupabaseClient(rows=[])
    monkeypatch.setattr("repositories.settings.get_supabase_admin_client", lambda: admin_client)

    repository = SettingsRepository()

    assert repository.client is admin_client


def test_settings_repository_reads_and_mutates_by_user() -> None:
    client = FakeSupabaseClient(rows=[{"user_id": "user-1"}])
    repository = SettingsRepository(supabase_client=client)

    assert repository.get_by_user(user_id="user-1") == {"user_id": "user-1"}
    assert latest_query(client).calls == [
        ("select", "*"),
        ("eq", "user_id", "user-1"),
        ("limit", 1),
    ]

    payload = {"user_id": "user-1", "calendar_view": "month"}
    assert repository.upsert_defaults(payload=payload) == {"user_id": "user-1"}
    assert latest_query(client).calls == [
        ("upsert", payload, "user_id"),
    ]

    assert repository.update(user_id="user-1", payload={"language": "en"}) == {"user_id": "user-1"}
    assert latest_query(client).calls == [
        ("update", {"language": "en"}),
        ("eq", "user_id", "user-1"),
    ]
