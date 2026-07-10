from __future__ import annotations

from fastapi.testclient import TestClient

from core.auth import get_auth_service as get_auth_dependency
from core.auth import require_current_user_id
from exceptions.auth import AuthTokenExpiredError
from exceptions.goals import GoalNotFoundError
from exceptions.milestones import MilestoneNotFoundError
from services.auth_service import AuthSession, AuthUser, get_auth_service
from services.calendar_service import get_calendar_service
from services.goal_service import get_goal_service
from services.milestone_service import get_milestone_service
from services.settings_service import get_settings_service


class FakeAuthService:
    # Auth router 테스트용 Supabase 대체 서비스
    def signup(self, *, email: str, password: str) -> AuthUser:
        return AuthUser(id="user-1", email=email)

    def login(self, *, email: str, password: str) -> AuthSession:
        return AuthSession(
            access_token="jwt_access_token",
            refresh_token="refresh_token",
            token_type="bearer",
            user=AuthUser(id="user-1", email=email),
        )

    def get_user(self, access_token: str) -> AuthUser:
        assert access_token == "jwt_access_token"
        return AuthUser(id="user-1", email="user@example.com")

    def logout(self, access_token: str) -> None:
        assert access_token == "jwt_access_token"


def override_auth_service() -> FakeAuthService:
    # FastAPI 의존성 override용 생성 함수
    return FakeAuthService()


class ExpiredTokenAuthService(FakeAuthService):
    # 라우터가 실제 예외 핸들러 경로를 타도록 강제로 만료 토큰 예외를 던진다.
    def get_user(self, access_token: str) -> AuthUser:
        raise AuthTokenExpiredError()


def override_expired_auth_service() -> ExpiredTokenAuthService:
    return ExpiredTokenAuthService()


def override_current_user_id() -> str:
    return "user-1"


class FakeGoalService:
    def __init__(self) -> None:
        self.goals = {
            "goal-1": {
                "id": "goal-1",
                "user_id": "user-1",
                "title": "AI engineer job preparation",
                "deadline": "2026-09-30",
                "is_recurring": False,
                "recurrence_type": None,
                "color": "#4F46E5",
                "created_at": "2026-07-01T10:00:00+09:00",
                "updated_at": "2026-07-01T10:00:00+09:00",
            }
        }
        self.deleted: list[tuple[str, str]] = []

    def list_goals(self, *, user_id: str) -> list[dict]:
        assert user_id == "user-1"
        return list(self.goals.values())

    def get_goal(self, *, goal_id: str, user_id: str) -> dict:
        assert user_id == "user-1"
        if goal_id not in self.goals:
            raise GoalNotFoundError(detail={"goal_id": goal_id})
        return self.goals[goal_id]

    def create_goal(self, *, user_id: str, body) -> dict:
        assert user_id == "user-1"
        data = {
            "id": "goal-2",
            "user_id": user_id,
            "created_at": "2026-07-02T10:00:00+09:00",
            "updated_at": "2026-07-02T10:00:00+09:00",
            **body.model_dump(mode="json"),
        }
        self.goals[data["id"]] = data
        return data

    def update_goal(self, *, goal_id: str, user_id: str, body) -> dict:
        current = self.get_goal(goal_id=goal_id, user_id=user_id)
        current.update(body.model_dump(exclude_unset=True, mode="json"))
        return current

    def delete_goal(self, *, goal_id: str, user_id: str) -> None:
        self.get_goal(goal_id=goal_id, user_id=user_id)
        self.deleted.append((goal_id, user_id))
        del self.goals[goal_id]


def override_goal_service() -> FakeGoalService:
    return FakeGoalService()


