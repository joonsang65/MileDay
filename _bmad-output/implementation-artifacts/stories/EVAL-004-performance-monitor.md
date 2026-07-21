# Story EVAL-004: Performance Monitor

## Status

done

## Goal

Add configurable CPU, RAM, Ollama RSS, and optional NVML VRAM sampling for evaluation runs.

## Context

Depends on EVAL-001.

## Acceptance Criteria

- [x] System RAM usage is sampled.
- [x] Ollama process RSS is sampled when available.
- [x] VRAM is sampled through NVML when available.
- [x] Missing NVML degrades clearly without failing unit tests.
- [x] Peak metrics are calculated.
- [x] Sample interval is configurable between 100ms and 250ms.

## Out of Scope

- GPU scheduling
- Full performance dashboard

## Expected Files

- `harness/performance/monitor.py`
- `tests/harness/performance/test_monitor.py`

## Verification

```powershell
pytest tests/harness/performance/test_monitor.py
```

## Completion Evidence

Use `.agents/skills/bmad-implement-story/templates/completion-report.md`.
