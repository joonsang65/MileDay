from typer.testing import CliRunner

from harness.benchmarks.mcq import MCQCaseResult
from harness.cli import PublicBenchmarkCase, _evaluate_mileday_record, _mileday_generation_prompt, app
from harness.mileday.dataset import load_mileday_generation_cases
from harness.mileday.explanation_judge import ExplanationJudgeResult
from harness.runtime.base import RuntimeResponse
from harness.schemas import RequestResult, ResultStatus, RuntimeMetrics


def test_preflight_command_runs():
    result = CliRunner().invoke(app, ["preflight"])

    assert result.exit_code == 0
    assert "MileDay harness preflight" in result.stdout
    assert "status=ok" in result.stdout


def test_preflight_command_accepts_ollama_check(monkeypatch):
    monkeypatch.setattr("harness.cli.OllamaRuntime.check_health", lambda self, timeout_seconds: None)

    result = CliRunner().invoke(app, ["preflight", "--check-ollama"])

    assert result.exit_code == 0
    assert "status=ok" in result.stdout
    assert "ollama_status=ok" in result.stdout


def test_list_models_command_runs_without_install_check():
    result = CliRunner().invoke(app, ["list-models"])

    assert result.exit_code == 0
    assert "candidate-1" in result.stdout
    assert "not_checked" in result.stdout


def test_run_mileday_smoke_uses_mocked_runtime_and_stores_results(monkeypatch, tmp_path):
    monkeypatch.setenv("HARNESS_ARTIFACTS_DIR", str(tmp_path / "artifacts"))
    monkeypatch.setenv("HARNESS_RUNS_DIR", str(tmp_path / "artifacts" / "runs"))
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    runtimes = []

    class MockOllamaRuntime:
        def __init__(self, base_url):
            self.base_url = base_url
            self.requests = []
            runtimes.append(self)

        def stream(self, request):
            return iter(())

        def generate(self, request):
            self.requests.append(request)
            return RuntimeResponse(
                model_tag=request.model_tag,
                text=(
                    "[EXPLANATION]\n"
                    "자격증 취득 목표를 마감일 전까지 준비하도록 세 단계로 나눴습니다. "
                    "초반에는 계획을 세우고, 중반에는 문제 풀이를 진행하며, 마지막에는 최종 점검을 합니다.\n"
                    "\n"
                    "[JSON]\n"
                    "```json\n"
                    '{"milestones":['
                    '{"title":"Certification plan","scheduled_date":"2026-09-01"},'
                    '{"title":"Certification practice","scheduled_date":"2026-09-15"},'
                    '{"title":"Certification review","scheduled_date":"2026-09-29"}'
                    "]}\n"
                    "```"
                ),
                metrics=RuntimeMetrics(ttft_ms=1, latency_ms=2, tokens_per_second=3),
            )

    monkeypatch.setattr("harness.cli.OllamaRuntime", MockOllamaRuntime)

    result = CliRunner().invoke(
        app,
        [
            "run-mileday-smoke",
            "--fixture",
            "tests/fixtures/mileday/synthetic_schedule.jsonl",
            "--model-id",
            "candidate-1",
            "--run-id",
            "cli-smoke",
        ],
    )

    assert result.exit_code == 0
    assert "batch_id=cli-smoke" in result.stdout
    assert "candidate-1 -> cli-smoke" in result.stdout
    assert "completed=1 failed=0" in result.stdout
    assert (tmp_path / "artifacts" / "runs" / "cli-smoke" / "parsed" / "results.jsonl").exists()
    assert (tmp_path / "artifacts" / "runs" / "cli-smoke" / "report.md").exists()
    assert (tmp_path / "artifacts" / "runs" / "cli-smoke-summary.md").exists()
    assert runtimes[0].requests[0].response_format is None
    assert runtimes[0].requests[0].options == {"temperature": 0}