class FakeMilestoneService:
    def __init__(self) -> None:
        self.milestones = {
            "milestone-1": {
                "id": "milestone-1",
                "goal_id": "goal-1",
                "user_id": "user-1",
                "title": "이력서 초안 작성",
                "color": "#F97316",
                "scheduled_date": "2026-07-10",
                "is_completed": False,
                "created_at": "2026-07-01T10:00:00+09:00",
                "updated_at": "2026-07-01T10:00:00+09:00",
            }
        }
        self.deleted: list[tuple[str, str]] = []

    def list_goal_milestones(self, *, goal_id: str, user_id: str) -> list[dict]:
        assert goal_id == "goal-1"
        assert user_id == "user-1"
        return list(self.milestones.values())

    def list_today_milestones(self, *, user_id: str) -> list[dict]:
        assert user_id == "user-1"
        return list(self.milestones.values())

    def get_milestone(self, *, milestone_id: str, user_id: str) -> dict:
        assert user_id == "user-1"
        if milestone_id not in self.milestones:
            raise MilestoneNotFoundError(detail={"milestone_id": milestone_id})
        return self.milestones[milestone_id]

    def create_milestone(self, *, goal_id: str, user_id: str, body) -> dict:
        assert goal_id == "goal-1"
        assert user_id == "user-1"
        data = {
            "id": "milestone-2",
            "goal_id": goal_id,
            "user_id": user_id,
            "is_completed": False,
            "created_at": "2026-07-02T10:00:00+09:00",
            "updated_at": "2026-07-02T10:00:00+09:00",
            **body.model_dump(mode="json"),
        }
        self.milestones[data["id"]] = data
        return data

    def update_milestone(self, *, milestone_id: str, user_id: str, body) -> dict:
        current = self.get_milestone(milestone_id=milestone_id, user_id=user_id)
        current.update(body.model_dump(exclude_unset=True, mode="json"))
        return current

    def complete_milestone(self, *, milestone_id: str, user_id: str, body) -> dict:
        current = self.get_milestone(milestone_id=milestone_id, user_id=user_id)
        current["is_completed"] = body.is_completed
        return current

    def delete_milestone(self, *, milestone_id: str, user_id: str) -> None:
        self.get_milestone(milestone_id=milestone_id, user_id=user_id)
        self.deleted.append((milestone_id, user_id))
        del self.milestones[milestone_id]


def override_milestone_service() -> FakeMilestoneService:
    return FakeMilestoneService()


class FakeCalendarService:
    def get_month_calendar(self, *, user_id: str, year: int, month: int) -> dict:
        assert user_id == "user-1"
        assert year == 2026
        assert month == 7
        goal = {
            "id": "goal-1",
            "user_id": "user-1",
            "title": "포트폴리오 준비",
            "deadline": "2026-07-10",
            "is_recurring": False,
            "recurrence_type": None,
            "color": "#4F46E5",
            "created_at": "2026-07-01T10:00:00+09:00",
            "updated_at": "2026-07-01T10:00:00+09:00",
        }
        milestone = {
            "id": "milestone-1",
            "goal_id": "goal-1",
            "user_id": "user-1",
            "goal_title": "포트폴리오 준비",
            "title": "이력서 초안 작성",
            "color": "#F97316",
            "scheduled_date": "2026-07-10",
            "is_completed": False,
            "created_at": "2026-07-01T10:00:00+09:00",
            "updated_at": "2026-07-01T10:00:00+09:00",
        }
        return {
            "year": 2026,
            "month": 7,
            "days": [
                {
                    "date": "2026-07-10",
                    "is_today": False,
                    "goal_count": 1,
                    "milestone_count": 1,
                    "completed_milestone_count": 0,
                    "goals": [goal],
                    "milestones": [milestone],
                }
            ],
            "goals": [goal],
            "milestones": [milestone],
        }

    def get_week_calendar(self, *, user_id: str, start_date) -> dict:
        assert user_id == "user-1"
        assert start_date.isoformat() == "2026-07-08"
        goal = {
            "id": "goal-1",
            "user_id": "user-1",
            "title": "포트폴리오 준비",
            "deadline": "2026-07-10",
            "is_recurring": False,
            "recurrence_type": None,
            "color": "#4F46E5",
            "created_at": "2026-07-01T10:00:00+09:00",
            "updated_at": "2026-07-01T10:00:00+09:00",
        }
        milestone = {
            "id": "milestone-1",
            "goal_id": "goal-1",
            "user_id": "user-1",
            "goal_title": "포트폴리오 준비",
            "title": "이력서 초안 작성",
            "color": "#F97316",
            "scheduled_date": "2026-07-10",
            "is_completed": False,
            "created_at": "2026-07-01T10:00:00+09:00",
            "updated_at": "2026-07-01T10:00:00+09:00",
        }
        return {
            "start_date": "2026-07-08",
            "end_date": "2026-07-14",
            "days": [
                {
                    "date": "2026-07-10",
                    "is_today": False,
                    "goal_count": 1,
                    "milestone_count": 1,
                    "completed_milestone_count": 0,
                    "goals": [goal],
                    "milestones": [milestone],
                }
            ],
            "goals": [goal],
            "milestones": [milestone],
        }

    def get_date_calendar(self, *, user_id: str, target_date) -> dict:
        assert user_id == "user-1"
        assert target_date.isoformat() == "2026-07-10"
        return {
            "date": "2026-07-10",
            "is_today": False,
            "goal_count": 1,
            "milestone_count": 1,
            "completed_milestone_count": 0,
            "goals": [
                {
                    "id": "goal-1",
                    "user_id": "user-1",
                    "title": "포트폴리오 준비",
                    "deadline": "2026-07-10",
                    "is_recurring": False,
                    "recurrence_type": None,
                    "color": "#4F46E5",
                    "created_at": "2026-07-01T10:00:00+09:00",
                    "updated_at": "2026-07-01T10:00:00+09:00",
                }
            ],
            "milestones": [
                {
                    "id": "milestone-1",
                    "goal_id": "goal-1",
                    "goal_title": "포트폴리오 준비",
                    "title": "이력서 초안 작성",
                    "color": "#F97316",
                    "scheduled_date": "2026-07-10",
                    "is_completed": False,
                }
            ],
        }


