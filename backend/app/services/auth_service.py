from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.supabase import get_supabase_client
from exceptions.auth import (
    AuthInvalidCredentialsError,
    AuthInvalidTokenError,
    AuthLogoutFailedError,
    AuthUserNotFoundError,
)
from exceptions.common import SupabaseUnavailableError


@dataclass(frozen=True)
class AuthUser:
    # 인증된 사용자 최소 정보
    id: str
    email: str


@dataclass(frozen=True)
class AuthSession:
    # 로그인 성공 시 반환할 세션 정보
    access_token: str
    refresh_token: str
    token_type: str
    user: AuthUser


def _get_value(source: Any, key: str) -> Any:
    # SDK 응답 객체와 테스트 dict 응답을 같은 방식으로 조회
    if isinstance(source, dict):
        return source.get(key)
    return getattr(source, key, None)


def _safe_detail(exc: Exception) -> dict[str, str]:
    # 외부 오류 원문 대신 예외 타입만 detail에 포함
    return {"type": exc.__class__.__name__}


class AuthService:
    def __init__(self, supabase_client: Any | None = None) -> None:
        # 테스트에서는 주입 객체, 운영에서는 Supabase 클라이언트 사용
        self.client = supabase_client or get_supabase_client()

    def signup(self, *, email: str, password: str) -> AuthUser:
        # Supabase Auth 사용자 생성 요청
        try:
            response = self.client.auth.sign_up(
                {"email": email, "password": password}
            )
        except Exception as exc:
            raise SupabaseUnavailableError(
                message="Supabase Auth 회원가입 요청에 실패했습니다.",
                detail=_safe_detail(exc),
            ) from exc

        # 생성된 사용자 정보 정규화
        user = _get_value(response, "user")
        return self._build_user(user)

    def login(self, *, email: str, password: str) -> AuthSession:
        # Supabase Auth 로그인 요청
        try:
            response = self.client.auth.sign_in_with_password(
                {"email": email, "password": password}
            )
        except Exception as exc:
            raise AuthInvalidCredentialsError(detail=_safe_detail(exc)) from exc

        # 세션과 사용자 정보가 모두 있어야 로그인 성공
        session = _get_value(response, "session")
        user = _get_value(response, "user")
        if not session or not user:
            raise AuthInvalidCredentialsError()

        return AuthSession(
            access_token=str(_get_value(session, "access_token") or ""),
            refresh_token=str(_get_value(session, "refresh_token") or ""),
            token_type=str(_get_value(session, "token_type") or "bearer"),
            user=self._build_user(user),
        )

    def get_user(self, access_token: str) -> AuthUser:
        # 접근 토큰 검증 후 사용자 조회
        try:
            response = self.client.auth.get_user(access_token)
        except Exception as exc:
            raise AuthInvalidTokenError(detail=_safe_detail(exc)) from exc

        # JWT 기준 사용자 정보 정규화
        user = _get_value(response, "user")
        return self._build_user(user)

    def logout(self, access_token: str) -> None:
        # 로그아웃 전 접근 토큰 유효성 확인
        self.get_user(access_token)
        try:
            self.client.auth.sign_out()
        except Exception as exc:
            raise AuthLogoutFailedError(detail=_safe_detail(exc)) from exc

    def _build_user(self, user: Any) -> AuthUser:
        # SDK 사용자 응답을 내부 AuthUser로 변환
        if not user:
            raise AuthUserNotFoundError()

        user_id = _get_value(user, "id")
        email = _get_value(user, "email")
        if not user_id or not email:
            raise AuthUserNotFoundError()

        return AuthUser(id=str(user_id), email=str(email))


def get_auth_service() -> AuthService:
    # FastAPI 의존성 주입용 인증 서비스 생성
    return AuthService()
