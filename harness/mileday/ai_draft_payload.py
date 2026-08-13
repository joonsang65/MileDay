from __future__ import annotations

from typing import Any


DEFAULT_GOAL_COLOR = "#7F9278"
DEFAULT_MILESTONE_COLOR = "#55A873"


def build_ai_draft_create_payload(draft: dict[str, Any]) -> dict[str, Any]:
    goal = draft.get("goal") if isinstance(draft.get("goal"), dict) else {}
    milestones = draft.get("milestones") if isinstance(draft.get("milestones"), list) else []
    return {
        "goal": {
            "title": goal.get("title"),
            "deadline": goal.get("deadline"),
            "is_recurring": False,
            "recurrence_type": None,
            "color": DEFAULT_GOAL_COLOR,
        },
        "milestones": [
            {
                "title": item.get("title"),
                "scheduled_date": item.get("scheduled_date"),
                "color": DEFAULT_MILESTONE_COLOR,
                "is_completed": False,
            }
            for item in milestones
            if isinstance(item, dict)
        ],
        "write_policy": "user_confirmation_required",
    }


def build_ai_draft_create_sql_preview(payload: dict[str, Any]) -> str:
    milestones = payload.get("milestones")
    if not isinstance(milestones, list):
        milestones = []
    rows = [
        f"    (:milestone_{index}_title, :milestone_{index}_color, :milestone_{index}_scheduled_date, false)"
        for index, item in enumerate(milestones, start=1)
        if isinstance(item, dict)
    ]
    goal_sql = (
        "INSERT INTO public.goals (user_id, title, deadline, is_recurring, recurrence_type, color)\n"
        "  VALUES (:user_id, :goal_title, :goal_deadline, false, null, :goal_color)\n"
        "  RETURNING id"
    )
    if not rows:
        return (
            "-- Preview only. Execute after explicit user confirmation.\n"
            "-- Bind :user_id from the authenticated JWT subject.\n"
            f"{goal_sql};"
        )
    return (
        "-- Preview only. Execute after explicit user confirmation.\n"
        "-- Bind :user_id from the authenticated JWT subject.\n"
        "WITH inserted_goal AS (\n"
        f"  {goal_sql}\n"
        "),\n"
        "milestone_rows(title, color, scheduled_date, is_completed) AS (\n"
        "  VALUES\n"
        + ",\n".join(rows)
        + "\n"
        ")\n"
        "INSERT INTO public.milestones (goal_id, user_id, title, color, scheduled_date, is_completed)\n"
        "SELECT inserted_goal.id, :user_id, milestone_rows.title, milestone_rows.color, "
        "milestone_rows.scheduled_date, milestone_rows.is_completed\n"
        "FROM inserted_goal\n"
        "CROSS JOIN milestone_rows;"
    )


def build_ai_draft_sql_parameters(payload: dict[str, Any], *, user_id: str | None = None) -> dict[str, Any]:
    goal = payload.get("goal") if isinstance(payload.get("goal"), dict) else {}
    milestones = payload.get("milestones") if isinstance(payload.get("milestones"), list) else []
    params = {
        "user_id": user_id,
        "goal_title": goal.get("title"),
        "goal_deadline": goal.get("deadline"),
        "goal_color": goal.get("color"),
    }
    for index, item in enumerate(milestones, start=1):
        if not isinstance(item, dict):
            continue
        params[f"milestone_{index}_title"] = item.get("title")
        params[f"milestone_{index}_color"] = item.get("color")
        params[f"milestone_{index}_scheduled_date"] = item.get("scheduled_date")
    return params
