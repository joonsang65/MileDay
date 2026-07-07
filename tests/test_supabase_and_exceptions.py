from __future__ import annotations

import pytest


def test_supabase_client_factories(monkeypatch: pytest.MonkeyPatch) -> None:
    import core.config as config
    import core.supabase as supabase_module

    created: list[tuple[str, str]] = []

    def fake_create_client(url: str, key: str) -> dict[str, str]:
        created.append((url, key))
        return {"url": url, "key": key}

    config.get_settings.cache_clear()
    supabase_module.get_supabase_client.cache_clear()
    supabase_module.get_supabase_admin_client.cache_clear()
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service")
    monkeypatch.setattr(supabase_module, "create_client", fake_create_client)

    assert supabase_module.get_supabase_client() == {
        "url": "https://example.supabase.co",
        "key": "anon",
    }
    assert supabase_module.get_supabase_admin_client() == {
        "url": "https://example.supabase.co",
        "key": "service",
    }
    assert created == [
        ("https://example.supabase.co", "anon"),
        ("https://example.supabase.co", "service"),
    ]


def test_supabase_admin_client_requires_service_role_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import core.config as config
    import core.supabase as supabase_module

    config.get_settings.cache_clear()
    supabase_module.get_supabase_admin_client.cache_clear()
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon")
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)

    with pytest.raises(RuntimeError, match="service role key"):
        supabase_module.get_supabase_admin_client()


def test_supabase_client_factories_raise_for_missing_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import core.config as config
    import core.supabase as supabase_module

    config.get_settings.cache_clear()
    supabase_module.get_supabase_client.cache_clear()
    supabase_module.get_supabase_admin_client.cache_clear()
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)

    with pytest.raises(RuntimeError, match="Supabase URL and anon key"):
        supabase_module.get_supabase_client()

    with pytest.raises(RuntimeError, match="Supabase URL and service role key"):
        supabase_module.get_supabase_admin_client()


def test_exception_classes_expose_status_code_and_error_code() -> None:
    from exceptions.auth import (
        AuthInvalidCredentialsError,
        AuthInvalidTokenError,
        AuthLogoutFailedError,
        AuthTokenExpiredError,
        AuthUserNotFoundError,
    )
    from exceptions.common import (
        BadRequestError,
        ConflictError,
        ExternalServiceError,
        NotFoundError,
        SupabaseUnavailableError,
        UnauthorizedError,
    )
    from exceptions.goals import (
        GoalCreateFailedError,
        GoalDeleteFailedError,
        GoalNotFoundError,
        GoalUpdateFailedError,
    )
    from exceptions.milestones import (
        MilestoneCreateFailedError,
        MilestoneDeleteFailedError,
        MilestoneNotFoundError,
        MilestoneUpdateFailedError,
    )
    from exceptions.settings import (
        SettingsInvalidValueError,
        SettingsNotFoundError,
        SettingsUpdateFailedError,
    )

    exceptions = [
        BadRequestError(),
        UnauthorizedError(),
        NotFoundError(),
        ConflictError(),
        ExternalServiceError(),
        SupabaseUnavailableError(),
        AuthInvalidCredentialsError(),
        AuthInvalidTokenError(),
        AuthLogoutFailedError(),
        AuthTokenExpiredError(),
        AuthUserNotFoundError(),
        GoalNotFoundError(),
        GoalCreateFailedError(),
        GoalUpdateFailedError(),
        GoalDeleteFailedError(),
        MilestoneNotFoundError(),
        MilestoneCreateFailedError(),
        MilestoneUpdateFailedError(),
        MilestoneDeleteFailedError(),
        SettingsNotFoundError(),
        SettingsUpdateFailedError(),
        SettingsInvalidValueError(),
    ]

    assert all(exc.status_code >= 400 for exc in exceptions)
    assert all(str(exc.error_code) for exc in exceptions)
    assert all(exc.message for exc in exceptions)
