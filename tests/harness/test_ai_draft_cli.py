from typer.testing import CliRunner

from harness.cli import app
from harness.mileday.ai_draft_judge import AiDraftJudgeResult
from harness.mileday.ai_draft_schema import AI_DRAFT_MODEL_ID, AI_DRAFT_PROMPT_VERSION
from harness.runtime.base import RuntimeResponse
from harness.schemas import RuntimeMetrics


def _draft_response() -> str:
    return """
    {
      "goal": {"title": "데이터 분석 과제", "deadline": "2026-09-30"},
      "milestones": [
        {"title": "자료 수집", "scheduled_date": "2026-08-22"},
        {"title": "분석 수행", "scheduled_date": "2026-09-06"},
        {"title": "보고서 정리", "scheduled_date": "2026-09-27"}
      ],
      "planning_preference": {"intensity": "relaxed", "preferred_days": ["saturday", "sunday"]}
    }
    """


def test_test_draft_runs_flash_lite_without_db_write(monkeypatch, tmp_path):
    monkeypatch.setenv("HARNESS_ARTIFACTS_DIR", str(tmp_path / "artifacts"))
    monkeypatch.setenv("HARNESS_RUNS_DIR", str(tmp_path / "artifacts" / "runs"))
    monkeypatch.setenv("GEMINI_API_KEY", "shared-key")
    runtimes = []
    sleeps = []
    progress_events = []

    class FakeTqdm:
        def __init__(self, *, total, desc, unit, dynamic_ncols):
            progress_events.append(("init", total, desc, unit, dynamic_ncols))

        def update(self, count):
            progress_events.append(("update", count))

        def close(self):
            progress_events.append(("close",))

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
                text=_draft_response(),
                metrics=RuntimeMetrics(ttft_ms=1, latency_ms=2, tokens_per_second=3),
                metadata={"provider": "gemini"},
            )

    class MockJudge:
        def __init__(self, api_key, base_url):
            self.api_key = api_key
            self.base_url = base_url

        def evaluate(self, case, draft):
            return AiDraftJudgeResult(is_aligned=True, score=0.95, reason="좋은 초안입니다.")

    monkeypatch.setattr("harness.mileday.ai_draft_runner.GeminiRuntime", MockGeminiRuntime)
    monkeypatch.setattr("harness.mileday.ai_draft_runner.GeminiAiDraftJudge", MockJudge)
    monkeypatch.setattr("harness.mileday.ai_draft_runner.time.sleep", lambda seconds: sleeps.append(seconds))
    monkeypatch.setattr("harness.mileday.ai_draft_runner.tqdm", FakeTqdm)

    result = CliRunner().invoke(app, ["test_draft", "--limit", "1"])

    assert result.exit_code == 0
    assert "| run_id         | prompt-draft-1" in result.stdout
    assert f"| model          | {AI_DRAFT_MODEL_ID}" in result.stdout
    assert f"| prompt_version | {AI_DRAFT_PROMPT_VERSION}" in result.stdout
    assert "| db_write       | disabled" in result.stdout
    assert "| case_pass" in result.stdout
    assert "1/1" in result.stdout
    assert "| passed" in result.stdout
    assert " | 1 " in result.stdout
    assert runtimes[0].api_key == "shared-key"
    assert runtimes[0].requests[0].model_tag == AI_DRAFT_MODEL_ID
    assert isinstance(runtimes[0].requests[0].response_format, dict)
    assert "selected_slot_ids" not in runtimes[0].requests[0].prompt
    assert sleeps == [3.0]
    assert progress_events == [
        ("init", 1, f"{AI_DRAFT_MODEL_ID} MileDay AI draft", "case", True),
        ("update", 1),
        ("close",),
    ]
    run_dir = tmp_path / "artifacts" / "runs" / "prompt-draft-1"
    assert (run_dir / "parsed" / "results.jsonl").exists()
    assert (run_dir / "report.md").exists()
    assert (run_dir / "report.html").exists()
    assert not (run_dir / "db_manifest.json").exists()
    assert (tmp_path / "artifacts" / "runs" / "prompt-draft-1-summary.md").exists()
    assert "report_html" in result.stdout


def test_test_draft_help_and_limit_validation(monkeypatch):
    help_result = CliRunner().invoke(app, ["test_draft", "--help"])
    assert help_result.exit_code == 0
    assert "--limit" in help_result.stdout
    assert "--write-no" not in help_result.stdout

    monkeypatch.setenv("GEMINI_API_KEY", "shared-key")
    invalid_result = CliRunner().invoke(app, ["test_draft", "--limit", "0"])
    assert invalid_result.exit_code != 0
    assert "limit must be positive" in invalid_result.output


def test_test_draft_requires_gemini_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    result = CliRunner().invoke(app, ["test_draft"])

    assert result.exit_code != 0
    assert "GEMINI_API_KEY is required." in result.output
