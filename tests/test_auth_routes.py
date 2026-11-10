from __future__ import annotations

from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from supabase import AuthApiError

from core.config import get_settings
from services.auth_service import AuthService, get_auth_service


@pytest.fixture
def auth_provider(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    provider = Mock()
    provider.auth.sign_in_with_password.return_value = {
        "session": {
            "access_token": "login-access",
            "refresh_token": "login-refresh",
            "token_type": "bearer",
            "expires_at": 1800000000,
        },
        "user": {"id": "user-1", "email": "user@example.com"},
    }
    provider.auth.refresh_session.return_value = {
        "session": {
            "access_token": "rotated-access",
            "refresh_token": "rotated-refresh",
            "token_type": "bearer",
            "expires_at": 1800003600,
        },
        "user": {"id": "user-1", "email": "user@example.com"},
    }
    client.app.dependency_overrides[get_auth_service] = lambda: AuthService(provider)
    monkeypatch.setattr("services.auth_service.time.sleep", lambda _: None)
    try:
        yield provider
    finally:
        client.app.dependency_overrides.clear()


def test_login_and_refresh_return_session_expiry_and_rotated_tokens(
    client: TestClient,
    auth_provider: Mock,
) -> None:
    login = client.post(
        "/auth/login",
        json={"email": "user@example.com", "password": "password123"},
    )
    assert login.status_code == 200
    assert login.json()["data"] == {
        "access_token": "login-access",
        "refresh_token": "login-refresh",
        "expires_at": 1800000000,
        "token_type": "bearer",
        "user": {"id": "user-1", "email": "user@example.com"},
    }

    refresh = client.post(
        "/auth/refresh",
        json={"refresh_token": login.json()["data"]["refresh_token"]},
        headers={"Authorization": "Bearer expired-access-token"},
    )
    assert refresh.status_code == 200
    assert refresh.json() == {
        "success": True,
        "data": {
            "access_token": "rotated-access",
            "refresh_token": "rotated-refresh",
            "expires_at": 1800003600,
            "token_type": "bearer",
            "user": {"id": "user-1", "email": "user@example.com"},
        },
    }
    auth_provider.auth.refresh_session.assert_called_once_with("login-refresh")

    rollover = client.post(
        "/auth/refresh",
        json={"refresh_token": refresh.json()["data"]["refresh_token"]},
    )
    assert rollover.status_code == 200
    auth_provider.auth.refresh_session.assert_called_with("rotated-refresh")


@pytest.mark.parametrize(
    "body",
    [
        None,
        {},
        {"refresh_token": ""},
        {"refresh_token": " \t\n"},
        {"refresh_token": None},
        {"refresh_token": 123},
        {"refresh_token": []},
    ],
)
def test_refresh_rejects_invalid_body_with_common_validation_error(
    client: TestClient,
    auth_provider: Mock,
    body,
) -> None:
    response = client.post("/auth/refresh", json=body)

    assert response.status_code == 400
    assert response.json()["success"] is False
    assert response.json()["error"]["code"] == "BAD_REQUEST"
    assert response.json()["request_id"]
    auth_provider.auth.refresh_session.assert_not_called()


def test_refresh_normalizes_surrounding_whitespace(
    client: TestClient,
    auth_provider: Mock,
) -> None:
    response = client.post("/auth/refresh", json={"refresh_token": "  refresh-token\n"})

    assert response.status_code == 200
    auth_provider.auth.refresh_session.assert_called_once_with("refresh-token")


@pytest.mark.parametrize(
    ("message", "provider_status", "provider_code", "status", "code", "attempts"),
    [
        (
            "Invalid refresh token",
            400,
            "refresh_token_not_found",
            401,
            "AUTH_INVALID_TOKEN",
            1,
        ),
        (
            "Refresh token already used",
            400,
            "refresh_token_already_used",
            401,
            "AUTH_INVALID_TOKEN",
            1,
        ),
        ("Refresh token expired", 401, "session_expired", 401, "AUTH_TOKEN_EXPIRED", 1),
        ("Auth unavailable", 503, None, 502, "SUPABASE_UNAVAILABLE", 3),
    ],
)
def test_refresh_returns_consistent_provider_errors(
    client: TestClient,
    auth_provider: Mock,
    message,
    provider_status,
    provider_code,
    status,
    code,
    attempts,
) -> None:
    auth_provider.auth.refresh_session.side_effect = AuthApiError(
        message,
        provider_status,
        provider_code,
    )

    response = client.post("/auth/refresh", json={"refresh_token": "refresh-token"})

    assert response.status_code == status
    assert response.json()["success"] is False
    assert response.json()["error"]["code"] == code
    assert response.json()["request_id"]
    assert auth_provider.auth.refresh_session.call_count == attempts


def test_refresh_rejects_missing_provider_session(
    client: TestClient,
    auth_provider: Mock,
) -> None:
    auth_provider.auth.refresh_session.return_value = {"session": None, "user": None}

    response = client.post("/auth/refresh", json={"refresh_token": "refresh-token"})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_INVALID_TOKEN"


@pytest.mark.parametrize(
    ("provider_status", "provider_code", "status", "code"),
    [
        (400, "invalid_credentials", 401, "AUTH_INVALID_CREDENTIALS"),
        (400, "email_not_confirmed", 401, "AUTH_EMAIL_NOT_CONFIRMED"),
        (503, None, 502, "SUPABASE_UNAVAILABLE"),
    ],
)
def test_login_errors_use_common_envelope(
    client: TestClient,
    auth_provider: Mock,
    provider_status,
    provider_code,
    status,
    code,
) -> None:
    auth_provider.auth.sign_in_with_password.side_effect = AuthApiError(
        provider_code or "Auth unavailable",
        provider_status,
        provider_code,
    )

    response = client.post(
        "/auth/login",
        json={"email": "user@example.com", "password": "password123"},
    )

    assert response.status_code == status
    assert response.json()["success"] is False
    assert response.json()["error"]["code"] == code
    assert response.json()["request_id"]


@pytest.mark.parametrize("fails", [False, True])
def test_request_dependency_closes_auth_connections_on_success_and_failure(
    client: TestClient,
    auth_provider: Mock,
    monkeypatch: pytest.MonkeyPatch,
    fails: bool,
) -> None:
    client.app.dependency_overrides.pop(get_auth_service)
    monkeypatch.setattr(
        "services.auth_service.create_supabase_auth_client",
        lambda: auth_provider,
    )
    if fails:
        auth_provider.auth.refresh_session.side_effect = AuthApiError(
            "Invalid refresh token",
            400,
            "refresh_token_not_found",
        )

    response = client.post("/auth/refresh", json={"refresh_token": "refresh-token"})

    assert response.status_code == (401 if fails else 200)
    auth_provider.auth.close.assert_called_once_with()


def test_auth_success_and_error_logs_do_not_contain_raw_tokens_or_passwords(
    client: TestClient,
    auth_provider: Mock,
) -> None:
    password = "private-password-log-marker"
    refresh_token = "private-refresh-log-marker"
    authorization = "private-access-log-marker"
    auth_provider.auth.sign_in_with_password.return_value["session"].update(
        access_token=authorization,
        refresh_token=refresh_token,
    )
    auth_provider.auth.refresh_session.return_value["session"].update(
        access_token="private-rotated-access-log-marker",
        refresh_token="private-rotated-refresh-log-marker",
    )

    for fails in (False, True):
        if fails:
            auth_provider.auth.sign_in_with_password.side_effect = AuthApiError(
                f"Invalid credentials: {password}",
                400,
                "invalid_credentials",
            )
            auth_provider.auth.refresh_session.side_effect = AuthApiError(
                f"Invalid refresh token: {refresh_token}",
                400,
                "refresh_token_not_found",
            )
        login = client.post(
            "/auth/login",
            json={"email": "user@example.com", "password": password},
        )
        refresh = client.post(
            "/auth/refresh",
            json={"refresh_token": refresh_token},
            headers={"Authorization": f"Bearer {authorization}"},
        )
        assert login.status_code == refresh.status_code == (401 if fails else 200)

    invalid = client.post(
        "/auth/refresh", json={"refresh_token": {"secret": refresh_token}}
    )
    assert invalid.status_code == 400
    logs = (get_settings().log_dir / "mileday.log").read_text(encoding="utf-8")
    assert "application error" in logs
    for secret in (
        password,
        refresh_token,
        authorization,
        "private-rotated-access-log-marker",
        "private-rotated-refresh-log-marker",
    ):
        assert secret not in logs
