import json

import pytest

import harness.dataset_processor as dataset_processor
from harness.dataset_registry import DatasetConfig
from harness.dataset_processor import (
    DatasetProcessingError,
    _answer_from_choice_text,
    _answer_from_one_based_value,
    load_prepared_dataset_rows,
    _parse_labeled_choices,
)
from harness.schemas import FailureCategory


def test_answer_from_one_based_value_converts_to_label():
    assert _answer_from_one_based_value("1", 4, 1) == "A"
    assert _answer_from_one_based_value("4", 4, 1) == "D"
    assert _answer_from_one_based_value("B", 4, 1) == "B"


def test_answer_from_one_based_value_rejects_out_of_range():
    with pytest.raises(DatasetProcessingError) as exc_info:
        _answer_from_one_based_value("5", 4, 1)

    assert exc_info.value.category == FailureCategory.DATASET_SCHEMA_CHANGED


def test_answer_from_choice_text_maps_exact_choice():
    assert _answer_from_choice_text("Seoul", ["Busan", "Seoul"], 1) == "B"


def test_answer_from_choice_text_rejects_unknown_answer():
    with pytest.raises(DatasetProcessingError) as exc_info:
        _answer_from_choice_text("Daegu", ["Busan", "Seoul"], 1)

    assert exc_info.value.category == FailureCategory.DATASET_SCHEMA_CHANGED


def test_parse_labeled_choices_reads_a_to_j_lines():
    choices = _parse_labeled_choices("Question\n\nA: first\nB: second\nC: third\n", 1)

    assert choices == {"A": "first", "B": "second", "C": "third"}


def test_load_prepared_dataset_rows_reads_processed_jsonl(monkeypatch, tmp_path):
    monkeypatch.setattr(dataset_processor, "BASE_DIR", tmp_path)
    processed_path = tmp_path / "datasets" / "kobalt-700" / "rev-1" / "processed" / "data.jsonl"
    processed_path.parent.mkdir(parents=True)
    processed_path.write_text(
        json.dumps({"case_id": "case-1", "question": "Q", "answer": "A"}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    config = DatasetConfig(
        dataset_id="snunlp/KoBALT-700",
        source_url="https://example.test/kobalt",
        official_repository="https://example.test/repo",
        revision="rev-1",
        config="kobalt_v1",
        split="raw",
        license="cc-by-nc-4.0",
        commercial_use_verified=False,
        fields={"question": "Question", "answer": "Answer"},
    )

    loaded = load_prepared_dataset_rows("kobalt", config)

    assert loaded.source_path == processed_path
    assert loaded.rows == [{"case_id": "case-1", "question": "Q", "answer": "A"}]
