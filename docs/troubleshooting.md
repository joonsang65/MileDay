# MileDay 트러블 슈팅 기록

이 문서는 M3부터 M6.5까지 구현하면서 실제로 발생한 오류, 수정 요청, 원인, 대응 내용을 정리한다.
같은 문제가 다시 발생했을 때 로그만 보고 원인을 좁힐 수 있도록 증상과 확인 지점을 함께 기록한다.

## 1. 반복 예외 날짜 처리 방식 결정

### 증상과 요청

M3 요구사항에는 반복 예외 날짜 처리가 포함되어 있었지만, 당시 schema에는 `is_recurring`, `recurrence_type`만 존재했다.
예외 날짜를 별도 테이블로 관리할지, 실제 마일스톤 row를 생성/삭제할지 결정이 필요했다.

### 결정

반복 설정 시 반복 기간 안의 각 날짜에 실제 `milestones` row를 생성한다.
예외 날짜는 별도 예외 테이블에 저장하지 않고, 해당 날짜의 마일스톤 row를 생성하지 않거나 삭제한다.

### 반영 위치

- `docs/milestones/m3_goal_management.md`
- `docs/milestones/m4_milestone_management.md`
- `backend/app/services/milestone_service.py`

## 2. 한글 문서와 주석 정리

### 증상과 요청

M3 이후 문서와 주석을 한글로 통일해야 한다는 요청이 있었다.

### 대응

마일스톤 문서와 신규 구현 주석은 한글 기준으로 작성했다.
일부 파일은 기존 인코딩 문제로 깨진 한글이 남아 있을 수 있다. 해당 파일을 수정할 때는 UTF-8 기준으로 깨진 문자열을 함께 정리해야 한다.

### 확인 지점

- `backend/app/api/routers/goals.py`
- `backend/app/schemas/goal_schemas.py`
- `backend/app/core/supabase.py`
- `frontend/src/components/CreationPanel.tsx`

## 3. M5 프론트엔드 미구현 지적

### 증상과 요청

M5 문서 기반 구현 후, 백엔드 calendar API는 구현됐지만 프론트엔드 화면이 빠졌다는 지적이 있었다.

### 원인

초기 M5 구현 범위를 백엔드 calendar API 중심으로 좁게 잡았다.
사용자 요구는 Electron renderer의 실제 캘린더 UI까지 포함하는 것이었다.

### 대응

`frontend/` Electron + React + TypeScript 프로젝트를 추가했다.
월간/주간 캘린더, 날짜 상세, Today List, 완료 토글, 로그인 연동을 구현했다.

### 반영 위치

- `frontend/src/App.tsx`
- `frontend/src/components/CalendarBoard.tsx`
- `frontend/src/components/DateDetail.tsx`
- `frontend/src/components/TodayList.tsx`
- `frontend/src/api/client.ts`

## 4. npm 설치와 sandbox 제한

### 증상

프론트엔드 의존성 설치와 테스트 실행 중 sandbox 또는 네트워크 제한이 발생했다.
특히 Vitest 실행 시 다음 오류가 발생했다.

```text
Cannot read directory "../../../..": Access is denied.
Could not resolve ".../frontend/vite.config.ts"
```

### 원인

Codex 실행 환경의 파일 접근 sandbox가 Vite/esbuild 설정 로딩 경로와 충돌했다.
네트워크가 필요한 `npm install`은 사용자 승인 후 실행해야 했다.

### 대응

`npm install`은 사용자 승인 후 실행했다.
Vitest가 sandbox에서 Vite 설정을 읽지 못할 때는 승인된 권한으로 재실행했다.

### 확인 명령

```powershell
cd frontend
npm test
npm run lint
npm run build
```

## 5. Electron dev server entry 파일 오류

### 증상

`scripts/dev.ps1`로 실행 중 Electron renderer dev server는 떴지만 Electron app 시작이 실패했다.

```text
Error: No electron app entry file found:
frontend\dist-electron\main.js
```

### 원인