def override_calendar_service() -> FakeCalendarService:
    return FakeCalendarService()


class FakeSettingsService:
    def __init__(self) -> None:
        self.settings = {
            "calendar_view": "month",
            "theme": "system",
            "accent_color": "#4F46E5",
            "font_family": "system",
            "font_size": 14,
            "ai_suggestion": False,
            "holiday_display": "normal",
            "week_starts_on": 1,
            "completed_milestones": True,
            "default_goal_color": "#4F46E5",
            "default_milestone_color": "#F97316",
            "language": "ko",
            "timezone": "Asia/Seoul",
        }

    def get_settings(self, *, user_id: str) -> dict:
        assert user_id == "user-1"
        return self.settings

    def update_settings(self, *, user_id: str, body) -> dict:
        assert user_id == "user-1"
        self.settings.update(body.model_dump(exclude_unset=True, exclude_none=True))
        return self.settings


def override_settings_service() -> FakeSettingsService:
    return FakeSettingsService()


def test_health_endpoints(client: TestClient, monkeypatch) -> None:
    import main

    monkeypatch.setattr(main, "check_supabase_db_health", lambda: {"row_count": 0})

    response = client.get("/health", headers={"X-Request-ID": "req-test-health"})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "req-test-health"
    assert response.json() == {"status": "ok"}

    db_response = client.get("/health/db")
    assert db_response.status_code == 200
    assert db_response.json() == {"status": "ok", "row_count": 0}


def test_health_db_returns_503_when_real_db_check_fails(client: TestClient, monkeypatch) -> None:
    import main

    def fail_db_check():
        raise RuntimeError("db unavailable")

    monkeypatch.setattr(main, "check_supabase_db_health", fail_db_check)

    response = client.get("/health/db")

    assert response.status_code == 503
    body = response.json()
    assert body["success"] is False
    assert body["error"]["detail"]["status"] == "unavailable"
    assert body["error"]["detail"]["type"] == "RuntimeError"


def test_settings_get_and_patch(client: TestClient) -> None:
    client.app.dependency_overrides[require_current_user_id] = override_current_user_id
    client.app.dependency_overrides[get_settings_service] = override_settings_service
    try:
        get_response = client.get("/settings")
        assert get_response.status_code == 200
        body = get_response.json()
        assert body["success"] is True
        assert body["data"]["calendar_view"] == "month"
        assert body["data"]["week_starts_on"] == 1

        patch_response = client.patch(
            "/settings",
            json={
                "calendar_view": "week",
                "holiday_display": "weekend_like",
                "week_starts_on": 0,
                "language": "en",
            },
        )
        assert patch_response.status_code == 200
        patched = patch_response.json()
        assert patched["data"]["calendar_view"] == "week"
        assert patched["data"]["holiday_display"] == "weekend_like"
        assert patched["data"]["week_starts_on"] == 0
        assert patched["data"]["language"] == "en"
    finally:
        client.app.dependency_overrides.clear()


def test_settings_routes_require_authentication(client: TestClient) -> None:
    response = client.get("/settings")

    assert response.status_code == 401


def test_settings_routes_reject_invalid_values(client: TestClient) -> None:
    client.app.dependency_overrides[require_current_user_id] = override_current_user_id
    client.app.dependency_overrides[get_settings_service] = override_settings_service
    try:
        response = client.patch(
            "/settings",
            json={"calendar_view": "year", "week_starts_on": 2, "language": "jp"},
        )

        assert response.status_code == 400
        assert response.json()["success"] is False
    finally:
        client.app.dependency_overrides.clear()


