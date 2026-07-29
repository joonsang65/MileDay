# Story Completion Report

## Story

- ID: EVAL-015
- Title: Markdown Report
- Final Status: done

## Source Documents

- `AGENTS.md`
- `docs/codex_rules.md`
- Story: `_bmad-output/implementation-artifacts/stories/EVAL-015-markdown-report.md`
- Supporting documents:
  - `_bmad-output/planning-artifacts/product-brief.md`
  - `_bmad-output/planning-artifacts/prd.md`
  - `_bmad-output/planning-artifacts/architecture.md`
  - `_bmad-output/planning-artifacts/epics.md`
  - `_bmad-output/planning-artifacts/schemas.md`
  - `_bmad-output/implementation-artifacts/stories/EVAL-014-result-store.md`
  - `docs/decisions/0002-separate-official-and-generation-evaluation.md`
  - `docs/decisions/0003-preserve-raw-model-output.md`

## Summary

저장된 `artifacts/runs/{run_id}/` 결과만 읽어 deterministic Markdown 리포트를 생성하는 `harness.reporting` 모듈을 추가했다. 리포트는 모델별, 데이터셋별, invalid/failure, latency/TTFT/throughput/resource metric 요약을 포함하며, 원문 모델 출력은 본문에 삽입하지 않고 raw artifact path만 참조한다.

## Changed Files

- `harness/reporting.py`: stored request results와 performance JSONL을 읽고 `report.md`를 렌더링하는 리포터를 추가했다.
- `tests/harness/test_reporting.py`: complete results, missing metrics, invalid/failed results, partial runs, deterministic output fixture 테스트를 추가했다.
- `_bmad-output/implementation-artifacts/stories/EVAL-015-markdown-report.md`: Story 상태와 Acceptance Criteria를 `done`으로 갱신했다.
- `_bmad-output/implementation-artifacts/sprint-status.yaml`: EVAL-015 상태를 `done`으로 갱신했다.

## Commands Run

```text
pytest tests\harness\test_reporting.py
pytest tests\harness\test_recommendation.py
pytest
pytest -c pytest-backend.ini
```

## Verification Results

| Verification | Result | Evidence |
|---|---|---|
| Story reporting tests | PASS | `pytest tests\harness\test_reporting.py`: 5 passed. |
| Recommendation compatibility tests | PASS | `pytest tests\harness\test_recommendation.py`: 7 passed. |
| Default tests | PASS | `pytest`: 201 passed, 1 deselected. |
| Backend coverage profile | PASS | `pytest -c pytest-backend.ini`: 201 passed, 1 deselected, coverage 94.83%. |

## Acceptance Criteria

- [x] `ResultStore`를 통해 `artifacts/runs/{run_id}/parsed/results.jsonl` 결과를 읽는다.
- [x] `generate_markdown_report()`가 run directory 아래 `report.md`를 생성한다.
- [x] 데이터가 있을 때 모델별 및 데이터셋별 요약 표를 생성한다.
- [x] invalid output과 failed output을 failure category 기준으로 요약한다.
- [x] request metric과 resource metric이 있을 때 latency, TTFT, throughput, CPU/RAM/VRAM 요약을 표시한다.
- [x] raw output 본문은 삽입하지 않고 `raw_output_path`만 참조한다.
- [x] 누락된 결과와 metric은 `missing` 또는 `not executed`로 표시한다.
- [x] public benchmark와 MileDay generation 결과를 별도 family로 분리한다.
- [x] 동일 입력에 대해 동일한 Markdown을 생성하도록 정렬과 포맷을 고정했다.
- [x] offline fixture 테스트가 complete, missing metrics, invalid, failed, partial, deterministic 케이스를 포함한다.

## Generated Artifacts

- `_bmad-output/implementation-artifacts/completion-reports/EVAL-015-markdown-report.md`

## Failures / Not Executed Items

- Category: NOT_EXECUTED
- Description: Frontend 검증은 harness-only 변경이므로 실행하지 않았다.
- Reproduction: 해당 없음.
- Recommended action: frontend 또는 Electron 변경 Story에서만 frontend 검증을 실행한다.

## Known Risks

- 데이터셋 family 구분은 저장된 `dataset_id`와 `parsed_output`의 명시 필드를 기준으로 한다. 새로운 family가 추가되면 reporter 분류 규칙을 확장해야 한다.

## Follow-Up Work

- EVAL-016 Final Model Recommendation Summary.
