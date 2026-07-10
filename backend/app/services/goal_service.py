from __future__ import annotations

from datetime import date
from typing import Any

from exceptions.goals import (
    GoalCreateFailedError,
    GoalDeleteFailedError,
    GoalNotFoundError,
    GoalUpdateFailedError,
)
from exceptions.common import BadRequestError
from repositories.goals import GoalRepository, get_goal_repository
from schemas.goal_schemas import GoalCreateRequest, GoalUpdateRequest


class GoalService:
    def __init__(self, repository: GoalRepository | None = None) -> None:
        self.repository = repository or get_goal_repository()

    def list_goals(self, *, user_id: str) -> list[dict[str, Any]]:
        return self.repository.list_by_user(user_id=user_id)

    def get_goal(self, *, goal_id: str, user_id: str) -> dict[str, Any]:
        goal = self.repository.get_by_id(goal_id=goal_id, user_id=user_id)
        if not goal:
            raise GoalNotFoundError(detail={"goal_id": goal_id})
        return goal

    def create_goal(
        self,
        *,
        user_id: str,
        body: GoalCreateRequest,
    ) -> dict[str, Any]:
        payload = self._serialize_payload(body.model_dump())
        payload["user_id"] = user_id
        try:
            goal = self.repository.create(payload=payload)
        except Exception as exc:
            raise GoalCreateFailedError(detail=self._exception_detail(exc)) from exc
        if not goal:
            raise GoalCreateFailedError()
        return goal

    def update_goal(
        self,
        *,
        goal_id: str,
        user_id: str,
        body: GoalUpdateRequest,
    ) -> dict[str, Any]:
        current = self.get_goal(goal_id=goal_id, user_id=user_id)
        payload = body.model_dump(exclude_unset=True)
        if not payload:
            return current

        merged = {**current, **payload}
        try:
            self._validate_recurrence_state(merged)
        except ValueError as exc:
            raise BadRequestError(message="반복 설정이 올바르지 않습니다.", detail=str(exc)) from exc

        try:
            updated = self.repository.update(
                goal_id=goal_id,
                user_id=user_id,
                payload=self._serialize_payload(payload),
            )
        except Exception as exc:
            raise GoalUpdateFailedError(detail={"type": exc.__class__.__name__}) from exc
        if not updated:
            raise GoalNotFoundError(detail={"goal_id": goal_id})
        return updated

    def delete_goal(self, *, goal_id: str, user_id: str) -> None:
        self.get_goal(goal_id=goal_id, user_id=user_id)
        try:
            deleted = self.repository.delete(goal_id=goal_id, user_id=user_id)
        except Exception as exc:
            raise GoalDeleteFailedError(detail={"type": exc.__class__.__name__}) from exc
        if not deleted:
            raise GoalDeleteFailedError(detail={"goal_id": goal_id})

    def _validate_recurrence_state(self, payload: dict[str, Any]) -> None:
        is_recurring = bool(payload.get("is_recurring"))
        recurrence_type = payload.get("recurrence_type")
        if is_recurring and recurrence_type is None:
            raise ValueError("반복 목표에는 recurrence_type이 필요합니다.")
        if not is_recurring and recurrence_type is not None:
            raise ValueError("반복하지 않는 목표의 recurrence_type은 null이어야 합니다.")

    def _serialize_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            key: value.isoformat() if isinstance(value, date) else value
            for key, value in payload.items()
        }

    def _exception_detail(self, exc: Exception) -> dict[str, Any]:
        detail: dict[str, Any] = {"type": exc.__class__.__name__}
        for field in ("code", "message", "details", "hint"):
            value = getattr(exc, field, None)
            if value:
                detail[field] = value
        return detail


def get_goal_service() -> GoalService:
    return GoalService()
