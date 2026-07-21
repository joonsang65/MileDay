# 스토리 완료 보고서

## 스토리

- ID: EVAL-007
- 제목: KoBALT-700 Adapter
- 최종 상태: done

## 기준 문서

- `AGENTS.md`
- `docs/codex_rules.md`
- 스토리: `_bmad-output/implementation-artifacts/stories/EVAL-007-kobalt-700-adapter.md`
- 지원 문서:
  - `_bmad-output/planning-artifacts/product-brief.md`
  - `_bmad-output/planning-artifacts/prd.md`
  - `_bmad-output/planning-artifacts/architecture.md`
  - `_bmad-output/planning-artifacts/epics.md`
  - `_bmad-output/planning-artifacts/schemas.md`
  - `docs/decisions/0002-separate-official-and-generation-evaluation.md`
  - `docs/decisions/0003-preserve-raw-model-output.md`

## 요약

명시적 field mapping을 통해 local JSONL/CSV 입력을 로드하는 KoBALT-700 benchmark adapter를 구현했다. 지원되는 choice-answer row만 internal benchmark case로 정규화하고, unsupported row는 조용히 보정하지 않고 `DATASET_SCHEMA_CHANGED`로 실패시킨다. Prompt/scoring/aggregation은 공통 MCQ primitive를 재사용한다.

## 변경 파일

- `harness/benchmarks/kobalt_700.py`: KoBALT-700 field mapping, dataset loading, row normalization, unsupported row 검증, prompt/scoring helper, categorized dataset error를 추가했다.
- `tests/fixtures/benchmarks/kobalt_700/synthetic.jsonl`: offline adapter test용 최소 synthetic local fixture data를 추가했다.
- `tests/harness/benchmarks/test_kobalt_700.py`: fixture loading, explicit custom mapping, missing dataset, missing mapped field, unsupported row shape, invalid answer, aggregate scoring 테스트를 추가했다.
- `_bmad-output/implementation-artifacts/stories/EVAL-007-kobalt-700-adapter.md`: AC 완료와 Story done 상태를 반영했다.
- `_bmad-output/implementation-artifacts/sprint-status.yaml`: EVAL-007을 done으로 표시했다.

## 실행한 명령

```text
pytest tests/harness/benchmarks/test_kobalt_700.py
pytest
pytest -c pytest-backend.ini
```

## 검증 결과

| 검증 | 결과 | 근거 |
|---|---|---|
| Backend tests | PASS | `pytest`: 128 passed, 1 deselected. |
| Frontend audit | NOT_EXECUTED | 이 Story는 frontend 파일을 변경하지 않았다. |
| Frontend tests | NOT_EXECUTED | 이 Story는 frontend 파일을 변경하지 않았다. |
| Frontend lint | NOT_EXECUTED | 이 Story는 frontend 파일을 변경하지 않았다. |
| Frontend build | NOT_EXECUTED | 이 Story는 frontend 파일을 변경하지 않았다. |
| Story smoke test | PASS | `pytest tests/harness/benchmarks/test_kobalt_700.py`: 8 passed. |
| Backend coverage | PASS | `pytest -c pytest-backend.ini`: 128 passed, 1 deselected, coverage 94.83%. |

## 인수 조건

- [x] KoBALT-700 adapter module이 `harness/benchmarks/` 아래에 존재한다: `harness/benchmarks/kobalt_700.py`를 추가했다.
- [x] Adapter가 network access 없이 versioned local fixture file을 로드한다: JSONL/CSV loader는 local path만 읽는다.
- [x] Source-to-internal field mapping이 명시적이다: `KoBALT700FieldMapping`이 source field name을 정의한다.
- [x] Adapter가 누락된 KoBALT-700 dataset field를 추론, rename, fabricate하지 않는다: 누락된 mapped field는 `DATASET_SCHEMA_CHANGED`를 발생시킨다.
- [x] Supported loaded row가 `schemas.md`의 internal Benchmark Case schema로 정규화된다: `KoBALT700Case`가 benchmark, dataset, case, category, question, choices, answer, metadata를 가진다.
- [x] Choice label은 공통 MCQ A-J 범위를 지원하고 mapped choice-answer row의 answer membership을 검증한다: mapping validation과 case validation으로 강제한다.
- [x] Unsupported 또는 non-choice-answer local row는 silent coercion 없이 `DATASET_SCHEMA_CHANGED`로 실패한다: choice field가 없는 free-form shape 테스트로 검증했다.
- [x] Missing file 또는 unreadable dataset path는 `DATASET_UNAVAILABLE`로 보고된다: missing file 테스트로 검증했다.
- [x] Prompt building, answer parsing, scoring, aggregation은 supported choice-answer row에 대해 `harness/benchmarks/mcq.py`를 재사용한다: adapter가 `build_mcq_prompt`, `score_mcq_response`, `aggregate_mcq_results`에 위임한다.
- [x] Raw model output은 downstream result storage에서 사용할 수 있고 parsed answer로 덮어쓰지 않는다: scoring은 `raw_output`을 보존하는 shared MCQ result를 반환한다.
- [x] Offline fixture test가 valid mapped row, explicit custom mapping, missing required mapped field, unsupported row shape, invalid answer label, aggregate scoring을 포함한다: `tests/harness/benchmarks/test_kobalt_700.py`가 해당 case를 검증한다.

## 산출물

- `_bmad-output/implementation-artifacts/completion-reports/EVAL-007-kobalt-700-adapter.md`

## 실패/미실행 항목

- 분류: NOT_EXECUTED
- 설명: Frontend audit/tests/lint/build는 실행하지 않았다. 이 Story는 Python harness와 BMAD 산출물만 변경했다.
- 재현: 해당 없음.
- 권장 조치: frontend 파일을 변경하는 Story 또는 release 검증 시 frontend 검증을 실행한다.

## 알려진 위험

- Fixture data는 synthetic이며 official KoBALT-700 data가 아니다.
- Adapter는 official KoBALT-700 source field 또는 task layout을 다운로드, 재배포, 추정하지 않는다.
- 실제 KoBALT-700 run에는 사용하는 local dataset version에 맞는 explicit field mapping이 필요하다.
- 현재 Story는 supported choice-answer row만 다루며, non-MCQ/free-form KoBALT-700 task는 후속 Story나 별도 adapter 규칙이 필요하다.

## 후속 작업

- EVAL-008 CLIcK adapter를 작성하고 구현한다. MCQ로 표현 가능한 입력은 공통 MCQ primitive를 재사용하되, official source field는 계속 추정하지 않는다.
