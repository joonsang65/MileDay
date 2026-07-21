import pytest
from pydantic import ValidationError

from harness.benchmarks.mcq import (
    MCQChoice,
    MCQParseStatus,
    MCQQuestion,
    aggregate_mcq_results,
    build_mcq_prompt,
    parse_mcq_answer,
    score_mcq_response,
)


def _question(**overrides):
    data = {
        "benchmark_id": "sample-benchmark",
        "case_id": "case-1",
        "category": "reasoning",
        "question": "Which option is correct?",
        "choices": [
            MCQChoice(label="A", text="First"),
            MCQChoice(label="B", text="Second"),
            MCQChoice(label="C", text="Third"),
        ],
        "answer": "B",
    }
    data.update(overrides)
    return MCQQuestion(**data)


def test_prompt_builder_renders_question_and_choices():
    prompt = build_mcq_prompt(_question())

    assert "Question:" in prompt
    assert "Which option is correct?" in prompt
    assert "A. First" in prompt
    assert "B. Second" in prompt
    assert "Answer with exactly one choice label" in prompt


@pytest.mark.parametrize(
    ("raw_output", "expected"),
    [
        ("B", "B"),
        ("Answer: b", "B"),
        ("The answer is (J).", "J"),
    ],
)
def test_parser_accepts_a_to_j_single_answer_choices(raw_output, expected):
    parsed = parse_mcq_answer(raw_output)

    assert parsed.status == MCQParseStatus.PARSED
    assert parsed.parsed_answer == expected


@pytest.mark.parametrize(
    "raw_output",
    [
        "The answer could be A or B.",
        "A, B",
        "I cannot determine the answer.",
    ],
)
def test_parser_marks_ambiguous_or_missing_answers_invalid(raw_output):
    parsed = parse_mcq_answer(raw_output)

    assert parsed.status == MCQParseStatus.INVALID
    assert parsed.parsed_answer is None
    assert parsed.invalid_reason is not None


def test_score_mcq_response_preserves_invalid_raw_output():
    result = score_mcq_response(_question(), "B or C")

    assert result.raw_output == "B or C"
    assert result.is_invalid is True
    assert result.is_correct is False
    assert result.invalid_reason == "Multiple distinct answer choices found."


def test_score_mcq_response_marks_correct_answers():
    result = score_mcq_response(_question(), "Answer: B")

    assert result.is_invalid is False
    assert result.is_correct is True
    assert result.parsed_answer == "B"


def test_aggregate_supports_benchmark_and_category_metrics():
    results = [
        score_mcq_response(_question(case_id="case-1", category="reasoning"), "B"),
        score_mcq_response(_question(case_id="case-2", category="reasoning"), "A"),
        score_mcq_response(
            _question(
                benchmark_id="other-benchmark",
                case_id="case-3",
                category="knowledge",
            ),
            "A or B",
        ),
    ]

    report = aggregate_mcq_results(results)

    assert report.overall.total == 3
    assert report.overall.correct == 1
    assert report.overall.invalid == 1
    assert report.overall.accuracy == pytest.approx(1 / 3)
    assert report.overall.invalid_rate == pytest.approx(1 / 3)
    assert report.by_benchmark["sample-benchmark"].total == 2
    assert report.by_category["reasoning"].total == 2
    assert report.by_category["knowledge"].invalid == 1


def test_question_rejects_duplicate_labels_and_answers_outside_choices():
    with pytest.raises(ValidationError, match="choice labels must be unique"):
        _question(
            choices=[
                MCQChoice(label="A", text="First"),
                MCQChoice(label="A", text="Duplicate"),
            ],
            answer="A",
        )

    with pytest.raises(ValidationError, match="answer must match one of the choices"):
        _question(answer="J")

