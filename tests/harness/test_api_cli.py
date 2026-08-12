from typer.testing import CliRunner

from harness.cli import (
    MILEDAY_API_MODEL_ID,
    MILEDAY_API_MULTITURN_PROMPT_VERSION,
    MILEDAY_API_SLEEP_SECONDS,
    MILEDAY_MULTITURN_FIXTURE,
    app,
)
from harness.mileday.api_runner import _apply_db_write_record_to_create_state
from harness.mileday.api_db_manifest import new_api_db_write_record
from harness.mileday.dataset import load_mileday_multiturn_cases
from harness.mileday.explanation_judge import ExplanationJudgeResult
from harness.runtime.base import RuntimeResponse
from harness.schemas import RuntimeMetrics


def _intent_response_for_prompt(prompt: str) -> str:
    action = "부분수정" if "expected_action: partial_update" in prompt else "생성"
    operation = "none"
    if action == "부분수정":
        operation = "add" if "추가" in prompt else "rename"
    target = "S001" if action == "부분수정" else "전체 일정"
    return (
        "[일정_의도]\n"
        f"행동: {action}\n"
        f"operation: {operation}\n"
        f"대상: {target}\n"
        f"target_selector_type: {'slot_id' if action == '부분수정' else 'ambiguous'}\n"
        f"target_selector_value: {target}\n"
        "target_selector_confidence: high\n"
        "preserve_selector_type: none\n"
        "preserve_selector_values: none\n"
        "requires_clarification: false\n"
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
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-role")
    monkeypatch.setenv("TEST_USER_ID", "user-1")
    monkeypatch.setenv("TEST_TITLE_PREFIX", "[TEST]")
    fast_cases = load_mileday_multiturn_cases(MILEDAY_MULTITURN_FIXTURE)[:2]
    runtimes = []
    sleeps = []
    db_writes = []

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

    class MockApiDbWriter:
        def __init__(self):
            self.user_id = "user-1"

        @classmethod
        def from_settings(cls, settings):
            assert settings.supabase_url == "https://example.supabase.co"
            assert settings.supabase_service_role_key == "service-role"
            assert settings.test_user_id == "user-1"
            assert settings.test_title_prefix == "[TEST]"
            return cls()

        def insert_create_payload(self, *, run_id, case_id, turn_id, payload, plan_items):
            db_writes.append(
                {
                    "operation": "create",
                    "run_id": run_id,
                    "case_id": case_id,
                    "turn_id": turn_id,
                    "payload": payload,
                    "plan_items": plan_items,
                }
            )
            return new_api_db_write_record(
                operation="create",
                run_id=run_id,
                case_id=case_id,
                turn_id=turn_id,
                goal_id="goal-1",
                milestone_ids=["milestone-1"],
                milestone_slot_ids={"S001": "milestone-1"},
                goal_title="[TEST] goal",
                milestone_titles={"S001": "[TEST] milestone"},
                user_id=self.user_id,
            )

        def update_partial_payload(self, *, run_id, case_id, turn_id, create_record, parsed_json):
            db_writes.append(
                {
                    "operation": "partial_update",
                    "run_id": run_id,
                    "case_id": case_id,
                    "turn_id": turn_id,
                    "create_record": create_record,
                    "parsed_json": parsed_json,
                }
            )
            return new_api_db_write_record(
                operation="partial_update",
                run_id=run_id,
                case_id=case_id,
                turn_id=turn_id,
                goal_id="goal-1",
                milestone_ids=["milestone-1"],
                milestone_slot_ids={"S001": "milestone-1"},
                goal_title="[TEST] goal",
                milestone_titles={"S001": "[TEST] milestone updated"},
                user_id=self.user_id,
            )

    monkeypatch.setattr("harness.mileday.api_runner.GeminiExplanationJudge", MockJudge)
    monkeypatch.setattr("harness.mileday.api_runner.GeminiRuntime", MockGeminiRuntime)
    monkeypatch.setattr("harness.mileday.api_runner.ApiDbWriter", MockApiDbWriter)
    monkeypatch.setattr("harness.mileday.api_runner.load_mileday_multiturn_cases", lambda _fixture: fast_cases)
    monkeypatch.setattr("harness.mileday.api_runner.time.sleep", lambda seconds: sleeps.append(seconds))

    result = CliRunner().invoke(app, ["test_api", "--limit", "1"])

    assert result.exit_code == 0
    assert "batch_id=prompt-test-1" in result.stdout
    assert f"model={MILEDAY_API_MODEL_ID}" in result.stdout
    assert f"sleep_seconds={MILEDAY_API_SLEEP_SECONDS:g}" in result.stdout
    assert "db_write=enabled" in result.stdout
    assert f"prompt_version={MILEDAY_API_MULTITURN_PROMPT_VERSION}" in result.stdout
    assert "case_pass=1/1 passed=" in result.stdout
    assert [runtime.api_key for runtime in runtimes] == ["shared-key"]
    assert [runtime.requests[0].model_tag for runtime in runtimes] == [MILEDAY_API_MODEL_ID]
    assert runtimes[0].requests[0].options == {"thinking_level": "minimal"}
    assert isinstance(runtimes[0].requests[0].response_format, dict)
    assert runtimes[0].requests[0].response_format["properties"]["operation"]["enum"] == [
        "add",
        "remove",
        "rename",
        "none",
    ]
    expected_turn_count = len(fast_cases[0].turns)
    assert sleeps == [MILEDAY_API_SLEEP_SECONDS] * expected_turn_count
    assert len(db_writes) == expected_turn_count
    assert db_writes[0]["turn_id"] == 1
    assert [write["operation"] for write in db_writes] == ["create", "partial_update"]
    run_dir = tmp_path / "artifacts" / "runs" / "prompt-test-1"
    assert (run_dir / "parsed" / "results.jsonl").exists()
    assert (run_dir / "db_manifest.json").exists()
    assert (run_dir / "report.html").exists()
    summary_path = tmp_path / "artifacts" / "runs" / "prompt-test-1-summary.md"
    assert summary_path.exists()
    summary_text = summary_path.read_text(encoding="utf-8")
    assert MILEDAY_API_MODEL_ID in summary_text
    assert "self-check mismatches" in summary_text


def test_test_api_help_exposes_only_limit_option():
    result = CliRunner().invoke(app, ["test_api", "--help"])

    assert result.exit_code == 0
    assert "--limit" in result.stdout
    assert "--write-no" in result.stdout
    assert "--model-id" not in result.stdout
    assert "--sleep-seconds" not in result.stdout
    assert "--mode" not in result.stdout


def test_test_api_write_no_skips_db_writer(monkeypatch, tmp_path):
    monkeypatch.setenv("HARNESS_ARTIFACTS_DIR", str(tmp_path / "artifacts"))
    monkeypatch.setenv("HARNESS_RUNS_DIR", str(tmp_path / "artifacts" / "runs"))
    monkeypatch.setenv("GEMINI_API_KEY", "shared-key")
    fast_cases = load_mileday_multiturn_cases(MILEDAY_MULTITURN_FIXTURE)[:1]

    class MockJudge:
        def __init__(self, api_key, model, base_url):
            pass

        def evaluate_multiturn(self, case, turn_id, explanation, parsed_output, previous_output):
            return ExplanationJudgeResult(is_aligned=True, score=0.95, reason="ok")

    class MockGeminiRuntime:
        def __init__(self, api_key, base_url):
            pass

        def stream(self, request):
            return iter(())

        def generate(self, request):
            return RuntimeResponse(
                model_tag=request.model_tag,
                text=_intent_response_for_prompt(request.prompt),
                metrics=RuntimeMetrics(ttft_ms=1, latency_ms=2, tokens_per_second=3),
                metadata={"provider": "gemini"},
            )

    class FailApiDbWriter:
        @classmethod
        def from_settings(cls, settings):
            raise AssertionError("DB writer must not be created when --write-no is set")

    monkeypatch.setattr("harness.mileday.api_runner.GeminiExplanationJudge", MockJudge)
    monkeypatch.setattr("harness.mileday.api_runner.GeminiRuntime", MockGeminiRuntime)
    monkeypatch.setattr("harness.mileday.api_runner.ApiDbWriter", FailApiDbWriter)
    monkeypatch.setattr("harness.mileday.api_runner.load_mileday_multiturn_cases", lambda _fixture: fast_cases)
    monkeypatch.setattr("harness.mileday.api_runner.time.sleep", lambda _seconds: None)

    result = CliRunner().invoke(app, ["test_api", "--limit", "1", "--write-no"])

    assert result.exit_code == 0
    assert "db_write=disabled" in result.stdout
    assert not (tmp_path / "artifacts" / "runs" / "prompt-test-1" / "db_manifest.json").exists()


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


def test_cleanup_uses_run_manifest(monkeypatch, tmp_path):
    monkeypatch.setenv("HARNESS_RUNS_DIR", str(tmp_path / "runs"))
    manifest_dir = tmp_path / "runs" / "prompt-test-1"
    manifest_dir.mkdir(parents=True)
    (manifest_dir / "db_manifest.json").write_text(
        """
{
  "records": [
    {
      "case_id": "case-1-turn-1",
      "created_at": "2026-08-11T00:00:00+00:00",
      "goal_id": "goal-1",
            "milestone_ids": ["milestone-1", "milestone-2"],
            "milestone_slot_ids": {"S001": "milestone-1", "S002": "milestone-2"},
            "milestone_titles": {"S001": "[TEST] one", "S002": "[TEST] two"},
            "operation": "create",
            "run_id": "prompt-test-1",
            "turn_id": 1,
            "user_id": "user-1"
    }
  ]
}
""".strip()
        + "\n",
        encoding="utf-8",
    )
    cleanup_records = []

    class MockApiDbWriter:
        @classmethod
        def from_settings(cls, settings):
            return cls()

        def cleanup_record(self, record):
            cleanup_records.append(record)
            return {"goals": 1, "milestones": 2}

    monkeypatch.setattr("harness.mileday.api_runner.ApiDbWriter", MockApiDbWriter)

    result = CliRunner().invoke(app, ["cleanup", "--run-id", "prompt-test-1"])

    assert result.exit_code == 0
    assert "deleted_goals=1" in result.stdout
    assert "deleted_milestones=2" in result.stdout
    assert [record["goal_id"] for record in cleanup_records] == ["goal-1"]


def test_runner_applies_add_remove_and_rename_db_state():
    create_record = {
        "milestone_slot_ids": {"S001": "milestone-1", "S002": "milestone-2"},
        "milestone_titles": {"S001": "[TEST] one", "S002": "[TEST] two"},
    }

    _apply_db_write_record_to_create_state(
        create_record,
        {
            "milestone_slot_ids": {"S003": "milestone-3"},
            "milestone_titles": {"S003": "[TEST] three"},
        },
        {"add_items": [{"slot_id": "S003"}], "remove_slot_ids": []},
    )
    assert create_record["milestone_slot_ids"]["S003"] == "milestone-3"
    assert create_record["milestone_titles"]["S003"] == "[TEST] three"

    _apply_db_write_record_to_create_state(
        create_record,
        {
            "milestone_slot_ids": {"S002": "milestone-2"},
            "milestone_titles": {},
        },
        {"remove_slot_ids": ["S002"]},
    )
    assert "S002" not in create_record["milestone_slot_ids"]
    assert "S002" not in create_record["milestone_titles"]

    _apply_db_write_record_to_create_state(
        create_record,
        {
            "milestone_slot_ids": {"S001": "milestone-1"},
            "milestone_titles": {"S001": "[TEST] one renamed"},
        },
        {"patch_items": [{"slot_id": "S001"}], "remove_slot_ids": []},
    )
    assert create_record["milestone_slot_ids"]["S001"] == "milestone-1"
    assert create_record["milestone_titles"]["S001"] == "[TEST] one renamed"
