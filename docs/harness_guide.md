# MileDay Flash-Lite API Harness Guide

이 문서는 현재 브랜치의 harness 사용법과 코드 구조를 정리한다. 현재 harness는 여러 모델 benchmark가 아니라 `gemini-3.5-flash-lite` 기반 MileDay 멀티턴 prompt/parser 개선에 집중한다.

## 현재 목적

- API 모델은 `gemini-3.5-flash-lite`로 고정한다.
- 실행 명령은 `python -m harness.cli test_api` 하나로 단순화한다.
- 모델 출력은 `[SCHEDULE_INTENT]` 블록으로 받고, parser가 DB 적재 후보를 만든다.
- 실제 DB write, Supabase 호출, migration은 하지 않는다.
- parser output에서 `db_payload`와 SQL preview로 이어질 수 있는 순수 함수 경계를 유지한다.

## 환경 설정

루트 `.env`에 Gemini key만 추가한다.

```env
GEMINI_API_KEY=your_gemini_api_key
```

generation과 judge는 같은 key를 사용한다. API base URL, generation model, judge model, sleep time은 코드 내부 상수로 고정한다.

## 실행 명령

전체 fixture 실행:

```powershell
python -m harness.cli test_api
```

일부 case만 실행:

```powershell
python -m harness.cli test_api --limit 3
```

`test_api`의 선택 옵션은 `--limit`만 둔다. `--model-id`, `--sleep-seconds`, `--mode`는 사용하지 않는다.

고정값:

| 항목 | 값 |
|---|---|
| generation model | `gemini-3.5-flash-lite` |
| judge model | `gemini-3.5-flash` |
| sleep | `3.0` seconds |
| mode | cold |
| run id | `prompt-test-<n>` |
| prompt version | `v12-api` |

## 결과 파일

예:

```text
artifacts/runs/
  prompt-test-1/
    raw/
    parsed/
      results.jsonl
      results.pretty.json
    metrics/
      performance.jsonl
    report.md
    report.html
  prompt-test-1-summary.md
```

파일 의미:

- `raw/*.txt`: Gemini 원본 응답
- `parsed/results.jsonl`: 머신 처리용 결과
- `parsed/results.pretty.json`: 사람이 보기 좋은 결과
- `metrics/performance.jsonl`: latency, TTFT, throughput, resource sample
- `report.md`: 기본 Markdown report
- `report.html`: MileDay 멀티턴 전용 HTML report
- `prompt-test-<n>-summary.md`: 단일 flash-lite prompt test 요약

## 평가 흐름

```text
fixture case 로드
-> flash-lite prompt 생성
-> Gemini generation 호출
-> [SCHEDULE_INTENT] 추출
-> intent parse 또는 freeform fallback
-> plan_items / patch_items / add_items / remove_slot_ids 생성
-> deterministic validation
-> db_payload 생성
-> Gemini judge 평가
-> result artifact 저장
-> Markdown/HTML/summary 생성
```

필수 output contract:

```text
[SCHEDULE_INTENT]
action: create or partial_update
target: create target, or existing slot_id/task for partial_update
change: requested change
tasks:
- Korean task name
[/SCHEDULE_INTENT]
```

## 코드 구조

| 파일 | 책임 |
|---|---|
| `harness/cli.py` | Typer app과 얇은 command wrapper |
| `harness/mileday/api_constants.py` | flash-lite API harness 고정 상수 |
| `harness/mileday/api_runner.py` | `test_api` 실행 흐름, Gemini runtime/judge 연결 |
| `harness/mileday/api_prompt.py` | flash-lite 전용 prompt builder와 allowed slot formatting |
| `harness/mileday/api_intent.py` | `[SCHEDULE_INTENT]` 추출, intent parsing, fallback |
| `harness/mileday/api_plan_builder.py` | create/partial_update plan, patch, add, remove item 생성 |
| `harness/mileday/api_validation.py` | slot/date/time/schema/safety gate 검증 |
| `harness/mileday/api_db_payload.py` | DB payload와 SQL preview 순수 함수 |
| `harness/mileday/api_parser.py` | `evaluate_api_multiturn_record()` orchestration |
| `harness/mileday/api_summary.py` | API run Markdown summary와 multiturn report append |
| `harness/results.py` | raw output, parsed result, metric artifact 저장 |
| `harness/reporting.py` | run artifact 기반 공통 Markdown report 생성 |