Electron Vite main process entry 빌드/설정이 renderer dev 실행과 맞지 않았다.
Electron main entry가 `dist-electron/main.js`에 생성되지 않은 상태에서 Electron을 시작하려 했다.

### 대응

Electron main process 파일과 dev 실행 스크립트를 정리했다.
`ELECTRON_RUN_AS_NODE` 환경 변수가 Electron 실행을 방해하지 않도록 `frontend/scripts/dev.mjs`에서 제거 후 복원하도록 했다.

### 반영 위치

- `frontend/electron/main.ts`
- `frontend/electron/windowOptions.ts`
- `frontend/scripts/dev.mjs`
- `scripts/dev.ps1`

## 6. 루트에서 backend health 이후 frontend 자동 실행

### 요청

루트 경로에서 한 번의 명령으로 backend를 띄우고, health check 성공 후 frontend dev run으로 넘어가도록 자동화하고 싶다는 요청이 있었다.

### 대응

`scripts/dev.ps1`을 추가했다.

처리 흐름은 다음과 같다.

1. backend health endpoint 확인
2. backend가 떠 있지 않으면 `uvicorn` 실행
3. `/health` 성공 대기
4. `/health/db` 성공 대기
5. frontend dev 실행
6. 스크립트 종료 시 자신이 띄운 backend process tree 정리

### 실행 명령

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\dev.ps1
```

### 반영 위치

- `scripts/dev.ps1`
- `backend/app/main.py`
- `backend/app/core/supabase.py`

## 7. `/health/db`가 실제 DB 헬스체크가 아니었던 문제

### 증상과 요청

`health_db`가 실제 DB 헬스체크를 하는 구조인지 확인하고, 아니면 수정해달라는 요청이 있었다.

### 원인

기존 `/health/db`는 Supabase 환경변수 설정 여부만 확인했다.
실제 DB 질의나 schema 상태를 검증하지 않았다.

### 대응

`check_supabase_db_health()`를 추가해 Supabase service role client로 `goals` 테이블을 실제 조회하도록 변경했다.
이후 `id`만 조회하면 앱에서 사용하는 컬럼 누락을 잡지 못한다는 문제가 확인되어, 다음 컬럼까지 조회하도록 강화했다.

```text
id,title,deadline,is_recurring,recurrence_type,color
```

### 효과

DB 연결뿐 아니라 앱 생성/조회 계약에 필요한 컬럼이 Supabase REST schema cache에서 보이는지도 확인한다.
현재 DB에 `goals.color`가 없으면 `/health/db`가 실패하고 `scripts/dev.ps1`은 frontend 실행으로 넘어가지 않는다.

### 반영 위치

- `backend/app/core/supabase.py`
- `backend/app/main.py`
- `scripts/dev.ps1`
- `tests/test_supabase_and_exceptions.py`
- `tests/test_app_routes.py`

## 8. 로그 파일 용도 정리

### 증상과 요청

`logs` 아래 여러 파일이 생겼고, 필요한 파일만 남기고 싶다는 질문이 있었다.

### 파일별 목적

| 파일 | 목적 |
| --- | --- |
| `logs/dev_backend.out.log` | `scripts/dev.ps1`이 띄운 backend process의 stdout |
| `logs/dev_backend.err.log` | `scripts/dev.ps1`이 띄운 backend process의 stderr |
| `logs/mileday.log` | backend app logger의 현재 로그 |
| `logs/mileday.log.YYYY-MM-DD` | 날짜별 rotate된 backend app 로그 |

### 판단 기준

개발 실행 상태 확인에는 `dev_backend.*.log`가 유용하다.
API 요청, Supabase 요청, 예외 추적에는 `mileday.log`가 유용하다.
오래된 rotate 로그는 과거 추적이 필요 없으면 삭제해도 된다.

## 9. 목표/마일스톤 생성 UI 누락

### 증상과 요청

캘린더와 Today List는 있었지만 목표 생성, 마일스톤 생성 위치가 없다는 지적이 있었다.

### 대응

M6.5 문서를 추가하고, 빠른 추가 패널을 구현했다.
목표 생성은 `POST /goals`, 마일스톤 생성은 `POST /goals/{goal_id}/milestones`를 호출한다.

### 반영 위치

- `docs/milestones/m6_5_creation_ui.md`
- `frontend/src/components/CreationPanel.tsx`
- `frontend/src/api/client.ts`
- `frontend/src/App.tsx`

## 10. 목표 생성 실패: service role client 필요

### 증상

목표 생성 시 다음 메시지가 표시됐다.

```text
Failed to create goal.
```

backend 로그에는 Supabase `POST /rest/v1/goals`가 `400 Bad Request`로 남았다.

### 원인

초기 repository가 기본 Supabase anon client를 사용했다.
서버는 JWT로 현재 사용자를 검증한 뒤 `user_id`를 직접 설정하는 구조이므로, DB 쓰기 작업은 service role client로 수행해야 한다.

### 대응

데이터 repository 기본 client를 service role client로 변경했다.
Auth API는 Supabase Auth 호출을 위해 anon client를 유지한다.

### 반영 위치

- `backend/app/repositories/goals.py`
- `backend/app/repositories/milestones.py`
- `backend/app/repositories/calendar.py`
- `backend/app/core/supabase.py`

## 11. 목표 생성 실패: `goals.color` 컬럼 누락

### 증상

프론트에서 목표 생성 시 다음처럼 표시됐다.

```text
Failed to create goal.
```

직접 재현한 backend 응답 detail은 다음과 같았다.

```text
Could not find the 'color' column of 'goals' in the schema cache
```

이후 `/health/db`에서도 다음 오류가 확인됐다.

```text
column goals.color does not exist
```

### 원인

마이그레이션의 `create table if not exists public.goals (...)`는 이미 존재하는 테이블에 새 컬럼을 추가하지 않는다.
원격 Supabase DB에는 초기 테이블이 이미 있었고, 이후 앱 계약에 추가된 `color` 컬럼이 반영되지 않았다.

### 대응

기존 테이블에도 안전하게 컬럼을 추가하는 보정 migration을 추가했다.

```sql
alter table if exists public.goals
add column if not exists color text not null default '#4F46E5';

