# Story EVAL-014: Result Store

## Status

done

## Goal

Implement append/resume-friendly result storage for raw outputs, parsed outputs, metrics, errors, and request-level status using the canonical artifact layout and resume key.

## Context

Depends on EVAL-001, EVAL-003, EVAL-004, and at least one benchmark or MileDay evaluator Story.

Reference:

- `AGENTS.md`
- `_bmad-output/planning-artifacts/product-brief.md`
- `_bmad-output/planning-artifacts/prd.md`
- `_bmad-output/planning-artifacts/architecture.md`
- `_bmad-output/planning-artifacts/epics.md`
- `_bmad-output/planning-artifacts/schemas.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `docs/decisions/0003-preserve-raw-model-output.md`

## Acceptance Criteria

- [x] Result store writes artifacts under `artifacts/runs/{run_id}/`.
- [x] Run configuration snapshot can be written once per run.
- [x] Raw model output is written before parsed or scored output.
- [x] Raw output filenames are deterministic from `model_id`, `dataset_id`, and `case_id`.
- [x] Parsed request results are appended to `parsed/results.jsonl`.
- [x] Performance samples are written to `metrics/performance.jsonl`.
- [x] Stored request results follow the `Request Result` schema from `_bmad-output/planning-artifacts/schemas.md`.
- [x] Resume lookup is keyed by `run_id`, `model_id`, `dataset_id`, and `case_id`.
- [x] Store can identify completed, invalid, failed, and skipped request results without re-running them.
- [x] Partial writes and missing raw output paths are reported clearly without fabricating success.
- [x] Offline unit tests cover raw-first write order, deterministic paths, append behavior, resume lookup, invalid results, failed results, and Windows-compatible paths.

## Out of Scope

- Markdown report rendering
- Final model recommendation policy
- Full benchmark orchestration
- Automatic cleanup or retention policy
- External database storage

## Expected Files

- `harness/results.py`
- `tests/harness/test_results.py`
- Optional updates to `harness/schemas.py`

## Implementation Notes

- Keep storage local and file-based.
- Prefer JSONL for append-friendly request results.
- Do not store raw prompt secrets beyond the already preserved model output requirements.
- Use deterministic filenames and avoid path characters that are invalid on Windows.
- Keep result schema compatible with later Markdown reporting.

## Verification

```powershell
pytest tests/harness/test_results.py
pytest
pytest -c pytest-backend.ini
```

## Completion Evidence

Use `.agents/skills/bmad-implement-story/templates/completion-report.md`.

The EVAL completion report must be written in Korean. Record:

- Files changed
- Test results
- Acceptance Criteria evidence
- Generated artifacts
- Known limitations
- Follow-up Story
