import json
from datetime import date

from typer.testing import CliRunner

from harness.benchmarks.mcq import MCQCaseResult
from harness.cli import (
    MILEDAY_API_MODEL_IDS,
    MILEDAY_API_MULTITURN_PROMPT_VERSION,
    MILEDAY_MULTITURN_FIXTURE,
    MILEDAY_MULTITURN_MODEL_ID,
    MILEDAY_MULTITURN_PROMPT_VERSION,
    MILEDAY_MULTITURN_RUNTIME_OPTIONS,
    THIRD_BENCHMARK_SYSTEM_PROMPT,
    PublicBenchmarkCase,
    _evaluate_mileday_multiturn_record,
    _evaluate_mileday_record,
    _mileday_multiturn_api_prompt,
    _load_third_benchmark_cases,
    _mileday_generation_prompt,
    _mileday_multiturn_prompt,
    app,
)
from harness.dataset_processor import ProcessedDataset, ProcessedDatasetRows
from harness.dataset_registry import DatasetConfig
from harness.mileday.dataset import load_mileday_generation_cases, load_mileday_multiturn_cases
from harness.mileday.explanation_judge import ExplanationJudgeResult
from harness.runtime.base import RuntimeResponse
from harness.schemas import RequestResult, ResultStatus, RuntimeMetrics


def _multiturn_response(*, action: str = "create", requires_confirmation: bool = True) -> str:
    return (
        "[EXPLANATION]\n"
        "사용자의 가능 시간에 맞춰 마일스톤을 다시 배치했습니다. "
        "언급되지 않은 일정은 유지하고 요청된 변경만 반영했습니다. "
        "아래 JSON은 사용자가 승인한 뒤 DB에 반영할 수 있는 후보입니다.\n"
        "\n"
        "[JSON]\n"
        "```json\n"
        "{"
        f'"action":"{action}",'
        '"explanation":"사용자 요청에 맞춰 일정 후보를 구성했습니다.",'
        '"db_payload":{'
        '"goal":{"title":"테스트 목표","deadline":"2026-12-15","is_recurring":false,"recurrence_type":null,"color":"#4F46E5"},'
        '"milestones":['
        '{"title":"[월 19:00-21:00] 대표 프로젝트 2개 선정","color":"#4F46E5","scheduled_date":"2026-08-03"},'
        '{"title":"[수 19:00-21:00] 기본 계획 수립","color":"#4F46E5","scheduled_date":"2026-08-05"},'
        '{"title":"[토 19:00-21:00] 핵심 연습 진행","color":"#4F46E5","scheduled_date":"2026-08-08"},'
        '{"title":"[월 19:00-21:00] 중간 점검","color":"#4F46E5","scheduled_date":"2026-08-10"},'
        '{"title":"[수 19:00-21:00] 최종 정리","color":"#4F46E5","scheduled_date":"2026-08-12"}'
        "]},"
        '"changes":[{"operation":"update","target":"요청 항목","reason":"사용자 부분 수정 요청 반영"}],'
        f'"requires_confirmation":{str(requires_confirmation).lower()},'
        '"unresolved_constraints":[]'
        "}\n"
        "```"
    )


def _multiturn_response_with_payload(
    *,
    action: str,
    goal_title: str,
    deadline: str,
    color: str,
    milestones: list[dict[str, str]],
) -> str:
    payload = {
        "action": action,
        "explanation": "사용자 요청에 맞춰 일정 후보를 구성했습니다.",
        "db_payload": {
            "goal": {
                "title": goal_title,
                "deadline": deadline,
                "is_recurring": False,
                "recurrence_type": None,
                "color": color,
            },
            "milestones": milestones,
        },
        "changes": [{"operation": "update", "target": "요청 항목", "reason": "사용자 부분 수정 요청 반영"}],
        "requires_confirmation": True,
        "unresolved_constraints": [],
    }
    return (
        "[EXPLANATION]\n"
        "사용자의 가용 시간과 이전 일정 상태를 반영해 일정 후보를 구성했습니다. "
        "언급되지 않은 일정은 유지했고, 요청된 변경만 반영했습니다.\n\n"
        "[JSON]\n"
        "```json\n"
        f"{json.dumps(payload, ensure_ascii=False, separators=(',', ':'))}\n"
        "```"
    )


