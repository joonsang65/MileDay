# Story EVAL-013: Cold/Warm Benchmark Mode

## Status

done

## Goal

Add cold and warm benchmark execution modes so latency, time to first token, and throughput can be compared with warmup runs separated from measured runs.

## Context

Depends on EVAL-001, EVAL-003, EVAL-004, and at least one benchmark or MileDay evaluator Story.

Reference:

- `AGENTS.md`
- `_bmad-output/planning-artifacts/product-brief.md`
- `_bmad-output/planning-artifacts/prd.md`
- `_bmad-output/planning-artifacts/architecture.md`
- `_bmad-output/planning-artifacts/epics.md`
- `_bmad-output/planning-artifacts/schemas.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/stories/EVAL-003-ollama-streaming-runtime.md`
- `_bmad-output/implementation-artifacts/stories/EVAL-004-performance-monitor.md`

## Acceptance Criteria

- [x] Harness configuration or CLI supports explicit cold and warm benchmark modes.
- [x] Warmup executions are recorded separately from measured executions.
- [x] Warmup metrics are not included in measured latency, TTFT, or throughput aggregates.
- [x] Performance monitor can be started and stopped around measured runs.
- [x] Metrics output distinguishes cold, warmup, and warm measured phases.
- [x] Resume behavior does not treat warmup-only records as completed measured cases.
- [x] Missing Ollama, timeout, and runtime failures are categorized without fabricating performance metrics.
- [x] Offline tests use a mock runtime and mock performance monitor; they do not require Ollama or GPU.

## Out of Scope

- GPU optimization
- Automatic model download or cache management
- Full report ranking
- Public benchmark adapter changes unless a small interface hook is required
- Production serving infrastructure

## Expected Files

- `harness/orchestrator.py`
- `tests/harness/test_orchestrator.py`
- Optional updates to `harness/cli.py`
- Optional updates to `harness/performance/monitor.py`

## Implementation Notes

- Keep mode names explicit and documented.
- Use runtime metrics from EVAL-003 and performance samples from EVAL-004.
- Do not hide runtime failures as skipped warmup records.
- Avoid adding dependencies that break offline CI.
- Preserve raw output and result storage compatibility for EVAL-014.

## Verification

```powershell
pytest tests/harness/test_orchestrator.py
pytest tests/harness/performance/test_monitor.py
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