def test_auth_placeholder_routes(client: TestClient) -> None:
    client.app.dependency_overrides[get_auth_service] = override_auth_service
    client.app.dependency_overrides[get_auth_dependency] = override_auth_service

    signup = client.post(
        "/auth/signup",
        json={"email": "user@example.com", "password": "secret-password"},
    )
    assert signup.status_code == 200
    assert signup.json()["data"]["email"] == "user@example.com"

    login = client.post(
        "/auth/login",
        json={"email": "user@example.com", "password": "secret-password"},
    )
    assert login.status_code == 200
    assert login.json()["data"]["token_type"] == "bearer"

    logout = client.post(
        "/auth/logout",
        headers={"Authorization": "Bearer jwt_access_token"},
    )
    assert logout.status_code == 200
    assert logout.json()["success"] is True

    current_user = client.get(
        "/auth/me",
        headers={"Authorization": "Bearer jwt_access_token"},
    )
    assert current_user.status_code == 200
    assert current_user.json()["data"]["email"] == "user@example.com"

    client.app.dependency_overrides.clear()


def test_auth_routes_return_common_errors_for_token_edge_cases(
    client: TestClient,
) -> None:
    # 인증 엣지 케이스를 서비스 예외가 아니라 HTTP 응답 형태로 검증한다.
    client.app.dependency_overrides[get_auth_service] = override_auth_service
    client.app.dependency_overrides[get_auth_dependency] = override_auth_service
    try:
        missing = client.post("/auth/logout")
        assert missing.status_code == 401
        assert missing.json()["error"]["code"] == "UNAUTHORIZED"

        malformed = client.post(
            "/auth/logout",
            headers={"Authorization": "Bearer jwt_access_token extra"},
        )
        assert malformed.status_code == 401
        assert malformed.json()["error"]["code"] == "AUTH_INVALID_TOKEN"

        client.app.dependency_overrides[get_auth_service] = override_expired_auth_service
        client.app.dependency_overrides[get_auth_dependency] = override_expired_auth_service
        expired = client.get(
            "/auth/me",
            headers={"Authorization": "Bearer jwt_access_token"},
        )
        assert expired.status_code == 401
        assert expired.json()["error"]["code"] == "AUTH_TOKEN_EXPIRED"
    finally:
        client.app.dependency_overrides.clear()


def test_goal_routes_require_authentication(client: TestClient) -> None:
    response = client.get("/goals")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_goal_routes_use_current_user_and_service(client: TestClient) -> None:
    client.app.dependency_overrides[require_current_user_id] = override_current_user_id
    client.app.dependency_overrides[get_goal_service] = override_goal_service
    try:
        listed = client.get("/goals")
        assert listed.status_code == 200
        assert listed.json()["data"][0]["title"] == "AI engineer job preparation"

        created = client.post(
            "/goals",
            json={
                "title": "Review M3",
                "deadline": "2026-08-01",
                "is_recurring": False,
                "recurrence_type": None,
                "color": "#111111",
            },
        )
        assert created.status_code == 200
        assert created.json()["data"]["title"] == "Review M3"
        assert created.json()["data"]["user_id"] == "user-1"

        recurring = client.post(
            "/goals",
            json={
                "title": "Weekly planning",
                "deadline": "2026-09-01",
                "is_recurring": True,
                "recurrence_type": "weekly",
                "color": "#22C55E",
            },
        )
        assert recurring.status_code == 200
        assert recurring.json()["data"]["recurrence_type"] == "weekly"

        detail = client.get("/goals/goal-1")
        assert detail.status_code == 200
        assert detail.json()["data"]["id"] == "goal-1"

        updated = client.patch("/goals/goal-1", json={"title": "Updated"})
        assert updated.status_code == 200
        assert updated.json()["data"]["title"] == "Updated"

        missing = client.get("/goals/not-owned")
        assert missing.status_code == 404
        assert missing.json()["error"]["code"] == "GOAL_NOT_FOUND"

        deleted = client.delete("/goals/goal-1")
        assert deleted.status_code == 200
        assert deleted.json()["success"] is True
    finally:
        client.app.dependency_overrides.clear()


