from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from core.config import get_settings
from repositories.push import PushRepository, get_push_repository
from services.calendar_service import CalendarService, get_calendar_service
from services.push_service import PushService, get_push_service, utc_now


def milestone_notification_body(milestones: list[dict[str, Any]]) -> str:
    # Stable ordering also handles equal titles and input rows returned in any order.
    ordered = sorted(milestones, key=lambda m: (str(m.get("created_at") or ""), str(m.get("id") or ""), str(m.get("title") or "")))
    titles = []
    for milestone in ordered[:2]:
        title = " ".join(str(milestone.get("title") or "").split()) or "마일스톤"
        titles.append(title if len(title) <= 35 else title[:34] + "…")
    remaining = len(ordered) - len(titles)
    return ", ".join(titles) + (f" 외 {remaining}개" if remaining else "")


class NotificationScheduler:
    def __init__(
        self,
        *,
        repository: PushRepository | None = None,
        calendar_service: CalendarService | None = None,
        push_service: PushService | None = None,
    ) -> None:
        self.repository = repository or get_push_repository()
        self.calendar_service = calendar_service or get_calendar_service()
        self.push_service = push_service or get_push_service()
        self._task: asyncio.Task[None] | None = None
        self._stop_event: asyncio.Event | None = None

    def start(self) -> None:
        settings = get_settings()
        if not settings.notification_scheduler_enabled or self._task is not None:
            return
        self._stop_event = asyncio.Event()
        self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        if self._stop_event:
            self._stop_event.set()
        if self._task:
            await self._task
        self._task = None
        self._stop_event = None

    async def _run_loop(self) -> None:
        settings = get_settings()
        assert self._stop_event is not None
        while not self._stop_event.is_set():
            await asyncio.to_thread(self.run_once)
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=max(10, settings.notification_scheduler_interval_seconds),
                )
            except asyncio.TimeoutError:
                pass

    def run_once(self, now: datetime | None = None) -> dict[str, int]:
        current = now or utc_now()
        checked = 0
        sent_users = 0
        skipped = 0
        for setting in self.repository.list_enabled_notification_settings():
            checked += 1
            due = self._due_local_time(setting=setting, now=current)
            if due is None:
                skipped += 1
                continue
            user_id = setting["user_id"]
            date_data = self.calendar_service.get_date_calendar(
                user_id=user_id,
                target_date=due.date(),
            )
            milestones = [m for m in date_data.get("milestones", []) if not m.get("is_completed") and str(m.get("scheduled_date"))[:10] == due.date().isoformat()]
            if not milestones:
                skipped += 1
                continue
            if not self.repository.list_user_subscriptions(user_id=user_id):
                skipped += 1
                continue
            if not self.repository.try_create_delivery_log(
                user_id=user_id,
                delivery_date=due.date(),
                notification_type="daily_schedule",
            ):
                skipped += 1
                continue
            self.push_service.send_user_push(
                user_id=user_id,
                title="MileDay · 오늘의 마일스톤",
                body=milestone_notification_body(milestones),
                url="/#/today",
            )
            sent_users += 1
        return {"checked": checked, "sent_users": sent_users, "skipped": skipped}

    def _due_local_time(self, *, setting: dict[str, Any], now: datetime) -> datetime | None:
        timezone = setting.get("timezone") or "Asia/Seoul"
        notification_time = str(setting.get("notification_time") or "08:00")[:5]
        try:
            local_now = now.astimezone(ZoneInfo(timezone))
        except ZoneInfoNotFoundError:
            return None
        if local_now.strftime("%H:%M") != notification_time:
            return None
        return local_now


def get_notification_scheduler() -> NotificationScheduler:
    return NotificationScheduler()
