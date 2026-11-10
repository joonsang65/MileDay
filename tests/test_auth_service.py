from __future__ import annotations

from types import SimpleNamespace

import pytest

from exceptions.auth import (
    AuthEmailNotConfirmedError,
    AuthAccountDeleteFailedError,
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
        self.deleted_user_id = None
        self.sign_out_error: Exception | None = None
        self.delete_user_error: Exception | None = None

    def sign_out(self, jwt: str, scope: str = "global") -> None:
        self.sign_out_token = jwt
        self.sign_out_scope = scope
        if self.sign_out_error:
            raise self.sign_out_error

    def delete_user(self, user_id: str) -> None:
        self.deleted_user_id = user_id
        if self.delete_user_error:
            raise self.delete_user_error


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
        self.refresh_token = None
        self.refresh_response: dict | None = None
        self.refresh_error: Exception | None = None
        self.refresh_calls = 0
        self.close_calls = 0
        self.get_user_error: Exception | None = None
        self.get_user_errors: list[Exception] = []

    def close(self) -> None:
        self.close_calls += 1

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
                "expires_at": 1800000000,
            },
            "user": {"id": "user-1", "email": payload["email"]},
        }

    def refresh_session(self, refresh_token: str) -> dict:
        self.refresh_token = refresh_token
        self.refresh_calls += 1
        if self.refresh_error:
            raise self.refresh_error
        return (
            self.refresh_response
            if self.refresh_response is not None
            else {
                "session": {
                    "access_token": "new-access-token",
                    "refresh_token": "rotated-refresh-token",
                    "token_type": "bearer",
                    "expires_at": 1800003600,
                },
                "user": {"id": "user-1", "email": "user@example.com"},
            }
        )

    def get_user(self, token: str) -> dict:
        self.user_token = token
        if self.get_user_errors:
            raise self.get_user_errors.pop(0)
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
    assert session.expires_at == 1800000000
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

    client.auth.login_error = FakeAuthError(
        "email not confirmed",
        status=400,
        code="email_not_confirmed",
    )
    with pytest.raises(AuthEmailNotConfirmedError):
        service.login(email="user@example.com", password="password123")

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


def test_get_user_retries_retryable_auth_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = FakeSupabaseClient()
    service = AuthService(client)
    sleeps: list[float] = []
    client.auth.get_user_errors = [
        FakeAuthError("RemoteProtocolError: server disconnected", status=503),
    ]
    monkeypatch.setattr("services.auth_service.time.sleep", sleeps.append)

    user = service.get_user("access-token")

    assert user.id == "user-1"
    assert sleeps == [0.1]


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


def test_delete_account_verifies_token_and_deletes_auth_user() -> None:
    client = FakeSupabaseClient()
    service = AuthService(client, supabase_admin_client=client)

    user = service.delete_account("access-token")

    assert user.id == "user-1"
    assert client.auth.user_token == "access-token"
    assert client.auth.admin.deleted_user_id == "user-1"


def test_delete_account_maps_admin_delete_failures() -> None:
    client = FakeSupabaseClient()
    service = AuthService(client, supabase_admin_client=client)

    with pytest.raises(AuthInvalidTokenError):
        service.delete_account("")

    client.auth.admin.delete_user_error = FakeAuthError("delete failed", status=400)
    with pytest.raises(AuthAccountDeleteFailedError):
        service.delete_account("access-token")

    client.auth.admin.delete_user_error = FakeAuthError("auth unavailable", status=503)
    with pytest.raises(SupabaseUnavailableError):
        service.delete_account("access-token")


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


def test_refresh_returns_rotated_session_and_supports_rollover() -> None:
    client = FakeSupabaseClient()
    service = AuthService(client)

    session = service.refresh("refresh-token")

    assert client.auth.refresh_token == "refresh-token"
    assert session.access_token == "new-access-token"
    assert session.refresh_token == "rotated-refresh-token"
    assert session.expires_at == 1800003600
    assert session.token_type == "bearer"
    assert session.user.id == "user-1"

    service.refresh(session.refresh_token)
    assert client.auth.refresh_token == "rotated-refresh-token"


