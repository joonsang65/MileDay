from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_endpoints(client: TestClient) -> None:
    response = client.get("/health", headers={"X-Request-ID": "req-test-health"})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "req-test-health"
    assert response.json() == {"status": "ok"}

    db_response = client.get("/health/db")
    assert db_response.status_code == 200
    assert db_response.json() == {"status": "configured"}


def test_settings_get_and_patch(client: TestClient) -> None:
    get_response = client.get("/settings")
    assert get_response.status_code == 200
    body = get_response.json()
    assert body["success"] is True
    assert body["data"]["calendar_view"] == "month"
    assert body["data"]["week_starts_on"] == 1

    patch_response = client.patch(
        "/settings",
        json={"theme": "dark", "font_size": 16, "ai_suggestion": True},
    )
    assert patch_response.status_code == 200
    patched = patch_response.json()
    assert patched["data"]["theme"] == "dark"
    assert patched["data"]["font_size"] == 16
    assert patched["data"]["ai_suggestion"] is True


def test_auth_placeholder_routes(client: TestClient) -> None:
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

    logout = client.post("/auth/logout")
    assert logout.status_code == 200
    assert logout.json()["success"] is True

    current_user = client.get("/auth/me")
    assert current_user.status_code == 200
    assert current_user.json()["data"]["email"] == "user@example.com"


def test_goal_placeholder_routes(client: TestClient) -> None:
    listed = client.get("/goals")
    assert listed.status_code == 200
    assert listed.json()["data"][0]["title"] == "AI engineer job preparation"

    created = client.post(
        "/goals",
        json={
            "title": "Review M1",
            "deadline": "2026-08-01",
            "is_recurring": False,
            "recurrence_type": None,
            "color": "#111111",
        },
    )
    assert created.status_code == 200
    assert created.json()["data"]["title"] == "Review M1"

    detail = client.get("/goals/goal-1")
    assert detail.status_code == 200
    assert detail.json()["data"]["id"] == "goal-1"

    updated = client.patch("/goals/goal-1", json={"title": "Updated"})
    assert updated.status_code == 200
    assert updated.json()["data"]["title"] == "Updated"

    deleted = client.delete("/goals/goal-1")
    assert deleted.status_code == 200
    assert deleted.json()["success"] is True


def test_milestone_placeholder_routes(client: TestClient) -> None:
    listed = client.get("/goals/goal-1/milestones")
    assert listed.status_code == 200
    assert listed.json()["data"][0]["goal_id"] == "goal-1"

    created = client.post(
        "/goals/goal-1/milestones",
        json={"title": "Write tests", "color": "#222222", "scheduled_date": "2026-07-10"},
    )
    assert created.status_code == 200
    assert created.json()["data"]["title"] == "Write tests"

    today = client.get("/milestones/today")
    assert today.status_code == 200
    assert today.json()["data"][0]["is_completed"] is False

    detail = client.get("/milestones/milestone-1")
    assert detail.status_code == 200
    assert detail.json()["data"]["id"] == "milestone-1"

    updated = client.patch("/milestones/milestone-1", json={"is_completed": True})
    assert updated.status_code == 200
    assert updated.json()["data"]["is_completed"] is True

    completed = client.patch("/milestones/milestone-1/complete", json={"is_completed": True})
    assert completed.status_code == 200
    assert completed.json()["data"]["is_completed"] is True

    deleted = client.delete("/milestones/milestone-1")
    assert deleted.status_code == 200
    assert deleted.json()["success"] is True


def test_calendar_placeholder_routes(client: TestClient) -> None:
    month = client.get("/calendar/month", params={"year": 2026, "month": 7})
    assert month.status_code == 200
    assert month.json()["data"]["year"] == 2026
    assert month.json()["data"]["month"] == 7

    date = client.get("/calendar/date/2026-07-10")
    assert date.status_code == 200
    assert date.json()["data"]["date"] == "2026-07-10"


def test_validation_error_uses_common_error_response(client: TestClient) -> None:
    response = client.get("/calendar/month", params={"year": 2026, "month": 13})
    assert response.status_code == 400
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "BAD_REQUEST"
    assert body["request_id"].startswith("req_")
