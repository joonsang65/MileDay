# 스토리 완료 보고서

## 스토리

- ID: EVAL-006
- 제목: KMMLU-Pro Adapter
- 최종 상태: done

## 기준 문서

- `AGENTS.md`
- `docs/codex_rules.md`
- 스토리: `_bmad-output/implementation-artifacts/stories/EVAL-006-kmmlu-pro-adapter.md`
- 지원 문서:
  - `_bmad-output/planning-artifacts/product-brief.md`
  - `_bmad-output/planning-artifacts/prd.md`
  - `_bmad-output/planning-artifacts/architecture.md`
  - `_bmad-output/planning-artifacts/epics.md`
  - `_bmad-output/planning-artifacts/schemas.md`
  - `docs/decisions/0002-separate-official-and-generation-evaluation.md`
  - `docs/decisions/0003-preserve-raw-model-output.md`

## 요약

명시적 field mapping을 통해 local JSONL/CSV 입력을 로드하는 KMMLU-Pro benchmark adapter를 구현했다. Row를 internal benchmark case로 정규화하고, 공통 MCQ prompt/scoring primitive를 재사용하며, dataset availability/schema failure를 shared failure category로 보고한다.

## 변경 파일

- `harness/benchmarks/kmmlu_pro.py`: KMMLU-Pro field mapping, dataset loading, row normalization, prompt/scoring helper, categorized dataset error를 추가했다.
- `tests/fixtures/benchmarks/kmmlu_pro/synthetic.jsonl`: offline adapter test용 최소 synthetic local fixture data를 추가했다.
- `tests/harness/benchmarks/test_kmmlu_pro.py`: fixture loading, explicit mapping, invalid row, missing dataset, prompt, aggregate scoring 테스트를 추가했다.
- `_bmad-output/implementation-artifacts/stories/EVAL-006-kmmlu-pro-adapter.md`: AC 완료와 Story done 상태를 반영했다.
- `_bmad-output/implementation-artifacts/sprint-status.yaml`: EVAL-006을 done으로 표시했다.

## 실행한 명령

```text
pytest tests/harness/benchmarks/test_kmmlu_pro.py
pytest
pytest -c pytest-backend.ini
```

## 검증 결과

| 검증 | 결과 | 근거 |
|---|---|---|
| Backend tests | PASS | `pytest`: 120 passed, 1 deselected. |
| Frontend audit | NOT_EXECUTED | 이 Story는 frontend 파일을 변경하지 않았다. |
| Frontend tests | NOT_EXECUTED | 이 Story는 frontend 파일을 변경하지 않았다. |
| Frontend lint | NOT_EXECUTED | 이 Story는 frontend 파일을 변경하지 않았다. |
| Frontend build | NOT_EXECUTED | 이 Story는 frontend 파일을 변경하지 않았다. |
| Story smoke test | PASS | `pytest tests/harness/benchmarks/test_kmmlu_pro.py`: 7 passed. |
| Backend coverage | PASS | `pytest -c pytest-backend.ini`: 120 passed, 1 deselected, coverage 94.83%. |

## 인수 조건

- [x] KMMLU-Pro adapter module이 `harness/benchmarks/` 아래에 존재한다: `harness/benchmarks/kmmlu_pro.py`를 추가했다.
- [x] Adapter가 network access 없이 versioned local fixture file을 로드한다: JSONL/CSV loader는 local path만 읽는다.
- [x] Source-to-internal field mapping이 명시적이다: `KMMLUProFieldMapping`이 모든 source field name을 정의한다.
- [x] Adapter가 누락된 KMMLU-Pro dataset field를 추론, rename, fabricate하지 않는다: 누락된 required mapped field는 `DATASET_SCHEMA_CHANGED`를 발생시킨다.
- [x] Loaded row가 `schemas.md`의 internal Benchmark Case schema로 정규화된다: `KMMLUProCase`가 benchmark, dataset, case, category, question, choices, answer, metadata를 가진다.
- [x] Choice label은 공통 MCQ A-J 범위를 지원하고 answer membership을 검증한다: mapping과 case validation이 A-J label 및 answer membership을 강제한다.
- [x] Invalid dataset row는 상황에 따라 `DATASET_SCHEMA_CHANGED` 또는 `DATASET_UNAVAILABLE`로 보고된다: missing file, missing field, invalid answer, malformed input path 테스트로 검증했다.
- [x] Prompt building, answer parsing, scoring, aggregation은 `harness/benchmarks/mcq.py`를 재사용한다: adapter가 `build_mcq_prompt`, `score_mcq_response`, `aggregate_mcq_results`에 위임한다.
- [x] Raw model output은 downstream result storage에서 사용할 수 있고 parsed answer로 덮어쓰지 않는다: scoring은 `raw_output`을 보존하는 shared MCQ result를 반환한다.
- [x] Offline fixture test가 valid row, missing required mapped field, invalid answer label, aggregate scoring을 포함한다: `tests/harness/benchmarks/test_kmmlu_pro.py`가 해당 case를 검증한다.

## 산출물

- `_bmad-output/implementation-artifacts/completion-reports/EVAL-006-kmmlu-pro-adapter.md`

## 실패/미실행 항목

- 분류: TEST_FAILURE
- 설명: 초기 targeted test run에서 두 가지 validation gap이 드러났다. optional `category`를 required처럼 처리했고, `KMMLUProCase`가 `answer`가 available choices 안에 있는지 검증하지 않았다.
- 재현: 초기 EVAL-006 구현 상태에서 `pytest tests/harness/benchmarks/test_kmmlu_pro.py`를 실행한다.
- 권장 조치: nullable category와 invalid answer membership 테스트를 regression coverage로 유지한다.

## 알려진 위험

- Fixture data는 synthetic이며 official KMMLU-Pro data가 아니다.
- Adapter는 official KMMLU-Pro source field를 다운로드, 재배포, 추정하지 않는다.
- 실제 KMMLU-Pro run에는 사용하는 local dataset version에 맞는 explicit field mapping이 필요하다.

## 후속 작업

- 같은 explicit mapping과 raw-output preservation 규칙을 사용해 EVAL-007 KoBALT-700 adapter를 구현한다.
