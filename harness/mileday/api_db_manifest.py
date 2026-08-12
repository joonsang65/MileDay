from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


API_DB_MANIFEST_FILENAME = "db_manifest.json"


@dataclass(frozen=True)
class ApiDbWriteRecord:
    operation: str
    run_id: str
    case_id: str
    turn_id: int
    goal_id: str
    milestone_ids: list[str]
    milestone_slot_ids: dict[str, str]
    goal_title: str
    milestone_titles: dict[str, str]
    user_id: str
    created_at: str


def new_api_db_write_record(
    *,
    operation: str,
    run_id: str,
    case_id: str,
    turn_id: int,
    goal_id: str,
    milestone_ids: list[str],
    milestone_slot_ids: dict[str, str] | None = None,
    goal_title: str = "",
    milestone_titles: dict[str, str] | None = None,
    user_id: str,
) -> ApiDbWriteRecord:
    return ApiDbWriteRecord(
        operation=operation,
        run_id=run_id,
        case_id=case_id,
        turn_id=turn_id,
        goal_id=goal_id,
        milestone_ids=milestone_ids,
        milestone_slot_ids=milestone_slot_ids or {},
        goal_title=goal_title,
        milestone_titles=milestone_titles or {},
        user_id=user_id,
        created_at=datetime.now(UTC).isoformat(),
    )


def api_db_manifest_path(run_dir: Path) -> Path:
    return run_dir / API_DB_MANIFEST_FILENAME


def load_api_db_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"records": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Invalid DB manifest: {path}")
    records = data.get("records")
    if not isinstance(records, list):
        raise ValueError(f"Invalid DB manifest records: {path}")
    return data


def append_api_db_manifest_record(path: Path, record: ApiDbWriteRecord) -> Path:
    manifest = load_api_db_manifest(path)
    manifest["records"].append(asdict(record))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return path