def _multiturn_response_for_prompt(prompt: str, *, action: str = "create") -> str:
    if action == "partial_update" or "예상_행동: 부분수정" in prompt:
        return _multiturn_intent_response(
            action="partial_update",
            target="수요일 일정",
            change="회복 위주로 변경",
            tasks=["회복 조깅"],
        )
    return _multiturn_intent_response(
        action="create",
        target="전체 일정",
        change="새 일정 생성",
        tasks=["기초 준비", "핵심 연습", "중간 점검", "심화 연습", "최종 점검"],
    )
    if "SQLD" in prompt:
        return _multiturn_response_with_payload(
            action=action,
            goal_title="SQLD 자격증 준비",
            deadline="2026-09-30",
            color="#2563EB",
            milestones=[
                {"title": "[화 20:00-22:00] SQL 기본 문법 공부", "color": "#2563EB", "scheduled_date": "2026-09-01"},
                {"title": "[목 20:00-22:00] 데이터 모델링 연습", "color": "#2563EB", "scheduled_date": "2026-09-03"},
                {"title": "[일 10:00-12:00] 실전 문제 풀이", "color": "#2563EB", "scheduled_date": "2026-09-06"},
                {"title": "[화 20:00-22:00] 오답 노트 정리", "color": "#2563EB", "scheduled_date": "2026-09-08"},
                {"title": "[목 20:00-22:00] 최종 모의고사", "color": "#2563EB", "scheduled_date": "2026-09-10"},
            ],
        )
    if "개발자 이력서" in prompt or "포트폴리오" in prompt:
        return _multiturn_response_with_payload(
            action=action,
            goal_title="개발자 이력서 및 포트폴리오 정리",
            deadline="2026-11-30",
            color="#059669",
            milestones=[
                {"title": "[월 21:00-23:00] 대표 프로젝트 2개 선정", "color": "#059669", "scheduled_date": "2026-08-03"},
                {"title": "[수 21:00-23:00] 포트폴리오 문서화", "color": "#059669", "scheduled_date": "2026-10-07"},
                {"title": "[토 14:00-18:00] 배포 자료 점검", "color": "#059669", "scheduled_date": "2026-10-10"},
                {"title": "[월 21:00-23:00] 프로젝트 설명 보완", "color": "#059669", "scheduled_date": "2026-10-12"},
                {"title": "[수 21:00-23:00] 최종 제출 자료 검토", "color": "#059669", "scheduled_date": "2026-10-14"},
            ],
        )
    if "이사" in prompt:
        return _multiturn_response_with_payload(
            action=action,
            goal_title="이사 준비",
            deadline="2026-09-12",
            color="#DC2626",
            milestones=[
                {"title": "[금 19:30-21:30] 전입 신고 서류 확인", "color": "#DC2626", "scheduled_date": "2026-08-28"},
                {"title": "[일 09:00-12:00] 포장 준비", "color": "#DC2626", "scheduled_date": "2026-08-30"},
                {"title": "[금 19:30-21:30] 이삿짐센터 확인", "color": "#DC2626", "scheduled_date": "2026-09-04"},
                {"title": "[일 09:00-12:00] 공과금 정산 확인", "color": "#DC2626", "scheduled_date": "2026-09-06"},
                {"title": "[금 19:30-21:30] 최종 체크리스트 점검", "color": "#DC2626", "scheduled_date": "2026-09-11"},
            ],
        )
    if "일본어" in prompt:
        return _multiturn_response_with_payload(
            action=action,
            goal_title="일본어 회화 연습",
            deadline="2026-10-20",
            color="#7C3AED",
            milestones=[
                {"title": "[화 07:30-08:30] 일본어 회화 기본 표현", "color": "#7C3AED", "scheduled_date": "2026-09-01"},
                {"title": "[목 07:30-08:30] 문장 말하기 연습", "color": "#7C3AED", "scheduled_date": "2026-09-03"},
                {"title": "[토 16:00-18:00] 회화 녹음 피드백", "color": "#7C3AED", "scheduled_date": "2026-09-05"},
                {"title": "[화 07:30-08:30] 상황별 대화 연습", "color": "#7C3AED", "scheduled_date": "2026-09-08"},
                {"title": "[목 07:30-08:30] 발음 교정 연습", "color": "#7C3AED", "scheduled_date": "2026-09-10"},
            ],
        )
    return _multiturn_response(action=action)


def _multiturn_plan_response(
    *,
    slot_ids: list[str] | None = None,
    task_prefix: str = "실행 항목",
    include_plan: bool = True,
) -> str:
    selected_slot_ids = slot_ids or ["S001", "S002", "S003", "S004", "S005"]
    sections = []
    if include_plan:
        lines = [
            f"- {slot_id} | {index}차 {task_prefix}"
            for index, slot_id in enumerate(selected_slot_ids, start=1)
        ]
        sections.append("[PLAN]\n" + "\n".join(lines) + "\n[/PLAN]")
    return "\n\n".join(sections)


def _multiturn_patch_response(
    *,
    slot_id: str = "S002",
    task: str = "회복 조깅",
    include_patch: bool = True,
) -> str:
    sections = []
    if include_patch:
        sections.append(f"[PATCH]\n- {slot_id} | {task}\n[/PATCH]")
    return "\n\n".join(sections)


def _multiturn_intent_response(
    *,
    action: str = "create",
    target: str = "전체 일정",
    change: str = "새 일정 생성",
    tasks: list[str] | None = None,
) -> str:
    task_lines = "\n".join(f"- {task}" for task in (tasks or ["기초 준비", "핵심 연습", "최종 점검"]))
    return (
        "[일정_의도]\n"
        f"행동: {_ko_multiturn_action_for_test(action)}\n"
        f"대상: {target}\n"
        f"변경: {change}\n"
        "작업:\n"
        f"{task_lines}\n"
        "[/일정_의도]"
    )


