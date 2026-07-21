# Story EVAL-003: Ollama Streaming Runtime

## Status

done

## Goal

Implement the common runtime interface and an Ollama adapter that supports streaming, timing, metadata preservation, timeout handling, and mock-based tests.

## Context

Depends on EVAL-001 and EVAL-002.

## Acceptance Criteria

- [x] Common runtime interface exists.
- [x] Streaming responses are supported.
- [x] TTFT is recorded.
- [x] Total latency is recorded.
- [x] Ollama token and duration metadata are preserved.
- [x] Timeout and HTTP errors are categorized.
- [x] Mock-based unit tests exist.

## Out of Scope

- Full benchmark execution
- Real model quality scoring

## Expected Files

- `harness/runtime/base.py`
- `harness/runtime/ollama.py`
- `tests/harness/runtime/test_ollama.py`

## Verification

```powershell
pytest tests/harness/runtime/test_ollama.py
python -m harness.cli preflight --check-ollama
```

## Completion Evidence

Use `.agents/skills/bmad-implement-story/templates/completion-report.md`.
