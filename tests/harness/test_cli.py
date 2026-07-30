from typer.testing import CliRunner

from harness.benchmarks.mcq import MCQCaseResult
from harness.cli import (
    THIRD_BENCHMARK_SYSTEM_PROMPT,
    PublicBenchmarkCase,
    _evaluate_mileday_record,
    _load_third_benchmark_cases,
    _mileday_generation_prompt,
    app,
)
from harness.dataset_processor import ProcessedDataset, ProcessedDatasetRows
from harness.dataset_registry import DatasetConfig
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


def test_run_third_benchmark_uses_fixed_models_datasets_and_system_prompt(monkeypatch, tmp_path):
    monkeypatch.setenv("HARNESS_ARTIFACTS_DIR", str(tmp_path / "artifacts"))
    monkeypatch.setenv("HARNESS_RUNS_DIR", str(tmp_path / "artifacts" / "runs"))
    runtimes = []

    def score_response(raw_output):
        return MCQCaseResult(
            benchmark_id="kobalt-700",
            case_id="case-1",
            category="reasoning",
            correct_answer="A",
            raw_output=raw_output,
            parsed_answer=raw_output.strip(),
            is_correct=raw_output.strip() == "A",
            is_invalid=False,
        )

    def fake_load_cases(dataset_configs, *, snapshot_dir):
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        return {
            "ifeval_ko": [],
            "kobalt": [
                PublicBenchmarkCase(
                    dataset_key="kobalt",
                    dataset_id="kobalt-700",
                    benchmark_id="kobalt-700",
                    case_id="case-1",
                    prompt="question",
                    score_response=score_response,
                )
            ],
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

    monkeypatch.setattr("harness.cli._load_third_benchmark_cases", fake_load_cases)
    monkeypatch.setattr("harness.cli.OllamaRuntime", MockOllamaRuntime)

    result = CliRunner().invoke(app, ["run-third-benchmark"])

    assert result.exit_code == 0
    assert "batch_id=third-benchmark-batch-1" in result.stdout
    assert "models=candidate-3, candidate-5" in result.stdout
    assert "datasets=ifeval_ko:0, kobalt:1" in result.stdout
    assert "sampling=none" in result.stdout
    assert "candidate-3 -> candidate-3-third-benchmark-1" in result.stdout
    assert "candidate-5 -> candidate-5-third-benchmark-1" in result.stdout
    assert [runtime.requests[0].model_tag for runtime in runtimes] == [
        "granite4.1:3b",
        "ministral-3:3b",
    ]
    assert all(runtime.requests[0].system == THIRD_BENCHMARK_SYSTEM_PROMPT for runtime in runtimes)
    summary_path = tmp_path / "artifacts" / "runs" / "third-benchmark-batch-1-summary.md"
    assert summary_path.exists()
    summary_text = summary_path.read_text(encoding="utf-8")
    assert "3차 형식 제약·추론 안정성 테스트" in summary_text
    assert "IFEval-Ko=60%, KoBALT-700=40%" in summary_text


def test_load_third_benchmark_cases_rebuilds_full_processed_datasets(monkeypatch, tmp_path):
    prepared = []
    loaded = []

    config = DatasetConfig(
        dataset_id="dataset",
        source_url="https://example.test/source",
        official_repository="https://example.test/repo",
        revision="rev-1",
        config="default",
        split="train",
        license="test",
        commercial_use_verified=False,
        fields={"question": "question"},
    )

    def fake_prepare_dataset(dataset_key, dataset, *, sample_limit=None):
        prepared.append((dataset_key, sample_limit))
        return ProcessedDataset(
            dataset_key=dataset_key,
            source_path=tmp_path / "source",
            processed_path=tmp_path / "processed" / dataset_key / "data.jsonl",
            row_count=1,
        )

    def fake_load_prepared_dataset_rows(dataset_key, dataset):
        loaded.append(dataset_key)
        if dataset_key == "ifeval_ko":
            return ProcessedDatasetRows(
                dataset_key=dataset_key,
                source_path=tmp_path / "ifeval_ko.jsonl",
                rows=[
                        {
                            "benchmark_id": "ifeval-ko",
                            "dataset_id": "ifeval-ko",
                            "case_id": "ifeval-1",
                            "prompt": "지시를 따르세요.",
                            "instruction_ids": ["keywords:existence"],
                            "kwargs": [{"keywords": ["지시"]}],
                        }
                ],
            )
        return ProcessedDatasetRows(
            dataset_key=dataset_key,
            source_path=tmp_path / "kobalt.jsonl",
            rows=[
                {
                    "case_id": "kobalt-1",
                    "question": "Q",
                    "choice_a": "A1",
                    "choice_b": "B1",
                    "answer": "A",
                    "category": "reasoning",
                }
            ],
        )

    monkeypatch.setattr("harness.cli.prepare_dataset", fake_prepare_dataset)
    monkeypatch.setattr("harness.cli.load_prepared_dataset_rows", fake_load_prepared_dataset_rows)

    cases = _load_third_benchmark_cases(
        {"ifeval_ko": config, "kobalt": config},
        snapshot_dir=tmp_path / "snapshots",
    )

    assert prepared == [("ifeval_ko", None), ("kobalt", None)]
    assert loaded == ["ifeval_ko", "kobalt"]
    assert {key: len(value) for key, value in cases.items()} == {"ifeval_ko": 1, "kobalt": 1}


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
