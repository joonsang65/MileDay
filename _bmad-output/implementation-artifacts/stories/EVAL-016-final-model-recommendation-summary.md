# Story EVAL-016: Final Model Recommendation Summary

## Status

done

## Goal

Implement a hard-gate final model recommendation summary that combines public benchmark results, MileDay validation results, performance metrics, and failure rates with traceable evidence.

## Context

Depends on EVAL-009, EVAL-012, EVAL-013, EVAL-014, and EVAL-015.

Reference:

- `AGENTS.md`
- `_bmad-output/planning-artifacts/product-brief.md`
- `_bmad-output/planning-artifacts/prd.md`
- `_bmad-output/planning-artifacts/architecture.md`
- `_bmad-output/planning-artifacts/epics.md`
- `_bmad-output/planning-artifacts/schemas.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/stories/EVAL-014-result-store.md`
- `_bmad-output/implementation-artifacts/stories/EVAL-015-markdown-report.md`
- `docs/decisions/0002-separate-official-and-generation-evaluation.md`
- `docs/decisions/0003-preserve-raw-model-output.md`

## Acceptance Criteria

- [x] Recommendation logic uses explicit hard-gate rules documented in code or harness-local documentation.
- [x] Recommendation combines public benchmark evidence, MileDay deterministic validation, MileDay semantic rubric results, performance metrics, and failure or invalid rates.
- [x] Missing required evidence produces `no recommendation` or `insufficient data` rather than a fabricated winner.
- [x] Model tags and model identities come from configured/stored results and are not invented.
- [x] Public benchmark scores and MileDay generation scores remain separate before any combined summary is produced.
- [x] Recommendation summary includes traceable references to run id, model id, dataset id, and report or artifact paths.
- [x] Tie or near-tie behavior is explicit and deterministic.
- [x] Failed, skipped, and invalid results affect recommendation according to documented rules.
- [x] Summary can be included in or appended to the Markdown report from EVAL-015.
- [x] Offline fixture tests cover clear winner, insufficient data, missing MileDay results, missing performance metrics, high invalid rate, failed model runs, and deterministic tie handling.

## Out of Scope

- Automatic model installation
- Production serving deployment
- Real user A/B testing
- Changing benchmark adapter scoring rules
- Fabricating scores for missing datasets
- Frontend report UI

## Expected Files

- `harness/recommendation.py`
- `tests/harness/test_recommendation.py`
- Optional updates to `harness/reporting.py`
- Optional fixture artifacts under `tests/fixtures/results/`

## Implementation Notes

- Treat recommendation as a summary over stored evidence, not as a new evaluator.
- Use hard gates before weighted ranking.
- If a required evidence family is absent, prefer no recommendation over a weak recommendation.
- Keep all output reproducible from stored artifacts.
- Do not assume all five configured models have completed every dataset unless stored results prove it.

## Verification

```powershell
pytest tests/harness/test_recommendation.py
pytest tests/harness/test_reporting.py
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