@pytest.mark.parametrize("token", ["", " \t\n", None, 123])
def test_refresh_rejects_blank_or_invalid_input_without_calling_supabase(token) -> None:
    client = FakeSupabaseClient()
    with pytest.raises(AuthInvalidTokenError):
        AuthService(client).refresh(token)
    assert client.auth.refresh_calls == 0


@pytest.mark.parametrize(
    ("error", "expected", "calls"),
    [
        (
            FakeAuthError(
                "Invalid Refresh Token", status=400, code="refresh_token_not_found"
            ),
            AuthInvalidTokenError,
            1,
        ),
        (
            FakeAuthError(
                "Already Used", status=400, code="refresh_token_already_used"
            ),
            AuthInvalidTokenError,
            1,
        ),
        (FakeAuthError("Refresh token expired", status=401), AuthTokenExpiredError, 1),
        (FakeAuthError("Service unavailable", status=503), SupabaseUnavailableError, 3),
        (RuntimeError("Server disconnected"), SupabaseUnavailableError, 3),
    ],
)
def test_refresh_maps_provider_errors(error, expected, calls, monkeypatch) -> None:
    client = FakeSupabaseClient()
    client.auth.refresh_error = error
    monkeypatch.setattr("services.auth_service.time.sleep", lambda _: None)

    with pytest.raises(expected):
        AuthService(client).refresh("refresh-token")

    assert client.auth.refresh_calls == calls


@pytest.mark.parametrize(
    "response",
    [
        {},
        {"session": None, "user": {"id": "user-1", "email": "user@example.com"}},
        {
            "session": {"access_token": "access", "refresh_token": "refresh"},
            "user": None,
        },
        {
            "session": {"access_token": "", "refresh_token": "refresh"},
            "user": {"id": "user-1", "email": "user@example.com"},
        },
        {
            "session": {"access_token": "access", "refresh_token": " "},
            "user": {"id": "user-1", "email": "user@example.com"},
        },
        {
            "session": {"access_token": 123, "refresh_token": "refresh"},
            "user": {"id": "user-1", "email": "user@example.com"},
        },
        {
            "session": {"access_token": "access", "refresh_token": "refresh"},
            "user": {"id": "user-1"},
        },
        {
            "session": {
                "access_token": "access",
                "refresh_token": "refresh",
                "expires_at": -1,
            },
            "user": {"id": "user-1", "email": "user@example.com"},
        },
    ],
)
def test_refresh_rejects_incomplete_provider_responses(response) -> None:
    client = FakeSupabaseClient()
    client.auth.refresh_response = response

    with pytest.raises(AuthInvalidTokenError):
        AuthService(client).refresh("refresh-token")


def test_session_normalization_supports_sdk_objects_and_relative_expiry(
    monkeypatch,
) -> None:
    client = FakeSupabaseClient()
    client.auth.login_response = SimpleNamespace(
        session=SimpleNamespace(
            access_token="access-token",
            refresh_token="refresh-token",
            expires_in=3600,
        ),
        user=SimpleNamespace(id="user-1", email="user@example.com"),
    )
    monkeypatch.setattr("services.auth_service.time.time", lambda: 1800000000)

    session = AuthService(client).login(
        email="user@example.com", password="password123"
    )

    assert session.expires_at == 1800003600
    assert session.token_type == "bearer"


def test_legacy_session_payload_and_constructor_remain_compatible() -> None:
    from services.auth_service import AuthSession, AuthUser

    session = AuthSession(
        "access", "refresh", "bearer", AuthUser("user-1", "user@example.com")
    )
    assert session.expires_at is None

    client = FakeSupabaseClient()
    client.auth.login_response = {
        "session": {"access_token": "access", "refresh_token": "refresh"},
        "user": {"id": "user-1", "email": "user@example.com"},
    }
    assert (
        AuthService(client)
        .login(email="user@example.com", password="password123")
        .expires_at
        is None
    )