alter table if exists public.milestones
add column if not exists color text not null default '#F97316';

notify pgrst, 'reload schema';
```

프론트 `ApiClientError`가 backend `detail`을 보존하도록 수정해, 다음부터는 실제 DB 오류 메시지를 화면에서 확인할 수 있게 했다.

### 반영 위치

- `supabase/migrations/202607090001_backfill_goal_milestone_color_columns.sql`
- `backend/app/core/supabase.py`
- `frontend/src/api/client.ts`
- `frontend/src/App.tsx`
- `tests/test_migration.py`
- `tests/test_supabase_and_exceptions.py`

## 12. 목표 생성 실패: `recurrence_type` NOT NULL 제약

### 증상

목표 생성 시 다음 오류가 표시됐다.

```text
Failed to create goal. (null value in column "recurrence_type" of relation "goals" violates not-null constraint)
```

### 원인

프론트와 백엔드 계약은 반복하지 않는 목표에서 `recurrence_type: null`을 사용한다.
하지만 실제 Supabase DB의 `goals.recurrence_type` 컬럼에는 `NOT NULL` 제약이 남아 있었다.

### 대응

`recurrence_type`의 `NOT NULL`을 제거하고, 반복 상태와 반복 유형의 조합을 DB check constraint로 보강했다.

```sql
alter table if exists public.goals
alter column recurrence_type drop not null;

alter table public.goals
add constraint goals_recurrence_type_state
check (
  (is_recurring = true and recurrence_type in ('daily', 'weekly', 'monthly'))
  or
  (is_recurring = false and recurrence_type is null)
);

