from __future__ import annotations

import calendar
from datetime import date, timedelta
from typing import Any, Iterable

from exceptions.goals import GoalNotFoundError
from exceptions.milestones import (
    MilestoneCreateFailedError,
    MilestoneDeleteFailedError,
    MilestoneNotFoundError,
    MilestoneUpdateFailedError,
)
from repositories.goals import GoalRepository, get_goal_repository
from repositories.milestones import MilestoneRepository, get_milestone_repository
from schemas.milestone_schemas import (
    MilestoneCompleteRequest,
    MilestoneCreateRequest,
    MilestoneUpdateRequest,
)


class MilestoneService:
    def __init__(
        self,
        repository: MilestoneRepository | None = None,
        goal_repository: GoalRepository | None = None,
    ) -> None:
        self.repository = repository or get_milestone_repository()
        self.goal_repository = goal_repository or get_goal_repository()

    def list_goal_milestones(self, *, goal_id: str, user_id: str) -> list[dict[str, Any]]:
        self._get_owned_goal(goal_id=goal_id, user_id=user_id)
        return self.repository.list_by_goal(goal_id=goal_id, user_id=user_id)

    def list_today_milestones(
        self,
        *,
        user_id: str,
        today: date | None = None,
    ) -> list[dict[str, Any]]:
        target_date = today or date.today()
        return [
            self._with_goal_title(row)
            for row in self.repository.list_by_scheduled_date(
                scheduled_date=target_date.isoformat(),
                user_id=user_id,
            )
        ]

    def get_milestone(self, *, milestone_id: str, user_id: str) -> dict[str, Any]:
        milestone = self.repository.get_by_id(
            milestone_id=milestone_id,
            user_id=user_id,
        )
        if not milestone:
            raise MilestoneNotFoundError(detail={"milestone_id": milestone_id})
        return milestone

    def create_milestone(
        self,
        *,
        goal_id: str,
        user_id: str,
        body: MilestoneCreateRequest,
    ) -> dict[str, Any]:
        self._get_owned_goal(goal_id=goal_id, user_id=user_id)
        payload = self._serialize_payload(body.model_dump())
        payload["goal_id"] = goal_id
        payload["user_id"] = user_id
        try:
            milestone = self.repository.create(payload=payload)
        except Exception as exc:
            raise MilestoneCreateFailedError(detail=self._exception_detail(exc)) from exc
        if not milestone:
            raise MilestoneCreateFailedError()
        return milestone

    def update_milestone(
        self,
        *,
        milestone_id: str,
        user_id: str,
        body: MilestoneUpdateRequest,
    ) -> dict[str, Any]:
        current = self.get_milestone(milestone_id=milestone_id, user_id=user_id)
        payload = body.model_dump(exclude_unset=True)
        if not payload:
            return current
        try:
            updated = self.repository.update(
                milestone_id=milestone_id,
                user_id=user_id,
                payload=self._serialize_payload(payload),
            )
        except Exception as exc:
            raise MilestoneUpdateFailedError(
                detail={"type": exc.__class__.__name__}
            ) from exc
        if not updated:
            raise MilestoneNotFoundError(detail={"milestone_id": milestone_id})
        return updated

    def complete_milestone(
        self,
        *,
        milestone_id: str,
        user_id: str,
        body: MilestoneCompleteRequest,
    ) -> dict[str, Any]:
        return self.update_milestone(
            milestone_id=milestone_id,
            user_id=user_id,
            body=MilestoneUpdateRequest(is_completed=body.is_completed),
        )

    def delete_milestone(self, *, milestone_id: str, user_id: str) -> None:
        self.get_milestone(milestone_id=milestone_id, user_id=user_id)
        try:
            deleted = self.repository.delete(milestone_id=milestone_id, user_id=user_id)
        except Exception as exc:
            raise MilestoneDeleteFailedError(
                detail={"type": exc.__class__.__name__}
            ) from exc
        if not deleted:
            raise MilestoneDeleteFailedError(detail={"milestone_id": milestone_id})

    def create_recurring_milestones(
        self,
        *,
        goal: dict[str, Any],
        user_id: str,
        start_date: date,
        exception_dates: Iterable[date] | None = None,
    ) -> list[dict[str, Any]]:
        if goal.get("user_id") != user_id:
            raise GoalNotFoundError(detail={"goal_id": goal.get("id")})
        if not goal.get("is_recurring"):
            return []

        scheduled_dates = self.calculate_recurring_dates(
            start_date=start_date,
            end_date=self._parse_date(goal["deadline"]),
            recurrence_type=str(goal.get("recurrence_type")),
            exception_dates=exception_dates,
        )
        payloads = [
            {
                "goal_id": goal["id"],
                "user_id": user_id,
                "title": goal["title"],
                "color": goal["color"],
                "scheduled_date": scheduled_date.isoformat(),
                "is_completed": False,
            }
            for scheduled_date in scheduled_dates
        ]
        try:
            return self.repository.bulk_create(payloads=payloads)
        except Exception as exc:
            raise MilestoneCreateFailedError(detail=self._exception_detail(exc)) from exc

    def calculate_recurring_dates(
        self,
        *,
        start_date: date,
        end_date: date,
        recurrence_type: str,
        exception_dates: Iterable[date] | None = None,
    ) -> list[date]:
        exceptions = set(exception_dates or [])
        if start_date > end_date:
            return []

        dates: list[date] = []
        current = start_date
        while current <= end_date:
            if current not in exceptions:
                dates.append(current)
            current = self._next_date(current, recurrence_type, start_date.day)
        return dates

    def _get_owned_goal(self, *, goal_id: str, user_id: str) -> dict[str, Any]:
        goal = self.goal_repository.get_by_id(goal_id=goal_id, user_id=user_id)
        if not goal:
            raise GoalNotFoundError(detail={"goal_id": goal_id})
        return goal

    def _next_date(
        self,
        current: date,
        recurrence_type: str,
        preferred_day: int,
    ) -> date:
        if recurrence_type == "daily":
            return current + timedelta(days=1)
        if recurrence_type == "weekly":
            return current + timedelta(weeks=1)
        if recurrence_type == "monthly":
            return self._add_month(current, preferred_day=preferred_day)
        raise ValueError("지원하지 않는 반복 유형입니다.")

    def _add_month(self, current: date, *, preferred_day: int) -> date:
        year = current.year + (current.month // 12)
        month = 1 if current.month == 12 else current.month + 1
        last_day = calendar.monthrange(year, month)[1]
        return date(year, month, min(preferred_day, last_day))

    def _parse_date(self, value: date | str) -> date:
        if isinstance(value, date):
            return value
        return date.fromisoformat(value)

    def _serialize_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            key: value.isoformat() if isinstance(value, date) else value
            for key, value in payload.items()
        }

    def _with_goal_title(self, row: dict[str, Any]) -> dict[str, Any]:
        milestone = dict(row)
        goal_data = milestone.pop("goals", None) or milestone.pop("goal", None)
        if "goal_title" not in milestone:
            milestone["goal_title"] = self._extract_goal_title(goal_data)
        return milestone

    def _extract_goal_title(self, goal_data: Any) -> str | None:
        if isinstance(goal_data, list):
            goal_data = goal_data[0] if goal_data else None
        if isinstance(goal_data, dict):
            return goal_data.get("title")
        return None

    def _exception_detail(self, exc: Exception) -> dict[str, Any]:
        detail: dict[str, Any] = {"type": exc.__class__.__name__}
        for field in ("code", "message", "details", "hint"):
            value = getattr(exc, field, None)
            if value:
                detail[field] = value
        return detail


def get_milestone_service() -> MilestoneService:
    return MilestoneService()
