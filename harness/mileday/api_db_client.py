from __future__ import annotations

from typing import Any

from supabase import Client, create_client

from harness.config import HarnessSettings
from harness.mileday.api_db_manifest import ApiDbWriteRecord, new_api_db_write_record


class ApiDbConfigError(ValueError):
    pass


class ApiDbWriter:
    def __init__(
        self,
        *,
        supabase_url: str,
        service_role_key: str,
        user_id: str,
        title_prefix: str,
        client: Client | Any | None = None,
    ) -> None:
        if not supabase_url:
            raise ApiDbConfigError("SUPABASE_URL is required for DB write.")
        if not service_role_key:
            raise ApiDbConfigError("SUPABASE_SERVICE_ROLE_KEY is required for DB write.")
        if not user_id:
            raise ApiDbConfigError("TEST_USER_ID is required for DB write.")
        if not title_prefix:
            raise ApiDbConfigError("TEST_TITLE_PREFIX is required for DB write.")
        self.user_id = user_id
        self.title_prefix = title_prefix
        self.client = client or create_client(supabase_url, service_role_key)

    @classmethod
    def from_settings(cls, settings: HarnessSettings) -> "ApiDbWriter":
        return cls(
            supabase_url=settings.supabase_url or "",
            service_role_key=settings.supabase_service_role_key or "",
            user_id=settings.test_user_id or "",
            title_prefix=settings.test_title_prefix or "",
        )

    def insert_create_payload(
        self,
        *,
        run_id: str,
        case_id: str,
        turn_id: int,
        payload: dict[str, Any],
        plan_items: list[dict[str, Any]],
    ) -> ApiDbWriteRecord:
        goal_payload, milestone_payloads = self._insert_payloads(payload)
        goal_response = self.client.table("goals").insert(goal_payload).execute()
        goal_rows = list(goal_response.data or [])
        if not goal_rows or not isinstance(goal_rows[0].get("id"), str):
            raise RuntimeError("Goal insert did not return an id.")
        goal_id = goal_rows[0]["id"]

        milestone_rows: list[dict[str, Any]] = []
        if milestone_payloads:
            rows = [{**item, "goal_id": goal_id} for item in milestone_payloads]
            milestone_response = self.client.table("milestones").insert(rows).execute()
            milestone_rows = list(milestone_response.data or [])
        milestone_ids = [str(row["id"]) for row in milestone_rows if isinstance(row.get("id"), str)]
        milestone_slot_ids = _milestone_slot_id_map(plan_items, milestone_rows)
        milestone_titles = {
            str(plan_item["slot_id"]): str(payload_row.get("title", ""))
            for plan_item, payload_row in zip(plan_items, milestone_payloads, strict=False)
            if isinstance(plan_item, dict)
            and isinstance(plan_item.get("slot_id"), str)
            and isinstance(payload_row, dict)
        }
        return new_api_db_write_record(
            operation="create",
            run_id=run_id,
            case_id=case_id,
            turn_id=turn_id,
            goal_id=goal_id,
            milestone_ids=milestone_ids,
            milestone_slot_ids=milestone_slot_ids,
            goal_title=str(goal_payload["title"]),
            milestone_titles=milestone_titles,
            user_id=self.user_id,
        )

    def update_partial_payload(
        self,
        *,
        run_id: str,
        case_id: str,
        turn_id: int,
        create_record: dict[str, Any],
        parsed_json: dict[str, Any],
    ) -> ApiDbWriteRecord | None:
        self._validate_record_user(create_record)
        goal_id = _required_string(create_record, "goal_id")
        milestone_slot_ids = create_record.get("milestone_slot_ids")
        if not isinstance(milestone_slot_ids, dict):
            raise ValueError("DB manifest record must contain milestone_slot_ids for partial updates.")

        mutations = _partial_update_mutations(parsed_json)
        updates = mutations["rename"]
        additions = mutations["add"]
        removals = mutations["remove"]
        if not updates and not additions and not removals:
            return None

        updated_ids: list[str] = []
        updated_titles: dict[str, str] = {}
        for slot_id, title in updates.items():
            milestone_id = milestone_slot_ids.get(slot_id)
            if not isinstance(milestone_id, str) or not milestone_id:
                raise ValueError(f"Cannot find milestone id for slot_id: {slot_id}")
            prefixed_title = self._prefixed_title(title)
            response = (
                self.client.table("milestones")
                .update({"title": prefixed_title})
                .eq("id", milestone_id)
                .eq("goal_id", goal_id)
                .eq("user_id", self.user_id)
                .execute()
            )
            if not response.data:
                raise RuntimeError(f"Milestone update did not affect a row: {milestone_id}")
            updated_ids.append(milestone_id)
            updated_titles[slot_id] = prefixed_title

        added_ids: list[str] = []
        added_slot_ids: dict[str, str] = {}
        added_titles: dict[str, str] = {}
        if additions:
            rows = []
            add_slot_order = []
            for slot_id, milestone in additions.items():
                rows.append(
                    {
                        "goal_id": goal_id,
                        "user_id": self.user_id,
                        "title": self._prefixed_title(milestone.get("title")),
                        "color": milestone.get("color"),
                        "scheduled_date": milestone.get("scheduled_date"),
                        "is_completed": False,
                    }
                )
                add_slot_order.append(slot_id)
            response = self.client.table("milestones").insert(rows).execute()
            inserted_rows = list(response.data or [])
            if len(inserted_rows) != len(rows):
                raise RuntimeError("Milestone add insert did not return all rows.")
            for slot_id, row, source in zip(add_slot_order, inserted_rows, rows, strict=True):
                milestone_id = row.get("id")
                if not isinstance(milestone_id, str) or not milestone_id:
                    raise RuntimeError("Milestone add insert did not return an id.")
                added_ids.append(milestone_id)
                added_slot_ids[slot_id] = milestone_id
                added_titles[slot_id] = str(source["title"])

        removed_ids: list[str] = []
        removed_slot_ids: dict[str, str] = {}
        for slot_id in removals:
            milestone_id = milestone_slot_ids.get(slot_id)
            if not isinstance(milestone_id, str) or not milestone_id:
                raise ValueError(f"Cannot find milestone id for slot_id: {slot_id}")
            response = (
                self.client.table("milestones")
                .delete()
                .eq("id", milestone_id)
                .eq("goal_id", goal_id)
                .eq("user_id", self.user_id)
                .execute()
            )
            if not response.data:
                raise RuntimeError(f"Milestone delete did not affect a row: {milestone_id}")
            removed_ids.append(milestone_id)
            removed_slot_ids[slot_id] = milestone_id

        operation = _manifest_operation(
            has_add=bool(added_ids),
            has_remove=bool(removed_ids),
            has_rename=bool(updated_ids),
        )
        return new_api_db_write_record(
            operation=operation,
            run_id=run_id,
            case_id=case_id,
            turn_id=turn_id,
            goal_id=goal_id,
            milestone_ids=[*updated_ids, *added_ids, *removed_ids],
            milestone_slot_ids={
                **{slot_id: milestone_slot_ids[slot_id] for slot_id in updates},
                **added_slot_ids,
                **removed_slot_ids,
            },
            goal_title=str(create_record.get("goal_title", "")),
            milestone_titles={**updated_titles, **added_titles},
            user_id=self.user_id,
        )

    def cleanup_record(self, record: dict[str, Any]) -> dict[str, int]:
        self._validate_record_user(record)
        if record.get("operation") in {"rename", "remove", "none"}:
            return {"goals": 0, "milestones": 0}

        deleted_milestones = 0
        for milestone_id in record.get("milestone_ids", []):
            if not isinstance(milestone_id, str) or not milestone_id:
                continue
            response = (
                self.client.table("milestones")
                .delete()
                .eq("id", milestone_id)
                .eq("user_id", self.user_id)
                .execute()
            )
            deleted_milestones += len(response.data or [])

        deleted_goals = 0
        goal_id = record.get("goal_id")
        if isinstance(goal_id, str) and goal_id:
            response = (
                self.client.table("goals")
                .delete()
                .eq("id", goal_id)
                .eq("user_id", self.user_id)
                .execute()
            )
            deleted_goals += len(response.data or [])
        return {"goals": deleted_goals, "milestones": deleted_milestones}

    def _validate_record_user(self, record: dict[str, Any]) -> None:
        user_id = record.get("user_id")
        if user_id != self.user_id:
            raise ValueError("Manifest user_id does not match TEST_USER_ID.")

    def _insert_payloads(self, payload: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        goal = payload.get("goal")
        milestones = payload.get("milestones")
        if not isinstance(goal, dict) or not isinstance(milestones, list):
            raise ValueError("DB payload must contain goal and milestones.")

        goal_payload = {
            "user_id": self.user_id,
            "title": self._prefixed_title(goal.get("title")),
            "deadline": goal.get("deadline"),
            "is_recurring": goal.get("is_recurring"),
            "recurrence_type": goal.get("recurrence_type"),
            "color": goal.get("color"),
        }
        milestone_payloads = [
            {
                "user_id": self.user_id,
                "title": self._prefixed_title(item.get("title")),
                "color": item.get("color"),
                "scheduled_date": item.get("scheduled_date"),
                "is_completed": False,
            }
            for item in milestones
            if isinstance(item, dict)
        ]
        return goal_payload, milestone_payloads

    def _prefixed_title(self, title: object) -> str:
        text = str(title or "").strip()
        if text.startswith(self.title_prefix):
            return text
        return f"{self.title_prefix} {text}".strip()


def _milestone_slot_id_map(
    plan_items: list[dict[str, Any]],
    milestone_rows: list[dict[str, Any]],
) -> dict[str, str]:
    return {
        str(plan_item["slot_id"]): str(row["id"])
        for plan_item, row in zip(plan_items, milestone_rows, strict=False)
        if isinstance(plan_item, dict)
        and isinstance(plan_item.get("slot_id"), str)
        and isinstance(row, dict)
        and isinstance(row.get("id"), str)
    }


def _partial_update_mutations(parsed_json: dict[str, Any]) -> dict[str, Any]:
    patch_items = parsed_json.get("patch_items")
    add_items = parsed_json.get("add_items")
    remove_slot_ids = parsed_json.get("remove_slot_ids")
    plan_items = parsed_json.get("plan_items")
    db_payload = parsed_json.get("db_payload")
    milestones = db_payload.get("milestones") if isinstance(db_payload, dict) else None
    if (
        not isinstance(patch_items, list)
        or not isinstance(add_items, list)
        or not isinstance(remove_slot_ids, list)
        or not isinstance(plan_items, list)
        or not isinstance(milestones, list)
    ):
        raise ValueError(
            "partial_update requires patch_items, add_items, remove_slot_ids, plan_items, and db_payload.milestones."
        )

    plan_index_by_slot_id = {
        item.get("slot_id"): index
        for index, item in enumerate(plan_items)
        if isinstance(item, dict) and isinstance(item.get("slot_id"), str)
    }
    updates: dict[str, str] = {}
    for item in patch_items:
        if not isinstance(item, dict):
            continue
        slot_id = item.get("slot_id")
        if not isinstance(slot_id, str):
            continue
        index = plan_index_by_slot_id.get(slot_id)
        if not isinstance(index, int) or index >= len(milestones):
            raise ValueError(f"Cannot find final milestone payload for slot_id: {slot_id}")
        milestone = milestones[index]
        if not isinstance(milestone, dict) or not isinstance(milestone.get("title"), str):
            raise ValueError(f"Invalid milestone title for slot_id: {slot_id}")
        updates[slot_id] = milestone["title"]

    additions: dict[str, dict[str, Any]] = {}
    for item in add_items:
        if not isinstance(item, dict):
            continue
        slot_id = item.get("slot_id")
        if not isinstance(slot_id, str):
            continue
        index = plan_index_by_slot_id.get(slot_id)
        if not isinstance(index, int) or index >= len(milestones):
            raise ValueError(f"Cannot find final milestone payload for added slot_id: {slot_id}")
        milestone = milestones[index]
        if not isinstance(milestone, dict):
            raise ValueError(f"Invalid milestone payload for added slot_id: {slot_id}")
        additions[slot_id] = milestone

    removals = [slot_id for slot_id in remove_slot_ids if isinstance(slot_id, str)]
    return {"rename": updates, "add": additions, "remove": removals}


def _manifest_operation(*, has_add: bool, has_remove: bool, has_rename: bool) -> str:
    operations = []
    if has_add:
        operations.append("add")
    if has_remove:
        operations.append("remove")
    if has_rename:
        operations.append("rename")
    if not operations:
        return "none"
    return operations[0] if len(operations) == 1 else "partial_update"


def _required_string(record: dict[str, Any], key: str) -> str:
    value = record.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"DB manifest record must contain {key}.")
    return value
