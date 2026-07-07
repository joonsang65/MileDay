from __future__ import annotations

import pytest

from exceptions.auth import AuthInvalidCredentialsError, AuthInvalidTokenError
from exceptions.common import UnauthorizedError
from services.auth_service import AuthService


class FakeAuthClient:
    # 인증 서비스 단위 테스트용 Supabase Auth 대체 객체
    def __init__(self) -> None:
        self.sign_up_payload = None
        self.sign_in_payload = None
        self.user_token = None
        self.signed_out = False

    def sign_up(self, payload: dict[str, str]) -> dict:
        self.sign_up_payload = payload
        return {"user": {"id": "user-1", "email": payload["email"]}}

    def sign_in_with_password(self, payload: dict[str, str]) -> dict:
        self.sign_in_payload = payload
        return {
            "session": {
                "access_token": "access-token",
                "refresh_token": "refresh-token",
                "token_type": "bearer",
            },
            "user": {"id": "user-1", "email": payload["email"]},
        }

    def get_user(self, token: str) -> dict:
        self.user_token = token
        return {"user": {"id": "user-1", "email": "user@example.com"}}

    def sign_out(self) -> None:
        self.signed_out = True


class FakeSupabaseClient:
    # Supabase 클라이언트의 auth 속성만 제공
    def __init__(self) -> None:
        self.auth = FakeAuthClient()


def test_auth_service_signup_login_me_logout() -> None:
    # 회원가입, 로그인, 사용자 조회, 로그아웃 정상 흐름 검증
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
    assert client.auth.signed_out is True


def test_auth_service_maps_login_failure() -> None:
    # Supabase 로그인 실패를 도메인 예외로 변환
    class FailingAuthClient(FakeAuthClient):
        def sign_in_with_password(self, payload: dict[str, str]) -> dict:
            raise RuntimeError("bad password")

    client = FakeSupabaseClient()
    client.auth = FailingAuthClient()
    service = AuthService(client)

    with pytest.raises(AuthInvalidCredentialsError):
        service.login(email="user@example.com", password="wrong-password")


def test_auth_service_maps_token_failure() -> None:
    # Supabase 토큰 검증 실패를 도메인 예외로 변환
    class FailingAuthClient(FakeAuthClient):
        def get_user(self, token: str) -> dict:
            raise RuntimeError("invalid jwt")

    client = FakeSupabaseClient()
    client.auth = FailingAuthClient()
    service = AuthService(client)

    with pytest.raises(AuthInvalidTokenError):
        service.get_user("bad-token")


def test_get_bearer_token_validates_header() -> None:
    # 인증 헤더 누락과 형식 오류 검증
    from core.auth import get_bearer_token

    assert get_bearer_token("Bearer access-token") == "access-token"

    with pytest.raises(UnauthorizedError):
        get_bearer_token(None)

    with pytest.raises(AuthInvalidTokenError):
        get_bearer_token("Basic access-token")

    with pytest.raises(AuthInvalidTokenError):
        get_bearer_token("Bearer ")
