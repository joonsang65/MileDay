# Story EVAL-005: Common MCQ Adapter

## Status

done

## Goal

Implement reusable multiple-choice prompt building, answer parsing, invalid-output handling, and aggregate scoring for public benchmark adapters.

## Context

Depends on EVAL-001 and EVAL-003.

## Acceptance Criteria

- [x] Question and choices prompt builder exists.
- [x] A-J answer choices are parsed.
- [x] Ambiguous or multiple answers are marked invalid.
- [x] Accuracy and invalid rate are calculated.
- [x] Benchmark-level and category-level aggregates are supported.
- [x] Parser unit tests exist.

## Out of Scope

- Loading real benchmark datasets
- Semantic judging

## Expected Files

- `harness/benchmarks/mcq.py`
- `tests/harness/benchmarks/test_mcq.py`

## Verification

```powershell
pytest tests/harness/benchmarks/test_mcq.py
```

## Completion Evidence

Use `.agents/skills/bmad-implement-story/templates/completion-report.md`.
