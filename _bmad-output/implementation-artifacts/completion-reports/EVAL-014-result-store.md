# Story Completion Report

## Story

- ID: EVAL-014
- Title: Result Store
- Final Status: done

## Summary

로컬 파일 기반 result store를 추가했다. 저장소는 `artifacts/runs/{run_id}/` 아래에 config snapshot, raw output, parsed request result JSONL, performance JSONL을 저장하며, raw output을 parsed/scored result보다 먼저 기록한다.

## Changed Files

- `harness/results.py`: append/resume-friendly result store와 deterministic raw path 생성을 추가했다.
- `harness/cli.py`: MileDay smoke 실행 결과를 result store에 저장하도록 연결했다.
- `tests/harness/test_results.py`: raw-first write, deterministic path, append, resume lookup, invalid/failed result, missing raw path, performance sample 테스트를 추가했다.
- `_bmad-output/implementation-artifacts/stories/EVAL-014-result-store.md`: Story 상태와 AC를 완료로 갱신했다.
- `_bmad-output/implementation-artifacts/sprint-status.yaml`: EVAL-014 상태를 `done`으로 갱신했다.

## Commands Run

```text
pytest tests/harness/test_results.py
pytest
pytest -c pytest-backend.ini
```

## Verification Results

| Verification | Result | Evidence |
|---|---|---|
| Story unit tests | PASS | `pytest tests/harness/test_results.py`: 5 passed. |
| Default tests | PASS | `pytest`: 198 passed, 1 deselected. |
| Backend coverage | PASS | `pytest -c pytest-backend.ini`: 198 passed, 1 deselected, coverage 94.83%. |

## Acceptance Criteria Evidence

- [x] artifacts are written under `artifacts/runs/{run_id}/`.
- [x] config snapshot, raw output, parsed JSONL, metrics JSONL writing을 지원한다.
- [x] raw output filename은 `model_id`, `dataset_id`, `case_id`에서 deterministic하게 만든다.
- [x] resume lookup은 `run_id`, `model_id`, `dataset_id`, `case_id`를 key로 사용한다.
- [x] missing raw path는 `CODE_ERROR`로 실패하며 성공으로 숨기지 않는다.

## Known Risks

- store는 local file 기반이며 cleanup/retention policy는 범위 밖이다.

## Follow-Up Work

- EVAL-015 Markdown Report.
