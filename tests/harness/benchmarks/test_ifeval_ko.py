from pathlib import Path

import pytest

from harness.benchmarks.ifeval_ko import (
    BENCHMARK_ID,
    IFEvalKoDatasetError,
    IFEvalKoFieldMapping,
    check_official_evaluator_available,
    load_ifeval_ko_cases,
    score_ifeval_ko_responses,
)
from harness.schemas import FailureCategory


FIXTURE_PATH = Path("tests/fixtures/benchmarks/ifeval_ko/synthetic.jsonl")


def test_loads_synthetic_fixture_into_instruction_following_cases():
    cases = load_ifeval_ko_cases(
        FIXTURE_PATH,
        dataset_id="ifeval-ko-synthetic-v1",
        mapping=IFEvalKoFieldMapping(metadata={"source_version": "source_version"}),
    )

    assert len(cases) == 2
    assert cases[0].benchmark_id == BENCHMARK_ID
    assert cases[0].dataset_id == "ifeval-ko-local"
    assert cases[0].case_id == "synthetic-1"
    assert cases[0].prompt == "Write exactly two bullet points without commas."
    assert cases[0].instruction_ids == [
        "punctuation:no_comma",
        "detectable_format:number_bullet_lists",
    ]
    assert cases[0].kwargs == [{}, {"num_bullets": 2}]
    assert cases[0].metadata == {"source_version": "synthetic-v1"}


def test_build_prompt_returns_prompt_without_mcq_formatting():
    cases = load_ifeval_ko_cases(FIXTURE_PATH)

    assert cases[0].build_prompt() == "Write exactly two bullet points without commas."
    assert "Choices:" not in cases[0].build_prompt()


def test_missing_dataset_file_is_dataset_unavailable():
    with pytest.raises(IFEvalKoDatasetError) as exc_info:
        load_ifeval_ko_cases("tests/fixtures/benchmarks/ifeval_ko/missing.jsonl")

    assert exc_info.value.category == FailureCategory.DATASET_UNAVAILABLE


def test_custom_mapping_is_explicit_and_does_not_infer_fields(tmp_path):
    source = tmp_path / "custom-fields.jsonl"
    source.write_text(
        (
            '{"key":101,"prompt_text":"Avoid commas.",'
            '"ids":["punctuation:no_comma"],"args":[{}],"source":"synthetic"}\n'
        ),
        encoding="utf-8",
    )
    mapping = IFEvalKoFieldMapping(
        case_id="key",
        prompt="prompt_text",
        instruction_ids="ids",
        kwargs="args",
        benchmark_id=None,
        dataset_id=None,
        metadata={"source": "source"},
    )

    cases = load_ifeval_ko_cases(source, dataset_id="custom-dataset", mapping=mapping)

    assert cases[0].case_id == "101"
    assert cases[0].dataset_id == "custom-dataset"
    assert cases[0].instruction_ids == ["punctuation:no_comma"]
    assert cases[0].metadata == {"source": "synthetic"}


def test_csv_mapping_decodes_jsonish_list_fields(tmp_path):
    source = tmp_path / "custom-fields.csv"
    source.write_text(
        "\n".join(
            [
                "case_id,prompt,instruction_ids,kwargs",
                'case-1,Avoid commas.,"[""punctuation:no_comma""]","[{}]"',
            ]
        ),
        encoding="utf-8",
    )

    cases = load_ifeval_ko_cases(source)

    assert cases[0].instruction_ids == ["punctuation:no_comma"]
    assert cases[0].kwargs == [{}]


def test_missing_mapped_required_field_is_schema_changed(tmp_path):
    source = tmp_path / "missing-prompt.jsonl"
    source.write_text(
        '{"case_id":"case-1","instruction_ids":["punctuation:no_comma"],"kwargs":[{}]}\n',
        encoding="utf-8",
    )

    with pytest.raises(IFEvalKoDatasetError) as exc_info:
        load_ifeval_ko_cases(source)

    assert exc_info.value.category == FailureCategory.DATASET_SCHEMA_CHANGED
    assert "not a supported mapped instruction-following row" in exc_info.value.message
    assert "prompt" in exc_info.value.message


def test_unsupported_non_instruction_following_row_is_schema_changed(tmp_path):
    source = tmp_path / "unsupported.jsonl"
    source.write_text(
        '{"case_id":"case-1","question":"Pick one.","choice_a":"A","answer":"A"}\n',
        encoding="utf-8",
    )

    with pytest.raises(IFEvalKoDatasetError) as exc_info:
        load_ifeval_ko_cases(source)

    assert exc_info.value.category == FailureCategory.DATASET_SCHEMA_CHANGED
    assert "instruction-following row" in exc_info.value.message
    assert "instruction_ids" in exc_info.value.message


def test_invalid_jsonl_is_schema_changed(tmp_path):
    source = tmp_path / "invalid.jsonl"
    source.write_text('{"case_id": "case-1"\n', encoding="utf-8")

    with pytest.raises(IFEvalKoDatasetError) as exc_info:
        load_ifeval_ko_cases(source)

    assert exc_info.value.category == FailureCategory.DATASET_SCHEMA_CHANGED
    assert "Invalid JSONL" in exc_info.value.message


def test_kwargs_length_must_match_instruction_ids(tmp_path):
    source = tmp_path / "mismatch.jsonl"
    source.write_text(
        (
            '{"case_id":"case-1","prompt":"Avoid commas.",'
            '"instruction_ids":["punctuation:no_comma"],"kwargs":[{},{}]}\n'
        ),
        encoding="utf-8",
    )

    with pytest.raises(IFEvalKoDatasetError) as exc_info:
        load_ifeval_ko_cases(source)

    assert exc_info.value.category == FailureCategory.DATASET_SCHEMA_CHANGED
    assert "kwargs length must match" in exc_info.value.message


def test_official_scoring_preserves_raw_output_and_aggregates_results():
    cases = load_ifeval_ko_cases(FIXTURE_PATH)

    report = score_ifeval_ko_responses(
        cases,
        {
            "synthetic-1": "- First item\n- Second item",
            "synthetic-2": "word word word word word",
        },
    )
    result = cases[0].score_response("- First item\n- Second item")

    assert result.raw_output == "- First item\n- Second item"
    assert result.prompt_level_strict is True
    assert result.prompt_level_loose is True
    assert report.overall.total == 2
    assert report.overall.invalid == 0
    assert report.overall.prompt_level_strict_accuracy == 1.0
    assert report.overall.inst_level_strict_accuracy == 1.0
    assert report.by_benchmark[BENCHMARK_ID].total == 2


def test_unknown_instruction_id_is_schema_changed(tmp_path):
    source = tmp_path / "unsupported-instruction.jsonl"
    source.write_text(
        (
            '{"case_id":"case-1","prompt":"Do something.",'
            '"instruction_ids":["unknown:instruction"],"kwargs":[{}]}\n'
        ),
        encoding="utf-8",
    )
    case = load_ifeval_ko_cases(source)[0]

    with pytest.raises(IFEvalKoDatasetError) as exc_info:
        case.score_response("Any response")

    assert exc_info.value.category == FailureCategory.DATASET_SCHEMA_CHANGED
    assert "Official IFEval-Ko evaluator rejected case" in exc_info.value.message


def test_official_evaluator_boundary_is_available():
    status = check_official_evaluator_available()

    assert status.available is True
    assert status.module == "lm_eval.tasks.ifeval_ko.utils"
