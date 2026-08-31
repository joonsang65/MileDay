# ADR 0023. RLS/service role 보안 구조 검증

## 상태

Accepted. 현재 repo 기준으로 보안 경계를 재정의한다.

## 결론

MileDay의 사용자 데이터 분리 1차 방어선은 RLS가 아니라 backend application layer다. DB repository는 `service_role` client를 사용하므로 Supabase RLS를 우회할 수 있다. 따라서 사용자 데이터 분리는 다음 흐름으로 설명해야 한다.

```text
Authorization: Bearer <access_token>
-> Supabase Auth로 JWT 사용자 확인
-> backend가 current_user.id를 추출
-> service/repository/RPC에 user_id 전달
-> 모든 조회/수정/삭제에 user_id 조건 적용
-> 생성 payload의 user_id는 서버가 설정
```

## 코드 기준

| 영역 | 확인 결과 |
|---|---|
| Frontend | Supabase에 직접 접근하지 않고 FastAPI API client만 사용한다. |
| Auth | `get_supabase_client()`는 회원가입, 로그인, JWT 사용자 확인에 사용한다. |
| DB repository | `get_supabase_admin_client()` 기반 service role client를 사용한다. |
| Goal | 조회/수정/삭제는 `goal_id + user_id`, 생성은 서버가 `payload["user_id"] = user_id`로 설정한다. |
| Milestone | 생성 전 목표 소유권을 확인하고, 조회/수정/삭제는 `milestone_id + user_id` 조건을 사용한다. |
| Settings | `user_settings.user_id` 기준으로 조회/수정하고, 기본값 생성도 서버 user_id로 수행한다. |
| RPC | `complete_goal_with_milestones`, `complete_milestone_and_sync_goal`은 `p_user_id` 조건으로 update/select 범위를 제한한다. |

## DB 방어선

마이그레이션에는 `goals`, `milestones`, `user_settings` RLS 정책이 있다. 이 정책은 anon/authenticated client 또는 향후 클라이언트 직접 DB 접근 경로가 생길 때 의미가 있다.

현재 runtime에서 일반 데이터 repository가 service role을 사용하므로, RLS를 “현재 사용자 분리의 핵심 방어선”으로 표현하지 않는다. RLS는 보조 방어선이며, service role 경로에서는 backend의 `user_id` 조건과 owner check가 핵심이다.

DB 레벨 보조 장치:

- `auth.uid() = user_id` RLS policy
- `ensure_milestone_goal_owner()` trigger
- completion RPC의 `p_user_id` 조건
- RPC 실행 권한을 `service_role`로 제한

## 리스크

- service role key가 노출되면 RLS 우회 권한까지 노출된다.
- repository 신규 메서드가 `user_id` 조건 없이 추가되면 사용자 데이터 분리 위반이 생길 수 있다.
- `check_supabase_db_health()`는 service role로 `goals` 1건을 조회하므로 사용자 데이터는 반환하지 않지만, health check 이상의 데이터 조회로 확장하면 안 된다.

## 문서 표현 원칙

- “RLS가 사용자 데이터 분리의 주 방어선이다”라고 쓰지 않는다.
- “backend가 JWT에서 user_id를 확인하고 모든 DB 작업에 user_id 조건을 강제한다”를 먼저 쓴다.
- RLS는 anon/authenticated client와 향후 직접 DB 접근 경로를 위한 보조 방어선으로 설명한다.
