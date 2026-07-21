# AGENTS.md

## Project Purpose

MileDay is a Windows desktop planner built with Electron, React, FastAPI, and Supabase. The app lets users manage goals and milestone tasks on a calendar, review today's milestones, and keep user-specific settings.

This repository also adopts a BMAD Lite + Harness Engineering workflow for future local LLM evaluation work. Harness work must stay separate from the existing MileDay app unless a Story explicitly changes shared code.

## Source of Truth

For MileDay app work, read the relevant documents in this order:

1. `docs/codex_rules.md`
2. Current request or Story
3. `docs/requirements.md`
4. `docs/api_spec.md`
5. `docs/db_schema.md`
6. `docs/data_flow.md`
7. `docs/error_logging.md`
8. `docs/troubleshooting.md`
9. Existing code

For BMAD harness work, read these after `docs/codex_rules.md`:

1. Current Story in `_bmad-output/implementation-artifacts/stories/`
2. Relevant ADRs in `docs/decisions/`
3. `_bmad-output/planning-artifacts/architecture.md`
4. `_bmad-output/planning-artifacts/prd.md`
5. `_bmad-output/planning-artifacts/product-brief.md`
6. `_bmad-output/implementation-artifacts/sprint-status.yaml`
7. Existing code

If documents and code conflict, do not guess. Report the conflicting files, the conflict, possible choices, and the smallest safe next step.

## Required Workflow

1. Inspect the existing repository structure before changing files.
2. Read the documents that match the requested area.
3. Check current code and tests before implementation.
4. Present a scoped plan before substantial edits.
5. Keep changes narrow and aligned with existing layers.
6. Run relevant verification commands.
7. Report commands that failed or could not be executed.
8. For BMAD Story work, write completion evidence and update sprint status.

## MileDay Architecture Rules

Use this backend flow:

```text
Router -> Service -> Repository / Infrastructure -> Supabase
```

Use this application boundary:

```text
Electron + React + TypeScript + Vite
        -> FastAPI
        -> Supabase PostgreSQL / Supabase Auth
```

Rules:

- Frontend must not access Supabase directly.
- Frontend must not store service role keys, DB URLs, or DB passwords.
- Protected API requests must use Supabase Auth JWT through `Authorization: Bearer <access_token>`.
- Backend must derive `user_id` from JWT `sub`; do not trust client-provided `user_id`.
- Repository queries must include current-user ownership conditions where applicable.
- RLS remains part of the DB security boundary.
- User data access failures should not expose whether another user's resource exists.
- Local window position, size, opacity, always-on-top, startup, and widget layout settings belong to local Electron storage, not `user_settings`.

## API and Error Rules

- Request and response bodies use JSON.
- Date values use `YYYY-MM-DD`.
- Success responses use `{ "success": true, "data": ... }`.
- Error responses use the common error envelope with `success`, `error.code`, `error.message`, optional `error.detail`, and `request_id`.
- FastAPI validation errors should be normalized to `400 BAD_REQUEST`.
- Authentication failures use `401`.
- Missing or unauthorized resources should generally resolve to `404`.
- Upstream service failures should be classified as 502, 503, or 504 where appropriate.
- Logs must include `request_id` and must not include raw passwords, tokens, Authorization headers, external calendar tokens, or full AI prompts.

## Current Verification Commands

Use commands that currently exist in this repository.

Backend:

```powershell
pytest
pytest -c pytest-backend.ini
pytest -m integration
```

Frontend:

```powershell
cd frontend
npm audit
npm test
npm run lint
npm run build
```

Development run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\dev.ps1
```

Notes:

- Integration tests require real Supabase test credentials and are excluded by default.
- `pytest` runs the default non-integration test suite without backend coverage gates.
- `pytest -c pytest-backend.ini` runs the backend coverage profile with a 90% threshold.
- Frontend Vite/Vitest commands may require elevated execution in Codex sandbox because esbuild can fail to read config paths.
- Run frontend verification only when frontend, Electron, frontend dependency, or frontend build/config files changed, or when release/full validation is explicitly requested.
- Do not report a command as passed unless it actually ran.

## BMAD Lite Rules

BMAD Lite artifacts live under `_bmad-output/`.

- Product Brief defines the problem and success criteria.
- PRD defines functional and non-functional requirements.
- Architecture defines module boundaries and data flow.
- Epics define Story groupings.
- Stories define implementable units.
- Completion reports record evidence.
- `sprint-status.yaml` records Story state.

Status enum:

```text
backlog
ready
in_progress
blocked
review
done
```

## Failure Categories

Use these categories for harness failures and completion reports:

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

## Commit Guidance

When asked to create a commit message, follow `docs/commit_guide.md`:

```text
<type>(<scope>): <summary>

<description line 1>
<description line 2>
```

Prefer these scopes when applicable: `project`, `env`, `backend`, `frontend`, `electron`, `auth`, `goals`, `milestones`, `calendar`, `settings`, `db`, `api`, `ui`, `docs`, `test`, `config`.

## Never

- Do not implement Future scope features such as external calendar sync, AI scheduling, mobile integration, or full LLM evaluation unless explicitly requested.
- Do not invent model tags, benchmark fields, dataset schemas, or test results.
- Do not weaken, delete, or skip tests to make work pass.
- Do not remove existing user changes.
- Do not introduce frontend Supabase access or secrets.
- Do not hide upstream errors as normal success results.
