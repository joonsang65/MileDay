# Docs

`docs/`는 MileDay 제품 설계, API, DB, 운영 규칙, LLM 하네스 의사결정을 기록하는 문서 디렉터리입니다. 구현 중 판단 기준이 필요할 때 먼저 확인해야 하는 source of truth입니다.

## 주요 문서

| 문서 | 역할 |
|---|---|
| `codex_rules.md` | Codex 작업 원칙, 금지 사항, 구현 우선순위 |
| `requirements.md` | MileDay 기능 요구사항과 MVP/Future 범위 |
| `api_spec.md` | FastAPI endpoint, request/response, 인증 필요 여부 |
| `db_schema.md` | Supabase PostgreSQL table, field, RLS 기준 |
| `data_flow.md` | 기능별 frontend/backend/database 데이터 흐름 |
| `error_logging.md` | 공통 에러 envelope, error code, request_id, logging 기준 |
| `troubleshooting.md` | 개발 중 자주 발생하는 문제와 해결 절차 |
| `harness_guide.md` | flash-lite API prompt/parser harness 실행, report, judge, troubleshooting |
| `commit_guide.md` | commit message 형식과 분할 기준 |
| `performance_report._v1.md` | 성능 측정 결과와 분석 기록 |

## Decisions

`docs/decisions/`는 ADR 성격의 의사결정 기록을 둡니다.

예:

```text
docs/decisions/
  0001-use-ollama-as-default-runtime.md
  0011-select-gemini-flash-lite-for-api-llm.md
```

모델 후보 제외, 평가 범위 변경, prompt/parser 기준 변경처럼 나중에 다시 확인해야 하는 판단은 일반 README보다 decision 문서로 남기는 편이 좋습니다.

## 문서 읽는 순서

### MileDay 앱 구현

1. `codex_rules.md`
2. 현재 요청 또는 Story
3. `requirements.md`
4. `api_spec.md`
5. `db_schema.md`
6. `data_flow.md`
7. `error_logging.md`
8. `troubleshooting.md`
9. 기존 코드

### Harness 구현

1. `codex_rules.md`
2. 현재 Story 또는 요청
3. `docs/decisions/`
4. `_bmad-output/planning-artifacts/architecture.md`
5. `_bmad-output/planning-artifacts/prd.md`
6. `_bmad-output/planning-artifacts/product-brief.md`
7. `_bmad-output/implementation-artifacts/sprint-status.yaml`
8. 기존 코드

## 문서 작성 기준

- 구현 사실과 계획을 구분해서 씁니다.
- 평가 결과는 실행 명령, 모델 id, fixture revision, case 수, prompt version, date를 함께 남깁니다.
- 단순 사용법은 README 또는 guide에 둡니다.
- 되돌아볼 의사결정은 `docs/decisions/`에 둡니다.
- 실제 코드와 충돌하는 문서는 그대로 방치하지 않고 차이를 명시합니다.
- API, DB, error envelope 변경은 관련 문서를 함께 갱신합니다.

## 인코딩 주의

일부 기존 Markdown은 Windows 환경에서 잘못된 인코딩으로 열릴 경우 한글이 깨져 보일 수 있습니다. 새 문서는 UTF-8 기준으로 작성합니다. 편집기에서 한글이 깨지면 파일 인코딩을 UTF-8로 다시 열어 확인합니다.
