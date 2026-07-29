from pathlib import Path

import pytest

from harness.mileday.dataset import (
    DEFAULT_DATASET_ID,
    MileDayDatasetError,
    load_mileday_generation_cases,
)
from harness.schemas import FailureCategory


FIXTURE_PATH = Path("tests/fixtures/mileday/synthetic_schedule.jsonl")


def test_loads_synthetic_fixture_cases_without_network_or_app_state():
    cases = load_mileday_generation_cases(FIXTURE_PATH)

    assert len(cases) == 20
    assert cases[0].dataset_id == DEFAULT_DATASET_ID
    assert cases[0].case_id == "synthetic-1"
    assert cases[0].locale == "ko-KR"
    assert cases[0].timezone == "Asia/Seoul"
    assert cases[0].input.goal_title == "Prepare certification exam"
    assert cases[0].input.deadline == "2026-09-30"
    assert cases[0].input.constraints == {
        "workdays_only": True,
        "avoid_weekends": True,
    }
    assert cases[0].expected.min_milestones == 3
    assert cases[0].expected.max_milestones == 6
    assert cases[0].expected.latest_allowed_date == "2026-09-30"
    assert cases[0].expected.required_fields == ["title", "scheduled_date"]
    assert cases[0].metadata == {"source": "synthetic", "version": "v1", "domain": "study"}


def test_json_array_multi_case_loading(tmp_path):
    source = tmp_path / "cases.json"
    source.write_text(
        """
        [
          {
            "dataset_id": "mileday-schedule",
            "case_id": "case-1",
            "locale": "ko-KR",
            "timezone": "Asia/Seoul",
            "input": {
              "goal_title": "Build a study plan",
              "deadline": "2026-08-31",
              "constraints": {}
            },
            "expected": {
              "min_milestones": 1,
              "max_milestones": 3,
              "latest_allowed_date": "2026-08-31",
              "required_fields": []
            },
            "metadata": {}
          },
          {
            "dataset_id": "mileday-schedule",
            "case_id": "case-2",
            "locale": "en-US",
            "timezone": "UTC",
            "input": {
              "goal_title": "Build a travel checklist",
              "deadline": "2026-12-01",
              "constraints": {"recurrence": "none"}
            },
            "expected": {
              "min_milestones": 2,
              "max_milestones": 4,
              "latest_allowed_date": "2026-12-01",
              "required_fields": ["title"]
            },
            "metadata": {"source": "synthetic"}
          }
        ]
        """,
        encoding="utf-8",
    )

    cases = load_mileday_generation_cases(source)

    assert [case.case_id for case in cases] == ["case-1", "case-2"]
    assert cases[1].locale == "en-US"
    assert cases[1].timezone == "UTC"


def test_missing_fixture_file_is_dataset_unavailable():
    with pytest.raises(MileDayDatasetError) as exc_info:
        load_mileday_generation_cases("tests/fixtures/mileday/missing.jsonl")

    assert exc_info.value.category == FailureCategory.DATASET_UNAVAILABLE


def test_invalid_jsonl_is_dataset_schema_changed(tmp_path):
    source = tmp_path / "broken.jsonl"
    source.write_text('{"dataset_id":"mileday-schedule"\n', encoding="utf-8")

    with pytest.raises(MileDayDatasetError) as exc_info:
        load_mileday_generation_cases(source)

    assert exc_info.value.category == FailureCategory.DATASET_SCHEMA_CHANGED


def test_missing_required_field_is_dataset_schema_changed(tmp_path):
    source = tmp_path / "missing-field.jsonl"
    source.write_text(
        (
            '{"dataset_id":"mileday-schedule","case_id":"case-1",'
            '"locale":"ko-KR","timezone":"Asia/Seoul",'
            '"input":{"goal_title":"Plan","deadline":"2026-09-01","constraints":{}},'
            '"metadata":{}}\n'
        ),
        encoding="utf-8",
    )

    with pytest.raises(MileDayDatasetError) as exc_info:
        load_mileday_generation_cases(source)

    assert exc_info.value.category == FailureCategory.DATASET_SCHEMA_CHANGED
    assert "expected" in exc_info.value.message


def test_invalid_date_is_dataset_schema_changed(tmp_path):
    source = tmp_path / "invalid-date.jsonl"
    source.write_text(
        (
            '{"dataset_id":"mileday-schedule","case_id":"case-1",'
            '"locale":"ko-KR","timezone":"Asia/Seoul",'
            '"input":{"goal_title":"Plan","deadline":"2026-02-30","constraints":{}},'
            '"expected":{"min_milestones":1,"max_milestones":3,'
            '"latest_allowed_date":"2026-09-01","required_fields":[]},'
            '"metadata":{}}\n'
        ),
        encoding="utf-8",
    )

    with pytest.raises(MileDayDatasetError) as exc_info:
        load_mileday_generation_cases(source)

    assert exc_info.value.category == FailureCategory.DATASET_SCHEMA_CHANGED
    assert "valid calendar date" in exc_info.value.message


def test_invalid_milestone_bounds_are_dataset_schema_changed(tmp_path):
    source = tmp_path / "invalid-bounds.jsonl"
    source.write_text(
        (
            '{"dataset_id":"mileday-schedule","case_id":"case-1",'
            '"locale":"ko-KR","timezone":"Asia/Seoul",'
            '"input":{"goal_title":"Plan","deadline":"2026-09-01","constraints":{}},'
            '"expected":{"min_milestones":5,"max_milestones":3,'
            '"latest_allowed_date":"2026-09-01","required_fields":[]},'
            '"metadata":{}}\n'
        ),
        encoding="utf-8",
    )

    with pytest.raises(MileDayDatasetError) as exc_info:
        load_mileday_generation_cases(source)

    assert exc_info.value.category == FailureCategory.DATASET_SCHEMA_CHANGED
    assert "max_milestones" in exc_info.value.message


def test_invalid_required_fields_are_dataset_schema_changed(tmp_path):
    source = tmp_path / "invalid-required-fields.jsonl"
    source.write_text(
        (
            '{"dataset_id":"mileday-schedule","case_id":"case-1",'
            '"locale":"ko-KR","timezone":"Asia/Seoul",'
            '"input":{"goal_title":"Plan","deadline":"2026-09-01","constraints":{}},'
            '"expected":{"min_milestones":1,"max_milestones":3,'
            '"latest_allowed_date":"2026-09-01","required_fields":["title"," "]},'
            '"metadata":{}}\n'
        ),
        encoding="utf-8",
    )

    with pytest.raises(MileDayDatasetError) as exc_info:
        load_mileday_generation_cases(source)

    assert exc_info.value.category == FailureCategory.DATASET_SCHEMA_CHANGED
    assert "required_fields" in exc_info.value.message


def test_invalid_dataset_id_is_dataset_schema_changed(tmp_path):
    source = tmp_path / "invalid-dataset-id.jsonl"
    source.write_text(
        (
            '{"dataset_id":"other","case_id":"case-1",'
            '"locale":"ko-KR","timezone":"Asia/Seoul",'
            '"input":{"goal_title":"Plan","deadline":"2026-09-01","constraints":{}},'
            '"expected":{"min_milestones":1,"max_milestones":3,'
            '"latest_allowed_date":"2026-09-01","required_fields":[]},'
            '"metadata":{}}\n'
        ),
        encoding="utf-8",
    )

    with pytest.raises(MileDayDatasetError) as exc_info:
        load_mileday_generation_cases(source)

    assert exc_info.value.category == FailureCategory.DATASET_SCHEMA_CHANGED
    assert "dataset_id" in exc_info.value.message
