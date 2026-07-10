from __future__ import annotations

from datetime import date
from urllib.parse import parse_qs, urlparse

from services.holiday_service import HolidayService


def test_holiday_service_returns_empty_when_service_key_is_missing() -> None:
    service = HolidayService(service_key="", base_url="http://holiday.test")

    assert service.get_holidays_for_month(year=2026, month=7) == {}


def test_holiday_service_parses_public_holiday_response() -> None:
    service = HolidayService(service_key="key", base_url="http://holiday.test")
    payload = {
        "response": {
            "body": {
                "items": {
                    "item": [
                        {"locdate": 20260717, "dateName": "제헌절", "isHoliday": "Y"},
                        {"locdate": 20260718, "dateName": "비휴일", "isHoliday": "N"},
                    ]
                }
            }
        }
    }

    assert service._parse_holiday_response(payload) == {"2026-07-17": "제헌절"}


def test_holiday_service_keeps_legacy_kotra_response_compatibility() -> None:
    service = HolidayService(service_key="key", base_url="http://holiday.test")
    payload = {
        "data": [
            {
                "hldyDeFrom": "20260717",
                "hldyName": "제헌절",
                "isoWd2NatCd": "KR",
            },
            {
                "hldyDeFrom": "20260718",
                "hldyName": "임시휴일",
                "isoWd2NatCd": "KR",
            },
        ]
    }

    assert service._parse_holiday_response(payload) == {
        "2026-07-17": "제헌절",
        "2026-07-18": "임시휴일",
    }


def test_holiday_service_uses_kasi_year_and_month_query(monkeypatch) -> None:
    requested_urls: list[str] = []

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def read(self):
            return b'{"data":[]}'

    def fake_urlopen(url, timeout):
        requested_urls.append(url)
        return FakeResponse()

    monkeypatch.setattr("services.holiday_service.urlopen", fake_urlopen)
    service = HolidayService(
        service_key="service-key",
        base_url="http://holiday.test/api",
    )

    assert service.get_holidays_for_month(year=2026, month=7) == {}
    query = parse_qs(urlparse(requested_urls[0]).query)
    assert query["serviceKey"] == ["service-key"]
    assert query["_type"] == ["json"]
    assert query["solYear"] == ["2026"]
    assert query["solMonth"] == ["07"]


def test_holiday_service_filters_range_and_falls_back_on_failure() -> None:
    class FailingHolidayService(HolidayService):
        def _fetch_holidays_for_month(self, *, year: int, month: int):
            raise RuntimeError("api down")

    service = FailingHolidayService(service_key="key", base_url="http://holiday.test")

    assert service.get_holidays_for_range(
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 31),
    ) == {}