def _ko_multiturn_action_for_test(action: str) -> str:
    return {
        "create": "생성",
        "partial_update": "부분수정",
    }.get(action, action)


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


def test_run_mileday_multiturn_uses_all_fixed_fixture_cases(monkeypatch, tmp_path):
    monkeypatch.setenv("HARNESS_ARTIFACTS_DIR", str(tmp_path / "artifacts"))
    monkeypatch.setenv("HARNESS_RUNS_DIR", str(tmp_path / "artifacts" / "runs"))
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    fast_cases = load_mileday_multiturn_cases(MILEDAY_MULTITURN_FIXTURE)[:2]
    runtimes = []

    class MockJudge:
        def __init__(self, **_kwargs):
            pass

        def evaluate_multiturn(self, case, turn_id, explanation, parsed_output, previous_output):
            return ExplanationJudgeResult(is_aligned=True, score=0.95, reason="ok")

    class MockOllamaRuntime:
        def __init__(self, base_url):
            self.base_url = base_url
            self.requests = []
            runtimes.append(self)

        def stream(self, request):
            return iter(())

        def generate(self, request):
            self.requests.append(request)
            action = (
                "partial_update"
                if "예상_행동: 부분수정" in request.prompt
                else "create"
            )
            return RuntimeResponse(
                model_tag=request.model_tag,
                text=_multiturn_response_for_prompt(request.prompt, action=action),
                metrics=RuntimeMetrics(ttft_ms=1, latency_ms=2, tokens_per_second=3),
            )

    monkeypatch.setattr("harness.cli.GeminiExplanationJudge", MockJudge)
    monkeypatch.setattr("harness.cli.OllamaRuntime", MockOllamaRuntime)
    monkeypatch.setattr("harness.cli.load_mileday_multiturn_cases", lambda _fixture: fast_cases)

    result = CliRunner().invoke(app, ["run-mileday-multiturn"])

    assert result.exit_code == 0
    assert f"model={MILEDAY_MULTITURN_MODEL_ID}" in result.stdout
    assert f"fixture={MILEDAY_MULTITURN_FIXTURE}" in result.stdout
    assert "cases=2" in result.stdout
    assert f"prompt_version={MILEDAY_MULTITURN_PROMPT_VERSION}" in result.stdout
    assert "stored=6" in result.stdout
    run_dir = tmp_path / "artifacts" / "runs" / "candidate-3-mileday-multiturn-1"
    assert (run_dir / "parsed" / "results.jsonl").exists()
    assert (run_dir / "report.md").exists()
    assert (run_dir / "report.html").exists()
    assert "html_report=" in result.stdout
    assert len(runtimes[0].requests) == 6
    assert runtimes[0].requests[0].options == MILEDAY_MULTITURN_RUNTIME_OPTIONS
    assert "[USER_MESSAGE]" not in runtimes[0].requests[0].prompt
    assert "[일정_의도]" in runtimes[0].requests[0].prompt
    assert "[이전_대화]" in runtimes[0].requests[0].prompt
    assert "내부 식별자, 날짜, 제목 앞 시간표현을 쓰지 않습니다" in runtimes[0].requests[1].prompt
    assert "assistant" in runtimes[0].requests[1].prompt
    stored_results = (run_dir / "parsed" / "results.jsonl").read_text(encoding="utf-8")
    assert f'"prompt_version": "{MILEDAY_MULTITURN_PROMPT_VERSION}"' in stored_results


