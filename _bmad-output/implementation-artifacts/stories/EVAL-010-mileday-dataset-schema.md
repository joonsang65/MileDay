# Story EVAL-010: MileDay Dataset Schema

## Status

done

## Goal

Define and validate the MileDay schedule-generation fixture schema for local LLM evaluation, including loader behavior, synthetic fixtures, and strict validation against the internal MileDay Generation Case shape.

## Context

Depends on EVAL-001.

Reference:

- `AGENTS.md`
- `_bmad-output/planning-artifacts/product-brief.md`
- `_bmad-output/planning-artifacts/prd.md`
- `_bmad-output/planning-artifacts/architecture.md`
- `_bmad-output/planning-artifacts/epics.md`
- `_bmad-output/planning-artifacts/schemas.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `docs/decisions/0002-separate-official-and-generation-evaluation.md`
- `docs/decisions/0004-use-deterministic-schedule-validation.md`

## Acceptance Criteria

- [x] MileDay evaluation package/module exists under `harness/`.
- [x] Loader reads versioned local MileDay schedule-generation fixture files without network access.
- [x] Fixture schema follows the `MileDay Generation Case` shape from `_bmad-output/planning-artifacts/schemas.md`.
- [x] `dataset_id`, `case_id`, `locale`, `timezone`, `input`, `expected`, and `metadata` are validated.
- [x] Dates are validated as `YYYY-MM-DD`.
- [x] Default synthetic fixtures use `locale=ko-KR` and `timezone=Asia/Seoul` unless a test explicitly checks alternate valid values.
- [x] Expected constraints validate `min_milestones`, `max_milestones`, `latest_allowed_date`, and `required_fields`.
- [x] Invalid fixture rows fail with `DATASET_SCHEMA_CHANGED`.
- [x] Missing files or unreadable fixture paths are reported with `DATASET_UNAVAILABLE`.
- [x] Fixture data is synthetic and does not depend on MileDay production user data, Supabase, or frontend state.
- [x] Offline unit tests cover valid fixtures, invalid dates, missing required fields, invalid milestone bounds, missing files, and multi-case loading.

## Out of Scope

- Running LLM inference
- Validating generated schedule outputs
- Semantic rubric evaluation
- Production DB, Supabase, or FastAPI integration
- Frontend or Electron changes
- Result persistence and Markdown report generation

## Expected Files

- `harness/mileday/`
- `harness/mileday/dataset.py`
- `tests/harness/mileday/test_dataset.py`
- `tests/fixtures/mileday/`
- Optional small synthetic fixture files under `tests/fixtures/mileday/`

## Implementation Notes

- Keep MileDay generation fixtures separate from public benchmark adapters.
- Use structured parsers for JSON or JSONL fixtures.
- Do not import frontend, Electron, backend service, repository, or Supabase modules.
- Do not add real user data to fixtures.
- Keep schema names aligned with `_bmad-output/planning-artifacts/schemas.md`.

## Verification

```powershell
pytest tests/harness/mileday/test_dataset.py
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
