# BMAD Lite + Harness Adoption Setup Report

## Story

- ID: ADOPT-SETUP
- Title: BMAD Lite + Harness Engineering environment setup
- Final Status: done

## Source Documents

- `codex_bmad_harness_adoption_spec.md`
- `AGENTS.md`
- `docs/codex_rules.md`
- `docs/commit_guide.md`
- `docs/data_flow.md`
- `docs/troubleshooting.md`
- `docs/performance_report._v1.md`

## Summary

Configured the repository-level BMAD Lite and Harness Engineering environment without changing MileDay runtime code. Added planning artifacts, initial stories, sprint status, ADRs, Codex skill guidance, completion report template, and GitHub Actions workflow.

## Files Changed

- `AGENTS.md`: repository guidance based on existing MileDay docs and BMAD harness workflow.
- `_bmad/README.md`: BMAD Lite workspace purpose and artifact routing.
- `_bmad-output/planning-artifacts/product-brief.md`: harness problem, scope, users, and success criteria.
- `_bmad-output/planning-artifacts/prd.md`: harness functional and non-functional requirements.
- `_bmad-output/planning-artifacts/architecture.md`: harness modules, data flow, result schema, artifact layout.
- `_bmad-output/planning-artifacts/epics.md`: initial epic breakdown.
- `_bmad-output/implementation-artifacts/sprint-status.yaml`: Story status tracking.
- `_bmad-output/implementation-artifacts/stories/EVAL-001-project-foundation.md`: first ready Story.
- `_bmad-output/implementation-artifacts/stories/EVAL-002-model-registry.md`: backlog Story.
- `_bmad-output/implementation-artifacts/stories/EVAL-003-ollama-streaming-runtime.md`: backlog Story.
- `_bmad-output/implementation-artifacts/stories/EVAL-004-performance-monitor.md`: backlog Story.
- `_bmad-output/implementation-artifacts/stories/EVAL-005-common-mcq-adapter.md`: backlog Story.
- `.agents/skills/bmad-implement-story/SKILL.md`: Codex Story implementation workflow.
- `.agents/skills/bmad-implement-story/templates/completion-report.md`: completion evidence template.
- `docs/decisions/0001-use-ollama-as-default-runtime.md`: initial runtime ADR.
- `docs/decisions/0002-separate-official-and-generation-evaluation.md`: benchmark/product evaluation split ADR.
- `docs/decisions/0003-preserve-raw-model-output.md`: raw output preservation ADR.
- `docs/decisions/0004-use-deterministic-schedule-validation.md`: deterministic schedule validation ADR.
- `docs/decisions/0005-use-bmad-lite-with-codex-harness.md`: BMAD Lite adoption ADR.
- `.github/workflows/evaluation-harness.yml`: existing project verification workflow.

## Commands Run

```text
Get-Content codex_bmad_harness_adoption_spec.md
Get-ChildItem -Force
git status --short
Get-Content docs\codex_rules.md
Get-Content docs\commit_guide.md
Get-Content docs\data_flow.md
Get-Content docs\troubleshooting.md
Get-Content docs\performance_report._v1.md
Test-Path AGENTS.md
Test-Path .agents\skills\bmad-implement-story\SKILL.md
Test-Path .agents\skills\bmad-implement-story\templates\completion-report.md
Test-Path _bmad-output\planning-artifacts\product-brief.md
Test-Path _bmad-output\implementation-artifacts\sprint-status.yaml
Test-Path docs\decisions\0005-use-bmad-lite-with-codex-harness.md
Test-Path .github\workflows\evaluation-harness.yml
Test-Path _bmad\README.md
Test-Path _bmad-output\implementation-artifacts\completion-reports\adoption-setup.md
pytest
```

## Verification Results

| Verification | Result | Evidence |
|---|---|---|
| Required paths | PASS | Required paths returned `True` during path checks. |
| Backend tests | PASS | `pytest`: 76 passed, 1 deselected, coverage 94.83%. |
| Frontend audit | NOT_EXECUTED | Previously passed after dependency update; not rerun for this doc-only setup. |
| Frontend tests | NOT_EXECUTED | Setup was documentation/configuration-only. |
| Frontend lint | NOT_EXECUTED | Setup was documentation/configuration-only. |
| Frontend build | NOT_EXECUTED | Setup was documentation/configuration-only. |

## Acceptance Criteria

- [x] Repository investigation performed: root structure, docs, tests, CI, BMAD paths, and git status were checked.
- [x] Product Brief created.
- [x] PRD created.
- [x] Architecture created.
- [x] Epics created.
- [x] Five initial Stories created.
- [x] Root `AGENTS.md` created and aligned with existing `docs/` guidance.
- [x] `bmad-implement-story` skill created.
- [x] Completion report template created.
- [x] Sprint status created.
- [x] Initial ADRs created.
- [x] CI workflow created for current offline project verification.
- [x] Next implementation Story is clearly defined as EVAL-001.

## Artifacts

- `_bmad-output/planning-artifacts/`
- `_bmad-output/implementation-artifacts/`
- `.agents/skills/bmad-implement-story/`
- `docs/decisions/`
- `.github/workflows/evaluation-harness.yml`

## Failures

- Category: NOT_EXECUTED
- Description: Runtime test commands were not rerun during the final doc alignment step.
- Reproduction: Run `pytest`, `npm audit`, `npm test`, `npm run lint`, and `npm run build`.
- Recommended Action: Run full verification before committing if desired.

## Known Risks

- Existing `docs/` files contain mojibake in several Korean sections. The generated BMAD files use ASCII English to avoid adding more encoding ambiguity.
- Future harness commands such as `python -m harness.cli preflight` are intentionally not implemented until EVAL-001.

## Follow-up

- Implement `_bmad-output/implementation-artifacts/stories/EVAL-001-project-foundation.md` using the `bmad-implement-story` workflow.
