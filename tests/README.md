# MileDay Tests

이 디렉터리는 MileDay backend, Supabase integration, harness, benchmark adapter, 성능 측정 스크립트를 함께 관리합니다. 기본 `pytest` 실행은 실제 Supabase 네트워크를 호출하지 않으며, `integration` marker가 붙은 테스트는 기본 실행에서 제외됩니다.

## 테스트 구조

```text
tests/
  conftest.py
  test_*.py
  integration/
  harness/
  fixtures/
  performance/
```

| 위치 | 역할 |
|---|---|
| `tests/test_*.py` | FastAPI backend service, repository, router, 설정, 오류 처리, migration 테스트 |
| `tests/integration/` | 실제 Supabase test project를 사용하는 통합 테스트 |
| `tests/harness/` | 로컬 LLM 평가 harness, benchmark adapter, runtime, reporting 테스트 |
| `tests/fixtures/` | harness 및 benchmark 테스트용 synthetic fixture |
| `tests/performance/` | Electron/frontend 흐름의 성능 측정용 Node.js 스크립트 |
| `tests/conftest.py` | backend app import path, FastAPI `TestClient`, test env 설정 |

## 기본 테스트 실행

프로젝트 루트에서 실행합니다.

```powershell
pytest
```

기본 실행 특징:

- `pytest.ini`를 사용합니다.
- `pythonpath = backend/app`을 설정합니다.
- `integration` marker 테스트는 제외합니다.
- backend unit test와 harness unit test를 함께 실행합니다.
- 실제 Supabase API를 호출하지 않습니다.

## Backend Coverage 테스트

backend coverage gate를 포함하려면 별도 config를 사용합니다.

```powershell
pytest -c pytest-backend.ini
```

`pytest-backend.ini`는 다음 조건을 적용합니다.

- `integration` 제외
- `--cov=backend/app`
- `--cov-report=term-missing`
- `--cov-fail-under=90`

## Harness 테스트

로컬 LLM 평가 harness만 빠르게 검증하려면 다음 명령을 사용합니다.

```powershell
pytest tests\harness
```

Harness 테스트 범위:

| 위치 | 범위 |
|---|---|
| `tests/harness/test_cli.py` | Typer CLI, smoke benchmark, public benchmark, 3차 benchmark command |
| `tests/harness/test_orchestrator.py` | cold/warm 실행, resume, progress callback, system prompt 전달 |
| `tests/harness/test_results.py` | raw output, JSONL, pretty JSON, metric artifact 저장 |
| `tests/harness/test_reporting.py` | 한글 Markdown report 생성 |
| `tests/harness/test_dataset_processor.py` | public dataset processed row 생성 및 로드 |
| `tests/harness/benchmarks/` | IFEval-Ko, KoBALT-700, CLIcK, KMMLU-Pro adapter/scoring |
| `tests/harness/mileday/` | MileDay 일정 생성 fixture, JSON 제약, rubric, Gemini judge |
| `tests/harness/runtime/` | Ollama runtime request/response/error 처리 |
| `tests/harness/performance/` | resource monitor 및 성능 metric summary |

Harness 단위 테스트는 Ollama 모델을 실제로 실행하지 않습니다. Runtime은 mock으로 대체합니다.

## Supabase Integration 테스트

실제 Supabase test project를 사용하는 통합 테스트는 명시적으로 실행합니다.

```powershell
pytest -m integration
```

필수 환경 변수:

```env
ENABLE_INTEGRATION_TESTS=true
SUPABASE_URL=...
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...
TEST_EMAIL=test+integration@example.com
TEST_PASSWORD=...
TEST_USER_ID=...
TEST_TITLE_PREFIX=[TEST]
```

안전 규칙:

- `TEST_EMAIL`은 test 전용 계정이어야 합니다.
- `TEST_TITLE_PREFIX`는 `[TEST`로 시작해야 합니다.
- cleanup은 반드시 `user_id = TEST_USER_ID` 조건으로만 실행합니다.
- 조건 없는 `delete`, `truncate`, 전체 테이블 초기화는 금지합니다.
- service role key는 integration test의 seed/cleanup에만 사용합니다.
- 실제 개인 계정 `user_id`로 integration test를 실행하지 않습니다.

## Backend 테스트 범위

Backend unit test는 다음 범위를 검증합니다.

- FastAPI app bootstrap, health check, router 등록
- 환경 설정 로드, CORS origin 파싱, 로그 경로 정규화
- `X-Request-ID` 생성/전달, 요청별 logging context 격리
- 공통 오류 envelope, validation error, HTTPException, unhandled exception 처리
- password, token, Authorization, email, AI prompt masking
- auth, goals, milestones, calendar, settings route 동작
- service 계층의 user ownership, domain rule, error translation
- repository 계층의 Supabase query 조건
- migration SQL의 핵심 테이블, FK cascade, trigger, RLS policy

## Fixture

주요 fixture:

| 경로 | 설명 |
|---|---|
| `tests/fixtures/mileday/synthetic_schedule.jsonl` | MileDay 일정 생성 smoke/evaluation fixture |
| `tests/fixtures/benchmarks/ifeval_ko/synthetic.jsonl` | IFEval-Ko adapter 테스트용 synthetic data |
| `tests/fixtures/benchmarks/kobalt_700/synthetic.jsonl` | KoBALT-700 adapter 테스트용 synthetic data |
| `tests/fixtures/benchmarks/click/synthetic.jsonl` | CLIcK adapter 테스트용 synthetic data |
| `tests/fixtures/benchmarks/kmmlu_pro/synthetic.jsonl` | KMMLU-Pro adapter 테스트용 synthetic data |

Fixture는 단위 테스트용 synthetic data입니다. 실제 benchmark 실행 dataset은 `datasets/` 아래 processed artifact를 사용합니다.

## Performance 스크립트

`tests/performance/`에는 Electron/frontend 주요 흐름의 latency 측정 스크립트가 있습니다.

```text
tests/performance/
  perf_lib.mjs
  goal_create_latency.mjs
  milestone_create_latency.mjs
  milestone_toggle_latency.mjs
  settings_update_latency.mjs
  date_select_latency.mjs
  cleanup_test_data.mjs
```

이 스크립트들은 일반 `pytest` 대상이 아닙니다. 실행 전 backend/frontend 개발 서버, test user, 필요한 환경 변수를 별도로 준비해야 합니다.

## 의존성

Python 테스트 의존성:

```powershell
pip install -r requirements.txt
```

Frontend 또는 performance 스크립트 의존성:

```powershell
npm install
```

## 자주 쓰는 명령

| 목적 | 명령 |
|---|---|
| 기본 non-integration 전체 테스트 | `pytest` |
| backend coverage gate | `pytest -c pytest-backend.ini` |
| 실제 Supabase integration | `pytest -m integration` |
| harness 전체 | `pytest tests\harness` |
| harness CLI만 | `pytest tests\harness\test_cli.py` |
| benchmark adapter만 | `pytest tests\harness\benchmarks` |

## 주의 사항

- 테스트를 통과시키기 위해 assertion이나 fixture를 약화하지 않습니다.
- integration test는 실제 Supabase project에 쓰기 작업을 수행할 수 있으므로 test 전용 계정만 사용합니다.
- `.env`의 API key, Supabase key, Gemini key는 commit하지 않습니다.
- harness benchmark command의 실제 모델 실행은 unit test가 아니라 local evaluation run입니다.
