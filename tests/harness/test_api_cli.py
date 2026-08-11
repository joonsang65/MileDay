from typer.testing import CliRunner

from harness.cli import (
    MILEDAY_API_MODEL_ID,
    MILEDAY_API_MULTITURN_PROMPT_VERSION,
    MILEDAY_API_SLEEP_SECONDS,
    MILEDAY_MULTITURN_FIXTURE,
    app,
)
from harness.mileday.dataset import load_mileday_multiturn_cases
from harness.mileday.explanation_judge import ExplanationJudgeResult
from harness.runtime.base import RuntimeResponse
from harness.schemas import RuntimeMetrics


def _intent_response_for_prompt(prompt: str) -> str:
    action = "부분수정" if "expected_action: partial_update" in prompt else "생성"
    target = "S001" if action == "부분수정" else "전체 일정"
    return (
        "[일정_의도]\n"
        f"행동: {action}\n"
        f"대상: {target}\n"
        "변경: 요청 반영\n"
        "작업:\n"
        "- 기초 준비\n"
        "- 핵심 실행\n"
        "- 최종 점검\n"
        "[/일정_의도]"
    )


def test_test_api_runs_flash_lite_only(monkeypatch, tmp_path):
    monkeypatch.setenv("HARNESS_ARTIFACTS_DIR", str(tmp_path / "artifacts"))
    monkeypatch.setenv("HARNESS_RUNS_DIR", str(tmp_path / "artifacts" / "runs"))
    monkeypatch.setenv("GEMINI_API_KEY", "shared-key")
    fast_cases = load_mileday_multiturn_cases(MILEDAY_MULTITURN_FIXTURE)[:2]
    runtimes = []
    sleeps = []

    class MockJudge:
        def __init__(self, api_key, model, base_url):
            self.api_key = api_key
            self.model = model
            self.base_url = base_url

        def evaluate_multiturn(self, case, turn_id, explanation, parsed_output, previous_output):
            return ExplanationJudgeResult(is_aligned=True, score=0.95, reason="ok")

    class MockGeminiRuntime:
        def __init__(self, api_key, base_url):
            self.api_key = api_key
            self.base_url = base_url
            self.requests = []
            runtimes.append(self)

        def stream(self, request):
            return iter(())

        def generate(self, request):
            self.requests.append(request)
            return RuntimeResponse(
                model_tag=request.model_tag,
                text=_intent_response_for_prompt(request.prompt),
                metrics=RuntimeMetrics(ttft_ms=1, latency_ms=2, tokens_per_second=3),
                metadata={"provider": "gemini"},
            )

    monkeypatch.setattr("harness.mileday.api_runner.GeminiExplanationJudge", MockJudge)
    monkeypatch.setattr("harness.mileday.api_runner.GeminiRuntime", MockGeminiRuntime)
    monkeypatch.setattr("harness.mileday.api_runner.load_mileday_multiturn_cases", lambda _fixture: fast_cases)
    monkeypatch.setattr("harness.mileday.api_runner.time.sleep", lambda seconds: sleeps.append(seconds))

    result = CliRunner().invoke(app, ["test_api", "--limit", "1"])

    assert result.exit_code == 0
    assert "batch_id=prompt-test-1" in result.stdout
    assert f"model={MILEDAY_API_MODEL_ID}" in result.stdout
    assert f"sleep_seconds={MILEDAY_API_SLEEP_SECONDS:g}" in result.stdout
    assert f"prompt_version={MILEDAY_API_MULTITURN_PROMPT_VERSION}" in result.stdout
    assert [runtime.api_key for runtime in runtimes] == ["shared-key"]
    assert [runtime.requests[0].model_tag for runtime in runtimes] == [MILEDAY_API_MODEL_ID]
    assert sleeps == [MILEDAY_API_SLEEP_SECONDS] * 3
    run_dir = tmp_path / "artifacts" / "runs" / "prompt-test-1"
    assert (run_dir / "parsed" / "results.jsonl").exists()
    assert (run_dir / "report.html").exists()
    summary_path = tmp_path / "artifacts" / "runs" / "prompt-test-1-summary.md"
    assert summary_path.exists()
    summary_text = summary_path.read_text(encoding="utf-8")
    assert MILEDAY_API_MODEL_ID in summary_text


def test_test_api_help_exposes_only_limit_option():
    result = CliRunner().invoke(app, ["test_api", "--help"])

    assert result.exit_code == 0
    assert "--limit" in result.stdout
    assert "--model-id" not in result.stdout
    assert "--sleep-seconds" not in result.stdout
    assert "--mode" not in result.stdout


def test_test_api_requires_gemini_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    result = CliRunner().invoke(app, ["test_api"])

    assert result.exit_code != 0
    assert "GEMINI_API_KEY is required." in result.output


def test_test_api_rejects_non_positive_limit(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "shared-key")

    result = CliRunner().invoke(app, ["test_api", "--limit", "0"])

    assert result.exit_code != 0
    assert "limit must be positive" in result.output
