import json

import httpx

from harness.mileday.ai_draft_judge import (
    AiDraftJudgeResult,
    GeminiAiDraftJudge,
    build_ai_draft_judge_prompt,
)
from harness.mileday.dataset import load_ai_schedule_draft_cases


def test_ai_draft_judge_result_normalizes_five_point_score():
    result = AiDraftJudgeResult(is_aligned=True, score=5, reason="좋음")

    assert result.score == 1.0


def test_ai_draft_judge_prompt_requires_zero_to_one_score():
    case = load_ai_schedule_draft_cases("tests/fixtures/mileday/ai_schedule_draft.json")[0]

    prompt = build_ai_draft_judge_prompt(case, {"goal": {}, "milestones": []})

    assert "0.0~1.0" in prompt
    assert "5점 만점 척도를 사용하지 않는다" in prompt


def test_gemini_ai_draft_judge_parses_and_normalizes_five_point_response(monkeypatch):
    captured = {}

    def mock_post(*args, **kwargs):
        captured["payload"] = kwargs["json"]
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "text": json.dumps(
                                        {
                                            "is_aligned": True,
                                            "score": 5.0,
                                            "reason": "좋은 초안입니다.",
                                            "critical_failures": [],
                                        },
                                        ensure_ascii=False,
                                    )
                                }
                            ]
                        }
                    }
                ]
            },
            request=httpx.Request("POST", "https://example.test"),
        )

    monkeypatch.setattr("harness.mileday.ai_draft_judge.httpx.post", mock_post)
    case = load_ai_schedule_draft_cases("tests/fixtures/mileday/ai_schedule_draft.json")[0]
    judge = GeminiAiDraftJudge(api_key="secret", model="gemini-test", base_url="https://example.test/v1")

    result = judge.evaluate(case, {"goal": {}, "milestones": []})

    assert result.error is None
    assert result.score == 1.0
    assert result.is_aligned is True
    assert captured["payload"]["generationConfig"]["responseSchema"]["properties"]["score"]["maximum"] == 1