def test_run_mileday_smoke_accepts_comma_separated_models_and_auto_run_ids(monkeypatch, tmp_path):
    monkeypatch.setenv("HARNESS_ARTIFACTS_DIR", str(tmp_path / "artifacts"))
    monkeypatch.setenv("HARNESS_RUNS_DIR", str(tmp_path / "artifacts" / "runs"))
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    runtimes = []

    class MockOllamaRuntime:
        def __init__(self, base_url):
            self.base_url = base_url
            self.requests = []
            runtimes.append(self)

        def stream(self, request):
            return iter(())

        def generate(self, request):
            self.requests.append(request)
            return RuntimeResponse(
                model_tag=request.model_tag,
                text=(
                    "[EXPLANATION]\n"
                    "일정을 목표 달성 전까지 순서대로 배치했습니다.\n"
                    "\n"
                    "[JSON]\n"
                    "```json\n"
                    '{"milestones":['
                    '{"title":"Plan","scheduled_date":"2026-09-01"},'
                    '{"title":"Practice","scheduled_date":"2026-09-15"},'
                    '{"title":"Review","scheduled_date":"2026-09-29"}'
                    "]}\n"
                    "```"
                ),
                metrics=RuntimeMetrics(ttft_ms=1, latency_ms=2, tokens_per_second=3),
            )

    monkeypatch.setattr("harness.cli.OllamaRuntime", MockOllamaRuntime)

    result = CliRunner().invoke(
        app,
        [
            "run-mileday-smoke",
            "--fixture",
            "tests/fixtures/mileday/synthetic_schedule.jsonl",
            "--model-id",
            "candidate-1,candidate-3",
            "--limit",
            "1",
            "--seed",
            "42",
        ],
    )

    assert result.exit_code == 0
    assert "batch_id=batch-1-1cases" in result.stdout
    assert "candidate-1 -> candidate-1-1-1cases" in result.stdout
    assert "candidate-3 -> candidate-3-1-1cases" in result.stdout
    assert "completed=2 failed=0" in result.stdout
    assert (tmp_path / "artifacts" / "runs" / "candidate-1-1-1cases" / "report.md").exists()
    assert (tmp_path / "artifacts" / "runs" / "candidate-3-1-1cases" / "report.md").exists()
    summary_path = tmp_path / "artifacts" / "runs" / "batch-1-1cases-summary.md"
    assert summary_path.exists()
    summary_text = summary_path.read_text(encoding="utf-8")
    assert "LLM-as-Judge 전체 평가" in summary_text
    assert "Judge 실행 여부" in summary_text
    assert "모델별 Judge 결과" in summary_text
    assert "실행 조건" in summary_text
    assert [runtime.requests[0].model_tag for runtime in runtimes] == [
        "ingu627/exaone4.0:1.2b",
        "granite4.1:3b",
    ]


def test_run_mileday_smoke_rejects_unknown_model_id():
    result = CliRunner().invoke(
        app,
        [
            "run-mileday-smoke",
            "--fixture",
            "tests/fixtures/mileday/synthetic_schedule.jsonl",
            "--model-id",
            "candidate-missing",
        ],
    )

    assert result.exit_code != 0
    assert "Unknown model id: candidate-missing" in result.output


def test_run_benchmark_uses_comma_models_and_writes_reports(monkeypatch, tmp_path):
    monkeypatch.setenv("HARNESS_ARTIFACTS_DIR", str(tmp_path / "artifacts"))
    monkeypatch.setenv("HARNESS_RUNS_DIR", str(tmp_path / "artifacts" / "runs"))
    runtimes = []

    def score_response(raw_output):
        return MCQCaseResult(
            benchmark_id="click",
            case_id="case-1",
            category="reading",
            correct_answer="A",
            raw_output=raw_output,
            parsed_answer=raw_output.strip(),
            is_correct=raw_output.strip() == "A",
            is_invalid=False,
        )

    def fake_load_cases(dataset_configs, *, sample_dir, limit, seed):
        assert limit == 1
        assert seed == 7
        sample_dir.mkdir(parents=True, exist_ok=True)
        return {
            "ifeval_ko": [],
            "kobalt": [],
            "click": [
                PublicBenchmarkCase(
                    dataset_key="click",
                    dataset_id="click",
                    benchmark_id="click",
                    case_id="case-1",
                    prompt="question",
                    score_response=score_response,
                )
            ],
            "kmmlu_pro": [],
        }

    class MockOllamaRuntime:
        def __init__(self, base_url):
            self.base_url = base_url
            self.requests = []
            runtimes.append(self)

        def stream(self, request):
            return iter(())

        def generate(self, request):
            self.requests.append(request)
            return RuntimeResponse(
                model_tag=request.model_tag,
                text="A",
                metrics=RuntimeMetrics(ttft_ms=1, latency_ms=2, tokens_per_second=3),
            )

    monkeypatch.setattr("harness.cli._load_public_benchmark_cases", fake_load_cases)
    monkeypatch.setattr("harness.cli.OllamaRuntime", MockOllamaRuntime)

    result = CliRunner().invoke(
        app,
        [
            "run-benchmark",
            "--model-id",
            "candidate-1,candidate-3",
            "--limit",
            "1",
            "--seed",
            "7",
        ],
    )

    assert result.exit_code == 0
    assert "batch_id=benchmark-batch-1-1cases" in result.stdout
    assert "candidate-1 -> candidate-1-benchmark-1-1cases" in result.stdout
    assert "candidate-3 -> candidate-3-benchmark-1-1cases" in result.stdout
    assert (tmp_path / "artifacts" / "runs" / "candidate-1-benchmark-1-1cases" / "report.md").exists()
    assert (tmp_path / "artifacts" / "runs" / "candidate-3-benchmark-1-1cases" / "report.md").exists()
    summary_path = tmp_path / "artifacts" / "runs" / "benchmark-batch-1-1cases-summary.md"
    assert summary_path.exists()
    assert "데이터셋별 점수" in summary_path.read_text(encoding="utf-8")
    assert [runtime.requests[0].model_tag for runtime in runtimes] == [
        "ingu627/exaone4.0:1.2b",
        "granite4.1:3b",
    ]


