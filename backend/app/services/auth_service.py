from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any, Callable

from core.supabase import get_supabase_admin_client, get_supabase_client, reset_supabase_client
from exceptions.auth import (
    AuthEmailNotConfirmedError,
    AuthAccountDeleteFailedError,
    AuthInvalidCredentialsError,
    AuthInvalidTokenError,
    AuthLogoutFailedError,
    AuthTokenExpiredError,
    AuthUserNotFoundError,
)
from exceptions.common import SupabaseUnavailableError

try:
    from supabase import AuthRetryableError, AuthUnknownError
except ImportError:  # pragma: no cover - fallback for partial environments
    class AuthRetryableError(Exception):  # type: ignore[no-redef]
        pass

    class AuthUnknownError(Exception):  # type: ignore[no-redef]
        pass


@dataclass(frozen=True)
class AuthUser:
    id: str
    email: str


@dataclass(frozen=True)
class AuthSession:
    access_token: str
    refresh_token: str
    token_type: str
    user: AuthUser


def _get_value(source: Any, key: str) -> Any:
    if isinstance(source, dict):
        return source.get(key)
    return getattr(source, key, None)


def _safe_detail(exc: Exception) -> dict[str, str]:
    detail = {"type": exc.__class__.__name__}
    for key in ("status", "code", "message"):
        value = getattr(exc, key, None)
        if value is not None:
            detail[key] = str(value)
    if "message" not in detail and str(exc):
        detail["message"] = str(exc)
    return detail


def _auth_error_text(exc: Exception) -> str:
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
    status = _auth_error_status(exc)
    text = _auth_error_text(exc)
    return (
        isinstance(exc, (AuthRetryableError, AuthUnknownError))
        or status is None
        or status >= 500
        or "remoteprotocolerror" in text
        or "server disconnected" in text
        or "timeout" in text
    )


def _is_expired_token_error(exc: Exception) -> bool:
    text = _auth_error_text(exc)
    return "expired" in text or "jwt_expired" in text or "token_expired" in text


def _is_email_not_confirmed_error(exc: Exception) -> bool:
    text = _auth_error_text(exc)
    return (
        "email_not_confirmed" in text
        or "email not confirmed" in text
        or "email not verified" in text
    )


def _map_login_error(exc: Exception) -> Exception:
    if _is_retryable_auth_error(exc):
        return SupabaseUnavailableError(
            message="Supabase Auth login request failed.",
            detail=_safe_detail(exc),
        )
    if _is_email_not_confirmed_error(exc):
        return AuthEmailNotConfirmedError(detail=_safe_detail(exc))
    return AuthInvalidCredentialsError(detail=_safe_detail(exc))


def _map_token_error(exc: Exception) -> Exception:
    if _is_retryable_auth_error(exc):
        return SupabaseUnavailableError(
            message="Supabase Auth token verification failed.",
            detail=_safe_detail(exc),
        )
    if _is_expired_token_error(exc):
        return AuthTokenExpiredError(detail=_safe_detail(exc))
    return AuthInvalidTokenError(detail=_safe_detail(exc))


def _map_logout_error(exc: Exception) -> Exception:
    if _is_retryable_auth_error(exc):
        return SupabaseUnavailableError(
            message="Supabase Auth logout request failed.",
            detail=_safe_detail(exc),
        )
    return AuthLogoutFailedError(detail=_safe_detail(exc))


def _map_delete_account_error(exc: Exception) -> Exception:
    if _is_retryable_auth_error(exc):
        return SupabaseUnavailableError(
            message="Supabase Auth account deletion request failed.",
            detail=_safe_detail(exc),
        )
    return AuthAccountDeleteFailedError(detail=_safe_detail(exc))


class AuthService:
    def __init__(self, supabase_client: Any | None = None, supabase_admin_client: Any | None = None) -> None:
        self._uses_default_client = supabase_client is None
        self._uses_default_admin_client = supabase_admin_client is None
        self.client = supabase_client or get_supabase_client()
        self.admin_client = supabase_admin_client

    def signup(self, *, email: str, password: str) -> AuthUser:
        try:
            response = self._run_auth_operation(
                lambda: self._get_client().auth.sign_up(
                    {"email": email, "password": password},
                ),
            )
        except Exception as exc:
            raise SupabaseUnavailableError(
                message="Supabase Auth signup request failed.",
                detail=_safe_detail(exc),
            ) from exc

        user = _get_value(response, "user")
        return self._build_user(user)

    def login(self, *, email: str, password: str) -> AuthSession:
        try:
            response = self._run_auth_operation(
                lambda: self._get_client().auth.sign_in_with_password(
                    {"email": email, "password": password},
                ),
            )
        except Exception as exc:
            raise _map_login_error(exc) from exc

        session = _get_value(response, "session")
        user = _get_value(response, "user")
        if not session or not user:
            raise AuthInvalidCredentialsError()

        access_token = str(_get_value(session, "access_token") or "")
        refresh_token = str(_get_value(session, "refresh_token") or "")
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

        try:
            response = self._run_auth_operation(
                lambda: self._get_client().auth.get_user(access_token),
            )
        except Exception as exc:
            raise _map_token_error(exc) from exc

        user = _get_value(response, "user")
        return self._build_user(user)

    def logout(self, access_token: str) -> None:
        if not access_token.strip():
            raise AuthInvalidTokenError()

        self.get_user(access_token)
        try:
            self._run_auth_operation(
                lambda: self._get_client().auth.admin.sign_out(
                    access_token,
                    scope="global",
                ),
            )
        except Exception as exc:
            raise _map_logout_error(exc) from exc

    def delete_account(self, access_token: str) -> AuthUser:
        if not access_token.strip():
            raise AuthInvalidTokenError()

        user = self.get_user(access_token)
        try:
            self._run_auth_operation(
                lambda: self._get_admin_client().auth.admin.delete_user(user.id),
            )
        except Exception as exc:
            raise _map_delete_account_error(exc) from exc
        return user

    def _get_client(self) -> Any:
        if self._uses_default_client:
            self.client = get_supabase_client()
        return self.client

    def _get_admin_client(self) -> Any:
        if self._uses_default_admin_client:
            self.admin_client = get_supabase_admin_client()
        return self.admin_client

    def _run_auth_operation(self, operation: Callable[[], Any]) -> Any:
        last_error: Exception | None = None
        for attempt in range(1, 4):
            try:
                return operation()
            except Exception as exc:
                last_error = exc
                if attempt >= 3 or not _is_retryable_auth_error(exc):
                    raise
                if self._uses_default_client:
                    reset_supabase_client()
                time.sleep(0.1 if attempt == 1 else 0.3)
        if last_error:
            raise last_error
        raise RuntimeError("Supabase auth operation did not run.")

    def _build_user(self, user: Any) -> AuthUser:
        if not user:
            raise AuthUserNotFoundError()

        user_id = _get_value(user, "id")
        email = _get_value(user, "email")
        if not user_id or not email:
            raise AuthUserNotFoundError()

        return AuthUser(id=str(user_id), email=str(email))


def get_auth_service() -> AuthService:
    return AuthService()
