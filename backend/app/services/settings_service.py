from __future__ import annotations

from typing import Any

from exceptions.settings import SettingsNotFoundError, SettingsUpdateFailedError
from repositories.settings import SettingsRepository, get_settings_repository
from schemas.settings_schemas import SettingsUpdateRequest


DEFAULT_SETTINGS: dict[str, Any] = {
    "calendar_view": "month",
    "theme": "system",
    "accent_color": "#4F46E5",
    "font_family": "system",
    "font_size": 14,
    "ai_suggestion": False,
    "holiday_display": "normal",
    "week_starts_on": 1,
    "completed_milestones": True,
    "default_goal_color": "#4F46E5",
    "default_milestone_color": "#F97316",
    "language": "ko",
    "timezone": "Asia/Seoul",
}


class SettingsService:
    def __init__(self, repository: SettingsRepository | None = None) -> None:
        self.repository = repository or get_settings_repository()

    def get_settings(self, *, user_id: str) -> dict[str, Any]:
        settings = self.repository.get_by_user(user_id=user_id)
        if settings:
            return self._to_response(settings)

        created = self.repository.upsert_defaults(
            payload={"user_id": user_id, **DEFAULT_SETTINGS}
        )
        if not created:
            raise SettingsNotFoundError(detail={"user_id": user_id})
        return self._to_response(created)

    def update_settings(
        self,
        *,
        user_id: str,
        body: SettingsUpdateRequest,
    ) -> dict[str, Any]:
        payload = body.model_dump(exclude_unset=True, exclude_none=True)
        if not payload:
            return self.get_settings(user_id=user_id)

        current = self.repository.get_by_user(user_id=user_id)
        if not current:
            current = self.repository.upsert_defaults(
                payload={"user_id": user_id, **DEFAULT_SETTINGS}
            )
        if not current:
            raise SettingsUpdateFailedError(detail={"user_id": user_id})

        updated = self.repository.update(user_id=user_id, payload=payload)
        if not updated:
            raise SettingsUpdateFailedError(detail={"user_id": user_id})
        return self._to_response(updated)

    def _to_response(self, row: dict[str, Any]) -> dict[str, Any]:
        return {key: row.get(key, value) for key, value in DEFAULT_SETTINGS.items()}


def get_settings_service() -> SettingsService:
    return SettingsService()
