import httpx

from harness.mileday.explanation_judge import (
    GeminiExplanationJudge,
    build_batch_quality_summary_prompt,
    skipped_explanation_judge_result,
)
from harness.mileday.dataset import load_mileday_generation_cases


def test_gemini_explanation_judge_parses_structured_response(monkeypatch):
    case = load_mileday_generation_cases("tests/fixtures/mileday/synthetic_schedule.jsonl")[0]

    class MockResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "text": (
                                        '{"is_aligned": true, "score": 0.92, '
                                        '"reason": "The explanation matches the milestones."}'
                                    )
                                }
                            ]
                        }
                    }
                ]
            }

    calls = []

    def mock_post(url, headers, json, timeout):
        calls.append((url, headers, json, timeout))
        return MockResponse()

    monkeypatch.setattr("harness.mileday.explanation_judge.httpx.post", mock_post)

    judge = GeminiExplanationJudge(api_key="secret", model="gemini-test", base_url="https://example.test/v1")
    result = judge.evaluate(
        case,
        "자격증 시험 준비를 위해 계획, 문제 풀이, 최종 점검을 배치했습니다.",
        {"milestones": [{"title": "계획", "scheduled_date": "2026-09-01"}]},
    )

    assert result.is_aligned is True
    assert result.score == 0.92
    assert calls[0][0] == "https://example.test/v1/models/gemini-test:generateContent"
    assert calls[0][1]["x-goog-api-key"] == "secret"
    assert calls[0][2]["generationConfig"]["responseMimeType"] == "application/json"
    assert calls[0][2]["generationConfig"]["responseSchema"]["required"] == [
        "is_aligned",
        "score",
        "reason",
    ]


def test_gemini_explanation_judge_retries_transient_503(monkeypatch):
    case = load_mileday_generation_cases("tests/fixtures/mileday/synthetic_schedule.jsonl")[0]
    calls = []
    sleeps = []

    class MockResponse:
        def __init__(self, status_code: int):
            self.status_code = status_code
            self.text = '{"error": {"message": "temporary"}}'

        def raise_for_status(self):
            if self.status_code >= 400:
                request = httpx.Request("POST", "https://example.test/v1/models/gemini-test:generateContent")
                response = httpx.Response(self.status_code, request=request, text=self.text)
                raise httpx.HTTPStatusError("temporary", request=request, response=response)

        def json(self):
            return {
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "text": (
                                        '{"is_aligned": true, "score": 0.91, '
                                        '"reason": "retry succeeded"}'
                                    )
                                }
                            ]
                        }
                    }
                ]
            }

    def mock_post(url, headers, json, timeout):
        calls.append((url, headers, json, timeout))
        return MockResponse(503 if len(calls) < 3 else 200)

    monkeypatch.setattr("harness.mileday.explanation_judge.httpx.post", mock_post)
    monkeypatch.setattr("harness.mileday.explanation_judge.sleep", lambda seconds: sleeps.append(seconds))

    judge = GeminiExplanationJudge(api_key="secret", model="gemini-test", base_url="https://example.test/v1")
    result = judge.evaluate(case, "설명", {"milestones": []})

    assert result.is_aligned is True
    assert result.score == 0.91
    assert len(calls) == 3
    assert sleeps == [0.5, 1.0, 2.0]


def test_skipped_explanation_judge_result_is_non_blocking():
    result = skipped_explanation_judge_result()

    assert result.skipped is True
    assert result.is_aligned is True


def test_gemini_batch_quality_summary_uses_selected_prompt_and_schema(monkeypatch):
    class MockResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "text": (
                                        '{"overall_summary": "candidate-3이 가장 안정적입니다.", '
                                        '"risk_signals": ["invalid가 있습니다."], '
                                        '"improvement_actions": ["프롬프트를 보강하세요."]}'
                                    )
                                }
                            ]
                        }
                    }
                ]
            }

    calls = []

    def mock_post(url, headers, json, timeout):
        calls.append((url, headers, json, timeout))
        return MockResponse()

    monkeypatch.setattr("harness.mileday.explanation_judge.httpx.post", mock_post)

    context = {
        "batch_id": "batch-1-5cases",
        "judge_execution_counts": {"completed": 2, "failed": 0, "skipped": 1},
        "model_summaries": [],
    }
    prompt = build_batch_quality_summary_prompt(context)
    judge = GeminiExplanationJudge(api_key="secret", model="gemini-test", base_url="https://example.test/v1")
    result = judge.summarize_batch_quality(context)

    assert "품질 분석가" in prompt
    assert "데이터에 없는 사실" in prompt
    assert result.overall_summary == "candidate-3이 가장 안정적입니다."
    assert result.risk_signals == ["invalid가 있습니다."]
    assert result.improvement_actions == ["프롬프트를 보강하세요."]
    schema = calls[0][2]["generationConfig"]["responseSchema"]
    assert schema["required"] == ["overall_summary", "risk_signals", "improvement_actions"]