def test_run_mileday_multiturn_api_runs_flash_lite_and_flash(monkeypatch, tmp_path):
    monkeypatch.setenv("HARNESS_ARTIFACTS_DIR", str(tmp_path / "artifacts"))
    monkeypatch.setenv("HARNESS_RUNS_DIR", str(tmp_path / "artifacts" / "runs"))
    monkeypatch.setenv("GEMINI_API_KEY", "judge-key")
    monkeypatch.setenv("GEMINI_GENERATION_API_KEY", "generation-key")
    fast_cases = load_mileday_multiturn_cases(MILEDAY_MULTITURN_FIXTURE)[:2]
    runtimes = []
    sleeps = []

    class MockJudge:
        def __init__(self, **_kwargs):
            pass

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
            action = (
                "partial_update"
                if "예상_행동: 부분수정" in request.prompt
                else "create"
            )
            return RuntimeResponse(
                model_tag=request.model_tag,
                text=_multiturn_response_for_prompt(request.prompt, action=action),
                metrics=RuntimeMetrics(ttft_ms=1, latency_ms=2, tokens_per_second=3),
                metadata={"provider": "gemini"},
            )

    monkeypatch.setattr("harness.cli.GeminiExplanationJudge", MockJudge)
    monkeypatch.setattr("harness.cli.GeminiRuntime", MockGeminiRuntime)
    monkeypatch.setattr("harness.cli.load_mileday_multiturn_cases", lambda _fixture: fast_cases)
    monkeypatch.setattr("harness.cli.time.sleep", lambda seconds: sleeps.append(seconds))

    result = CliRunner().invoke(
        app,
        ["run-mileday-multiturn-api", "--sleep-seconds", "0.01", "--limit", "1"],
    )

    assert result.exit_code == 0
    assert "batch_id=gemini-mileday-multiturn-1" in result.stdout
    assert "runtime=gemini" in result.stdout
    assert "sleep_seconds=0.01" in result.stdout
    assert "cases=1" in result.stdout
    assert "case_limit=1" in result.stdout
    assert f"prompt_version={MILEDAY_API_MULTITURN_PROMPT_VERSION}" in result.stdout
    assert "models=" + ", ".join(MILEDAY_API_MODEL_IDS) in result.stdout
    assert "gemini-3.5-flash-lite -> gemini-3-5-flash-lite-mileday-multiturn-1" in result.stdout
    assert "gemini-3.6-flash -> gemini-3-6-flash-mileday-multiturn-1" in result.stdout
    assert [runtime.api_key for runtime in runtimes] == ["generation-key", "generation-key"]
    assert [runtime.requests[0].model_tag for runtime in runtimes] == list(MILEDAY_API_MODEL_IDS)
    assert runtimes[0].requests[0].options == MILEDAY_MULTITURN_RUNTIME_OPTIONS
    assert MILEDAY_API_MULTITURN_PROMPT_VERSION in runtimes[0].requests[0].prompt
    assert "[PREVIOUS_PLAN_TARGETS]" in runtimes[0].requests[1].prompt
    assert "S001" in runtimes[0].requests[1].prompt
    assert sleeps == [0.01] * 6
    assert (
        tmp_path
        / "artifacts"
        / "runs"
        / "gemini-3-5-flash-lite-mileday-multiturn-1"
        / "report.html"
    ).exists()
    summary_path = tmp_path / "artifacts" / "runs" / "gemini-mileday-multiturn-1-summary.md"
    assert summary_path.exists()
    summary_text = summary_path.read_text(encoding="utf-8")
    assert "gemini-3.5-flash-lite" in summary_text
    assert "gemini-3.6-flash" in summary_text


def test_run_mileday_multiturn_api_requires_gemini_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_GENERATION_API_KEY", raising=False)

    result = CliRunner().invoke(app, ["run-mileday-multiturn-api"])

    assert result.exit_code != 0
    assert "GEMINI_API_KEY or GEMINI_GENERATION_API_KEY is required" in result.output


def test_run_mileday_multiturn_api_rejects_negative_sleep(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "judge-key")

    result = CliRunner().invoke(app, ["run-mileday-multiturn-api", "--sleep-seconds", "-1"])

    assert result.exit_code != 0
    assert "sleep_seconds must be non-negative" in result.output


def test_run_mileday_multiturn_api_rejects_non_positive_limit(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "judge-key")

    result = CliRunner().invoke(app, ["run-mileday-multiturn-api", "--limit", "0"])

    assert result.exit_code != 0
    assert "limit must be positive" in result.output


def test_v11_second_turn_receives_previous_intent_result():
    case = load_mileday_multiturn_cases("tests/fixtures/mileday/multiturn_schedule.pretty.json")[0]
    first_response = _multiturn_intent_response()
    transcript = [
        {"role": "user", "content": case.turns[0].content},
        {"role": "assistant", "content": first_response},
    ]

    prompt = _mileday_multiturn_prompt(case, 2, transcript)

    assert "[이전_대화]" in prompt
    assert case.turns[0].content in prompt
    assert "[일정_의도]" in prompt
    assert "행동: 생성" in prompt
    assert case.turns[1].content in prompt


def test_api_multiturn_prompt_has_strict_partial_update_targeting_rules():
    case = load_mileday_multiturn_cases(MILEDAY_MULTITURN_FIXTURE)[0]
    transcript = [
        {
            "role": "assistant",
            "content": "[CURRENT_PLAN_TARGETS]\n- S001 | 시험 범위 확인\n- S002 | 기본 개념 정리",
        }
    ]

    prompt = _mileday_multiturn_api_prompt(case, 2, transcript)

    assert MILEDAY_API_MULTITURN_PROMPT_VERSION in prompt
    assert "[PARTIAL_UPDATE_RULES]" in prompt
    assert "[PARTIAL_UPDATE_SCOPE_MAP]" in prompt
    assert "[TARGET_RULES]" in prompt
    assert "[PARTIAL_UPDATE_EXAMPLES]" in prompt
    assert "exactly one existing slot_id" in prompt
    assert "rewrite all task names" in prompt
    assert "S001" in prompt
    assert "[SCHEDULE_INTENT]" in prompt


