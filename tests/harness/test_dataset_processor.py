import pytest

from harness.dataset_processor import (
    DatasetProcessingError,
    _answer_from_choice_text,
    _answer_from_one_based_value,
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
