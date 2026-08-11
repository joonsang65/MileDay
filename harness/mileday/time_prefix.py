from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date


DAY_OF_WEEK_KO = {
    "monday": "월",
    "tuesday": "화",
    "wednesday": "수",
    "thursday": "목",
    "friday": "금",
    "saturday": "토",
    "sunday": "일",
}

KO_DAY_OF_WEEK = {value: key for key, value in DAY_OF_WEEK_KO.items()}
KO_DAY_OF_WEEK.update({f"{key}요일": value for key, value in KO_DAY_OF_WEEK.items()})
CANONICAL_PREFIX_PATTERN = re.compile(
    r"^\[(?P<weekday>[월화수목금토일]) (?P<start>\d{2}:\d{2})-(?P<end>\d{2}:\d{2})\] (?P<task>.+)$"
)


@dataclass(frozen=True)
class ParsedMilestoneTitle:
    day_of_week: str
    start_time: str
    end_time: str
    task: str


def ko_weekday(day_of_week: str | None) -> str:
    return DAY_OF_WEEK_KO.get(day_of_week or "", "")


def date_day_of_week(raw_date: str) -> str | None:
    try:
        weekday_index = date.fromisoformat(raw_date).weekday()
    except ValueError:
        return None
    return [
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    ][weekday_index]


def canonical_title_prefix(day_of_week: str, start_time: str, end_time: str) -> str:
    weekday = ko_weekday(day_of_week)
    if not weekday:
        raise ValueError(f"Unsupported day_of_week: {day_of_week}")
    return f"[{weekday} {start_time}-{end_time}]"


def canonical_milestone_title(day_of_week: str, start_time: str, end_time: str, task: str) -> str:
    cleaned = task.strip()
    if not cleaned:
        raise ValueError("task must not be blank")
    return f"{canonical_title_prefix(day_of_week, start_time, end_time)} {cleaned}"


def parse_canonical_milestone_title(title: str) -> ParsedMilestoneTitle | None:
    match = CANONICAL_PREFIX_PATTERN.fullmatch(title.strip())
    if match is None:
        return None
    day_of_week = KO_DAY_OF_WEEK.get(match.group("weekday"))
    if day_of_week is None:
        return None
    start_time = match.group("start")
    end_time = match.group("end")
    if end_time <= start_time:
        return None
    return ParsedMilestoneTitle(
        day_of_week=day_of_week,
        start_time=start_time,
        end_time=end_time,
        task=match.group("task").strip(),
    )
