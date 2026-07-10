from __future__ import annotations

from datetime import date

import pytest

from exceptions.goals import GoalNotFoundError
from exceptions.milestones import MilestoneDeleteFailedError, MilestoneNotFoundError
from schemas.milestone_schemas import (
    MilestoneCompleteRequest,
    MilestoneCreateRequest,
    MilestoneUpdateRequest,
)
from services.milestone_service import MilestoneService


def goal_row(**overrides):
    data = {
        "id": "goal-1",
        "user_id": "user-1",
        "title": "포트폴리오 준비",
        "deadline": "2026-03-31",
        "is_recurring": False,
        "recurrence_type": None,
        "color": "#4F46E5",
        "created_at": "2026-01-01T10:00:00+09:00",
        "updated_at": "2026-01-01T10:00:00+09:00",
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
        "scheduled_date": "2026-01-10",
        "is_completed": False,
        "created_at": "2026-01-01T10:00:00+09:00",
        "updated_at": "2026-01-01T10:00:00+09:00",
    }
    data.update(overrides)
    return data


class InMemoryGoalRepository:
    def __init__(self) -> None:
        self.rows = {"goal-1": goal_row()}

    def get_by_id(self, *, goal_id: str, user_id: str):
        row = self.rows.get(goal_id)
        if row and row["user_id"] == user_id:
            return row.copy()
        return None


class InMemoryMilestoneRepository:
    def __init__(self) -> None:
        self.rows = {"milestone-1": milestone_row()}
        self.created_payloads = []
        self.bulk_payloads = []
        self.updated_payloads = []
        self.deleted_filters = []
        self.today_queries = []

    def list_by_goal(self, *, goal_id: str, user_id: str):
        return [
            row.copy()
            for row in self.rows.values()
            if row["goal_id"] == goal_id and row["user_id"] == user_id
        ]

    def list_by_scheduled_date(self, *, scheduled_date: str, user_id: str):
        self.today_queries.append((scheduled_date, user_id))
        return [
            {**row, "goals": {"title": "포트폴리오 준비"}}
            for row in self.rows.values()
            if row["scheduled_date"] == scheduled_date and row["user_id"] == user_id
        ]

    def get_by_id(self, *, milestone_id: str, user_id: str):
        row = self.rows.get(milestone_id)
        if row and row["user_id"] == user_id:
            return row.copy()
        return None

    def create(self, *, payload: dict):
        self.created_payloads.append(payload.copy())
        row = milestone_row(id="milestone-2", **payload)
        self.rows[row["id"]] = row
        return row.copy()

    def bulk_create(self, *, payloads: list[dict]):
        self.bulk_payloads.append([payload.copy() for payload in payloads])
        rows = []
        for index, payload in enumerate(payloads, start=1):
            row = milestone_row(id=f"auto-{index}", **payload)
            self.rows[row["id"]] = row
            rows.append(row.copy())
        return rows

    def update(self, *, milestone_id: str, user_id: str, payload: dict):
        self.updated_payloads.append((milestone_id, user_id, payload.copy()))
        row = self.rows.get(milestone_id)
        if not row or row["user_id"] != user_id:
            return None
        row.update(payload)
        return row.copy()

    def delete(self, *, milestone_id: str, user_id: str):
        self.deleted_filters.append((milestone_id, user_id))
        row = self.rows.get(milestone_id)
        if not row or row["user_id"] != user_id:
            return False
        del self.rows[milestone_id]
        return True


def make_service() -> tuple[
    MilestoneService,
    InMemoryMilestoneRepository,
    InMemoryGoalRepository,
]:
    milestone_repository = InMemoryMilestoneRepository()
    goal_repository = InMemoryGoalRepository()
    return (
        MilestoneService(
            repository=milestone_repository,
            goal_repository=goal_repository,
        ),
        milestone_repository,
        goal_repository,
    )


def test_milestone_service_creates_milestone_under_owned_goal() -> None:
    service, milestone_repository, _ = make_service()

    created = service.create_milestone(
        goal_id="goal-1",
        user_id="user-1",
        body=MilestoneCreateRequest(
            title="테스트 작성",
            color="#222222",
            scheduled_date="2026-01-15",
        ),
    )

    assert created["goal_id"] == "goal-1"
    assert created["user_id"] == "user-1"
    assert milestone_repository.created_payloads == [
        {
            "title": "테스트 작성",
            "color": "#222222",
            "scheduled_date": "2026-01-15",
            "goal_id": "goal-1",
            "user_id": "user-1",
        }
    ]


