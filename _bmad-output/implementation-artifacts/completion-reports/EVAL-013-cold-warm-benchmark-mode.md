# Story Completion Report

## Story

- ID: EVAL-013
- Title: Cold/Warm Benchmark Mode
- Final Status: done

## Summary

cold/warm benchmark 실행 모드를 추가했다. warmup execution과 measured execution을 별도 phase로 기록하고, warmup-only record는 resume 완료 기준에 포함하지 않도록 분리했다.

## Changed Files

- `harness/orchestrator.py`: `BenchmarkMode`, `ExecutionPhase`, run config, execution record, mockable orchestrator를 추가했다.
- `harness/cli.py`: `run-mileday-smoke` CLI에 `--mode cold|warm` 실행 옵션을 추가했다.
- `tests/harness/test_orchestrator.py`: cold/warm phase, warmup 제외, resume skip, runtime failure category 테스트를 추가했다.
- `tests/harness/test_cli.py`: mock runtime 기반 MileDay smoke command 테스트를 추가했다.
- `_bmad-output/implementation-artifacts/stories/EVAL-013-cold-warm-benchmark-mode.md`: Story 상태와 AC를 완료로 갱신했다.
- `_bmad-output/implementation-artifacts/sprint-status.yaml`: EVAL-013 상태를 `done`으로 갱신했다.

## Commands Run

```text
pytest tests/harness/test_orchestrator.py
pytest tests/harness/performance/test_monitor.py
pytest tests/harness/test_cli.py
pytest
pytest -c pytest-backend.ini
```

## Verification Results

| Verification | Result | Evidence |
|---|---|---|
| Story unit tests | PASS | `pytest tests/harness/test_orchestrator.py`: 4 passed. |
| Performance monitor regression | PASS | included in grouped Story tests: 6 passed. |
| CLI smoke test | PASS | `pytest tests/harness/test_cli.py`: 4 passed. |
| Default tests | PASS | `pytest`: 198 passed, 1 deselected. |
| Backend coverage | PASS | `pytest -c pytest-backend.ini`: 198 passed, 1 deselected, coverage 94.83%. |

## Acceptance Criteria Evidence

- [x] cold/warm mode는 `BenchmarkRunConfig.mode`와 CLI `--mode`로 명시된다.
- [x] warmup phase와 measured phase를 `ExecutionPhase`로 분리했다.
- [x] `measured_records`는 warmup record를 집계/저장 대상에서 제외한다.
- [x] mock runtime과 mock performance monitor로 offline test를 구성했다.
- [x] runtime error는 기존 `EvaluationError` category를 유지한다.

## Known Risks

- 실제 long-running full benchmark orchestration은 아직 최소 smoke command 수준이다.

## Follow-Up Work

- EVAL-014 Result Store.
