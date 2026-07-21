---
name: bmad-implement-story
description: Implement a BMAD Story using MileDay docs, Acceptance Criteria, verification commands, and completion evidence.
---

# Trigger

Use this skill when the user asks to implement a Story from `_bmad-output/implementation-artifacts/stories/` or explicitly mentions `bmad-implement-story`.

# Required Reading

Read these first:

1. `AGENTS.md`
2. `docs/codex_rules.md`
3. The specified Story

Then read only the relevant supporting docs:

- App API work: `docs/api_spec.md`, `docs/error_logging.md`, `docs/data_flow.md`
- DB or RLS work: `docs/db_schema.md`, `docs/requirements.md`
- Auth or user ownership work: `docs/codex_rules.md`, `docs/api_spec.md`, `docs/db_schema.md`
- UI or Electron work: `docs/codex_rules.md`, `docs/data_flow.md`, relevant `docs/milestones/*.md`
- Existing failures or environment issues: `docs/troubleshooting.md`
- Performance-sensitive work: `docs/performance_report._v1.md`
- Harness work: `_bmad-output/planning-artifacts/*.md` and relevant `docs/decisions/*.md`

# Workflow

1. Read the Story and list Acceptance Criteria as a checklist.
2. Inspect existing files named in the Story and relevant tests.
3. Check `git status` so unrelated user changes are preserved.
4. Present a scoped implementation plan before edits.
5. Implement the smallest change that satisfies the Story.
6. Keep MileDay app code and harness code separated unless the Story explicitly crosses the boundary.
7. Run the Story's verification commands that match the files changed.
8. If a relevant command cannot run, record `NOT_EXECUTED` with the exact reason.
9. Categorize failures with the shared failure categories.
10. Write a completion report using `templates/completion-report.md`.
11. Update `_bmad-output/implementation-artifacts/sprint-status.yaml`.

Completion reports under `_bmad-output/implementation-artifacts/completion-reports/` for EVAL Stories must be written in Korean. Keep commands, file paths, status values, and failure category enum values unchanged.

# MileDay Rules To Preserve

- Frontend calls FastAPI only; it must not call Supabase directly.
- Backend extracts `user_id` from JWT, not from client input.
- Use Router -> Service -> Repository / Infrastructure -> Supabase.
- Keep common error envelope and `request_id` behavior.
- Do not log raw secrets, passwords, tokens, Authorization headers, or full AI prompts.
- Future features stay documented or scaffolded only unless explicitly requested.

# Verification Guidance

Run only commands that exist and are relevant to the change scope.

```powershell
pytest
pytest -c pytest-backend.ini
cd frontend
npm audit
npm test
npm run lint
npm run build
```

Run frontend verification only when frontend, Electron, frontend dependency, or frontend build/config files changed, or when the user explicitly requests release/full validation. Do not add frontend verification rows as `NOT_EXECUTED` for harness-only, backend-only, or documentation-only Stories.

For harness stories, also run any command listed in the Story, such as:

```powershell
python -m harness.cli preflight
```

Do not claim an unavailable future command passed.

# Failure Categories

- CODE_ERROR
- TEST_FAILURE
- CONFIG_ERROR
- MODEL_NOT_INSTALLED
- OLLAMA_UNAVAILABLE
- DATASET_UNAVAILABLE
- DATASET_SCHEMA_CHANGED
- PARSER_ERROR
- TIMEOUT
- RESOURCE_EXHAUSTED
- EXTERNAL_DEPENDENCY
- NOT_EXECUTED

# Completion

Completion requires:

- Files changed
- Commands run
- Verification results
- Acceptance Criteria evidence
- Generated artifacts
- Failures or not-executed items
- Known risks
- Follow-up Story recommendation
