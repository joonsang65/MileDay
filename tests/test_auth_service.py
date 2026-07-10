from __future__ import annotations

import pytest

from exceptions.auth import (
    AuthInvalidCredentialsError,
    AuthInvalidTokenError,
    AuthLogoutFailedError,
    AuthTokenExpiredError,
    AuthUserNotFoundError,
)
from exceptions.common import SupabaseUnavailableError, UnauthorizedError
from services.auth_service import AuthService


class FakeAuthError(Exception):
    # Supabase Auth 예외가 노출하는 status/code/message 필드를 흉내 낸다.
    def __init__(
        self,
        message: str,
        *,
        status: int | None = None,
        code: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status = status
        self.code = code


class FakeAdminAuthClient:
    # 요청 단위 서버에는 지속되는 Supabase 클라이언트 세션이 없으므로
    # AuthService는 admin.sign_out을 직접 호출한다.
    def __init__(self) -> None:
        self.sign_out_token = None
        self.sign_out_scope = None
        self.sign_out_error: Exception | None = None

    def sign_out(self, jwt: str, scope: str = "global") -> None:
        self.sign_out_token = jwt
        self.sign_out_scope = scope
        if self.sign_out_error:
            raise self.sign_out_error


class FakeAuthClient:
    # AuthService가 사용하는 최소 Supabase Auth 표면만 제공한다.
    def __init__(self) -> None:
        self.admin = FakeAdminAuthClient()
        self.sign_up_payload = None
        self.sign_in_payload = None
        self.user_token = None
        self.login_response: dict | None = None
        self.get_user_response: dict | None = None
        self.login_error: Exception | None = None
        self.get_user_error: Exception | None = None

    def sign_up(self, payload: dict[str, str]) -> dict:
        self.sign_up_payload = payload
        return {"user": {"id": "user-1", "email": payload["email"]}}

    def sign_in_with_password(self, payload: dict[str, str]) -> dict:
        self.sign_in_payload = payload
        if self.login_error:
            raise self.login_error
        return self.login_response or {
            "session": {
                "access_token": "access-token",
                "refresh_token": "refresh-token",
                "token_type": "bearer",
            },
            "user": {"id": "user-1", "email": payload["email"]},
        }

    def get_user(self, token: str) -> dict:
        self.user_token = token
        if self.get_user_error:
            raise self.get_user_error
        return self.get_user_response or {
            "user": {"id": "user-1", "email": "user@example.com"}
        }


class FakeSupabaseClient:
    def __init__(self) -> None:
        self.auth = FakeAuthClient()


def test_auth_service_signup_login_me_logout() -> None:
    # 정상 흐름에서 응답 정규화와 admin 로그아웃 직접 호출을 검증한다.
    client = FakeSupabaseClient()
    service = AuthService(client)

    user = service.signup(email="user@example.com", password="password123")
    assert user.id == "user-1"
    assert client.auth.sign_up_payload == {
        "email": "user@example.com",
        "password": "password123",
    }

    session = service.login(email="user@example.com", password="password123")
    assert session.access_token == "access-token"
    assert session.refresh_token == "refresh-token"
    assert session.user.email == "user@example.com"

    current_user = service.get_user("access-token")
    assert current_user.id == "user-1"
    assert client.auth.user_token == "access-token"

    service.logout("access-token")
    assert client.auth.admin.sign_out_token == "access-token"
    assert client.auth.admin.sign_out_scope == "global"


def test_login_maps_invalid_credentials_and_unavailable_errors() -> None:
    # 4xx 인증 오류는 자격 증명 오류로, 5xx 오류는 인증 제공자 장애로 매핑한다.
    client = FakeSupabaseClient()
    service = AuthService(client)

    client.auth.login_error = FakeAuthError(
        "invalid login credentials",
        status=400,
        code="invalid_credentials",
    )
    with pytest.raises(AuthInvalidCredentialsError):
        service.login(email="user@example.com", password="wrong-password")

    client.auth.login_error = FakeAuthError("service unavailable", status=503)
    with pytest.raises(SupabaseUnavailableError):
        service.login(email="user@example.com", password="password123")


def test_login_rejects_missing_session_user_or_tokens() -> None:
    # 사용 가능한 세션이 빠진 Supabase 응답은 성공으로 반환하지 않는다.
    client = FakeSupabaseClient()
    service = AuthService(client)

    for response in (
        {"session": None, "user": {"id": "user-1", "email": "user@example.com"}},
        {"session": {"access_token": "", "refresh_token": "refresh-token"}, "user": {}},
        {
            "session": {"access_token": "access-token", "refresh_token": ""},
            "user": {"id": "user-1", "email": "user@example.com"},
        },
    ):
        client.auth.login_response = response
        with pytest.raises(AuthInvalidCredentialsError):
            service.login(email="user@example.com", password="password123")


def test_get_user_maps_invalid_expired_and_unavailable_tokens() -> None:
    # 토큰 오류 매핑이 만료, 무효, 상위 서비스 장애를 구분하는지 검증한다.
    client = FakeSupabaseClient()
    service = AuthService(client)

    client.auth.get_user_error = FakeAuthError("bad jwt", status=401, code="bad_jwt")
    with pytest.raises(AuthInvalidTokenError):
        service.get_user("bad-token")

    client.auth.get_user_error = FakeAuthError(
        "jwt expired",
        status=401,
        code="jwt_expired",
    )
    with pytest.raises(AuthTokenExpiredError):
        service.get_user("expired-token")

    client.auth.get_user_error = FakeAuthError("upstream timeout", status=503)
    with pytest.raises(SupabaseUnavailableError):
        service.get_user("access-token")


def test_get_user_rejects_empty_or_missing_user_data() -> None:
    # 검증된 토큰이어도 사용자 payload가 불완전하면 사용자 없음으로 처리한다.
    client = FakeSupabaseClient()
    service = AuthService(client)

    with pytest.raises(AuthInvalidTokenError):
        service.get_user("   ")

    for response in (
        {"user": None},
        {"user": {"id": "", "email": "user@example.com"}},
        {"user": {"id": "user-1", "email": ""}},
    ):
        client.auth.get_user_response = response
        with pytest.raises(AuthUserNotFoundError):
            service.get_user("access-token")


def test_logout_maps_admin_sign_out_failures() -> None:
    # 로그아웃은 토큰을 먼저 검증한 뒤 admin sign-out 실패를 매핑한다.
    client = FakeSupabaseClient()
    service = AuthService(client)

    with pytest.raises(AuthInvalidTokenError):
        service.logout("")

    client.auth.admin.sign_out_error = FakeAuthError("logout failed", status=400)
    with pytest.raises(AuthLogoutFailedError):
        service.logout("access-token")

    client.auth.admin.sign_out_error = FakeAuthError("auth unavailable", status=503)
    with pytest.raises(SupabaseUnavailableError):
        service.logout("access-token")


def test_get_bearer_token_validates_header() -> None:
    # 헤더 파싱은 정확한 두 부분의 Bearer 형식만 허용한다.
    from core.auth import get_bearer_token

    assert get_bearer_token("Bearer access-token") == "access-token"
    assert get_bearer_token("bearer access-token") == "access-token"

    with pytest.raises(UnauthorizedError):
        get_bearer_token(None)

    with pytest.raises(AuthInvalidTokenError):
        get_bearer_token("Basic access-token")

    with pytest.raises(AuthInvalidTokenError):
        get_bearer_token("Bearer ")

    with pytest.raises(AuthInvalidTokenError):
        get_bearer_token("Bearer access-token extra")
