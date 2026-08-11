from pathlib import Path

import pytest

from harness.mileday.dataset import (
    DEFAULT_DATASET_ID,
    GOAL_DB_FIELDS,
    MILESTONE_DB_FIELDS,
    MULTITURN_DATASET_ID,
    MileDayDatasetError,
    load_mileday_generation_cases,
    load_mileday_multiturn_cases,
    summarize_mileday_multiturn_fixture_quality,
    validate_mileday_multiturn_fixture_quality,
)
from harness.schemas import FailureCategory


FIXTURE_PATH = Path("tests/fixtures/mileday/synthetic_schedule.jsonl")
MULTITURN_FIXTURE_PATH = Path("tests/fixtures/mileday/multiturn_schedule.jsonl")
MULTITURN_PRETTY_FIXTURE_PATH = Path("tests/fixtures/mileday/multiturn_schedule.pretty.json")


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


def test_loads_multiturn_fixture_with_db_payload_contract_and_required_judge():
    cases = load_mileday_multiturn_cases(MULTITURN_FIXTURE_PATH)

    turn_counts = [len(case.turns) for case in cases]
    domains = {case.metadata["domain"] for case in cases}

    assert len(cases) == 30
    assert cases[0].dataset_id == MULTITURN_DATASET_ID
    assert min(turn_counts) >= 2
    assert max(turn_counts) <= 5
    assert 85 <= sum(turn_counts) <= 95
    assert 2.8 <= sum(turn_counts) / len(turn_counts) <= 3.2
    assert len(domains) == 5

    for case in cases:
        assert case.locale == "ko-KR"
        assert case.timezone == "Asia/Seoul"
        assert case.expected.requires_judge is True
        assert case.expected.partial_update_only is True
        assert case.expected.response_sections in (["EXPLANATION", "JSON"], ["SCHEDULE_INTENT"], ["일정_의도"])
        assert case.expected.db_goal_fields == GOAL_DB_FIELDS
        assert case.expected.db_milestone_fields == MILESTONE_DB_FIELDS
        assert case.expected.constraints.must_preserve_unmentioned_milestones is True
        assert case.expected.constraints.must_require_user_confirmation is True
        assert any(turn.expected_action == "partial_update" for turn in case.turns[1:])
        assert case.metadata["primary_group"]
        assert case.metadata["user_segment"] in {"student", "early_career"}
        assert isinstance(case.metadata["tags"], list)


def test_multiturn_fixture_quality_contract_matches_adr_0009():
    cases = load_mileday_multiturn_cases(MULTITURN_PRETTY_FIXTURE_PATH)

    validate_mileday_multiturn_fixture_quality(cases)
    quality = summarize_mileday_multiturn_fixture_quality(cases)

    assert quality.case_count == 30
    assert quality.total_turns == 90
    assert quality.average_turns == 3.0
    assert quality.primary_group_counts == {
        "add_remove": 5,
        "ambiguous": 3,
        "basic_creation": 6,
        "conflict": 5,
        "partial_update": 7,
        "state_preservation": 4,
    }
    assert quality.user_segment_counts == {"early_career": 15, "student": 15}
    assert all(count == 6 for count in quality.domain_counts.values())


def test_loads_pretty_multiturn_fixture_json():
    compact_cases = load_mileday_multiturn_cases(MULTITURN_FIXTURE_PATH)
    pretty_cases = load_mileday_multiturn_cases(MULTITURN_PRETTY_FIXTURE_PATH)

    assert [case.case_id for case in pretty_cases] == [case.case_id for case in compact_cases]
    assert pretty_cases[0].turns[0].content == compact_cases[0].turns[0].content


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