def test_run_mileday_multiturn_skips_remaining_turns_after_invalid(monkeypatch, tmp_path):
    monkeypatch.setenv("HARNESS_ARTIFACTS_DIR", str(tmp_path / "artifacts"))
    monkeypatch.setenv("HARNESS_RUNS_DIR", str(tmp_path / "artifacts" / "runs"))
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    fast_cases = load_mileday_multiturn_cases(MILEDAY_MULTITURN_FIXTURE)[:2]
    calls = {"count": 0}

    class MockJudge:
        def __init__(self, **_kwargs):
            pass

        def evaluate_multiturn(self, case, turn_id, explanation, parsed_output, previous_output):
            return ExplanationJudgeResult(is_aligned=True, score=0.95, reason="ok")

    class MockOllamaRuntime:
        def __init__(self, base_url):
            self.base_url = base_url

        def stream(self, request):
            return iter(())

        def generate(self, request):
            calls["count"] += 1
            if calls["count"] == 1:
                text = ""
            else:
                action = (
                    "partial_update"
                if "예상_행동: 부분수정" in request.prompt
                    else "create"
                )
                text = _multiturn_response_for_prompt(request.prompt, action=action)
            return RuntimeResponse(
                model_tag=request.model_tag,
                text=text,
                metrics=RuntimeMetrics(ttft_ms=1, latency_ms=2, tokens_per_second=3),
            )

    monkeypatch.setattr("harness.cli.GeminiExplanationJudge", MockJudge)
    monkeypatch.setattr("harness.cli.OllamaRuntime", MockOllamaRuntime)
    monkeypatch.setattr("harness.cli.load_mileday_multiturn_cases", lambda _fixture: fast_cases)

    result = CliRunner().invoke(app, ["run-mileday-multiturn"])

    assert result.exit_code == 0
    stored_results = (
        tmp_path
        / "artifacts"
        / "runs"
        / "candidate-3-mileday-multiturn-1"
        / "parsed"
        / "results.jsonl"
    ).read_text(encoding="utf-8")
    assert '"status": "invalid"' in stored_results
    assert '"status": "skipped"' in stored_results
    assert calls["count"] == 4


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


def test_mileday_multiturn_prompt_v11_provides_intent_contract_without_slot_id_generation():
    case = load_mileday_multiturn_cases("tests/fixtures/mileday/multiturn_schedule.pretty.json")[0]

    prompt = _mileday_multiturn_prompt(case, 1, [])

    assert "[배정_가능_후보]" in prompt
    assert "[기준_날짜]" in prompt
    assert "[USER_MESSAGE]" not in prompt
    assert "[일정_의도]" in prompt
    assert "[/일정_의도]" in prompt
    assert "S001" not in prompt
    assert '"순번": "1"' in prompt
    assert '"schedule_plan"' not in prompt
    assert "저장용 구조 데이터, 내부 식별자, 날짜 계산, 사용자 설명문을 만들지 마세요" in prompt
    assert "내부 식별자, 날짜, 제목 앞 시간표현을 쓰지 않습니다" in prompt
    assert '"시간": "19:00-21:00"' in prompt
    assert '"날짜":' in prompt


def test_v11_intent_parser_builds_rule_based_payload():
    case = load_mileday_multiturn_cases("tests/fixtures/mileday/multiturn_schedule.pretty.json")[0]
    base_result = RequestResult(
        run_id="run-1",
        model_id="candidate-3",
        dataset_id=case.dataset_id,
        case_id="multiturn-001-turn-1",
        status=ResultStatus.PASSED,
        metrics=RuntimeMetrics(ttft_ms=1, latency_ms=2, tokens_per_second=3),
    )

    class MockJudge:
        def evaluate_multiturn(self, case, turn_id, explanation, parsed_output, previous_output):
            return ExplanationJudgeResult(is_aligned=True, score=0.95, reason="ok")

    result = _evaluate_mileday_multiturn_record(
        base_result,
        case,
        1,
        _multiturn_intent_response(tasks=["기초 체력 점검", "가벼운 조깅", "거리 적응", "페이스 연습", "최종 점검"]),
        previous_parsed=None,
        explanation_judge=MockJudge(),
    )

    assert result.status == ResultStatus.PASSED
    assert result.parsed_output["output_contract"]["intent_parseable"] is True
    assert result.parsed_output["output_contract"]["db_payload_schema_valid"] is True
    assert "rule_based_db_payload" in result.parsed_output["parsed_json"]
    assert "19:00-21:00" in result.parsed_output["user_message"]
    assert result.parsed_output["multiturn_validation"]["schedule_quality"]["availability_alignment"] is True


