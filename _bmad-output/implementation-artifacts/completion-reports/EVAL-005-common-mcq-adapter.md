# 스토리 완료 보고서

## 스토리

- ID: EVAL-005
- 제목: 공통 MCQ Adapter
- 최종 상태: done

## 기준 문서

- `AGENTS.md`
- `docs/codex_rules.md`
- 스토리: `_bmad-output/implementation-artifacts/stories/EVAL-005-common-mcq-adapter.md`
- 지원 문서:
  - `_bmad-output/planning-artifacts/prd.md`
  - `_bmad-output/planning-artifacts/architecture.md`
  - `docs/decisions/0002-separate-official-and-generation-evaluation.md`
  - `docs/decisions/0003-preserve-raw-model-output.md`

## 요약

harness-only 테스트와 backend coverage gate를 분리한 뒤, 재사용 가능한 MCQ benchmark adapter를 추가했다. Prompt building, A-J answer parsing, invalid-output handling, scoring, benchmark/category aggregation을 포함한다.

## 변경 파일

- `pytest.ini`: 기본 test profile을 backend coverage gate 없는 non-integration test로 변경했다.
- `pytest-backend.ini`: 기존 90% threshold를 유지하는 backend coverage profile을 추가했다.
- `AGENTS.md`: 기본 검증 명령과 backend coverage 검증 명령을 문서화했다.
- `.agents/skills/bmad-implement-story/SKILL.md`: verification guidance에 backend coverage 명령을 추가했다.
- `harness/benchmarks/__init__.py`: benchmark package marker를 추가했다.
- `harness/benchmarks/mcq.py`: MCQ model, prompt builder, parser, scorer, aggregate report를 추가했다.
- `tests/harness/benchmarks/test_mcq.py`: parser, invalid output, scoring, aggregation 테스트를 추가했다.
- `_bmad-output/implementation-artifacts/stories/EVAL-005-common-mcq-adapter.md`: AC 완료와 Story done 상태를 반영했다.
- `_bmad-output/implementation-artifacts/sprint-status.yaml`: EVAL-005를 done으로 표시했다.

## 실행한 명령

```text
pytest tests/harness/benchmarks/test_mcq.py
pytest tests/harness/runtime/test_ollama.py
pytest tests/harness/performance/test_monitor.py
pytest -c pytest-backend.ini
pytest
```

## 검증 결과

| 검증 | 결과 | 근거 |
|---|---|---|
| Default tests | PASS | `pytest`: 113 passed, 1 deselected. |
| Backend coverage | PASS | `pytest -c pytest-backend.ini`: 113 passed, 1 deselected, coverage 94.83%. |
| Frontend audit | NOT_EXECUTED | 이 Story는 frontend 파일을 변경하지 않았다. |
| Frontend tests | NOT_EXECUTED | 이 Story는 frontend 파일을 변경하지 않았다. |
| Frontend lint | NOT_EXECUTED | 이 Story는 frontend 파일을 변경하지 않았다. |
| Frontend build | NOT_EXECUTED | 이 Story는 frontend 파일을 변경하지 않았다. |
| Story MCQ test | PASS | `pytest tests/harness/benchmarks/test_mcq.py`: 11 passed. |
| Existing harness targeted tests | PASS | `pytest tests/harness/runtime/test_ollama.py`: 6 passed; `pytest tests/harness/performance/test_monitor.py`: 6 passed. |

## 인수 조건

- [x] Question/choices prompt builder가 존재한다: `build_mcq_prompt`가 question과 labeled choices를 렌더링한다.
- [x] A-J answer choice를 parsing한다: `parse_mcq_answer`가 단일 A-J label을 소문자와 괄호 형태까지 허용한다.
- [x] 모호하거나 여러 개인 answer는 invalid로 표시한다: parser가 missing 또는 multiple distinct label에 대해 `MCQParseStatus.INVALID`를 반환한다.
- [x] Accuracy와 invalid rate가 계산된다: `aggregate_mcq_results`가 `accuracy`와 `invalid_rate`를 계산한다.
- [x] Benchmark-level/category-level aggregate를 지원한다: report가 `by_benchmark`와 `by_category`를 포함한다.
- [x] Parser unit test가 존재한다: `tests/harness/benchmarks/test_mcq.py`가 parsing과 invalid handling을 검증한다.

## 산출물

- `_bmad-output/implementation-artifacts/completion-reports/EVAL-005-common-mcq-adapter.md`

## 실패/미실행 항목

- 분류: TEST_FAILURE
- 설명: 초기 parser가 `I cannot determine the answer.` 문장의 영어 대명사 `I`를 A-J answer로 잘못 처리했다.
- 재현: 초기 parser 구현 상태에서 `pytest tests/harness/benchmarks/test_mcq.py`를 실행한다.
- 권장 조치: 자연어 no-answer case에 대한 parser regression test를 유지한다.

## 알려진 위험

- EVAL-005는 실제 benchmark dataset을 로드하지 않는다. Dataset adapter는 후속 Story 범위다.
- Parser는 의도적으로 deterministic/conservative하게 동작한다. Benchmark-specific adapter는 필요 시 benchmark별 prompt/output 규칙으로 감싸야 한다.

## 후속 작업

- 공통 MCQ primitive를 사용해 EVAL-006 또는 다음 public benchmark-specific adapter를 구현한다.
