from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.supabase import get_supabase_client
from exceptions.auth import (
    AuthInvalidCredentialsError,    # 계정 인증 에러
    AuthInvalidTokenError,          # 인증 토큰 에러
    AuthLogoutFailedError,          # 로그아웃 실패 에러
    AuthTokenExpiredError,          # 인증 토큰 만료 에러
    AuthUserNotFoundError,          # 유저 정보 없음 에러
)
from exceptions.common import SupabaseUnavailableError  # supabase 요청 에러

try:
    # Supabase Auth 예외의 status/code/message를 기준으로 도메인 예외를 매핑한다.
    from supabase import AuthRetryableError, AuthUnknownError
except ImportError:  # pragma: no cover - fallback for partial environments
    class AuthRetryableError(Exception):  # type: ignore[no-redef]
        pass

    class AuthUnknownError(Exception):  # type: ignore[no-redef]
        pass


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


def _auth_error_text(exc: Exception) -> str:
    # SDK 예외는 str(exc) 대신 code/message에 핵심 사유를 담는 경우가 있다.
    parts = [
        str(getattr(exc, "code", "") or ""),
        str(getattr(exc, "message", "") or ""),
        str(exc),
    ]
    return " ".join(parts).lower()


def _auth_error_status(exc: Exception) -> int | None:
    status = getattr(exc, "status", None)
    return status if isinstance(status, int) else None


def _is_retryable_auth_error(exc: Exception) -> bool:
    # status가 없으면 사용자 입력 오류가 아니라 인프라 장애로 본다.
    status = _auth_error_status(exc)
    return (
        isinstance(exc, (AuthRetryableError, AuthUnknownError))
        or status is None
        or status >= 500
    )


def _is_expired_token_error(exc: Exception) -> bool:
    # Supabase는 토큰 만료를 error code 또는 message text로 내려줄 수 있다.
    text = _auth_error_text(exc)
    return "expired" in text or "jwt_expired" in text or "token_expired" in text


def _map_login_error(exc: Exception) -> Exception:
    # 로그인 오류는 자격 증명 오류와 인증 제공자 장애로 구분한다.
    if _is_retryable_auth_error(exc):
        return SupabaseUnavailableError(
            message="Supabase Auth login request failed.",
            detail=_safe_detail(exc),
        )
    return AuthInvalidCredentialsError(detail=_safe_detail(exc))


def _map_token_error(exc: Exception) -> Exception:
    # 토큰 검증 오류는 만료, 형식 오류/폐기, 인증 제공자 장애로 구분한다.
    if _is_retryable_auth_error(exc):
        return SupabaseUnavailableError(
            message="Supabase Auth token verification failed.",
            detail=_safe_detail(exc),
        )
    if _is_expired_token_error(exc):
        return AuthTokenExpiredError(detail=_safe_detail(exc))
    return AuthInvalidTokenError(detail=_safe_detail(exc))


def _map_logout_error(exc: Exception) -> Exception:
    # 로그아웃은 토큰 검증 성공 이후에도 별도로 실패할 수 있다.
    if _is_retryable_auth_error(exc):
        return SupabaseUnavailableError(
            message="Supabase Auth logout request failed.",
            detail=_safe_detail(exc),
        )
    return AuthLogoutFailedError(detail=_safe_detail(exc))


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
            raise _map_login_error(exc) from exc

        # 세션과 사용자 정보가 모두 있어야 로그인 성공
        session = _get_value(response, "session")
        user = _get_value(response, "user")
        if not session or not user:
            raise AuthInvalidCredentialsError()

        access_token = str(_get_value(session, "access_token") or "")
        refresh_token = str(_get_value(session, "refresh_token") or "")
        # 두 토큰이 모두 없으면 클라이언트가 사용할 수 있는 세션이 아니다.
        if not access_token or not refresh_token:
            raise AuthInvalidCredentialsError()

        return AuthSession(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type=str(_get_value(session, "token_type") or "bearer"),
            user=self._build_user(user),
        )

    def get_user(self, access_token: str) -> AuthUser:
        if not access_token.strip():
            raise AuthInvalidTokenError()

        # 접근 토큰 검증 후 사용자 조회
        try:
            response = self.client.auth.get_user(access_token)
        except Exception as exc:
            raise _map_token_error(exc) from exc

        # JWT 기준 사용자 정보 정규화
        user = _get_value(response, "user")
        return self._build_user(user)

    def logout(self, access_token: str) -> None:
        # 빈 bearer 값을 Supabase Auth에 보내지 않도록 먼저 차단한다.
        if not access_token.strip():
            raise AuthInvalidTokenError()

        # 로그아웃 전 접근 토큰 유효성 확인
        self.get_user(access_token)
        try:
            # 서버 요청에는 클라이언트 세션 저장소가 없으므로 JWT를 직접 전달한다.
            self.client.auth.admin.sign_out(access_token, scope="global")
        except Exception as exc:
            raise _map_logout_error(exc) from exc

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