def test_v11_intent_partial_update_preserves_previous_plan_and_builds_payload():
    case = load_mileday_multiturn_cases("tests/fixtures/mileday/multiturn_schedule.pretty.json")[0]
    case.turns[1].content = "수요일 일정만 회복 위주로 바꿔줘. 나머지 일정은 그대로 유지해줘."
    previous_parsed = {
        "plan_items": [
            {"slot_id": "S001", "task": "10km 달리기 연습"},
            {"slot_id": "S002", "task": "10km 달리기 연습"},
            {"slot_id": "S003", "task": "10km 달리기 연습"},
            {"slot_id": "S004", "task": "10km 달리기 연습"},
            {"slot_id": "S005", "task": "10km 달리기 연습"},
        ],
        "db_payload": {
            "goal": {
                "title": "10km 달리기 연습",
                "deadline": "2026-10-31",
                "is_recurring": False,
                "recurrence_type": None,
                "color": "#4F46E5",
            },
            "milestones": [
                {"title": "[월 19:00-21:00] 10km 달리기 연습", "color": "#4F46E5", "scheduled_date": "2026-08-03"},
                {"title": "[수 19:00-21:00] 10km 달리기 연습", "color": "#4F46E5", "scheduled_date": "2026-08-05"},
                {"title": "[토 19:00-21:00] 10km 달리기 연습", "color": "#4F46E5", "scheduled_date": "2026-08-08"},
                {"title": "[월 19:00-21:00] 10km 달리기 연습", "color": "#4F46E5", "scheduled_date": "2026-08-10"},
                {"title": "[수 19:00-21:00] 10km 달리기 연습", "color": "#4F46E5", "scheduled_date": "2026-08-12"},
            ],
        },
    }
    base_result = RequestResult(
        run_id="run-1",
        model_id="candidate-3",
        dataset_id=case.dataset_id,
        case_id="multiturn-001-turn-2",
        status=ResultStatus.PASSED,
    )

    class MockJudge:
        def evaluate_multiturn(self, case, turn_id, explanation, parsed_output, previous_output):
            return ExplanationJudgeResult(is_aligned=True, score=0.95, reason="ok")

    result = _evaluate_mileday_multiturn_record(
        base_result,
        case,
        2,
        _multiturn_intent_response(
            action="partial_update",
            target="수요일 일정",
            change="회복 위주로 변경",
            tasks=["회복 조깅"],
        ),
        previous_parsed=previous_parsed,
        explanation_judge=MockJudge(),
    )

    assert result.status == ResultStatus.PASSED
    parsed = result.parsed_output["parsed_json"]
    assert len(parsed["plan_items"]) == 5
    assert parsed["patch_items"] == [
        {"slot_id": "S001", "task": "회복 위주 운동"},
        {"slot_id": "S004", "task": "회복 위주 운동"},
    ]
    assert parsed["plan_items"][0]["task"] == "회복 위주 운동"
    assert parsed["plan_items"][3]["task"] == "회복 위주 운동"
    assert parsed["plan_items"][1]["task"] == "10km 달리기 연습"
    assert result.parsed_output["multiturn_validation"]["state"]["state_regression_count"] == 0


def test_api_intent_single_second_week_update_does_not_patch_all_slots():
    case = load_mileday_multiturn_cases("tests/fixtures/mileday/multiturn_schedule.pretty.json")[0]
    previous_parsed = {
        "plan_items": [
            {"slot_id": "S001", "task": "시험 범위 확인 및 학습 계획 수립"},
            {"slot_id": "S002", "task": "기본 개념 정리 및 교재 정독"},
            {"slot_id": "S003", "task": "핵심 요약 노트 작성"},
            {"slot_id": "S004", "task": "기출문제 풀이 및 오답 정리"},
            {"slot_id": "S005", "task": "최종 모의고사 풀이 및 취약점 보완"},
        ],
        "db_payload": {"goal": {}, "milestones": []},
    }
    base_result = RequestResult(
        run_id="run-1",
        model_id="gemini-3.5-flash-lite",
        dataset_id=case.dataset_id,
        case_id="multiturn-001-turn-2",
        status=ResultStatus.PASSED,
    )

    class MockJudge:
        def evaluate_multiturn(self, case, turn_id, explanation, parsed_output, previous_output):
            return ExplanationJudgeResult(is_aligned=True, score=0.95, reason="ok")

    raw_output = (
        "[SCHEDULE_INTENT]\n"
        "action: partial_update\n"
        "target: 중간고사 준비\n"
        "change: 두 번째 주 작업명 구체화\n"
        "tasks:\n"
        "- 기본 개념 심화 학습 및 핵심 교재 정독\n"
        "[/SCHEDULE_INTENT]"
    )

    result = _evaluate_mileday_multiturn_record(
        base_result,
        case,
        2,
        raw_output,
        previous_parsed=previous_parsed,
        explanation_judge=MockJudge(),
        prompt_version=MILEDAY_API_MULTITURN_PROMPT_VERSION,
    )

    parsed = result.parsed_output["parsed_json"]
    assert result.status == ResultStatus.PASSED
    assert parsed["patch_items"] == [
        {"slot_id": "S005", "task": "기본 개념 심화 학습 및 핵심 교재 정독"}
    ]
    assert len({item["task"] for item in parsed["plan_items"]}) == 5
    assert result.parsed_output["multiturn_validation"]["state"]["partial_update_scope_valid"] is True


def test_v11_create_skips_existing_schedule_dates_and_sanitizes_english_tasks():
    case = load_mileday_multiturn_cases("tests/fixtures/mileday/multiturn_schedule.pretty.json")[2]
    base_result = RequestResult(
        run_id="run-1",
        model_id="candidate-3",
        dataset_id=case.dataset_id,
        case_id="multiturn-003-turn-1",
        status=ResultStatus.PASSED,
    )

    class MockJudge:
        def evaluate_multiturn(self, case, turn_id, explanation, parsed_output, previous_output):
            return ExplanationJudgeResult(is_aligned=True, score=0.95, reason="ok")

    result = _evaluate_mileday_multiturn_record(
        base_result,
        case,
        1,
        _multiturn_intent_response(
            tasks=[
                "portfolio writing",
                "이력서 초안 작성",
                "포트폴리오 구조 정리",
                "프로젝트 설명 보완",
                "최종 검토",
            ]
        ),
        previous_parsed=None,
        explanation_judge=MockJudge(),
    )

    assert result.status == ResultStatus.PASSED
    milestones = result.parsed_output["parsed_json"]["db_payload"]["milestones"]
    assert all(item["scheduled_date"] != "2026-08-03" for item in milestones)
    assert milestones[0]["title"].endswith(case.input.initial_goal.title)


