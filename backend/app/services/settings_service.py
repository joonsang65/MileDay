from __future__ import annotations

import time
from typing import Any

from exceptions.settings import SettingsNotFoundError, SettingsUpdateFailedError
from repositories.settings import SettingsRepository, get_settings_repository
from schemas.settings_schemas import SettingsUpdateRequest


DEFAULT_SETTINGS: dict[str, Any] = {
    "calendar_view": "month",
    "holiday_display": "normal",
    "week_starts_on": 0,
    "language": "ko",
    "timezone": "Asia/Seoul",
    "gemini_data_consent": False,
}
SETTINGS_CACHE_TTL_SECONDS = 60
_settings_cache: dict[str, tuple[float, dict[str, Any]]] = {}


class SettingsService:
    def __init__(self, repository: SettingsRepository | None = None) -> None:
        self.repository = repository or get_settings_repository()

    def get_settings(self, *, user_id: str) -> dict[str, Any]:
        cached = _get_cached_settings(user_id)
        if cached:
            return cached

        settings = self.repository.get_by_user(user_id=user_id)
        if settings:
            response = self._to_response(settings)
            _set_cached_settings(user_id, response)
            return response

        created = self.repository.upsert_defaults(
            payload={"user_id": user_id, **DEFAULT_SETTINGS}
        )
        if not created:
            raise SettingsNotFoundError(detail={"user_id": user_id})
        response = self._to_response(created)
        _set_cached_settings(user_id, response)
        return response

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
        response = self._to_response(updated)
        _set_cached_settings(user_id, response)
        return response

    def _to_response(self, row: dict[str, Any]) -> dict[str, Any]:
        return {key: row.get(key, value) for key, value in DEFAULT_SETTINGS.items()}


def get_settings_service() -> SettingsService:
    return SettingsService()


def _get_cached_settings(user_id: str) -> dict[str, Any] | None:
    cached = _settings_cache.get(user_id)
    if not cached:
        return None
    cached_at, settings = cached
    if time.monotonic() - cached_at > SETTINGS_CACHE_TTL_SECONDS:
        _settings_cache.pop(user_id, None)
        return None
    return dict(settings)


def _set_cached_settings(user_id: str, settings: dict[str, Any]) -> None:
    _settings_cache[user_id] = (time.monotonic(), dict(settings))


def clear_settings_cache(user_id: str | None = None) -> None:
    if user_id is None:
        _settings_cache.clear()
        return
    _settings_cache.pop(user_id, None)
