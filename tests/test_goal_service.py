from __future__ import annotations

import pytest

from exceptions.common import BadRequestError
from exceptions.goals import GoalCreateFailedError, GoalDeleteFailedError, GoalNotFoundError
from schemas.goal_schemas import GoalCreateRequest, GoalUpdateRequest
from services.goal_service import GoalService


def goal_row(**overrides):
    data = {
        "id": "goal-1",
        "user_id": "user-1",
        "title": "Prepare portfolio",
        "deadline": "2026-09-30",
        "is_recurring": False,
        "recurrence_type": None,
        "color": "#4F46E5",
        "created_at": "2026-07-01T10:00:00+09:00",
        "updated_at": "2026-07-01T10:00:00+09:00",
    }
    data.update(overrides)
    return data


class InMemoryGoalRepository:
    def __init__(self) -> None:
        self.rows = {"goal-1": goal_row()}
        self.created_payloads = []
        self.updated_payloads = []
        self.deleted_filters = []

    def list_by_user(self, *, user_id: str):
        return [row for row in self.rows.values() if row["user_id"] == user_id]

    def get_by_id(self, *, goal_id: str, user_id: str):
        row = self.rows.get(goal_id)
        if row and row["user_id"] == user_id:
            return row.copy()
        return None

    def create(self, *, payload: dict):
        self.created_payloads.append(payload.copy())
        row = goal_row(id="goal-2", **payload)
        self.rows[row["id"]] = row
        return row.copy()

    def update(self, *, goal_id: str, user_id: str, payload: dict):
        self.updated_payloads.append((goal_id, user_id, payload.copy()))
        row = self.rows.get(goal_id)
        if not row or row["user_id"] != user_id:
            return None
        row.update(payload)
        return row.copy()

    def delete(self, *, goal_id: str, user_id: str):
        self.deleted_filters.append((goal_id, user_id))
        row = self.rows.get(goal_id)
        if not row or row["user_id"] != user_id:
            return False
        del self.rows[goal_id]
        return True


def test_goal_service_creates_goal_with_current_user_id_and_serialized_date() -> None:
    repository = InMemoryGoalRepository()
    service = GoalService(repository=repository)

    created = service.create_goal(
        user_id="user-1",
        body=GoalCreateRequest(
            title="Weekly planning",
            deadline="2026-08-01",
            is_recurring=True,
            recurrence_type="weekly",
            color="#22C55E",
        ),
    )

    assert created["user_id"] == "user-1"
    assert created["recurrence_type"] == "weekly"
    assert repository.created_payloads == [
        {
            "title": "Weekly planning",
            "deadline": "2026-08-01",
            "is_recurring": True,
            "recurrence_type": "weekly",
            "color": "#22C55E",
            "user_id": "user-1",
        }
    ]


def test_goal_service_preserves_create_exception_detail() -> None:
    class SupabaseError(Exception):
        code = "42501"
        message = "new row violates row-level security policy"
        details = "RLS check failed"
        hint = "Use a server-side client"

    repository = InMemoryGoalRepository()
    repository.create = lambda *, payload: (_ for _ in ()).throw(SupabaseError())
    service = GoalService(repository=repository)

    with pytest.raises(GoalCreateFailedError) as exc_info:
        service.create_goal(
            user_id="user-1",
            body=GoalCreateRequest(
                title="Weekly planning",
                deadline="2026-08-01",
                is_recurring=False,
                recurrence_type=None,
                color="#22C55E",
            ),
        )

    assert exc_info.value.detail == {
        "type": "SupabaseError",
        "code": "42501",
        "message": "new row violates row-level security policy",
        "details": "RLS check failed",
        "hint": "Use a server-side client",
    }


def test_goal_service_reads_and_updates_only_current_user_goal() -> None:
    repository = InMemoryGoalRepository()
    service = GoalService(repository=repository)

    listed = service.list_goals(user_id="user-1")
    assert [row["id"] for row in listed] == ["goal-1"]

    updated = service.update_goal(
        goal_id="goal-1",
        user_id="user-1",
        body=GoalUpdateRequest(title="Updated portfolio", deadline="2026-10-01"),
    )
    assert updated["title"] == "Updated portfolio"
    assert repository.updated_payloads == [
        ("goal-1", "user-1", {"title": "Updated portfolio", "deadline": "2026-10-01"})
    ]

    with pytest.raises(GoalNotFoundError):
        service.get_goal(goal_id="goal-1", user_id="other-user")


def test_goal_service_validates_partial_recurrence_updates_against_current_state() -> None:
    repository = InMemoryGoalRepository()
    service = GoalService(repository=repository)

    with pytest.raises(BadRequestError):
        service.update_goal(
            goal_id="goal-1",
            user_id="user-1",
            body=GoalUpdateRequest(recurrence_type="weekly"),
        )

    enabled = service.update_goal(
        goal_id="goal-1",
        user_id="user-1",
        body=GoalUpdateRequest(is_recurring=True, recurrence_type="weekly"),
    )
    assert enabled["is_recurring"] is True
    assert enabled["recurrence_type"] == "weekly"

    with pytest.raises(BadRequestError):
        service.update_goal(
            goal_id="goal-1",
            user_id="user-1",
            body=GoalUpdateRequest(is_recurring=False),
        )


def test_goal_service_delete_checks_ownership_and_failed_delete_result() -> None:
    repository = InMemoryGoalRepository()
    service = GoalService(repository=repository)

    service.delete_goal(goal_id="goal-1", user_id="user-1")
    assert repository.deleted_filters == [("goal-1", "user-1")]

    repository.rows["goal-1"] = goal_row()
    repository.delete = lambda *, goal_id, user_id: False
    with pytest.raises(GoalDeleteFailedError):
        service.delete_goal(goal_id="goal-1", user_id="user-1")