def test_milestone_service_rejects_milestone_for_unowned_goal() -> None:
    service, _, _ = make_service()

    with pytest.raises(GoalNotFoundError):
        service.create_milestone(
            goal_id="goal-1",
            user_id="other-user",
            body=MilestoneCreateRequest(
                title="권한 없는 생성",
                color="#222222",
                scheduled_date="2026-01-15",
            ),
        )


def test_milestone_service_reads_updates_completes_and_deletes_owned_milestone() -> None:
    service, milestone_repository, _ = make_service()

    listed = service.list_goal_milestones(goal_id="goal-1", user_id="user-1")
    assert [row["id"] for row in listed] == ["milestone-1"]

    today = service.list_today_milestones(user_id="user-1", today=date(2026, 1, 10))
    assert [row["id"] for row in today] == ["milestone-1"]
    assert today[0]["goal_title"] == "포트폴리오 준비"
    assert "goals" not in today[0]
    assert milestone_repository.today_queries == [("2026-01-10", "user-1")]

    updated = service.update_milestone(
        milestone_id="milestone-1",
        user_id="user-1",
        body=MilestoneUpdateRequest(title="수정된 마일스톤", scheduled_date="2026-01-20"),
    )
    assert updated["title"] == "수정된 마일스톤"
    assert milestone_repository.updated_payloads[0] == (
        "milestone-1",
        "user-1",
        {"title": "수정된 마일스톤", "scheduled_date": "2026-01-20"},
    )

    completed = service.complete_milestone(
        milestone_id="milestone-1",
        user_id="user-1",
        body=MilestoneCompleteRequest(is_completed=True),
    )
    assert completed["is_completed"] is True

    service.delete_milestone(milestone_id="milestone-1", user_id="user-1")
    assert milestone_repository.deleted_filters == [("milestone-1", "user-1")]


def test_milestone_service_maps_missing_and_failed_delete() -> None:
    service, milestone_repository, _ = make_service()

    with pytest.raises(MilestoneNotFoundError):
        service.get_milestone(milestone_id="milestone-1", user_id="other-user")

    milestone_repository.delete = lambda *, milestone_id, user_id: False
    with pytest.raises(MilestoneDeleteFailedError):
        service.delete_milestone(milestone_id="milestone-1", user_id="user-1")


def test_milestone_service_calculates_recurring_dates_with_exceptions() -> None:
    service, _, _ = make_service()

    assert service.calculate_recurring_dates(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 4),
        recurrence_type="daily",
        exception_dates=[date(2026, 1, 2)],
    ) == [date(2026, 1, 1), date(2026, 1, 3), date(2026, 1, 4)]

    assert service.calculate_recurring_dates(
        start_date=date(2026, 1, 5),
        end_date=date(2026, 1, 20),
        recurrence_type="weekly",
    ) == [date(2026, 1, 5), date(2026, 1, 12), date(2026, 1, 19)]

    assert service.calculate_recurring_dates(
        start_date=date(2026, 1, 31),
        end_date=date(2026, 3, 31),
        recurrence_type="monthly",
    ) == [date(2026, 1, 31), date(2026, 2, 28), date(2026, 3, 31)]


def test_milestone_service_creates_recurring_milestones_from_goal() -> None:
    service, milestone_repository, _ = make_service()
    goal = goal_row(
        is_recurring=True,
        recurrence_type="weekly",
        deadline="2026-01-31",
    )

    created = service.create_recurring_milestones(
        goal=goal,
        user_id="user-1",
        start_date=date(2026, 1, 5),
        exception_dates=[date(2026, 1, 12)],
    )

    assert [row["scheduled_date"] for row in created] == ["2026-01-05", "2026-01-19", "2026-01-26"]
    assert milestone_repository.bulk_payloads == [
        [
            {
                "goal_id": "goal-1",
                "user_id": "user-1",
                "title": "포트폴리오 준비",
                "color": "#4F46E5",
                "scheduled_date": "2026-01-05",
                "is_completed": False,
            },
            {
                "goal_id": "goal-1",
                "user_id": "user-1",
                "title": "포트폴리오 준비",
                "color": "#4F46E5",
                "scheduled_date": "2026-01-19",
                "is_completed": False,
            },
            {
                "goal_id": "goal-1",
                "user_id": "user-1",
                "title": "포트폴리오 준비",
                "color": "#4F46E5",
                "scheduled_date": "2026-01-26",
                "is_completed": False,
            },
        ]
    ]
