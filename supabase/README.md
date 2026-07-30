# Supabase

`supabase/`는 MileDay의 PostgreSQL schema, RLS, trigger, migration을 관리하는 디렉터리입니다. Supabase Auth와 PostgreSQL은 제품 데이터의 최종 저장소이며, FastAPI backend만 이 계층에 접근합니다.

Frontend는 Supabase에 직접 접근하지 않습니다.

## 구조

```text
supabase/
  migrations/
    202607050001_m1_base_schema.sql
    202607090001_backfill_goal_milestone_color_columns.sql
    202607090002_fix_goal_recurrence_type_nullability.sql
```

| 경로 | 설명 |
|---|---|
| `migrations/` | DB schema, RLS, trigger 변경 이력 |
| `.temp/` | Supabase CLI 임시 파일. 직접 수정 대상 아님 |

## Migration

현재 migration은 시간순 파일명으로 관리합니다.

| 파일 | 목적 |
|---|---|
| `202607050001_m1_base_schema.sql` | MileDay MVP 기본 schema, RLS, trigger 구성 |
| `202607090001_backfill_goal_milestone_color_columns.sql` | goal/milestone color column backfill |
| `202607090002_fix_goal_recurrence_type_nullability.sql` | goal recurrence type nullability 보정 |

새 migration은 기존 순서를 깨지 않도록 timestamp prefix를 붙입니다.

```text
YYYYMMDDNNNN_short_description.sql
```

## 적용 방식

Supabase CLI 또는 Supabase SQL Editor를 사용해 `migrations/`의 SQL을 순서대로 적용합니다.

예:

```powershell
supabase db push
```

로컬 환경에 Supabase CLI가 없거나 remote project에 직접 적용하는 경우에는 SQL Editor에서 migration 내용을 순서대로 실행합니다.

## 보안 기준

- 사용자 소유 데이터는 `user_id` 기준으로 분리합니다.
- RLS는 DB 계층의 보안 경계로 유지합니다.
- backend repository query도 현재 사용자 조건을 포함해야 합니다.
- service role key는 backend/server 환경에서만 사용합니다.
- frontend에 Supabase service role key, DB URL, DB password를 노출하지 않습니다.

## 주요 테이블

```text
auth.users
  -> goals
      -> milestones

auth.users
  -> user_settings
```

| 테이블 | 역할 |
|---|---|
| `goals` | 사용자 목표 |
| `milestones` | 목표 하위 일정/작업 |
| `user_settings` | 사용자 계정 기준 앱 설정 |
| `external_calendar_connections` | Future 범위. 외부 캘린더 연동용 |

DB schema의 자세한 기준은 [docs/db_schema.md](../docs/db_schema.md)를 확인합니다.

## 변경 기준

- DB 변경은 migration으로만 남깁니다.
- 이미 적용된 migration을 수정하기보다 새 migration으로 보정합니다.
- schema 변경 시 `docs/db_schema.md`, `docs/api_spec.md`, backend schema/service/repository, tests를 함께 확인합니다.
- RLS 변경은 반드시 사용자 간 데이터 접근 차단 관점에서 검토합니다.
- 민감 정보나 실제 토큰을 migration 또는 seed 파일에 넣지 않습니다.
