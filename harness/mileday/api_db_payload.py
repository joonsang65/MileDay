from __future__ import annotations

from typing import Any

from harness.mileday.dataset import MileDayMultiTurnCase
from harness.mileday.time_prefix import canonical_milestone_title


GOAL_INSERT_COLUMNS = (
    "user_id",
    "title",
    "deadline",
    "is_recurring",
    "recurrence_type",
    "color",
)
MILESTONE_INSERT_COLUMNS = (
    "goal_id",
    "user_id",
    "title",
    "color",
    "scheduled_date",
    "is_completed",
)


def build_goal_payload(case: MileDayMultiTurnCase) -> dict[str, Any]:
    goal = case.input.initial_goal
    return {
        "title": goal.title,
        "deadline": goal.deadline,
        "is_recurring": goal.is_recurring,
        "recurrence_type": goal.recurrence_type,
        "color": goal.color,
    }


def build_milestone_payloads(
    case: MileDayMultiTurnCase,
    plan_items: list[dict[str, Any]],
    slots_by_id: dict[str, dict[str, str]],
) -> list[dict[str, Any]]:
    milestones: list[dict[str, Any]] = []
    slot_ids_seen: set[str] = set()
    for item in plan_items:
        slot_id = item.get("slot_id")
        task = item.get("task")
        if not isinstance(slot_id, str) or slot_id not in slots_by_id or slot_id in slot_ids_seen:
            continue
        if not isinstance(task, str) or not task.strip():
            continue
        slot = slots_by_id[slot_id]
        slot_ids_seen.add(slot_id)
        milestones.append(
            {
                "title": canonical_milestone_title(
                    slot["day_of_week"],
                    slot["time_range"].split("-")[0],
                    slot["time_range"].split("-")[1],
                    task.strip(),
                ),
                "color": case.input.initial_goal.color,
                "scheduled_date": slot["scheduled_date"],
            }
        )
    return milestones


def build_schedule_db_payload(
    case: MileDayMultiTurnCase,
    plan_items: list[dict[str, Any]],
    slots_by_id: dict[str, dict[str, str]],
) -> dict[str, Any]:
    return {
        "goal": build_goal_payload(case),
        "milestones": build_milestone_payloads(case, plan_items, slots_by_id),
    }


def build_sql_statements(payload: dict[str, Any]) -> list[str]:
    goal = payload.get("goal")
    milestones = payload.get("milestones")
    if not isinstance(goal, dict) or not isinstance(milestones, list):
        return []

    goal_sql = (
        "INSERT INTO public.goals (user_id, title, deadline, is_recurring, recurrence_type, color)\n"
        "  VALUES (:user_id, :goal_title, :goal_deadline, :goal_is_recurring, :goal_recurrence_type, :goal_color)\n"
        "  RETURNING id"
    )
    statements = ["-- Preview only. Bind :user_id from the authenticated JWT subject."]
    if not milestones:
        return [*statements, f"{goal_sql};"]

    milestone_rows = [
        f"    (:milestone_{index}_title, :milestone_{index}_color, :milestone_{index}_scheduled_date, false)"
        for index, milestone in enumerate(milestones, start=1)
        if isinstance(milestone, dict)
    ]
    if not milestone_rows:
        return [*statements, f"{goal_sql};"]

    statements.append(
        "WITH inserted_goal AS (\n"
        f"  {goal_sql}\n"
        "),\n"
        "milestone_rows(title, color, scheduled_date, is_completed) AS (\n"
        "  VALUES\n"
        + ",\n".join(milestone_rows)
        + "\n"
        ")\n"
        "INSERT INTO public.milestones (goal_id, user_id, title, color, scheduled_date, is_completed)\n"
        "SELECT inserted_goal.id, :user_id, milestone_rows.title, milestone_rows.color, "
        "milestone_rows.scheduled_date, milestone_rows.is_completed\n"
        "FROM inserted_goal\n"
        "CROSS JOIN milestone_rows;"
    )
    return statements


def build_insert_sql_preview(payload: dict[str, Any]) -> str:
    return "\n".join(build_sql_statements(payload))


def build_sql_parameters(payload: dict[str, Any], *, user_id: str | None = None) -> dict[str, Any]:
    goal = payload.get("goal")
    milestones = payload.get("milestones")
    if not isinstance(goal, dict) or not isinstance(milestones, list):
        return {}

    params = {
        "user_id": user_id,
        "goal_title": goal.get("title"),
        "goal_deadline": goal.get("deadline"),
        "goal_is_recurring": goal.get("is_recurring"),
        "goal_recurrence_type": goal.get("recurrence_type"),
        "goal_color": goal.get("color"),
    }
    for index, milestone in enumerate(milestones, start=1):
        if not isinstance(milestone, dict):
            continue
        params[f"milestone_{index}_title"] = milestone.get("title")
        params[f"milestone_{index}_color"] = milestone.get("color")
        params[f"milestone_{index}_scheduled_date"] = milestone.get("scheduled_date")
    return params