## DB Payload / SQL Preview

parser의 최종 결과는 아래 주요 shape를 유지한다.

```text
plan_items
patch_items
add_items
remove_slot_ids
db_payload
requires_confirmation
```

`api_db_payload.py`는 다음 순수 함수를 제공한다.

- `build_goal_payload()`
- `build_milestone_payloads()`
- `build_schedule_db_payload()`
- `build_sql_statements()`
- `build_insert_sql_preview()`

현재 SQL은 preview 용도이며 실제 DB에 실행하지 않는다.

SQL preview는 실제 MileDay DB 스키마에 맞춰 다음 원칙을 따른다.

- 목표는 `public.goals`에 insert한다.
- 마일스톤은 `public.milestones`에 insert한다.
- `user_id`는 클라이언트 입력이 아니라 인증된 JWT subject에서 bind할 값으로 둔다.
- `goal_id`는 새로 insert된 goal의 `id`를 CTE의 `inserted_goal.id`로 연결한다.
- 마일스톤의 `is_completed`는 생성 시 `false`로 둔다.
- `created_at`, `updated_at`, `id`는 DB default와 trigger에 맡긴다.
- preview SQL은 `:goal_title`, `:milestone_1_title` 같은 named parameter를 사용한다.
- `build_sql_parameters()`는 SQL preview에 대응되는 parameter map을 만든다.

## 검증 명령

CLI help:

```powershell
python -m harness.cli --help
python -m harness.cli test_api --help
```

핵심 harness 테스트:

```powershell
pytest tests/harness/test_cli.py
pytest tests/harness/test_api_cli.py
pytest tests/harness/mileday/test_api_prompt.py
pytest tests/harness/mileday/test_api_intent.py
pytest tests/harness/mileday/test_api_plan_builder.py
pytest tests/harness/mileday/test_api_validation.py
pytest tests/harness/mileday/test_api_parser.py
```

전체 harness 회귀:

```powershell
pytest tests/harness
```

잔여 참조 검색은 이전 API command, benchmark command, legacy Gemini env, 비교 대상 모델명이 실행 코드에 남아 있지 않은지 확인하는 용도로 수행한다.

## 트러블 슈팅

### `GEMINI_API_KEY is required.`

원인:

- 루트 `.env`에 `GEMINI_API_KEY`가 없다.

해결:

- `.env.example`을 참고해 `.env`에 `GEMINI_API_KEY`를 추가한다.

### Gemini 429 Too Many Requests

원인:

- API quota 또는 rate limit에 걸렸다.
- 같은 key로 generation과 judge를 모두 호출하므로 turn 수가 늘면 호출량이 빠르게 증가한다.

해결:

- `--limit`으로 case 수를 줄여 실행한다.
- quota가 회복된 뒤 다시 실행한다.
- 현재 sleep은 3초로 고정되어 있다.

### Gemini 400 Bad Request

원인 후보:

- 현재 코드 상수의 모델 id가 실제 API에서 지원되지 않는다.
- Gemini structured output schema 또는 request body 형식이 API와 맞지 않는다.
- API key의 프로젝트 정책이나 quota 문제일 수 있다.

확인:

- `parsed/results.pretty.json`의 `error.message`를 확인한다.
- raw response body 일부가 error message에 저장되어 있는지 확인한다.

### invalid가 많은 경우

확인 순서:

1. `raw/*.txt`에서 `[SCHEDULE_INTENT]` 형식 확인
2. `parsed/results.pretty.json`의 `error.message` 확인
3. `parsed_output.multiturn_validation.deterministic_validation` 확인
4. `api_prompt.py`, `api_intent.py`, `api_plan_builder.py`, `api_validation.py` 중 실패 위치에 맞는 파일 수정

### 같은 run id로 재실행되지 않음

`test_api`는 `prompt-test-<n>` 형식으로 새 sequence를 자동 생성한다. 기존 결과를 덮어쓰지 않고 다음 번호로 저장한다.
