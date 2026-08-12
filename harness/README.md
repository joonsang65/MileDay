# MileDay Harness

이 브랜치의 harness는 flash-lite 기반 MileDay prompt/parser 테스트에 집중합니다.
과거 외부 평가 adapter와 dataset processor는 이전 평가 브랜치에 남겨 두고, 여기서는 API prompt 개선에 필요한 최소 실행 경로만 유지합니다.

## 실행 명령

```powershell
python -m harness.cli test_api
```

기본 실행은 create를 실제 Supabase DB에 insert하고, 통과한 partial_update를 milestone update로 반영합니다. DB 적재 없이 prompt/parser만 확인하려면 `--write-no`를 사용합니다.

```powershell
python -m harness.cli test_api --limit 3
python -m harness.cli test_api --write-no
python -m harness.cli cleanup --run-id prompt-test-1
```

고정값:

| 항목 | 값 |
|---|---|
| generation model | `gemini-3.5-flash-lite` |
| judge model | `gemini-3.5-flash` |
| sleep | `3.0` seconds |
| mode | cold |
| run id | `prompt-test-<n>` |

## 환경 변수

Gemini와 DB write에 필요한 최소 환경 변수만 사용합니다.

```env
GEMINI_API_KEY=...
SUPABASE_URL=...
SUPABASE_SERVICE_ROLE_KEY=...
TEST_USER_ID=...
TEST_TITLE_PREFIX=[TEST]
```

generation과 judge는 동일한 key를 사용합니다. API base URL과 judge model은 코드 내부 상수로 고정합니다.
`SUPABASE_ANON_KEY`, `SUPABASE_DB_URL`, `TEST_EMAIL`, `TEST_PASSWORD`는 현재 harness DB write 경로에서 사용하지 않습니다.

## 주요 구조

| 파일 | 책임 |
|---|---|
| `cli.py` | Typer app과 얇은 command wrapper |
| `config.py` | `.env` 기반 harness 설정 로드 |
| `model_registry.py` | 로컬 Ollama 후보 모델 조회 |
| `orchestrator.py` | 단일 case 실행 primitive와 performance sample 연결 |
| `results.py` | raw output, parsed result, metric artifact 저장 |
| `reporting.py` | run artifact 기반 Markdown report 생성 |
| `mileday/api_prompt.py` | flash-lite 전용 prompt builder |
| `mileday/api_intent.py` | intent block 추출, parsing, fallback |
| `mileday/api_plan_builder.py` | plan/patch/add/remove item 생성 |
| `mileday/api_validation.py` | deterministic validation과 safety gate |
| `mileday/api_db_payload.py` | DB payload와 SQL preview 순수 함수 |
| `mileday/api_db_client.py` | Supabase create insert, partial update, manifest 기반 cleanup |
| `mileday/api_db_manifest.py` | DB write record와 slot 매핑 저장/로드 |
| `mileday/api_parser.py` | parser orchestration entrypoint |
| `mileday/api_runner.py` | API run 실행 흐름 |
| `mileday/api_summary.py` | API summary와 multiturn report append |
| `runtime/` | Ollama/Gemini runtime adapter |

## 검증

```powershell
python -m harness.cli test_api --help
pytest tests/harness/test_api_cli.py
pytest tests/harness/mileday/test_api_prompt.py
pytest tests/harness/mileday/test_api_intent.py
pytest tests/harness/mileday/test_api_plan_builder.py
pytest tests/harness/mileday/test_api_validation.py
pytest tests/harness/mileday/test_api_parser.py
pytest tests/harness
```

## 주의

- `.env`의 `GEMINI_API_KEY`는 commit하지 않습니다.
- API 호출과 기본 DB write는 실제 과금, quota, 원격 DB row를 사용할 수 있습니다.
- `cleanup --run-id <id>`는 해당 run의 `db_manifest.json`에 기록된 row만 삭제합니다.
- prompt/parser 변경 후에는 `pytest tests/harness`로 회귀를 확인합니다.