def test_goal_routes_validate_recurrence_settings(client: TestClient) -> None:
    client.app.dependency_overrides[require_current_user_id] = override_current_user_id
    client.app.dependency_overrides[get_goal_service] = override_goal_service
    try:
        missing_type = client.post(
            "/goals",
            json={
                "title": "잘못된 반복 목표",
                "deadline": "2026-08-01",
                "is_recurring": True,
                "recurrence_type": None,
                "color": "#111111",
            },
        )
        assert missing_type.status_code == 400
        assert missing_type.json()["error"]["code"] == "BAD_REQUEST"

        unexpected_type = client.post(
            "/goals",
            json={
                "title": "잘못된 비반복 목표",
                "deadline": "2026-08-01",
                "is_recurring": False,
                "recurrence_type": "weekly",
                "color": "#111111",
            },
        )
        assert unexpected_type.status_code == 400
        assert unexpected_type.json()["error"]["code"] == "BAD_REQUEST"

        unsupported_type = client.post(
            "/goals",
            json={
                "title": "지원하지 않는 반복 목표",
                "deadline": "2026-08-01",
                "is_recurring": True,
                "recurrence_type": "yearly",
                "color": "#111111",
            },
        )
        assert unsupported_type.status_code == 400
        assert unsupported_type.json()["error"]["code"] == "BAD_REQUEST"
    finally:
        client.app.dependency_overrides.clear()


def test_milestone_routes_require_authentication(client: TestClient) -> None:
    response = client.get("/goals/goal-1/milestones")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_milestone_routes_use_current_user_and_service(client: TestClient) -> None:
    client.app.dependency_overrides[require_current_user_id] = override_current_user_id
    client.app.dependency_overrides[get_milestone_service] = override_milestone_service
    try:
        listed = client.get("/goals/goal-1/milestones")
        assert listed.status_code == 200
        assert listed.json()["data"][0]["goal_id"] == "goal-1"

        created = client.post(
            "/goals/goal-1/milestones",
            json={
                "title": "테스트 작성",
                "color": "#222222",
                "scheduled_date": "2026-07-10",
            },
        )
        assert created.status_code == 200
        assert created.json()["data"]["title"] == "테스트 작성"
        assert created.json()["data"]["user_id"] == "user-1"

        today = client.get("/milestones/today")
        assert today.status_code == 200
        assert today.json()["data"][0]["is_completed"] is False

        detail = client.get("/milestones/milestone-1")
        assert detail.status_code == 200
        assert detail.json()["data"]["id"] == "milestone-1"

        updated = client.patch("/milestones/milestone-1", json={"title": "수정된 작업"})
        assert updated.status_code == 200
        assert updated.json()["data"]["title"] == "수정된 작업"

        completed = client.patch(
            "/milestones/milestone-1/complete",
            json={"is_completed": True},
        )
        assert completed.status_code == 200
        assert completed.json()["data"]["is_completed"] is True

        missing = client.get("/milestones/not-owned")
        assert missing.status_code == 404
        assert missing.json()["error"]["code"] == "MILESTONE_NOT_FOUND"

        deleted = client.delete("/milestones/milestone-1")
        assert deleted.status_code == 200
        assert deleted.json()["success"] is True
    finally:
        client.app.dependency_overrides.clear()


def test_calendar_routes_require_authentication(client: TestClient) -> None:
    response = client.get("/calendar/month", params={"year": 2026, "month": 7})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_calendar_routes_use_current_user_and_service(client: TestClient) -> None:
    client.app.dependency_overrides[require_current_user_id] = override_current_user_id
    client.app.dependency_overrides[get_calendar_service] = override_calendar_service
    try:
        month = client.get("/calendar/month", params={"year": 2026, "month": 7})
        assert month.status_code == 200
        month_data = month.json()["data"]
        assert month_data["year"] == 2026
        assert month_data["month"] == 7
        assert month_data["days"][0]["goal_count"] == 1
        assert month_data["days"][0]["milestones"][0]["goal_title"] == "포트폴리오 준비"

        week = client.get("/calendar/week", params={"start_date": "2026-07-08"})
        assert week.status_code == 200
        week_data = week.json()["data"]
        assert week_data["start_date"] == "2026-07-08"
        assert week_data["end_date"] == "2026-07-14"
        assert week_data["days"][0]["milestone_count"] == 1

        date = client.get("/calendar/date/2026-07-10")
        assert date.status_code == 200
        date_data = date.json()["data"]
        assert date_data["date"] == "2026-07-10"
        assert date_data["goals"][0]["id"] == "goal-1"
        assert date_data["milestones"][0]["scheduled_date"] == "2026-07-10"
    finally:
        client.app.dependency_overrides.clear()


def test_validation_error_uses_common_error_response(client: TestClient) -> None:
    client.app.dependency_overrides[require_current_user_id] = override_current_user_id
    try:
        response = client.get("/calendar/month", params={"year": 2026, "month": 13})
        assert response.status_code == 400
        body = response.json()
        assert body["success"] is False
        assert body["error"]["code"] == "BAD_REQUEST"
        assert body["request_id"].startswith("req_")
    finally:
        client.app.dependency_overrides.clear()
