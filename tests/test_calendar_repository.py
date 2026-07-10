from __future__ import annotations

from repositories.calendar import CalendarRepository


class FakeResponse:
    def __init__(self, data):
        self.data = data


class FakeCalendarQuery:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    def select(self, value):
        self.calls.append(("select", value))
        return self

    def eq(self, field, value):
        self.calls.append(("eq", field, value))
        return self

    def gte(self, field, value):
        self.calls.append(("gte", field, value))
        return self

    def lte(self, field, value):
        self.calls.append(("lte", field, value))
        return self

    def order(self, field):
        self.calls.append(("order", field))
        return self

    def execute(self):
        return FakeResponse(self.rows)


class FakeSupabaseClient:
    def __init__(self, rows):
        self.rows = rows
        self.queries = []

    def table(self, name):
        query = FakeCalendarQuery(self.rows)
        self.queries.append((name, query))
        return query


def latest_query(client):
    return client.queries[-1]


def test_calendar_repository_default_client_uses_admin_client(monkeypatch) -> None:
    admin_client = FakeSupabaseClient(rows=[])
    monkeypatch.setattr(
        "repositories.calendar.get_supabase_admin_client",
        lambda: admin_client,
    )

    repository = CalendarRepository()

    assert repository.client is admin_client


def test_calendar_repository_applies_goal_deadline_range_filters() -> None:
    client = FakeSupabaseClient(rows=[{"id": "goal-1"}])
    repository = CalendarRepository(supabase_client=client)

    assert repository.list_goals_by_deadline_range(
        user_id="user-1",
        start_date="2026-07-01",
        end_date="2026-07-31",
    ) == [{"id": "goal-1"}]

    table_name, query = latest_query(client)
    assert table_name == "goals"
    assert query.calls == [
        ("select", "*"),
        ("eq", "user_id", "user-1"),
        ("gte", "deadline", "2026-07-01"),
        ("lte", "deadline", "2026-07-31"),
        ("order", "deadline"),
    ]


def test_calendar_repository_applies_milestone_scheduled_date_range_filters() -> None:
    client = FakeSupabaseClient(rows=[{"id": "milestone-1"}])
    repository = CalendarRepository(supabase_client=client)

    assert repository.list_milestones_by_scheduled_date_range(
        user_id="user-1",
        start_date="2026-07-01",
        end_date="2026-07-31",
    ) == [{"id": "milestone-1"}]

    table_name, query = latest_query(client)
    assert table_name == "milestones"
    assert query.calls == [
        ("select", "*, goals(title)"),
        ("eq", "user_id", "user-1"),
        ("gte", "scheduled_date", "2026-07-01"),
        ("lte", "scheduled_date", "2026-07-31"),
        ("order", "scheduled_date"),
    ]


def test_calendar_repository_applies_exact_date_filters() -> None:
    client = FakeSupabaseClient(rows=[])
    repository = CalendarRepository(supabase_client=client)

    assert repository.list_goals_by_deadline(
        user_id="user-1",
        deadline="2026-07-10",
    ) == []
    table_name, query = latest_query(client)
    assert table_name == "goals"
    assert query.calls == [
        ("select", "*"),
        ("eq", "user_id", "user-1"),
        ("eq", "deadline", "2026-07-10"),
        ("order", "created_at"),
    ]

    assert repository.list_milestones_by_scheduled_date(
        user_id="user-1",
        scheduled_date="2026-07-10",
    ) == []
    table_name, query = latest_query(client)
    assert table_name == "milestones"
    assert query.calls == [
        ("select", "*, goals(title)"),
        ("eq", "user_id", "user-1"),
        ("eq", "scheduled_date", "2026-07-10"),
        ("order", "created_at"),
    ]
