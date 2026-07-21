from pathlib import Path

import pytest

from harness.benchmarks.kmmlu_pro import (
    BENCHMARK_ID,
    KMMLUProDatasetError,
    KMMLUProFieldMapping,
    load_kmmlu_pro_cases,
    score_kmmlu_pro_responses,
)
from harness.schemas import FailureCategory


FIXTURE_PATH = Path("tests/fixtures/benchmarks/kmmlu_pro/synthetic.jsonl")


def test_loads_synthetic_fixture_into_internal_benchmark_cases():
    cases = load_kmmlu_pro_cases(
        FIXTURE_PATH,
        dataset_id="kmmlu-pro-synthetic-v1",
        mapping=KMMLUProFieldMapping(metadata={"source_version": "source_version"}),
    )

    assert len(cases) == 2
    assert cases[0].benchmark_id == BENCHMARK_ID
    assert cases[0].dataset_id == "kmmlu-pro-synthetic-v1"
    assert cases[0].case_id == "synthetic-1"
    assert cases[0].category == "general"
    assert cases[0].question == "Which option is the Korean word for one?"
    assert [choice.label for choice in cases[0].choices] == ["A", "B", "C", "D"]
    assert cases[0].answer == "A"
    assert cases[0].metadata == {"source_version": "synthetic-v1"}


def test_build_prompt_reuses_common_mcq_prompt_builder():
    cases = load_kmmlu_pro_cases(FIXTURE_PATH)
    prompt = cases[0].build_prompt()

    assert "Question:" in prompt
    assert "A. 하나" in prompt
    assert "Answer with exactly one choice label" in prompt


def test_missing_dataset_file_is_dataset_unavailable():
    with pytest.raises(KMMLUProDatasetError) as exc_info:
        load_kmmlu_pro_cases("tests/fixtures/benchmarks/kmmlu_pro/missing.jsonl")

    assert exc_info.value.category == FailureCategory.DATASET_UNAVAILABLE


def test_missing_mapped_required_field_is_schema_changed(tmp_path):
    source = tmp_path / "missing-question.jsonl"
    source.write_text(
        '{"case_id":"case-1","choice_a":"A","choice_b":"B","answer":"A"}\n',
        encoding="utf-8",
    )

    with pytest.raises(KMMLUProDatasetError) as exc_info:
        load_kmmlu_pro_cases(source)

    assert exc_info.value.category == FailureCategory.DATASET_SCHEMA_CHANGED
    assert "question" in exc_info.value.message


def test_invalid_answer_label_is_schema_changed(tmp_path):
    source = tmp_path / "invalid-answer.jsonl"
    source.write_text(
        (
            '{"case_id":"case-1","question":"Pick one.",'
            '"choice_a":"A","choice_b":"B","answer":"J"}\n'
        ),
        encoding="utf-8",
    )

    with pytest.raises(KMMLUProDatasetError) as exc_info:
        load_kmmlu_pro_cases(
            source,
            mapping=KMMLUProFieldMapping(choices={"A": "choice_a", "B": "choice_b"}),
        )

    assert exc_info.value.category == FailureCategory.DATASET_SCHEMA_CHANGED
    assert "answer must match one of the choices" in exc_info.value.message


def test_custom_mapping_is_explicit_and_does_not_infer_fields(tmp_path):
    source = tmp_path / "custom-fields.csv"
    source.write_text(
        "\n".join(
            [
                "id,prompt,opt1,opt2,gold,subject",
                "case-1,Pick the first option.,First,Second,A,synthetic",
            ]
        ),
        encoding="utf-8",
    )
    mapping = KMMLUProFieldMapping(
        case_id="id",
        question="prompt",
        choices={"A": "opt1", "B": "opt2"},
        answer="gold",
        category="subject",
    )

    cases = load_kmmlu_pro_cases(source, mapping=mapping)

    assert cases[0].case_id == "case-1"
    assert cases[0].question == "Pick the first option."
    assert [choice.text for choice in cases[0].choices] == ["First", "Second"]


def test_aggregate_scoring_reuses_common_mcq_scoring():
    cases = load_kmmlu_pro_cases(FIXTURE_PATH)

    report = score_kmmlu_pro_responses(
        cases,
        {
            "synthetic-1": "Answer: A",
            "synthetic-2": "A or B",
        },
    )

    assert report.overall.total == 2
    assert report.overall.correct == 1
    assert report.overall.invalid == 1
    assert report.by_benchmark[BENCHMARK_ID].total == 2
    assert report.by_category["general"].invalid == 1
