from __future__ import annotations

from datetime import date
from uuid import uuid4

import pytest

from core.config import get_settings
from core.supabase import get_supabase_admin_client


pytestmark = pytest.mark.integration


def cleanup_test_user_data(user_id: str) -> None:
    admin = get_supabase_admin_client()
    admin.table("milestones").delete().eq("user_id", user_id).execute()
    admin.table("goals").delete().eq("user_id", user_id).execute()
    admin.table("user_settings").delete().eq("user_id", user_id).execute()


def test_real_supabase_test_user_data_isolated() -> None:
    settings = get_settings()
    if not settings.integration_tests_enabled:
        pytest.skip("ENABLE_INTEGRATION_TESTS=true 필요")

    user_id = settings.integration_test_user_id
    title = f"{settings.integration_test_title_prefix} integration {uuid4()}"
    admin = get_supabase_admin_client()

    cleanup_test_user_data(user_id)
    try:
        goal_response = (
            admin.table("goals")
            .insert(
                {
                    "user_id": user_id,
                    "title": title,
                    "deadline": date(2026, 12, 31).isoformat(),
                    "is_recurring": False,
                    "recurrence_type": None,
                    "color": "#4F46E5",
                }
            )
            .execute()
        )
        goal = goal_response.data[0]

        milestone_response = (
            admin.table("milestones")
            .insert(
                {
                    "goal_id": goal["id"],
                    "user_id": user_id,
                    "title": title,
                    "color": "#F97316",
                    "scheduled_date": date(2026, 12, 1).isoformat(),
                }
            )
            .execute()
        )

        assert goal["user_id"] == user_id
        assert milestone_response.data[0]["user_id"] == user_id
        assert milestone_response.data[0]["goal_id"] == goal["id"]
    finally:
        cleanup_test_user_data(user_id)
