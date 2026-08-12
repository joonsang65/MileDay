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
    *,
    operation: str = "create",
    patch_items: list[dict[str, Any]] | None = None,
    add_items: list[dict[str, Any]] | None = None,
    remove_slot_ids: list[str] | None = None,
) -> dict[str, Any]:
    milestones = build_milestone_payloads(case, plan_items, slots_by_id)
    return {
        "operation": operation,
        "goal": build_goal_payload(case),
        "milestones": milestones,
        "mutations": build_operation_mutations(
            case,
            slots_by_id,
            operation=operation,
            patch_items=patch_items or [],
            add_items=add_items or [],
            remove_slot_ids=remove_slot_ids or [],
        ),
    }


def build_operation_mutations(
    case: MileDayMultiTurnCase,
    slots_by_id: dict[str, dict[str, str]],
    *,
    operation: str,
    patch_items: list[dict[str, Any]],
    add_items: list[dict[str, Any]],
    remove_slot_ids: list[str],
) -> dict[str, Any]:
    return {
        "operation": operation,
        "requires_goal_id": operation in {"add", "remove", "rename"},
        "requires_milestone_id": operation in {"remove", "rename"},
        "add": _add_mutation_payloads(case, add_items, slots_by_id),
        "remove": [
            {
                "slot_id": slot_id,
                "goal_id_required": True,
                "milestone_id_required": True,
            }
            for slot_id in remove_slot_ids
            if slot_id in slots_by_id
        ],
        "rename": _rename_mutation_payloads(case, patch_items, slots_by_id),
        "no_op": operation == "none",
        "requires_clarification": operation == "none",
    }


def _add_mutation_payloads(
    case: MileDayMultiTurnCase,
    add_items: list[dict[str, Any]],
    slots_by_id: dict[str, dict[str, str]],
) -> list[dict[str, Any]]:
    payloads = build_milestone_payloads(case, add_items, slots_by_id)
    return [
        {
            "slot_id": str(item.get("slot_id")),
            "goal_id_required": True,
            "milestone": payload,
        }
        for item, payload in zip(add_items, payloads, strict=False)
        if isinstance(item.get("slot_id"), str)
    ]


def _rename_mutation_payloads(
    case: MileDayMultiTurnCase,
    patch_items: list[dict[str, Any]],
    slots_by_id: dict[str, dict[str, str]],
) -> list[dict[str, Any]]:
    payloads = build_milestone_payloads(case, patch_items, slots_by_id)
    return [
        {
            "slot_id": str(item.get("slot_id")),
            "goal_id_required": True,
            "milestone_id_required": True,
            "milestone": payload,
        }
        for item, payload in zip(patch_items, payloads, strict=False)
        if isinstance(item.get("slot_id"), str)
    ]


def build_sql_statements(payload: dict[str, Any]) -> list[str]:
    operation = payload.get("operation") or "create"
    if operation == "create":
        return _build_create_sql_statements(payload)
    if operation == "none":
        return ["-- Preview only. No DB mutation is required for this turn."]
    return _build_partial_update_sql_statements(payload)


def _build_create_sql_statements(payload: dict[str, Any]) -> list[str]:
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


def _build_partial_update_sql_statements(payload: dict[str, Any]) -> list[str]:
    mutations = payload.get("mutations")
    if not isinstance(mutations, dict):
        return []

    statements = ["-- Preview only. Bind :user_id from the authenticated JWT subject."]
    add_items = mutations.get("add")
    if isinstance(add_items, list) and add_items:
        values = [
            f"    (:add_{index}_title, :add_{index}_color, :add_{index}_scheduled_date, false)"
            for index, item in enumerate(add_items, start=1)
            if isinstance(item, dict)
        ]
        if values:
            statements.append(
                "INSERT INTO public.milestones (goal_id, user_id, title, color, scheduled_date, is_completed)\n"
                "VALUES\n"
                + ",\n".join(
                    row.replace("(", "(:goal_id, :user_id, ", 1)
                    for row in values
                )
                + ";"
            )

    remove_items = mutations.get("remove")
    if isinstance(remove_items, list):
        for index, item in enumerate(remove_items, start=1):
            if not isinstance(item, dict):
                continue
            statements.append(
                "DELETE FROM public.milestones\n"
                f"WHERE id = :remove_{index}_milestone_id\n"
                "  AND goal_id = :goal_id\n"
                "  AND user_id = :user_id;"
            )

    rename_items = mutations.get("rename")
    if isinstance(rename_items, list):
        for index, item in enumerate(rename_items, start=1):
            if not isinstance(item, dict):
                continue
            statements.append(
                "UPDATE public.milestones\n"
                f"SET title = :rename_{index}_title,\n"
                "    updated_at = now()\n"
                f"WHERE id = :rename_{index}_milestone_id\n"
                "  AND goal_id = :goal_id\n"
                "  AND user_id = :user_id;"
            )

    return statements if len(statements) > 1 else ["-- Preview only. No DB mutation is required for this turn."]


def build_insert_sql_preview(payload: dict[str, Any]) -> str:
    return "\n".join(build_sql_statements(payload))


def build_sql_parameters(payload: dict[str, Any], *, user_id: str | None = None) -> dict[str, Any]:
    operation = payload.get("operation") or "create"
    if operation != "create":
        return _build_partial_update_sql_parameters(payload, user_id=user_id)

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


def _build_partial_update_sql_parameters(payload: dict[str, Any], *, user_id: str | None) -> dict[str, Any]:
    mutations = payload.get("mutations")
    if not isinstance(mutations, dict):
        return {}
    params: dict[str, Any] = {
        "user_id": user_id,
        "goal_id": None,
    }
    add_items = mutations.get("add")
    if isinstance(add_items, list):
        for index, item in enumerate(add_items, start=1):
            milestone = item.get("milestone") if isinstance(item, dict) else None
            if not isinstance(milestone, dict):
                continue
            params[f"add_{index}_title"] = milestone.get("title")
            params[f"add_{index}_color"] = milestone.get("color")
            params[f"add_{index}_scheduled_date"] = milestone.get("scheduled_date")

    remove_items = mutations.get("remove")
    if isinstance(remove_items, list):
        for index, item in enumerate(remove_items, start=1):
            if isinstance(item, dict):
                params[f"remove_{index}_slot_id"] = item.get("slot_id")
                params[f"remove_{index}_milestone_id"] = None

    rename_items = mutations.get("rename")
    if isinstance(rename_items, list):
        for index, item in enumerate(rename_items, start=1):
            milestone = item.get("milestone") if isinstance(item, dict) else None
            if not isinstance(item, dict) or not isinstance(milestone, dict):
                continue
            params[f"rename_{index}_slot_id"] = item.get("slot_id")
            params[f"rename_{index}_milestone_id"] = None
            params[f"rename_{index}_title"] = milestone.get("title")
    return params
