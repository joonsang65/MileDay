# Story EVAL-002: Model Registry

## Status

done

## Goal

Add a configurable model registry for five local LLM candidates.

## Context

Depends on EVAL-001.

## Acceptance Criteria

- [x] Five models are managed in YAML.
- [x] Model tags are not hardcoded in code.
- [x] Missing required fields produce clear validation errors.
- [x] Installed model availability can be checked.
- [x] Missing models are not auto-substituted.

## Out of Scope

- Automatic model download
- Benchmark execution

## Expected Files

- `configs/models.yaml`
- `harness/model_registry.py`
- `tests/harness/test_model_registry.py`

## Verification

```powershell
pytest tests/harness/test_model_registry.py
python -m harness.cli list-models
```

## Completion Evidence

Use `.agents/skills/bmad-implement-story/templates/completion-report.md`.
