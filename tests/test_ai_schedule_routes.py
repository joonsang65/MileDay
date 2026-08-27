from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient

from core.auth import require_current_user_id
from services.ai_schedule_service import get_ai_schedule_service


class FakeAiScheduleService:
    def __init__(self) -> None:
        self.calls = []

    def create_draft(self, *, user_id: str, body) -> dict:
        self.calls.append((user_id, body))
        return {
            "goal": {
                "title": "데이터 분석 과제 마무리",
                "deadline": "2026-09-30",
            },
            "milestones": [
                {
                    "client_id": "draft-1",
                    "title": "자료 수집과 전처리",
                    "scheduled_date": "2026-08-22",
                    "selected": True,
                }
            ],
            "planning_preference": {
                "intensity": "relaxed",
                "preferred_days": ["saturday"],
            },
            "validation": {
                "is_valid": True,
                "failure_codes": [],
                "warnings": [],
            },
            "create_goal_payload": {
                "goal": {
                    "title": "데이터 분석 과제 마무리",
                    "deadline": "2026-09-30",
                    "is_completed": False,
                    "is_recurring": False,
                    "recurrence_type": None,
                    "color": "#7F9278",
                },
                "milestones": [
                    {
                        "title": "자료 수집과 전처리",
                        "scheduled_date": "2026-08-22",
                        "color": "#7F9278",
                        "is_completed": False,
                    }
                ],
                "write_policy": "user_confirmation_required",
            },
        }


def override_current_user_id() -> str:
    return "user-1"


def test_ai_schedule_draft_route_requires_authentication(client: TestClient) -> None:
    response = client.post(
        "/ai/schedule/draft",
        json={
            "prompt": "일정 초안 만들어줘",
            "today": "2026-08-14",
            "timezone": "Asia/Seoul",
            "availability": [{"date": "2026-08-22", "available_minutes": 240}],
        },
    )

    assert response.status_code == 401


def test_ai_schedule_draft_route_returns_service_result(client: TestClient) -> None:
    service = FakeAiScheduleService()
    client.app.dependency_overrides[require_current_user_id] = override_current_user_id
    client.app.dependency_overrides[get_ai_schedule_service] = lambda: service
    try:
        response = client.post(
            "/ai/schedule/draft",
            json={
                "prompt": "9월 말까지 데이터 분석 과제를 끝내고 싶어.",
                "today": "2026-08-14",
                "timezone": "Asia/Seoul",
                "availability": [{"date": "2026-08-22", "available_minutes": 240}],
            },
        )
    finally:
        client.app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["goal"]["title"] == "데이터 분석 과제 마무리"
    assert body["data"]["milestones"][0]["selected"] is True
    assert body["data"]["create_goal_payload"]["write_policy"] == "user_confirmation_required"
    assert service.calls[0][0] == "user-1"
    assert service.calls[0][1].today == date(2026, 8, 14)
