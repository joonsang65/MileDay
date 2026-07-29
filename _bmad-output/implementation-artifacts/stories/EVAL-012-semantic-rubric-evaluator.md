# Story EVAL-012: Semantic Rubric Evaluator

## Status

done

## Goal

Define and implement a documented semantic rubric evaluator for MileDay schedule-generation outputs that runs after deterministic validation and never hides invalid schedules.

## Context

Depends on EVAL-001, EVAL-010, and EVAL-011.

Reference:

- `AGENTS.md`
- `_bmad-output/planning-artifacts/product-brief.md`
- `_bmad-output/planning-artifacts/prd.md`
- `_bmad-output/planning-artifacts/architecture.md`
- `_bmad-output/planning-artifacts/epics.md`
- `_bmad-output/planning-artifacts/schemas.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/stories/EVAL-010-mileday-dataset-schema.md`
- `_bmad-output/implementation-artifacts/stories/EVAL-011-schedule-constraint-validator.md`
- `docs/decisions/0002-separate-official-and-generation-evaluation.md`
- `docs/decisions/0003-preserve-raw-model-output.md`
- `docs/decisions/0004-use-deterministic-schedule-validation.md`

## Acceptance Criteria

- [x] Semantic rubric is documented in code or a harness-local documentation file.
- [x] Rubric evaluates MileDay-specific schedule usefulness without changing deterministic validation results.
- [x] Evaluator accepts deterministic validation output as an input.
- [x] Outputs that fail deterministic validation are not promoted to valid by semantic score.
- [x] Evaluator result includes rubric dimension scores, aggregate score, and explanatory notes.
- [x] Raw model output remains preserved and is not overwritten by rubric output.
- [x] Any optional LLM judge boundary is mockable and disabled for offline unit tests.
- [x] Missing or unavailable semantic judge dependencies degrade clearly with an appropriate failure category instead of fabricating scores.
- [x] Offline unit tests cover valid schedule scoring, invalid schedule gating, missing judge dependency, mock judge behavior, and rubric aggregation.

## Out of Scope

- Requiring a cloud-hosted judge
- Running real model inference
- Producing final model recommendation
- Public benchmark scoring
- Frontend, Electron, backend API, or Supabase changes
- Modifying deterministic schedule constraints from EVAL-011

## Expected Files

- `harness/mileday/rubric.py`
- `tests/harness/mileday/test_rubric.py`
- Optional harness-local rubric documentation

## Implementation Notes

- Deterministic validation is the hard gate.
- Semantic scoring should be explainable and reproducible for offline tests.
- Do not claim semantic scores are official benchmark scores.
- Keep MileDay semantic evaluation separate from public benchmark adapters.
- Do not add external service requirements for CI.

## Verification

```powershell
pytest tests/harness/mileday/test_rubric.py
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