def test_v11_fallback_partial_update_extracts_weekday_change_phrase():
    case = load_mileday_multiturn_cases("tests/fixtures/mileday/multiturn_schedule.pretty.json")[4]
    case.turns[1].content = "토요일은 회화 녹음과 피드백 위주로 바꿔줘. 평일 일정은 유지해줘."
    previous_parsed = {
        "plan_items": [
            {"slot_id": "S001", "task": "일본어 회화 루틴 만들기 준비"},
            {"slot_id": "S002", "task": "일본어 회화 루틴 만들기 기초 진행"},
            {"slot_id": "S003", "task": "일본어 회화 루틴 만들기 핵심 진행"},
            {"slot_id": "S004", "task": "일본어 회화 루틴 만들기 중간 점검"},
            {"slot_id": "S005", "task": "일본어 회화 루틴 만들기 최종 점검"},
        ],
        "db_payload": {
            "goal": {
                "title": "일본어 회화 루틴 만들기",
                "deadline": "2026-12-15",
                "is_recurring": False,
                "recurrence_type": None,
                "color": "#7C3AED",
            },
            "milestones": [
                {"title": "[월 19:00-21:00] 일본어 회화 루틴 만들기 준비", "color": "#7C3AED", "scheduled_date": "2026-08-03"},
                {"title": "[수 19:00-21:00] 일본어 회화 루틴 만들기 기초 진행", "color": "#7C3AED", "scheduled_date": "2026-08-05"},
                {"title": "[토 10:00-12:00] 일본어 회화 루틴 만들기 핵심 진행", "color": "#7C3AED", "scheduled_date": "2026-08-08"},
                {"title": "[월 19:00-21:00] 일본어 회화 루틴 만들기 중간 점검", "color": "#7C3AED", "scheduled_date": "2026-08-10"},
                {"title": "[수 19:00-21:00] 일본어 회화 루틴 만들기 최종 점검", "color": "#7C3AED", "scheduled_date": "2026-08-12"},
            ],
        },
    }
    base_result = RequestResult(
        run_id="run-1",
        model_id="candidate-3",
        dataset_id=case.dataset_id,
        case_id="multiturn-005-turn-2",
        status=ResultStatus.PASSED,
    )

    class MockJudge:
        def evaluate_multiturn(self, case, turn_id, explanation, parsed_output, previous_output):
            return ExplanationJudgeResult(is_aligned=True, score=0.95, reason="ok")

    result = _evaluate_mileday_multiturn_record(
        base_result,
        case,
        2,
        "토요일은 회화 녹음과 피드백 위주로 바꿔줘. 평일 아침 루틴은 유지해줘.",
        previous_parsed=previous_parsed,
        explanation_judge=MockJudge(),
    )

    assert result.status == ResultStatus.PASSED
    parsed = result.parsed_output["parsed_json"]
    assert parsed["patch_items"] == [
        {"slot_id": "S002", "task": "회화 녹음 및 피드백"},
        {"slot_id": "S005", "task": "회화 녹음 및 피드백"},
    ]


def test_v11_malformed_korean_intent_block_falls_back_to_freeform_tasks():
    case = load_mileday_multiturn_cases("tests/fixtures/mileday/multiturn_schedule.pretty.json")[1]
    base_result = RequestResult(
        run_id="run-1",
        model_id="candidate-3",
        dataset_id=case.dataset_id,
        case_id="multiturn-002-turn-1",
        status=ResultStatus.PASSED,
    )

    class MockJudge:
        def evaluate_multiturn(self, case, turn_id, explanation, parsed_output, previous_output):
            return ExplanationJudgeResult(is_aligned=True, score=0.95, reason="ok")

    raw_output = (
        "[일정_의도]\n"
        "SQLD 자격증 준비\n\n"
        "[작업]\n"
        "1. 화요일 20:00-22:00 SQLD 관련 문제 풀이\n"
        "2. 목요일 20:00-22:00 SQLD 이론 공부\n"
        "3. 일요일 10:00-12:00 복습 및 정리\n\n"
        "[/일정_의도]"
    )

    result = _evaluate_mileday_multiturn_record(
        base_result,
        case,
        1,
        raw_output,
        previous_parsed=None,
        explanation_judge=MockJudge(),
    )

    assert result.status == ResultStatus.PASSED
    assert result.parsed_output["output_contract"]["freeform_fallback_used"] is True


