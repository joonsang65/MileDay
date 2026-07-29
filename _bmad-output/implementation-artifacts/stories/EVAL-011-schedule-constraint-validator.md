# Story EVAL-011: Schedule Constraint Validator

## Status

done

## Goal

Implement deterministic validation for MileDay schedule-generation outputs so hard constraints are checked before any semantic evaluation.

## Context

Depends on EVAL-001 and EVAL-010.

Reference:

- `AGENTS.md`
- `_bmad-output/planning-artifacts/product-brief.md`
- `_bmad-output/planning-artifacts/prd.md`
- `_bmad-output/planning-artifacts/architecture.md`
- `_bmad-output/planning-artifacts/epics.md`
- `_bmad-output/planning-artifacts/schemas.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/stories/EVAL-010-mileday-dataset-schema.md`
- `docs/decisions/0003-preserve-raw-model-output.md`
- `docs/decisions/0004-use-deterministic-schedule-validation.md`

## Acceptance Criteria

- [x] Deterministic schedule validator module exists under `harness/mileday/`.
- [x] Validator accepts a MileDay generation case and parsed model output.
- [x] Validator checks structured output shape before schedule-specific constraints.
- [x] Validator checks `YYYY-MM-DD` date format for all generated scheduled dates.
- [x] Validator checks milestone count against `min_milestones` and `max_milestones`.
- [x] Validator checks generated scheduled dates do not exceed `latest_allowed_date`.
- [x] Validator checks required output fields listed in `expected.required_fields`.
- [x] Validator includes recurrence rule checks only for recurrence constraints explicitly present in the fixture.
- [x] Invalid schedules are classified as validation failures and cannot be converted to success by later semantic evaluation.
- [x] Validation results include machine-readable failure codes and human-readable messages.
- [x] Raw model output is not modified or discarded by validation.
- [x] Offline unit tests cover valid output, invalid JSON or parsed shape, bad date format, too few milestones, too many milestones, deadline violation, missing required fields, and explicit recurrence constraints.

## Out of Scope

- LLM semantic scoring
- Public benchmark scoring
- Final model recommendation
- Frontend or Electron schedule behavior changes
- Backend API, repository, database, or Supabase changes
- Full benchmark run orchestration

## Expected Files

- `harness/mileday/constraints.py`
- `tests/harness/mileday/test_constraints.py`
- Optional synthetic fixture updates under `tests/fixtures/mileday/`

## Implementation Notes

- Keep validators deterministic and side-effect free.
- Do not call MileDay production services or inspect production user data.
- Keep validation independent from semantic rubrics.
- Treat absent optional constraints as not applicable rather than inventing rules.
- Use shared failure categories from `AGENTS.md` where an error category is needed.

## Verification

```powershell
pytest tests/harness/mileday/test_constraints.py
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
