from __future__ import annotations

import calendar
from collections import defaultdict
from datetime import date, timedelta
from typing import Any

from repositories.calendar import CalendarRepository, get_calendar_repository


class CalendarService:
    def __init__(self, repository: CalendarRepository | None = None) -> None:
        self.repository = repository or get_calendar_repository()

    def get_month_calendar(
        self,
        *,
        user_id: str,
        year: int,
        month: int,
        today: date | None = None,
    ) -> dict[str, Any]:
        first_day, last_day = self._month_range(year=year, month=month)
        goals = self.repository.list_goals_by_deadline_range(
            user_id=user_id,
            start_date=first_day.isoformat(),
            end_date=last_day.isoformat(),
        )
        milestones = [
            self._with_goal_title(row)
            for row in self.repository.list_milestones_by_scheduled_date_range(
                user_id=user_id,
                start_date=first_day.isoformat(),
                end_date=last_day.isoformat(),
            )
        ]
        return {
            "year": year,
            "month": month,
            "days": self._build_days(
                start_date=first_day,
                end_date=last_day,
                goals=goals,
                milestones=milestones,
                today=today or date.today(),
            ),
            "goals": goals,
            "milestones": milestones,
        }

    def get_week_calendar(
        self,
        *,
        user_id: str,
        start_date: date,
        today: date | None = None,
    ) -> dict[str, Any]:
        end_date = start_date + timedelta(days=6)
        goals = self.repository.list_goals_by_deadline_range(
            user_id=user_id,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
        )
        milestones = [
            self._with_goal_title(row)
            for row in self.repository.list_milestones_by_scheduled_date_range(
                user_id=user_id,
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
            )
        ]
        return {
            "start_date": start_date,
            "end_date": end_date,
            "days": self._build_days(
                start_date=start_date,
                end_date=end_date,
                goals=goals,
                milestones=milestones,
                today=today or date.today(),
            ),
            "goals": goals,
            "milestones": milestones,
        }

    def get_date_calendar(
        self,
        *,
        user_id: str,
        target_date: date,
        today: date | None = None,
    ) -> dict[str, Any]:
        date_text = target_date.isoformat()
        goals = self.repository.list_goals_by_deadline(
            user_id=user_id,
            deadline=date_text,
        )
        milestones = [
            self._with_goal_title(row)
            for row in self.repository.list_milestones_by_scheduled_date(
                user_id=user_id,
                scheduled_date=date_text,
            )
        ]
        return {
            "date": target_date,
            "is_today": target_date == (today or date.today()),
            "goal_count": len(goals),
            "milestone_count": len(milestones),
            "completed_milestone_count": self._completed_count(milestones),
            "goals": goals,
            "milestones": milestones,
        }

    def _month_range(self, *, year: int, month: int) -> tuple[date, date]:
        last_day = calendar.monthrange(year, month)[1]
        return date(year, month, 1), date(year, month, last_day)

    def _build_days(
        self,
        *,
        start_date: date,
        end_date: date,
        goals: list[dict[str, Any]],
        milestones: list[dict[str, Any]],
        today: date,
    ) -> list[dict[str, Any]]:
        goals_by_date = self._group_by_date(rows=goals, date_field="deadline")
        milestones_by_date = self._group_by_date(
            rows=milestones,
            date_field="scheduled_date",
        )

        days: list[dict[str, Any]] = []
        current = start_date
        while current <= end_date:
            date_key = current.isoformat()
            day_goals = goals_by_date[date_key]
            day_milestones = milestones_by_date[date_key]
            days.append(
                {
                    "date": current,
                    "is_today": current == today,
                    "goal_count": len(day_goals),
                    "milestone_count": len(day_milestones),
                    "completed_milestone_count": self._completed_count(
                        day_milestones,
                    ),
                    "goals": day_goals,
                    "milestones": day_milestones,
                }
            )
            current = current + timedelta(days=1)
        return days

    def _group_by_date(
        self,
        *,
        rows: list[dict[str, Any]],
        date_field: str,
    ) -> dict[str, list[dict[str, Any]]]:
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            grouped[str(row[date_field])].append(row)
        return grouped

    def _completed_count(self, milestones: list[dict[str, Any]]) -> int:
        return sum(1 for milestone in milestones if milestone.get("is_completed") is True)

    def _with_goal_title(self, row: dict[str, Any]) -> dict[str, Any]:
        milestone = dict(row)
        goal_data = milestone.pop("goals", None) or milestone.pop("goal", None)
        if "goal_title" not in milestone:
            milestone["goal_title"] = self._extract_goal_title(goal_data)
        return milestone

    def _extract_goal_title(self, goal_data: Any) -> str | None:
        if isinstance(goal_data, list):
            goal_data = goal_data[0] if goal_data else None
        if isinstance(goal_data, dict):
            return goal_data.get("title")
        return None


def get_calendar_service() -> CalendarService:
    return CalendarService()
