# Story EVAL-001: Project Foundation

## Status

done

## Goal

Create the initial Python package structure for the local LLM evaluation harness with config loading, common Pydantic schemas, Typer CLI foundation, preflight checks, and unit tests.

## Context

Reference:

- `_bmad-output/planning-artifacts/product-brief.md`
- `_bmad-output/planning-artifacts/prd.md`
- `_bmad-output/planning-artifacts/architecture.md`
- `docs/decisions/0005-use-bmad-lite-with-codex-harness.md`

## Acceptance Criteria

- [x] Project package structure exists.
- [x] Basic configuration loader exists.
- [x] Common Pydantic schemas exist.
- [x] Typer CLI runs.
- [x] Basic unit tests pass.

## Out of Scope

- Real Ollama inference
- Public benchmark adapters
- Full MileDay semantic evaluation
- GPU monitoring
- Model ranking report

## Expected Files

- `harness/`
- `harness/config.py`
- `harness/schemas.py`
- `harness/cli.py`
- `tests/harness/`
- `pyproject.toml` or existing dependency file updates

## Verification

```powershell
pytest
python -m harness.cli preflight
```

## Completion Evidence

Record:

- Files changed
- Test results
- Acceptance Criteria evidence
- Generated artifacts
- Known limitations
- Follow-up Story
