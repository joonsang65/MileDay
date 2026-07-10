from __future__ import annotations

import json
from datetime import date
from typing import Any
from urllib.parse import quote, urlencode
from urllib.request import urlopen

from core.config import get_settings


class HolidayService:
    def __init__(
        self,
        *,
        service_key: str | None = None,
        base_url: str | None = None,
        timeout_seconds: int = 3,
    ) -> None:
        settings = get_settings()
        self.service_key = service_key if service_key is not None else settings.holiday_api_service_key
        self.base_url = base_url or settings.holiday_api_base_url
        self.timeout_seconds = timeout_seconds
        self._cache: dict[tuple[int, int], dict[str, str]] = {}

    def get_holidays_for_range(self, *, start_date: date, end_date: date) -> dict[str, str]:
        holidays: dict[str, str] = {}
        for year, month in self._months_between(start_date=start_date, end_date=end_date):
            holidays.update(self.get_holidays_for_month(year=year, month=month))
        return {
            date_key: name
            for date_key, name in holidays.items()
            if start_date.isoformat() <= date_key <= end_date.isoformat()
        }

    def get_holidays_for_month(self, *, year: int, month: int) -> dict[str, str]:
        cache_key = (year, month)
        if cache_key in self._cache:
            return self._cache[cache_key]
        if not self.service_key:
            self._cache[cache_key] = {}
            return {}

        try:
            holidays = self._fetch_holidays_for_month(year=year, month=month)
        except Exception:
            # 공휴일 API 실패는 캘린더 전체 실패로 전파하지 않는다.
            holidays = {}
        self._cache[cache_key] = holidays
        return holidays

    def _fetch_holidays_for_month(self, *, year: int, month: int) -> dict[str, str]:
        query = urlencode(
            {
                "pageNo": "1",
                "numOfRows": "200",
                "solYear": str(year),
                "solMonth": f"{month:02d}",
                "_type": "json",
            }
        )
        service_key = self._encoded_service_key()
        with urlopen(
            f"{self.base_url}?serviceKey={service_key}&{query}",
            timeout=self.timeout_seconds,
        ) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return {
            date_key: name
            for date_key, name in self._parse_holiday_response(payload).items()
            if date_key.startswith(f"{year}-{month:02d}-")
        }

    def _parse_holiday_response(self, payload: dict[str, Any]) -> dict[str, str]:
        items = self._extract_items(payload)
        if isinstance(items, dict):
            items = [items]

        holidays: dict[str, str] = {}
        for item in items:
            if not isinstance(item, dict) or not self._is_holiday_item(item):
                continue
            date_key = self._extract_date_key(item)
            if not date_key:
                continue
            holidays[date_key] = self._extract_name(item)
        return holidays

    def _extract_items(self, payload: dict[str, Any]) -> Any:
        # 공공데이터포털 GW API와 기존 특일 API 응답을 모두 수용한다.
        if isinstance(payload.get("data"), list):
            return payload["data"]
        if isinstance(payload.get("items"), list):
            return payload["items"]
        item_list = (
            payload.get("response", {})
            .get("body", {})
            .get("itemList", {})
            .get("item", [])
        )
        if item_list:
            return item_list
        return (
            payload.get("response", {})
            .get("body", {})
            .get("items", {})
            .get("item", [])
        )

    def _is_holiday_item(self, item: dict[str, Any]) -> bool:
        value = item.get("isHoliday", item.get("holiday_yn", item.get("is_holiday", "Y")))
        return str(value).upper() in {"Y", "TRUE", "1"}

    def _extract_date_key(self, item: dict[str, Any]) -> str | None:
        raw_value = (
            item.get("locdate")
            or item.get("holiday_date")
            or item.get("holiday_dt")
            or item.get("hldyDeFrom")
            or item.get("date")
            or item.get("base_date")
        )
        if raw_value is None:
            return None
        raw_text = str(raw_value).strip()
        digits = "".join(character for character in raw_text if character.isdigit())
        if len(digits) != 8:
            return None
        return f"{digits[:4]}-{digits[4:6]}-{digits[6:8]}"

    def _extract_name(self, item: dict[str, Any]) -> str:
        return str(
            item.get("dateName")
            or item.get("holiday_name")
            or item.get("holiday_nm")
            or item.get("hldyName")
            or item.get("name")
            or "공휴일"
        )

    def _encoded_service_key(self) -> str:
        # 공공데이터포털은 decoding key와 encoding key를 모두 제공한다.
        # 이미 인코딩된 키를 다시 인코딩하면 인증 실패가 나므로 %가 있으면 그대로 사용한다.
        if "%" in self.service_key:
            return self.service_key
        return quote(self.service_key, safe="")

    def _months_between(self, *, start_date: date, end_date: date) -> list[tuple[int, int]]:
        months: list[tuple[int, int]] = []
        year = start_date.year
        month = start_date.month
        while (year, month) <= (end_date.year, end_date.month):
            months.append((year, month))
            month += 1
            if month == 13:
                year += 1
                month = 1
        return months


def get_holiday_service() -> HolidayService:
    return HolidayService()
