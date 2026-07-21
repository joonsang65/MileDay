# Story EVAL-008: CLIcK Adapter

## Status

done

## Goal

Implement a CLIcK benchmark adapter that loads versioned local input files through explicit field mapping, normalizes supported choice-answer rows into the internal benchmark schema, reuses the common MCQ prompt/parser/scoring primitives where applicable, and preserves invalid or failed rows with clear failure categories.

## Context

Depends on EVAL-001, EVAL-003, EVAL-005, EVAL-006, and EVAL-007.

Reference:

- `AGENTS.md`
- `_bmad-output/planning-artifacts/product-brief.md`
- `_bmad-output/planning-artifacts/prd.md`
- `_bmad-output/planning-artifacts/architecture.md`
- `_bmad-output/planning-artifacts/epics.md`
- `_bmad-output/planning-artifacts/schemas.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/stories/EVAL-005-common-mcq-adapter.md`
- `_bmad-output/implementation-artifacts/stories/EVAL-006-kmmlu-pro-adapter.md`
- `_bmad-output/implementation-artifacts/stories/EVAL-007-kobalt-700-adapter.md`
- `_bmad-output/implementation-artifacts/completion-reports/EVAL-005-common-mcq-adapter.md`
- `_bmad-output/implementation-artifacts/completion-reports/EVAL-006-kmmlu-pro-adapter.md`
- `_bmad-output/implementation-artifacts/completion-reports/EVAL-007-kobalt-700-adapter.md`
- `docs/decisions/0002-separate-official-and-generation-evaluation.md`
- `docs/decisions/0003-preserve-raw-model-output.md`

## Acceptance Criteria

- [x] CLIcK adapter package/module exists under `harness/benchmarks/`.
- [x] Adapter loads versioned local fixture files without network access.
- [x] Source-to-internal field mapping is explicit and configurable or code-defined.
- [x] Adapter does not infer, rename, or fabricate missing CLIcK dataset fields.
- [x] Supported loaded rows are normalized into the internal Benchmark Case schema from `schemas.md`.
- [x] Choice labels support the common MCQ A-J range and validate answer membership for mapped choice-answer rows.
- [x] Unsupported or non-choice-answer local rows fail clearly with `DATASET_SCHEMA_CHANGED` rather than being silently coerced.
- [x] Missing files or unreadable dataset paths are reported with `DATASET_UNAVAILABLE`.
- [x] Prompt building, answer parsing, scoring, and aggregation reuse `harness/benchmarks/mcq.py` for supported choice-answer rows.
- [x] Raw model outputs remain available to downstream result storage and are not overwritten by parsed answers.
- [x] Offline fixture tests cover valid mapped rows, explicit custom mapping, missing required mapped fields, unsupported row shape, invalid answer labels, invalid JSONL, and aggregate scoring.

## Out of Scope

- Downloading or redistributing CLIcK data
- Assuming official CLIcK source field names or task layout
- Hardcoding real model tags
- Running full benchmark inference against Ollama models
- Implementing IFEval-Ko adapter
- Result persistence and Markdown report generation
- MileDay-specific schedule generation evaluation

## Expected Files

- `harness/benchmarks/click_adapter.py`
- `tests/harness/benchmarks/test_click_adapter.py`
- `tests/fixtures/benchmarks/click/`
- Optional small local fixture files under `tests/fixtures/benchmarks/click/`

## Implementation Notes

- Treat CLIcK input files as user-provided/versioned local artifacts.
- Keep fixture data synthetic and minimal; do not claim it is official CLIcK data.
- If the adapter needs source field names, define them explicitly in one mapping object or config model.
- Convert valid mapped source rows into the `Internal Benchmark Case` schema defined in `_bmad-output/planning-artifacts/schemas.md`.
- Preserve source metadata when available, but do not require metadata fields that are not explicitly mapped.
- Prefer JSONL or CSV parsing through standard structured parsers instead of ad hoc string splitting.
- Keep official public benchmark adapter logic separate from MileDay generation fixtures and semantic rubrics.
- Avoid naming the module `click.py` so it cannot be confused with the common Python `click` package.

## Verification

```powershell
pytest tests/harness/benchmarks/test_click_adapter.py
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
