# Story EVAL-009: IFEval-Ko Adapter

## Status

done

## Goal

Implement an IFEval-Ko benchmark adapter that loads versioned local input files, maps the actual source shape explicitly, evaluates instruction-following behavior without assuming the task is multiple-choice, and preserves raw outputs and invalid cases with clear failure categories.

## Context

Depends on EVAL-001, EVAL-003, EVAL-005, EVAL-006, EVAL-007, and EVAL-008.

Reference:

- `AGENTS.md`
- `_bmad-output/planning-artifacts/product-brief.md`
- `_bmad-output/planning-artifacts/prd.md`
- `_bmad-output/planning-artifacts/architecture.md`
- `_bmad-output/planning-artifacts/epics.md`
- `_bmad-output/planning-artifacts/schemas.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/stories/EVAL-005-common-mcq-adapter.md`
- `_bmad-output/implementation-artifacts/stories/EVAL-008-click-adapter.md`
- `_bmad-output/implementation-artifacts/completion-reports/dataset-setup-inspection.md`
- `_bmad-output/implementation-artifacts/completion-reports/dataset-processed-smoke.md`
- `docs/decisions/0002-separate-official-and-generation-evaluation.md`
- `docs/decisions/0003-preserve-raw-model-output.md`

## Acceptance Criteria

- [x] IFEval-Ko adapter package/module exists under `harness/benchmarks/`.
- [x] Adapter loads versioned local fixture or processed files without network access.
- [x] Source-to-internal field mapping is explicit and based on inspected local fixture/source shape.
- [x] Adapter does not infer, rename, fabricate, or silently coerce missing IFEval-Ko dataset fields.
- [x] The Story implementation documents that the official local evaluator is used for IFEval-Ko scoring.
- [x] Adapter does not assume IFEval-Ko is MCQ; MCQ primitives are reused only if the inspected source shape actually requires them.
- [x] Unsupported source rows fail clearly with `DATASET_SCHEMA_CHANGED`.
- [x] Missing files or unreadable dataset paths are reported with `DATASET_UNAVAILABLE`.
- [x] Raw model outputs remain available to downstream result storage and are not overwritten by parsed or judged outputs.
- [x] Offline fixture tests cover valid rows, explicit mapping, missing required fields, unsupported row shape, invalid JSONL, and official evaluator invocation behavior.

## Out of Scope

- Downloading or redistributing IFEval-Ko data
- Assuming official IFEval-Ko source fields without local inspection
- Hardcoding real model tags
- Running full benchmark inference against Ollama models
- Implementing MileDay-specific schedule generation evaluation
- Result persistence and Markdown report generation
- Final model recommendation

## Expected Files

- `harness/benchmarks/ifeval_ko.py`
- `tests/harness/benchmarks/test_ifeval_ko.py`
- `tests/fixtures/benchmarks/ifeval_ko/`
- Optional small synthetic fixture files under `tests/fixtures/benchmarks/ifeval_ko/`

## Implementation Notes

- Treat IFEval-Ko input files as user-provided/versioned local artifacts.
- Inspect the local source or processed fixture shape before defining the adapter mapping.
- Keep fixture data synthetic and minimal; do not claim it is official IFEval-Ko data.
- Use the official IFEval-Ko evaluator through a small adapter boundary and test it with a minimal fixture.
- Preserve source metadata when available, but do not require metadata fields that are not explicitly mapped.
- Keep official public benchmark adapter logic separate from MileDay generation fixtures and semantic rubrics.

## Verification

```powershell
pytest tests/harness/benchmarks/test_ifeval_ko.py
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
