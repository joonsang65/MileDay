# M1 변경사항: 같은 Supabase 프로젝트에서 테스트 데이터 분리

## 변경 배경

별도 Supabase 프로젝트를 두기 어려운 상황에서 실제 Supabase 연결 검증을 진행할 수 있도록, 같은 프로젝트 안에서 테스트 데이터를 안전하게 분리하는 기준을 추가했다.

핵심 방향은 다음과 같다.

- test 전용 테이블 생성 금지
- 운영과 동일한 `goals`, `milestones`, `user_settings` schema 사용
- 테스트 전용 auth user의 `user_id`로만 데이터 생성
- 통합 테스트는 기본 `pytest` 실행에서 제외
- service role key 사용 범위 제한

## 코드 변경사항

### 1. 통합 테스트 환경 변수 추가

`backend/app/core/config.py`에 통합 테스트용 설정을 추가했다.

```env
ENABLE_INTEGRATION_TESTS=false
INTEGRATION_TEST_EMAIL=test+integration@example.com
INTEGRATION_TEST_PASSWORD=your_test_user_password
INTEGRATION_TEST_USER_ID=your_test_user_uuid
INTEGRATION_TEST_TITLE_PREFIX=[TEST]
```

`ENABLE_INTEGRATION_TESTS=true`일 때는 다음 안전 조건을 검증한다.

- `INTEGRATION_TEST_EMAIL` 존재
- `INTEGRATION_TEST_PASSWORD` 존재
- `INTEGRATION_TEST_USER_ID` 존재 및 UUID 형식
- `INTEGRATION_TEST_TITLE_PREFIX` 존재
- `SUPABASE_SERVICE_ROLE_KEY` 존재
- 테스트 이메일 local-part가 `test`로 시작
- 테스트 title prefix가 `[TEST`로 시작

### 2. service role key fallback 제거

`backend/app/core/supabase.py`의 admin client 생성에서 anon key fallback을 제거했다.

이전 구조는 `SUPABASE_SERVICE_ROLE_KEY`가 없으면 anon key를 대신 사용했다. 이 경우 cleanup이나 seed 작업이 RLS에 걸려 실패하거나, 의도와 다른 권한으로 테스트가 수행될 수 있다.

변경 후 admin client는 반드시 service role key가 있어야 생성된다.

### 3. 통합 테스트 기본 제외

`pytest.ini`에 marker를 추가했다.

```ini
addopts =
    -m "not integration"
markers =
    integration: 실제 Supabase 프로젝트를 사용하는 통합 테스트
```

기본 명령은 빠른 단위 테스트만 실행한다.

```bash
pytest
```

실제 Supabase 연결 검증은 명시적으로 실행한다.

```bash
pytest -m integration
```

## schema_migrations 접근 권한 제한

Supabase CLI migration 기록 테이블은 일반 사용자 API 접근 대상이 아니므로 `anon`, `authenticated`, `public` 권한을 제거하는 기준을 추가했다.

적용 위치:

```text
supabase/migrations/202607050001_m1_base_schema.sql
```

적용 방식:

- `supabase_migrations` schema가 존재할 때만 권한 정리 실행
- `public`, `anon`, `authenticated`의 schema/table 권한 제거
- `postgres`의 schema/table 권한 유지
- CLI migration이 사용하는 `postgres` 권한은 revoke하지 않음

추가된 권한 기준:

```sql
revoke all on schema supabase_migrations from public;
revoke all on schema supabase_migrations from anon;
revoke all on schema supabase_migrations from authenticated;

revoke all on all tables in schema supabase_migrations from public;
revoke all on all tables in schema supabase_migrations from anon;
revoke all on all tables in schema supabase_migrations from authenticated;

grant usage on schema supabase_migrations to postgres;
grant all on all tables in schema supabase_migrations to postgres;
```

검증 쿼리:

```sql
select grantee, privilege_type
from information_schema.role_table_grants
where table_schema = 'supabase_migrations'
  and table_name = 'schema_migrations';
```

기대 상태:

- `postgres` 접근 가능
- `anon` 접근 불가
- `authenticated` 접근 불가
- Supabase CLI migration 정상 동작

### 4. 안전한 통합 테스트 skeleton 추가

`tests/integration/test_supabase_project.py`를 추가했다.

테스트 흐름은 다음과 같다.

1. 통합 테스트 환경 변수 검증
2. `INTEGRATION_TEST_USER_ID` 데이터 cleanup
3. 같은 user_id로 goal 생성
4. 같은 user_id와 goal_id로 milestone 생성
5. 생성 데이터 확인
6. finally 블록에서 같은 user_id 데이터 cleanup

cleanup은 다음 순서와 조건만 사용한다.

```text
milestones where user_id = INTEGRATION_TEST_USER_ID
goals where user_id = INTEGRATION_TEST_USER_ID
user_settings where user_id = INTEGRATION_TEST_USER_ID
```

조건 없는 delete와 truncate는 사용하지 않는다.

### 5. milestone 소유자 불일치 방지 trigger 추가

`supabase/migrations/202607050001_m1_base_schema.sql`에 `ensure_milestone_goal_owner` trigger를 추가했다.

목적은 다음 잘못된 데이터 방지다.

```text
milestones.goal_id = A 사용자의 goal
milestones.user_id = B 사용자
```

추가된 DB 기준:

```sql
select 1
from public.goals
where goals.id = new.goal_id
  and goals.user_id = new.user_id
```

위 조건이 맞지 않으면 insert/update가 실패한다.

## 남은 주의사항

- 현재 M1 router는 대부분 placeholder 응답을 반환하므로 API 레벨 Supabase 통합 테스트는 아직 제한적이다.
- 실제 API 통합 테스트는 service/repository 계층이 Supabase에 연결된 뒤 확장한다.
- 같은 Supabase 프로젝트를 쓰는 동안 실제 개인 계정의 `user_id`로 통합 테스트를 실행하면 안 된다.
- service role key는 `.env`에만 보관하고 git에 올리지 않는다.

## 검증 명령어

기본 테스트:

```bash
pytest
```

실제 Supabase 통합 테스트:

```bash
pytest -m integration
```
