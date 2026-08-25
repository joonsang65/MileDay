from __future__ import annotations

import pytest

from exceptions.settings import SettingsUpdateFailedError
from schemas.settings_schemas import SettingsUpdateRequest
from services.settings_service import DEFAULT_SETTINGS, SettingsService, clear_settings_cache


class InMemorySettingsRepository:
    def __init__(self) -> None:
        self.rows: dict[str, dict] = {}
        self.upserts: list[dict] = []
        self.updates: list[tuple[str, dict]] = []

    def get_by_user(self, *, user_id: str):
        row = self.rows.get(user_id)
        return row.copy() if row else None

    def upsert_defaults(self, *, payload: dict):
        self.upserts.append(payload.copy())
        self.rows[payload["user_id"]] = payload.copy()
        return payload.copy()

    def update(self, *, user_id: str, payload: dict):
        self.updates.append((user_id, payload.copy()))
        if user_id not in self.rows:
            return None
        self.rows[user_id].update(payload)
        return self.rows[user_id].copy()


def test_settings_service_creates_default_row_when_missing() -> None:
    clear_settings_cache()
    repository = InMemorySettingsRepository()
    service = SettingsService(repository=repository)

    result = service.get_settings(user_id="user-1")

    assert result["calendar_view"] == "month"
    assert result["week_starts_on"] == 1
    assert repository.upserts == [{"user_id": "user-1", **DEFAULT_SETTINGS}]


def test_settings_service_updates_only_given_fields() -> None:
    clear_settings_cache()
    repository = InMemorySettingsRepository()
    repository.rows["user-1"] = {"user_id": "user-1", **DEFAULT_SETTINGS}
    service = SettingsService(repository=repository)

    result = service.update_settings(
        user_id="user-1",
        body=SettingsUpdateRequest(
            calendar_view="week",
            holiday_display="hidden",
            week_starts_on=0,
            language="en",
        ),
    )

    assert result["calendar_view"] == "week"
    assert result["holiday_display"] == "hidden"
    assert result["week_starts_on"] == 0
    assert result["language"] == "en"
    assert repository.updates == [
        (
            "user-1",
            {
                "calendar_view": "week",
                "holiday_display": "hidden",
                "week_starts_on": 0,
                "language": "en",
            },
        )
    ]


def test_settings_update_request_rejects_removed_fields() -> None:
    with pytest.raises(ValueError):
        SettingsUpdateRequest.model_validate(
            {
                "calendar_view": "week",
                "accent_color": "#4F46E5",
            }
        )


def test_settings_service_raises_when_update_result_is_empty() -> None:
    clear_settings_cache()

    class FailingRepository(InMemorySettingsRepository):
        def update(self, *, user_id: str, payload: dict):
            return None

    repository = FailingRepository()
    repository.rows["user-1"] = {"user_id": "user-1", **DEFAULT_SETTINGS}
    service = SettingsService(repository=repository)

    with pytest.raises(SettingsUpdateFailedError):
        service.update_settings(
            user_id="user-1",
            body=SettingsUpdateRequest(calendar_view="week"),
        )


def test_settings_service_uses_cached_settings_for_repeated_reads() -> None:
    clear_settings_cache()
    repository = InMemorySettingsRepository()
    repository.rows["user-1"] = {"user_id": "user-1", **DEFAULT_SETTINGS}
    service = SettingsService(repository=repository)

    assert service.get_settings(user_id="user-1")["calendar_view"] == "month"
    repository.rows["user-1"]["calendar_view"] = "week"

    assert service.get_settings(user_id="user-1")["calendar_view"] == "month"
