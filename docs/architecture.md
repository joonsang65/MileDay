# MileDay Architecture

이 문서는 현재 MileDay 구조의 source of truth다.

## 전체 구조

```text
Electron main
  -> React renderer
  -> FastAPI backend
  -> Supabase Auth / PostgreSQL
  -> external providers: Korean holiday API, Gemini API
```

프론트엔드는 Supabase에 직접 접근하지 않는다. 사용자 데이터 요청은 FastAPI를 거치며, FastAPI가 Supabase Auth JWT에서 현재 사용자 ID를 확인한다.

## 주요 계층

| 위치 | 책임 |
|---|---|
| `frontend/electron/` | 창, tray, local UI settings, safeStorage token, auto launch |
| `frontend/src/` | 캘린더 UI, 패널, Zustand state, API client |
| `backend/app/api/routers/` | FastAPI endpoint |
| `backend/app/services/` | 비즈니스 규칙, 권한 확인, validation, cache |
| `backend/app/repositories/` | Supabase PostgreSQL 접근 |
| `backend/app/infrastructure/` | 외부 provider client |
| `supabase/migrations/` | DB schema 변경 기록 |

## 데이터 저장

| 데이터 | 저장 위치 | 핵심 field |
|---|---|---|
| 사용자 계정 | Supabase Auth | email, auth user id |
| 목표 | `goals` | `user_id`, `title`, `deadline`, `is_completed`, `is_recurring`, `recurrence_type`, `color` |
| 마일스톤 | `milestones` | `user_id`, `goal_id`, `title`, `scheduled_date`, `is_completed`, `color` |
| 계정 기준 설정 | `user_settings` | `calendar_view`, `holiday_display`, `week_starts_on`, `language`, `timezone`, `gemini_data_consent` |
| 로컬 UI 설정 | Electron userData `ui-settings.json` | font size, panel size, resize flag, opacity, window bounds |
| access token | Electron `safeStorage` 기반 `access-token.bin` | encrypted token |

반복 목표는 목표 row의 recurrence 설정을 기준으로 마일스톤 row를 생성해 관리한다. 복잡한 occurrence 단위 편집은 제품 범위 밖이다.

## 인증과 권한

- 보호 API는 `Authorization: Bearer <access_token>`을 요구한다.
- Auth 작업은 Supabase Auth client를 사용하고, DB repository는 service role client로 접근한다.
- backend service는 항상 현재 사용자 ID를 기준으로 조회/수정/삭제 대상을 제한한다.
- Supabase RLS와 owner check function은 DB 방어선이다.
- 다른 사용자 데이터 접근은 존재 여부를 숨기기 위해 404 계열로 처리한다.

## DB 계약

- 완료 동기화는 `complete_goal_with_milestones`, `complete_milestone_and_sync_goal` RPC를 사용한다.
- 캘린더 조회 성능을 위해 `goals(user_id, deadline)`, `milestones(user_id, scheduled_date)`, `milestones(user_id, goal_id)` index를 둔다.
- `recurrence_type`은 반복 목표일 때만 필수이고, 비반복 목표에서는 `null`이어야 한다.
- `week_starts_on` 기본값은 `0`이고, `gemini_data_consent` 기본값은 `false`다.

## Desktop 계약

- 창은 frameless, tray 중심, 작업 표시줄 숨김, 닫기 시 hide 흐름이다.
- 최소 크기는 `420x300`, 최대 크기는 `980x760`이다.
- 기본 창 크기는 작업 영역 기준으로 계산하고, 위치/크기 변경은 로컬 설정에 저장한다.
- renderer는 preload API로 token, 로컬 설정, 창 제어, auto launch 상태를 다룬다.

## 안정성 원칙

- `/health/db`는 Supabase 연결과 핵심 table/column을 확인한다.
- 휴일 API key가 없거나 외부 API가 실패하면 빈 휴일 목록으로 degrade한다.
- 월간 캘린더와 설정 조회는 cache/fallback으로 사용자-facing 오류를 줄인다.
- API 오류는 공통 error envelope와 `request_id`로 추적한다.
- 민감 정보는 로그에 남기지 않는다.

관련 상세: [api.md](api.md), [ai.md](ai.md), [archive/reference/db_schema.md](archive/reference/db_schema.md)