notify pgrst, 'reload schema';
```

### 반영 위치

- `supabase/migrations/202607090002_fix_goal_recurrence_type_nullability.sql`
- `tests/test_migration.py`

## 13. widget 형태 UI 요구

### 요청

첫 실행 화면에 회원가입 위치가 필요하고, 앱은 일반 창이 아니라 홈 화면 위에 캘린더만 떠 있는 widget 형태여야 한다는 요구가 있었다.
닫기, 최소화 버튼 같은 OS title bar는 보이지 않아야 하며, Chrome 같은 다른 창을 켰을 때는 보이지 않아야 한다.

### 대응

Electron BrowserWindow 설정을 widget 형태로 변경했다.

주요 설정은 다음과 같다.

- `frame: false`
- `skipTaskbar: true`
- `alwaysOnTop: false`
- `showInactive()` 사용

회원가입 UI는 로그인 패널 안에서 전환 가능하게 추가했다.

### 반영 위치

- `docs/milestones/m6_widget_auth_ui.md`
- `frontend/electron/windowOptions.ts`
- `frontend/electron/main.ts`
- `frontend/src/components/AuthPanel.tsx`

## 14. 실제 DB에 migration 적용 필요

### 주의점

코드와 migration 파일을 추가해도 원격 Supabase DB에는 자동 적용되지 않는다.
다음 명령 또는 Supabase SQL Editor 실행이 필요하다.

```powershell
supabase db push
```

Supabase CLI를 쓰지 않는 경우 SQL Editor에서 아래 파일을 순서대로 실행한다.

1. `supabase/migrations/202607090001_backfill_goal_milestone_color_columns.sql`
2. `supabase/migrations/202607090002_fix_goal_recurrence_type_nullability.sql`

## 15. 검증 기록

### 백엔드

최근 전체 테스트 결과는 다음과 같다.

```text
64 passed, 1 deselected
coverage 95.61%
```

### 프론트엔드

API client 테스트 결과는 다음과 같다.

```text
src/api/client.test.ts
8 passed
```

### 주의

프론트 테스트는 sandbox에서 Vite config 접근 오류가 날 수 있다.
이 경우 권한 승인 후 동일 명령을 재실행해야 한다.

## 16. 생성/수정/삭제 UI 흐름 재정리

### 증상과 요청

M6.5 생성 UI 이후 다음 문제가 확인됐다.

- 목표 생성 영역이 사이드 패널 상단에 항상 노출되어 캘린더 확인 흐름을 방해했다.
- 목표와 마일스톤은 추가만 가능했고 수정/삭제 진입점이 없었다.
- 목표와 마일스톤 생성이 탭처럼 분리되어 있어, 목표를 만든 뒤 필요한 경우에만 마일스톤을 추가하는 흐름과 맞지 않았다.
- 반복 설정이 목표 단위에 남아 있었지만, 실제 사용 흐름은 마일스톤 단위 반복이 더 자연스럽다.

### 결정

생성 패널은 사이드 패널 맨 아래로 내리고, 기본 상태에서는 접어 둔다.
사용자가 필요할 때만 `빠른 추가` 토글을 열어 목표를 생성한다.
마일스톤 생성 폼은 별도 페이지나 탭이 아니라, 목표 생성 후 또는 기존 목표가 있을 때만 여는 보조 토글로 제공한다.

수정/삭제는 날짜 상세에서 목표나 마일스톤 row를 클릭하면 인라인 편집 폼이 열리는 방식으로 처리한다.
별도 전역 편집 페이지를 만들지 않는다.

### 반복 정책

목표 반복 설정은 UI에서 제거한다.
마일스톤 반복은 DB에 반복 설정을 저장하지 않고, 생성 시 선택한 주기와 종료일에 따라 여러 개의 실제 `milestones` row를 만든다.
이는 앞서 정한 “반복은 실제 row로 물리화하고 예외 날짜는 row 생성/삭제로 처리한다”는 정책과 맞다.

### 반영 위치

- `frontend/src/components/CreationPanel.tsx`
- `frontend/src/components/DateDetail.tsx`
- `frontend/src/App.tsx`
- `frontend/src/api/client.ts`
- `frontend/src/api/types.ts`
- `frontend/src/styles.css`