def test_v11_fallback_partial_update_adds_new_task_to_next_unused_slot():
    case = load_mileday_multiturn_cases("tests/fixtures/mileday/multiturn_schedule.pretty.json")[2]
    case.turns[2].content = "기술 블로그 글 작성 일정을 추가해줘. 완료된 대표 프로젝트 선정은 건드리지 마."
    previous_parsed = {
        "plan_items": [
            {"slot_id": "S001", "task": "이력서 초안 작성"},
            {"slot_id": "S002", "task": "포트폴리오 구조 정리"},
            {"slot_id": "S003", "task": "프로젝트 설명 보완"},
        ],
        "db_payload": {
            "goal": {
                "title": "개발자 이력서 포트폴리오 정리",
                "deadline": "2026-11-30",
                "is_recurring": False,
                "recurrence_type": None,
                "color": "#059669",
            },
            "milestones": [],
        },
    }
    base_result = RequestResult(
        run_id="run-1",
        model_id="candidate-3",
        dataset_id=case.dataset_id,
        case_id="multiturn-003-turn-3",
        status=ResultStatus.PASSED,
    )

    class MockJudge:
        def evaluate_multiturn(self, case, turn_id, explanation, parsed_output, previous_output):
            return ExplanationJudgeResult(is_aligned=True, score=0.95, reason="ok")

    result = _evaluate_mileday_multiturn_record(
        base_result,
        case,
        3,
        "기술 블로그 글 작성 일정을 추가해줘. 완료된 대표 프로젝트 선정은 건드리지 마.",
        previous_parsed=previous_parsed,
        explanation_judge=MockJudge(),
    )

    assert result.status == ResultStatus.PASSED
    parsed = result.parsed_output["parsed_json"]
    assert parsed["patch_items"] == []
    assert parsed["add_items"] == [{"slot_id": "S004", "task": "기술 블로그 글 작성"}]
    assert parsed["plan_items"][-1] == {"slot_id": "S004", "task": "기술 블로그 글 작성"}


def test_mileday_multiturn_record_uses_freeform_fallback_without_intent_block():
    case = load_mileday_multiturn_cases("tests/fixtures/mileday/multiturn_schedule.pretty.json")[0]
    base_result = RequestResult(
        run_id="run-1",
        model_id="candidate-3",
        dataset_id=case.dataset_id,
        case_id="multiturn-001-turn-1",
        status=ResultStatus.PASSED,
    )

    result = _evaluate_mileday_multiturn_record(
        base_result,
        case,
        1,
        "[USER_MESSAGE]\n설명입니다.",
        previous_parsed=None,
        explanation_judge=None,
    )

    assert result.status == ResultStatus.FAILED
    assert result.parsed_output["output_contract"]["freeform_fallback_used"] is True
    assert result.error is not None


def test_mileday_multiturn_record_invalid_when_task_contains_time_prefix():
    case = load_mileday_multiturn_cases("tests/fixtures/mileday/multiturn_schedule.pretty.json")[0]
    base_result = RequestResult(
        run_id="run-1",
        model_id="candidate-3",
        dataset_id=case.dataset_id,
        case_id="multiturn-001-turn-1",
        status=ResultStatus.PASSED,
    )

    result = _evaluate_mileday_multiturn_record(
        base_result,
        case,
        1,
        _multiturn_intent_response(tasks=["[월 19:00-21:00] 실행 항목"]),
        previous_parsed=None,
        explanation_judge=None,
    )

    assert result.status == ResultStatus.INVALID
    deterministic = result.parsed_output["multiturn_validation"]["deterministic_validation"]
    assert deterministic["is_valid"] is False
    assert "plan_task_valid" in deterministic["failed_check_names"]


def test_mileday_multiturn_intent_invalid_when_expected_block_is_missing():
    case = load_mileday_multiturn_cases("tests/fixtures/mileday/multiturn_schedule.pretty.json")[0]
    base_result = RequestResult(
        run_id="run-1",
        model_id="candidate-3",
        dataset_id=case.dataset_id,
        case_id="multiturn-001-turn-1",
        status=ResultStatus.PASSED,
    )

    result = _evaluate_mileday_multiturn_record(
        base_result,
        case,
        1,
        "",
        previous_parsed=None,
        explanation_judge=None,
    )

    assert result.status == ResultStatus.INVALID
    assert result.parsed_output["contract_errors"] == ["Missing [일정_의도] or [/일정_의도] section."]


def test_mileday_multiturn_record_invalid_when_intent_action_is_unknown():
    case = load_mileday_multiturn_cases("tests/fixtures/mileday/multiturn_schedule.pretty.json")[0]
    base_result = RequestResult(
        run_id="run-1",
        model_id="candidate-3",
        dataset_id=case.dataset_id,
        case_id="multiturn-001-turn-1",
        status=ResultStatus.PASSED,
    )
    raw_output = _multiturn_intent_response(action="delete")

    result = _evaluate_mileday_multiturn_record(
        base_result,
        case,
        1,
        raw_output,
        previous_parsed=None,
        explanation_judge=None,
    )

    assert result.status == ResultStatus.INVALID
    assert "action must be create or partial_update." in result.parsed_output["intent_parse_errors"]


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

