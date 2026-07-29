# Story EVAL-015: Markdown Report

## Status

done

## Goal

Generate a reproducible Markdown report from stored harness results that summarizes model, dataset, validation, failure, and performance evidence without fabricating missing scores.

## Context

Depends on EVAL-014 and the completed benchmark or MileDay evaluator Stories that produce stored results.

Reference:

- `AGENTS.md`
- `_bmad-output/planning-artifacts/product-brief.md`
- `_bmad-output/planning-artifacts/prd.md`
- `_bmad-output/planning-artifacts/architecture.md`
- `_bmad-output/planning-artifacts/epics.md`
- `_bmad-output/planning-artifacts/schemas.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/stories/EVAL-014-result-store.md`
- `docs/decisions/0002-separate-official-and-generation-evaluation.md`
- `docs/decisions/0003-preserve-raw-model-output.md`

## Acceptance Criteria

- [x] Reporter reads stored results from `artifacts/runs/{run_id}/`.
- [x] Reporter generates `report.md` under the run directory.
- [x] Report includes model-level and dataset-level summaries when data exists.
- [x] Report includes invalid output and failure category analysis.
- [x] Report includes latency, TTFT, throughput, and resource metric summaries when metrics exist.
- [x] Report links or references raw artifact paths without embedding full raw outputs.
- [x] Missing datasets, metrics, or model results are shown as missing or not executed rather than inferred.
- [x] Public benchmark results and MileDay generation results remain separated in the report.
- [x] Report generation is deterministic for the same stored input.
- [x] Offline fixture tests cover complete results, missing metrics, invalid results, failed results, partial runs, and deterministic output.

## Out of Scope

- Final winner or recommendation policy
- Running real benchmark inference
- Changing result storage schema except for small compatibility gaps discovered during implementation
- CSV or Parquet export unless already available from prior code
- Frontend report UI

## Expected Files

- `harness/reporting.py`
- `tests/harness/test_reporting.py`
- Optional fixture artifacts under `tests/fixtures/results/`

## Implementation Notes

- Read stored results; do not re-score raw outputs during report generation.
- Keep report text concise and evidence-driven.
- Do not embed large raw outputs in Markdown.
- Avoid claiming official benchmark scores when only synthetic fixtures or partial runs exist.
- Preserve compatibility with EVAL-016 recommendation summary.

## Verification

```powershell
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
