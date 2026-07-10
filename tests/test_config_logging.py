from __future__ import annotations

import logging
from pathlib import Path

import pytest


def test_settings_loads_env_and_normalizes_paths(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from core.config import BASE_DIR, get_settings

    get_settings.cache_clear()
    monkeypatch.setenv("ENV", "test")
    monkeypatch.setenv("APP_NAME", "ConfiguredName")
    monkeypatch.setenv("API_PORT", "9000")
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon")
    monkeypatch.setenv("LOG_DIR", "relative-logs")
    monkeypatch.setenv("CORS_ORIGINS", " http://localhost:5173, ,http://localhost:3000 ")

    settings = get_settings()

    assert settings.env == "test"
    assert settings.app_name == "ConfiguredName"
    assert settings.api_port == 9000
    assert settings.cors_origins == ["http://localhost:5173", "http://localhost:3000"]
    assert settings.log_dir == BASE_DIR / "relative-logs"
    assert settings.is_supabase_configured is True

    get_settings.cache_clear()
    monkeypatch.setenv("LOG_DIR", str(tmp_path))
    monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)
    settings_without_key = get_settings()
    assert settings_without_key.log_dir == tmp_path
    assert settings_without_key.is_supabase_configured is False


def test_integration_test_settings_require_safe_identity(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from core.config import get_settings

    get_settings.cache_clear()
    monkeypatch.setenv("ENABLE_INTEGRATION_TESTS", "true")
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service")
    monkeypatch.setenv("TEST_EMAIL", "test+integration@example.com")
    monkeypatch.setenv("TEST_PASSWORD", "password")
    monkeypatch.setenv("TEST_USER_ID", "11111111-1111-1111-1111-111111111111")
    monkeypatch.setenv("TEST_TITLE_PREFIX", "[TEST]")
    monkeypatch.setenv("LOG_DIR", str(tmp_path))

    settings = get_settings()

    assert settings.integration_tests_enabled is True
    assert settings.integration_test_email == "test+integration@example.com"
    assert settings.integration_test_title_prefix == "[TEST]"


def test_integration_test_settings_reject_unsafe_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from core.config import get_settings

    get_settings.cache_clear()
    monkeypatch.setenv("ENABLE_INTEGRATION_TESTS", "true")
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service")
    monkeypatch.setenv("TEST_EMAIL", "real-user@example.com")
    monkeypatch.setenv("TEST_PASSWORD", "password")
    monkeypatch.setenv("TEST_USER_ID", "11111111-1111-1111-1111-111111111111")
    monkeypatch.setenv("TEST_TITLE_PREFIX", "[TEST]")

    with pytest.raises(ValueError, match="test-only account"):
        get_settings()

    get_settings.cache_clear()
    monkeypatch.setenv("TEST_EMAIL", "test+integration@example.com")
    monkeypatch.setenv("TEST_TITLE_PREFIX", "M1")

    with pytest.raises(ValueError, match="must start with"):
        get_settings()


def test_configure_logging_is_idempotent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from core.config import get_settings
    from core.logging import configure_logging

    get_settings.cache_clear()
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("LOG_RETENTION_DAYS", "2")

    configure_logging()
    configure_logging()

    root_logger = logging.getLogger()
    assert root_logger.level == logging.DEBUG
    assert len(root_logger.handlers) == 2
    assert (tmp_path / "logs").exists()


def test_mask_sensitive_data_recursively() -> None:
    from core.logging import mask_email, mask_sensitive_data

    assert mask_email("nobody") == "nobody"
    assert mask_email("a@example.com") == "a***@example.com"
    assert mask_email("tester@example.com") == "te***@example.com"

    masked = mask_sensitive_data(
        {
            "email": "tester@example.com",
            "password": "secret",
            "Authorization": "Bearer token",
            "profile": {
                "access_token": "access",
                "refresh_token": "refresh",
                "ai_prompt": "very long prompt",
            },
            "items": [{"token": "nested"}],
        }
    )

    assert masked["email"] == "te***@example.com"
    assert masked["password"] == "[MASKED]"
    assert masked["Authorization"] == "[MASKED]"
    assert masked["profile"]["access_token"] == "[MASKED]"
    assert masked["profile"]["refresh_token"] == "[MASKED]"
    assert masked["profile"]["ai_prompt"] == "[OMITTED]"
    assert masked["items"][0]["token"] == "[MASKED]"


def test_request_context_filter_defaults_and_context_values() -> None:
    from core.logging import (
        RequestContextFilter,
        duration_context,
        path_context,
        request_id_context,
        user_id_context,
    )

    record = logging.LogRecord("test", logging.INFO, __file__, 1, "message", (), None)
    assert RequestContextFilter().filter(record) is True
    assert record.request_id == "-"
    assert record.user_id == "-"
    assert record.path == "-"
    assert record.duration_ms == "-"

    request_token = request_id_context.set("req-1")
    user_token = user_id_context.set("user-1")
    path_token = path_context.set("/health")
    duration_token = duration_context.set(12.345)
    try:
        contextual = logging.LogRecord("test", logging.INFO, __file__, 1, "message", (), None)
        RequestContextFilter().filter(contextual)
        assert contextual.request_id == "req-1"
        assert contextual.user_id == "user-1"
        assert contextual.path == "/health"
        assert contextual.duration_ms == "12.35"
    finally:
        request_id_context.reset(request_token)
        user_id_context.reset(user_token)
        path_context.reset(path_token)
        duration_context.reset(duration_token)
