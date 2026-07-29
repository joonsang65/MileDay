# Story Completion Report

## Story

- ID: EVAL-016
- Title: Final Model Recommendation Summary
- Final Status: done

## Source Documents

- `AGENTS.md`
- `docs/codex_rules.md`
- Story: `_bmad-output/implementation-artifacts/stories/EVAL-016-final-model-recommendation-summary.md`
- Supporting documents:
  - `_bmad-output/planning-artifacts/product-brief.md`
  - `_bmad-output/planning-artifacts/prd.md`
  - `_bmad-output/planning-artifacts/architecture.md`
  - `_bmad-output/planning-artifacts/epics.md`
  - `_bmad-output/planning-artifacts/schemas.md`
  - `_bmad-output/implementation-artifacts/stories/EVAL-014-result-store.md`
  - `_bmad-output/implementation-artifacts/stories/EVAL-015-markdown-report.md`
  - `docs/decisions/0002-separate-official-and-generation-evaluation.md`
  - `docs/decisions/0003-preserve-raw-model-output.md`

## Summary

저장된 증거만 사용해 최종 모델 추천 여부를 판단하는 `harness.recommendation` 모듈을 추가했다. public benchmark, MileDay deterministic validation, MileDay semantic rubric, performance metrics, invalid/failure rate hard gate를 통과하지 못하면 추천하지 않으며, near-tie도 deterministic하게 `no_recommendation`으로 처리한다.

## Changed Files

- `harness/recommendation.py`: hard-gate 규칙, 모델별 evidence 집계, ranking score, near-tie 처리, Markdown 렌더링을 추가했다.
- `harness/reporting.py`: EVAL-015 Markdown report에 recommendation summary를 선택적으로 포함할 수 있게 연결했다.
- `tests/harness/test_recommendation.py`: clear winner, insufficient data, missing MileDay, missing performance, high invalid rate, failed run, deterministic tie 테스트를 추가했다.
- `_bmad-output/implementation-artifacts/stories/EVAL-016-final-model-recommendation-summary.md`: Story 상태와 Acceptance Criteria를 `done`으로 갱신했다.
- `_bmad-output/implementation-artifacts/sprint-status.yaml`: EVAL-016 상태를 `done`으로 갱신했다.

## Commands Run

```text
pytest tests\harness\test_recommendation.py
pytest tests\harness\test_reporting.py
pytest
pytest -c pytest-backend.ini
```

## Verification Results

| Verification | Result | Evidence |
|---|---|---|
| Story recommendation tests | PASS | `pytest tests\harness\test_recommendation.py`: 7 passed. |
| Reporting compatibility tests | PASS | `pytest tests\harness\test_reporting.py`: 5 passed. |
| Default tests | PASS | `pytest`: 201 passed, 1 deselected. |
| Backend coverage profile | PASS | `pytest -c pytest-backend.ini`: 201 passed, 1 deselected, coverage 94.83%. |

## Acceptance Criteria

- [x] hard-gate 규칙은 `HARD_GATE_RULES`와 gate 상수로 코드에 명시했다.
- [x] public benchmark, MileDay deterministic validation, semantic rubric, performance metrics, invalid/failure rate를 함께 사용한다.
- [x] 필수 evidence가 없으면 `insufficient_data` 또는 `no_recommendation`을 반환한다.
- [x] model identity는 stored result의 `model_id`만 사용하며 model tag를 새로 만들지 않는다.
- [x] public score와 MileDay score는 family별로 분리 집계한 뒤 ranking score에 반영한다.
- [x] summary는 run id, model id, dataset id, raw artifact path를 추적 가능한 evidence로 포함한다.
- [x] near-tie는 `NEAR_TIE_SCORE_DELTA` 이내에서 deterministic sorted order와 `no_recommendation`으로 처리한다.
- [x] failed, skipped, invalid result는 gate와 rate 계산에 반영된다.
- [x] `render_recommendation_markdown()` 결과를 EVAL-015 report에 선택적으로 포함할 수 있다.
- [x] offline fixture 테스트가 clear winner, insufficient data, missing MileDay, missing performance, high invalid rate, failed model runs, deterministic tie를 포함한다.

## Generated Artifacts

- `_bmad-output/implementation-artifacts/completion-reports/EVAL-016-final-model-recommendation-summary.md`

## Failures / Not Executed Items

- Category: NOT_EXECUTED
- Description: Frontend 검증은 harness-only 변경이므로 실행하지 않았다.
- Reproduction: 해당 없음.
- Recommended action: frontend 또는 Electron 변경 Story에서만 frontend 검증을 실행한다.

## Known Risks

- hard-gate threshold는 현재 local harness 정책으로 코드에 고정되어 있다. 실제 운영 기준이 정해지면 Story로 threshold 조정이 필요하다.

## Follow-Up Work

- 실제 completed run artifact를 대상으로 `generate_markdown_report(..., include_recommendation=True)` smoke 실행을 추가하는 후속 Story를 고려한다.
