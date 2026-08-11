# MileDay Tests

이 디렉터리는 MileDay backend, Supabase integration, harness, 성능 측정 스크립트를 함께 관리합니다.
기본 `pytest` 실행은 실제 Supabase 네트워크를 호출하지 않으며, `integration` marker가 붙은 테스트는 기본 실행에서 제외됩니다.

## 기본 실행

```powershell
pytest
```

Backend coverage gate:

```powershell
pytest -c pytest-backend.ini
```

실제 Supabase integration:

```powershell
pytest -m integration
```

## Harness 테스트

```powershell
pytest tests\harness
```

| 위치 | 범위 |
|---|---|
| `tests/harness/test_cli.py` | 기본 CLI smoke |
| `tests/harness/test_api_cli.py` | flash-lite 전용 `test_api` 명령 |
| `tests/harness/test_config.py` | harness 환경 설정 |
| `tests/harness/test_orchestrator.py` | cold/warm 실행, resume, progress callback |
| `tests/harness/test_results.py` | raw output, JSONL, pretty JSON, metric artifact 저장 |
| `tests/harness/test_reporting.py` | 한글 Markdown report 생성 |
| `tests/harness/mileday/test_api_prompt.py` | flash-lite prompt contract |
| `tests/harness/mileday/test_api_intent.py` | intent block parsing, fallback, invalid intent |
| `tests/harness/mileday/test_api_plan_builder.py` | create/add/remove/partial update plan 생성 |
| `tests/harness/mileday/test_api_validation.py` | schedule validation, DB payload, SQL preview |
| `tests/harness/mileday/test_api_parser.py` | parser orchestration end-to-end |
| `tests/harness/mileday/` | MileDay fixture, constraints, rubric, Gemini judge |
| `tests/harness/runtime/` | Ollama/Gemini runtime request/response/error 처리 |
| `tests/harness/performance/` | resource monitor 및 성능 metric summary |

## Fixture

| 경로 | 설명 |
|---|---|
| `tests/fixtures/mileday/synthetic_schedule.jsonl` | MileDay 일정 생성 smoke/evaluation fixture |
| `tests/fixtures/mileday/multiturn_schedule.pretty.json` | flash-lite prompt/parser 멀티턴 fixture |

## 주의

- 테스트를 통과시키기 위해 assertion이나 fixture를 약화하지 않습니다.
- integration test는 실제 Supabase project에 쓰기 작업을 수행할 수 있으므로 test 전용 계정만 사용합니다.
- `.env`의 API key, Supabase key, Gemini key는 commit하지 않습니다.
- 실제 Gemini 호출은 unit test가 아니라 `python -m harness.cli test_api` 실행입니다.
