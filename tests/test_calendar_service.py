from __future__ import annotations

from datetime import date

from services.calendar_service import CalendarService


def goal_row(**overrides):
    data = {
        "id": "goal-1",
        "user_id": "user-1",
        "title": "포트폴리오 준비",
        "deadline": "2026-07-10",
        "is_recurring": False,
        "recurrence_type": None,
        "color": "#4F46E5",
        "created_at": "2026-07-01T10:00:00+09:00",
        "updated_at": "2026-07-01T10:00:00+09:00",
    }
    data.update(overrides)
    return data


def milestone_row(**overrides):
    data = {
        "id": "milestone-1",
        "goal_id": "goal-1",
        "user_id": "user-1",
        "title": "이력서 초안 작성",
        "color": "#F97316",
        "scheduled_date": "2026-07-10",
        "is_completed": True,
        "created_at": "2026-07-01T10:00:00+09:00",
        "updated_at": "2026-07-01T10:00:00+09:00",
        "goals": {"title": "포트폴리오 준비"},
    }
    data.update(overrides)
    return data


class InMemoryCalendarRepository:
    def __init__(self) -> None:
        self.goals = [
            goal_row(),
            goal_row(id="goal-2", deadline="2026-08-01"),
            goal_row(id="other-goal", user_id="other-user"),
        ]
        self.milestones = [
            milestone_row(),
            milestone_row(
                id="milestone-2",
                scheduled_date="2026-07-11",
                is_completed=False,
            ),
            milestone_row(id="other-milestone", user_id="other-user"),
        ]
        self.range_queries = []
        self.date_queries = []

    def list_goals_by_deadline_range(self, *, user_id, start_date, end_date):
        self.range_queries.append(("goals", user_id, start_date, end_date))
        return [
            row.copy()
            for row in self.goals
            if row["user_id"] == user_id and start_date <= row["deadline"] <= end_date
        ]

    def list_milestones_by_scheduled_date_range(self, *, user_id, start_date, end_date):
        self.range_queries.append(("milestones", user_id, start_date, end_date))
        return [
            row.copy()
            for row in self.milestones
            if row["user_id"] == user_id
            and start_date <= row["scheduled_date"] <= end_date
        ]

    def list_goals_by_deadline(self, *, user_id, deadline):
        self.date_queries.append(("goals", user_id, deadline))
        return [
            row.copy()
            for row in self.goals
            if row["user_id"] == user_id and row["deadline"] == deadline
        ]

    def list_milestones_by_scheduled_date(self, *, user_id, scheduled_date):
        self.date_queries.append(("milestones", user_id, scheduled_date))
        return [
            row.copy()
            for row in self.milestones
            if row["user_id"] == user_id and row["scheduled_date"] == scheduled_date
        ]


def test_calendar_service_builds_month_days_from_owned_rows() -> None:
    repository = InMemoryCalendarRepository()
    service = CalendarService(repository=repository)

    result = service.get_month_calendar(
        user_id="user-1",
        year=2026,
        month=7,
        today=date(2026, 7, 10),
    )

    assert result["year"] == 2026
    assert result["month"] == 7
    assert len(result["days"]) == 31
    assert [row["id"] for row in result["goals"]] == ["goal-1"]
    assert [row["id"] for row in result["milestones"]] == [
        "milestone-1",
        "milestone-2",
    ]
    day = result["days"][9]
    assert day["date"] == date(2026, 7, 10)
    assert day["is_today"] is True
    assert day["goal_count"] == 1
    assert day["milestone_count"] == 1
    assert day["completed_milestone_count"] == 1
    assert day["milestones"][0]["goal_title"] == "포트폴리오 준비"
    assert "goals" not in day["milestones"][0]
    assert repository.range_queries == [
        ("goals", "user-1", "2026-07-01", "2026-07-31"),
        ("milestones", "user-1", "2026-07-01", "2026-07-31"),
    ]


def test_calendar_service_builds_date_detail_with_goal_title() -> None:
    repository = InMemoryCalendarRepository()
    service = CalendarService(repository=repository)

    result = service.get_date_calendar(
        user_id="user-1",
        target_date=date(2026, 7, 10),
        today=date(2026, 7, 11),
    )

    assert result["date"] == date(2026, 7, 10)
    assert result["is_today"] is False
    assert [row["id"] for row in result["goals"]] == ["goal-1"]
    assert [row["id"] for row in result["milestones"]] == ["milestone-1"]
    assert result["goal_count"] == 1
    assert result["milestone_count"] == 1
    assert result["completed_milestone_count"] == 1
    assert result["milestones"][0]["goal_title"] == "포트폴리오 준비"
    assert repository.date_queries == [
        ("goals", "user-1", "2026-07-10"),
        ("milestones", "user-1", "2026-07-10"),
    ]


def test_calendar_service_builds_week_days_from_start_date() -> None:
    repository = InMemoryCalendarRepository()
    service = CalendarService(repository=repository)

    result = service.get_week_calendar(
        user_id="user-1",
        start_date=date(2026, 7, 8),
        today=date(2026, 7, 11),
    )

    assert result["start_date"] == date(2026, 7, 8)
    assert result["end_date"] == date(2026, 7, 14)
    assert len(result["days"]) == 7
    assert result["days"][0]["date"] == date(2026, 7, 8)
    assert result["days"][-1]["date"] == date(2026, 7, 14)
    assert result["days"][3]["is_today"] is True
    assert [row["id"] for row in result["goals"]] == ["goal-1"]
    assert [row["id"] for row in result["milestones"]] == [
        "milestone-1",
        "milestone-2",
    ]
    assert repository.range_queries == [
        ("goals", "user-1", "2026-07-08", "2026-07-14"),
        ("milestones", "user-1", "2026-07-08", "2026-07-14"),
    ]