def test_mileday_prompt_enforces_korean_json_contract_and_required_fields():
    cases = load_mileday_generation_cases("tests/fixtures/mileday/synthetic_schedule.jsonl")

    first_prompt = _mileday_generation_prompt(cases[0])
    second_prompt = _mileday_generation_prompt(cases[1])

    assert "[EXPLANATION]" in first_prompt
    assert "[JSON]" in first_prompt
    assert "</think>" in first_prompt
    assert "3~5" in first_prompt
    assert "```json" in first_prompt
    assert "load" in first_prompt
    assert '"milestones"' in first_prompt
    assert '"scheduled_date": "YYYY-MM-DD"' in first_prompt
    assert '"description"' not in first_prompt
    assert '"description": "string"' in second_prompt


def test_mileday_record_passes_when_explanation_and_fenced_json_are_valid():
    case = load_mileday_generation_cases("tests/fixtures/mileday/synthetic_schedule.jsonl")[0]
    base_result = RequestResult(
        run_id="run-1",
        model_id="candidate-1",
        dataset_id=case.dataset_id,
        case_id=case.case_id,
        status=ResultStatus.PASSED,
        metrics=RuntimeMetrics(ttft_ms=1, latency_ms=2, tokens_per_second=3),
    )
    raw_output = (
        "[EXPLANATION]\n"
        "자격증 취득 목표를 마감일 전까지 준비하도록 세 단계로 나눴습니다. "
        "초반에는 계획을 세우고, 중반에는 문제 풀이를 진행하며, 마지막에는 최종 점검을 하도록 배치했습니다.\n"
        "\n"
        "[JSON]\n"
        "```json\n"
        '{"milestones":['
        '{"title":"계획 세우기","scheduled_date":"2026-09-01"},'
        '{"title":"문제 풀이","scheduled_date":"2026-09-15"},'
        '{"title":"최종 점검","scheduled_date":"2026-09-30"}'
        "]}\n"
        "```"
    )

    class MockJudge:
        def evaluate(self, case, explanation, parsed_output):
            return ExplanationJudgeResult(is_aligned=True, score=0.95, reason="aligned")

    result = _evaluate_mileday_record(base_result, case, raw_output, explanation_judge=MockJudge())

    assert result.status == ResultStatus.PASSED
    assert result.error is None
    assert result.parsed_output["output_contract"]["explanation_present"] is True
    assert result.parsed_output["output_contract"]["fenced_json_present"] is True
    assert result.parsed_output["output_contract"]["json_loadable"] is True
    assert result.parsed_output["validation"]["is_valid"] is True
    assert result.parsed_output["explanation_judge"]["is_aligned"] is True


def test_mileday_record_invalid_when_explanation_judge_rejects_alignment():
    case = load_mileday_generation_cases("tests/fixtures/mileday/synthetic_schedule.jsonl")[0]
    base_result = RequestResult(
        run_id="run-1",
        model_id="candidate-1",
        dataset_id=case.dataset_id,
        case_id=case.case_id,
        status=ResultStatus.PASSED,
        metrics=RuntimeMetrics(ttft_ms=1, latency_ms=2, tokens_per_second=3),
    )
    raw_output = (
        "[EXPLANATION]\n"
        "운동 루틴을 위한 일정입니다.\n"
        "\n"
        "[JSON]\n"
        "```json\n"
        '{"milestones":['
        '{"title":"계획 세우기","scheduled_date":"2026-09-01"},'
        '{"title":"문제 풀이","scheduled_date":"2026-09-15"},'
        '{"title":"최종 점검","scheduled_date":"2026-09-30"}'
        "]}\n"
        "```"
    )

    class RejectingJudge:
        def evaluate(self, case, explanation, parsed_output):
            return ExplanationJudgeResult(is_aligned=False, score=0.2, reason="not aligned")

    result = _evaluate_mileday_record(base_result, case, raw_output, explanation_judge=RejectingJudge())

    assert result.status == ResultStatus.INVALID
    assert result.error is not None
    assert result.parsed_output["explanation_judge"]["is_aligned"] is False


def test_mileday_record_fails_when_required_explanation_judge_is_missing():
    case = load_mileday_generation_cases("tests/fixtures/mileday/synthetic_schedule.jsonl")[0]
    base_result = RequestResult(
        run_id="run-1",
        model_id="candidate-1",
        dataset_id=case.dataset_id,
        case_id=case.case_id,
        status=ResultStatus.PASSED,
        metrics=RuntimeMetrics(ttft_ms=1, latency_ms=2, tokens_per_second=3),
    )
    raw_output = (
        "[EXPLANATION]\n"
        "자격증 취득 목표를 위해 계획, 문제 풀이, 최종 점검을 순서대로 배치했습니다.\n"
        "\n"
        "[JSON]\n"
        "```json\n"
        '{"milestones":['
        '{"title":"계획 세우기","scheduled_date":"2026-09-01"},'
        '{"title":"문제 풀이","scheduled_date":"2026-09-15"},'
        '{"title":"최종 점검","scheduled_date":"2026-09-30"}'
        "]}\n"
        "```"
    )

    result = _evaluate_mileday_record(base_result, case, raw_output, require_explanation_judge=True)

    assert result.status == ResultStatus.FAILED
    assert result.error is not None
    assert result.error.category == "EXTERNAL_DEPENDENCY"
