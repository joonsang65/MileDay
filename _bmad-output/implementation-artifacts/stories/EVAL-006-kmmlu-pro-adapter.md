# Story EVAL-006: KMMLU-Pro Adapter

## Status

done

## Goal

Implement a KMMLU-Pro benchmark adapter that loads versioned local input files through explicit field mapping, normalizes cases into the internal benchmark schema, reuses the common MCQ prompt/parser/scoring primitives, and preserves invalid or failed rows with clear failure categories.

## Context

Depends on EVAL-001, EVAL-003, and EVAL-005.

Reference:

- `AGENTS.md`
- `_bmad-output/planning-artifacts/product-brief.md`
- `_bmad-output/planning-artifacts/prd.md`
- `_bmad-output/planning-artifacts/architecture.md`
- `_bmad-output/planning-artifacts/epics.md`
- `_bmad-output/planning-artifacts/schemas.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/stories/EVAL-005-common-mcq-adapter.md`
- `_bmad-output/implementation-artifacts/completion-reports/EVAL-005-common-mcq-adapter.md`
- `docs/decisions/0002-separate-official-and-generation-evaluation.md`
- `docs/decisions/0003-preserve-raw-model-output.md`

## Acceptance Criteria

- [x] KMMLU-Pro adapter package/module exists under `harness/benchmarks/`.
- [x] Adapter loads versioned local fixture files without network access.
- [x] Source-to-internal field mapping is explicit and configurable or code-defined.
- [x] Adapter does not infer, rename, or fabricate missing KMMLU-Pro dataset fields.
- [x] Loaded rows are normalized into the internal Benchmark Case schema from `schemas.md`.
- [x] Choice labels support the common MCQ A-J range and validate answer membership.
- [x] Invalid dataset rows are reported with `DATASET_SCHEMA_CHANGED` or `DATASET_UNAVAILABLE` as appropriate.
- [x] Prompt building, answer parsing, scoring, and aggregation reuse `harness/benchmarks/mcq.py`.
- [x] Raw model outputs remain available to downstream result storage and are not overwritten by parsed answers.
- [x] Offline fixture tests cover valid rows, missing required mapped fields, invalid answer labels, and aggregate scoring.

## Out of Scope

- Downloading or redistributing KMMLU-Pro data
- Hardcoding real model tags
- Running full benchmark inference against Ollama models
- Implementing KoBALT-700, CLIcK, or IFEval-Ko adapters
- Result persistence and Markdown report generation
- MileDay-specific schedule generation evaluation

## Expected Files

- `harness/benchmarks/kmmlu_pro.py`
- `tests/harness/benchmarks/test_kmmlu_pro.py`
- `tests/fixtures/benchmarks/kmmlu_pro/`
- Optional small local fixture files under `tests/fixtures/benchmarks/kmmlu_pro/`

## Implementation Notes

- Treat KMMLU-Pro input files as user-provided/versioned local artifacts.
- Keep fixture data synthetic and minimal; do not claim it is official KMMLU-Pro data.
- If the adapter needs source field names, define them explicitly in one mapping object or config model.
- Convert valid source rows into the `Internal Benchmark Case` schema defined in `_bmad-output/planning-artifacts/schemas.md`.
- Preserve source metadata when available, but do not require metadata fields that are not explicitly mapped.
- Prefer JSONL or CSV parsing through standard structured parsers instead of ad hoc string splitting.
- Keep official public benchmark adapter logic separate from MileDay generation fixtures and semantic rubrics.

## Verification

```powershell
pytest tests/harness/benchmarks/test_kmmlu_pro.py
pytest
pytest -c pytest-backend.ini
```

## Completion Evidence

Use `.agents/skills/bmad-implement-story/templates/completion-report.md`.

Record:

- Files changed
- Test results
- Acceptance Criteria evidence
- Generated artifacts
- Known limitations
- Follow-up Story
