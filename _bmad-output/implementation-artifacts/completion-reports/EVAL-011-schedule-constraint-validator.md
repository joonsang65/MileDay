# Story Completion Report

## Story

- ID: EVAL-011
- Title: Schedule Constraint Validator
- Final Status: done

## Summary

MileDay 일정 생성 출력에 대한 결정적 제약 검증기를 추가했다. 검증기는 `MileDayGenerationCase`와 parsed model output을 입력으로 받아 structured output shape, `YYYY-MM-DD` 날짜, milestone 개수, `latest_allowed_date`, required fields, 명시된 weekly recurrence를 검사한다.

## Changed Files

- `harness/mileday/constraints.py`: 결정적 일정 검증 모델과 `validate_schedule_output`을 추가했다.
- `harness/mileday/__init__.py`: constraint validator export를 추가했다.
- `tests/harness/mileday/test_constraints.py`: valid/invalid output과 recurrence 테스트를 추가했다.
- `_bmad-output/implementation-artifacts/stories/EVAL-011-schedule-constraint-validator.md`: Story 상태와 AC를 완료로 갱신했다.
- `_bmad-output/implementation-artifacts/sprint-status.yaml`: EVAL-011 상태를 `done`으로 갱신했다.

## Commands Run

```text
pytest tests/harness/mileday/test_constraints.py
pytest
pytest -c pytest-backend.ini
```

## Verification Results

| Verification | Result | Evidence |
|---|---|---|
| Story unit tests | PASS | `pytest tests/harness/mileday/test_constraints.py`: 9 passed. |
| Default tests | PASS | `pytest`: 198 passed, 1 deselected. |
| Backend coverage | PASS | `pytest -c pytest-backend.ini`: 198 passed, 1 deselected, coverage 94.83%. |

## Acceptance Criteria Evidence

- [x] `harness/mileday/constraints.py`에 deterministic validator를 추가했다.
- [x] validator는 `MileDayGenerationCase`와 parsed output을 입력으로 받는다.
- [x] shape 검증을 먼저 수행하고 이후 일정 제약을 검사한다.
- [x] invalid schedule은 `ScheduleValidationResult.is_valid=False`와 machine-readable failure code로 남긴다.
- [x] raw output은 `ScheduleValidationResult.raw_output`에 보존된다.

## Known Risks

- EVAL-011은 fixture에 명시된 recurrence만 검증한다. 더 복잡한 반복 규칙은 별도 Story가 필요하다.

## Follow-Up Work

- EVAL-012 Semantic Rubric Evaluator.