def test_auth_services_do_not_share_mutable_clients(monkeypatch) -> None:
    clients: list[FakeSupabaseClient] = []

    def create_client():
        client = FakeSupabaseClient()
        clients.append(client)
        return client

    monkeypatch.setattr(
        "services.auth_service.create_supabase_auth_client", create_client
    )
    first = AuthService()
    second = AuthService()

    first.login(email="first@example.com", password="password123")
    second.refresh("second-refresh-token")
    first.get_user("first-access-token")

    assert len(clients) == 2
    assert first.client is clients[0]
    assert second.client is clients[1]
    assert clients[0].auth.refresh_token is None
    assert clients[1].auth.sign_in_payload is None
    assert clients[1].auth.user_token is None


def test_refresh_retry_replaces_only_the_request_client(monkeypatch) -> None:
    first = FakeSupabaseClient()
    first.auth.refresh_error = FakeAuthError("unavailable", status=503)
    second = FakeSupabaseClient()
    clients = iter([first, second])
    monkeypatch.setattr(
        "services.auth_service.create_supabase_auth_client", lambda: next(clients)
    )
    monkeypatch.setattr("services.auth_service.time.sleep", lambda _: None)

    session = AuthService().refresh("refresh-token")

    assert session.refresh_token == "rotated-refresh-token"
    assert first.auth.refresh_calls == second.auth.refresh_calls == 1
    assert first.auth.refresh_token == second.auth.refresh_token == "refresh-token"
    assert first.auth.close_calls == 1
    assert second.auth.close_calls == 0


def test_closing_service_does_not_close_injected_clients() -> None:
    client = FakeSupabaseClient()
    service = AuthService(client, supabase_admin_client=client)
    service.close()
    assert client.auth.close_calls == 0


def test_dependency_closes_owned_client_when_request_raises(monkeypatch) -> None:
    from services.auth_service import get_auth_service

    client = FakeSupabaseClient()
    admin_client = FakeSupabaseClient()
    monkeypatch.setattr(
        "services.auth_service.create_supabase_auth_client", lambda: client
    )
    dependency = get_auth_service()
    service = next(dependency)
    service.admin_client = admin_client
    service.login(email="user@example.com", password="password123")

    with pytest.raises(RuntimeError, match="request failed"):
        dependency.throw(RuntimeError("request failed"))

    assert client.auth.close_calls == 1
    assert admin_client.auth.close_calls == 0
    service.close()
    assert client.auth.close_calls == 1


def test_auth_client_factory_disables_persistence_and_auto_refresh(monkeypatch) -> None:
    import core.supabase as supabase_module

    created = []

    def fake_create_client(url, key, *, options):
        client = FakeSupabaseClient()
        created.append((url, key, options, client))
        return client

    monkeypatch.setattr(
        supabase_module,
        "get_settings",
        lambda: SimpleNamespace(
            supabase_url="https://example.supabase.co",
            supabase_anon_key="anon",
        ),
    )
    monkeypatch.setattr(supabase_module, "create_client", fake_create_client)

    first = supabase_module.create_supabase_auth_client()
    second = supabase_module.create_supabase_auth_client()

    assert first is not second
    assert len(created) == 2
    for url, key, options, _ in created:
        assert url == "https://example.supabase.co"
        assert key == "anon"
        assert options.persist_session is False
        assert options.auto_refresh_token is False


@pytest.mark.parametrize(
    ("url", "key"), [("", "anon"), ("https://example.supabase.co", "")]
)
def test_auth_client_factory_requires_anon_config(monkeypatch, url, key) -> None:
    import core.supabase as supabase_module

    monkeypatch.setattr(
        supabase_module,
        "get_settings",
        lambda: SimpleNamespace(
            supabase_url=url,
            supabase_anon_key=key,
        ),
    )
    with pytest.raises(RuntimeError, match="Supabase URL and anon key"):
        supabase_module.create_supabase_auth_client()
