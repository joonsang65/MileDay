from __future__ import annotations

from datetime import date
from typing import Any


def milestone_notification_body(milestones: list[dict[str, Any]]) -> str:
    ordered = sorted(
        milestones,
        key=lambda milestone: (
            str(milestone.get("created_at") or ""),
            str(milestone.get("id") or ""),
            str(milestone.get("title") or ""),
        ),
    )
    titles = []
    for milestone in ordered[:2]:
        title = " ".join(str(milestone.get("title") or "").split()) or "마일스톤"
        titles.append(title if len(title) <= 35 else title[:34] + "…")
    remaining = len(ordered) - len(titles)
    return ", ".join(titles) + (f" 외 {remaining}개" if remaining else "")


def build_daily_notification(
    date_data: dict[str, Any], target_date: date,
) -> dict[str, str] | None:
    milestones = [
        milestone for milestone in date_data.get("milestones", [])
        if not milestone.get("is_completed")
        and str(milestone.get("scheduled_date"))[:10] == target_date.isoformat()
    ]
    if not milestones:
        return None
    return {
        "title": "MileDay · 오늘의 마일스톤",
        "body": milestone_notification_body(milestones),
        "url": "/#/today",
    }
