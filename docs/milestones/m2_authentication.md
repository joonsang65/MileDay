# M2. 회원가입 기능 구현 진행 문서

## 문서 목적

M2 단계에서는 Supabase Auth를 기준으로 회원가입, 로그인, 로그아웃, 현재 사용자 조회, 인증 토큰 검증 흐름을 구현한다.
M1에서 준비한 FastAPI 공통 구조, Supabase client, 공통 응답, 예외 처리, 로그, 테스트 기준을 그대로 사용한다.

## 기준 문서

| 문서 | 확인 내용 |
| --- | --- |
| `docs/requirements.md` | M2 요구사항 MEM-01~MEM-05, SC-03 |
| `docs/api_spec.md` | Auth API endpoint, request/response 형식 |
| `docs/data_flow.md` | 인증 API 요청 흐름, JWT 기반 사용자 식별 흐름 |
| `docs/error_logging.md` | Auth 예외 코드, 인증 실패 status, 로그 masking 기준 |
| `docs/codex_rules.md` | Supabase Auth JWT, user_id 추출, 보호 API dependency 기준 |
| `docs/milestones/m1_changes.md` | M1 공통 기반, Supabase 연동, 테스트 기준 |

## M2 요구사항 범위

| ID | 분류 | 기능 | 구현 기준 |
| --- | --- | --- | --- |
| MEM-01 | 회원가입/로그인 | 회원가입 | 사용자는 이메일과 비밀번호를 입력하여 계정을 생성할 수 있음 |
| MEM-02 | 회원가입/로그인 | 로그인 | 사용자는 가입한 계정으로 로그인할 수 있음 |
| MEM-03 | 회원가입/로그인 | 자동 로그인 | 클라이언트가 저장한 refresh token 또는 session 기반으로 로그인 상태를 복원할 수 있음 |
| MEM-04 | 회원가입/로그인 | 로그아웃 | 사용자는 현재 로그인된 계정에서 로그아웃할 수 있음 |
| MEM-05 | 회원가입/로그인 | 사용자별 데이터 접근 | 인증된 사용자는 본인 `user_id` 기준 데이터만 접근할 수 있음 |
| SC-03 | 보안 | 인증 토큰 검증 | 백엔드는 API 요청 시 Supabase Auth JWT를 검증하고 인증된 사용자 기준으로 처리함 |

## 구현 대상 API

| 기능 | Method | Endpoint | 인증 필요 | 구현 내용 |
| --- | --- | --- | --- | --- |
| 회원가입 | POST | `/auth/signup` | X | 이메일/비밀번호 기반 Supabase Auth 사용자 생성 |
| 로그인 | POST | `/auth/login` | X | Supabase Auth 로그인 후 access token, refresh token 반환 |
| 로그아웃 | POST | `/auth/logout` | O | 현재 사용자 session 종료 요청 처리 |
| 현재 사용자 조회 | GET | `/auth/me` | O | JWT 검증 후 현재 사용자 ID와 이메일 반환 |

## 구현 원칙

- FastAPI는 자체 JWT를 발급하지 않음
- 인증 기준은 Supabase Auth에서 발급한 access token임
- 인증 필요 API는 `Authorization: Bearer <access_token>` header를 요구함
- 백엔드는 JWT의 `sub` 값을 현재 사용자의 `user_id`로 사용함
- 클라이언트가 보낸 `user_id`는 신뢰하지 않음
- password, access token, refresh token, Authorization header 원문은 로그에 남기지 않음
- 인증 실패는 기본적으로 `401 UNAUTHORIZED`로 처리함
- 사용자 데이터 존재 여부를 노출하면 안 되는 경우 `404 NOT_FOUND`로 처리함
- Supabase 원본 오류 메시지는 사용자 응답에 그대로 노출하지 않음

## 권장 구현 순서

| 순서 | 작업 | 산출물 |
| --- | --- | --- |
| 1 | Auth request/response schema 정의 | signup/login/logout/me schema |
| 2 | Auth 전용 예외 클래스 정의 | invalid credentials, invalid token, expired token, logout failed |
| 3 | Supabase Auth repository 또는 service wrapper 작성 | Supabase auth 호출 격리 |
| 4 | JWT 검증 dependency 작성 | `get_current_user` 계열 dependency |
| 5 | `/auth/signup` 구현 | 사용자 생성 API |
| 6 | `/auth/login` 구현 | token 반환 API |
| 7 | `/auth/logout` 구현 | 인증 필요 logout API |
| 8 | `/auth/me` 구현 | 현재 사용자 조회 API |
| 9 | 보호 API에 인증 dependency 적용 기준 정리 | M3 이후 goals/milestones 확장 준비 |
| 10 | 단위 테스트 및 통합 테스트 작성 | Auth API 테스트, Supabase mock, real Supabase opt-in |

## 세부 구현 계획

### 1. Schema

Auth API는 입력값 검증을 router 안에서 직접 처리하지 않고 Pydantic schema로 검증한다.

| Schema | 필드 | 검증 기준 |
| --- | --- | --- |
| `SignupRequest` | `email`, `password` | email 형식, password 최소 길이 |
| `LoginRequest` | `email`, `password` | email 형식, password 필수 |
| `TokenResponse` | `access_token`, `refresh_token`, `token_type`, `user` | `token_type`은 `bearer` |
| `CurrentUserResponse` | `user_id`, `email` | JWT 검증 결과 기반 |

### 2. Auth Service

Auth router는 Supabase SDK 호출 세부사항을 직접 알지 않도록 service 계층을 둔다.

| 메서드 | 역할 |
| --- | --- |
| `signup(email, password)` | Supabase Auth 사용자 생성 |
| `login(email, password)` | Supabase Auth session 생성 |
| `logout(access_token)` | 현재 token 기반 session 종료 |
| `get_user(access_token)` | access token 검증 및 사용자 조회 |

### 3. 인증 Dependency

보호 API에서 공통으로 사용할 dependency를 만든다.

| Dependency | 역할 |
| --- | --- |
| `get_bearer_token` | Authorization header에서 Bearer token 추출 |
| `get_current_user` | Supabase Auth로 token 검증 후 현재 사용자 반환 |
| `require_current_user_id` | JWT `sub` 기반 `user_id` 반환 |

## 예외 처리 기준

| 상황 | Error Code | HTTP Status | 처리 기준 |
| --- | --- | --- | --- |
| 로그인 정보 불일치 | `AUTH_INVALID_CREDENTIALS` | 401 | 이메일 또는 비밀번호 불일치 |
| Authorization header 없음 | `UNAUTHORIZED` | 401 | 인증 필요 API에서 header 누락 |
| Bearer 형식 오류 | `AUTH_INVALID_TOKEN` | 401 | `Bearer <token>` 형식 아님 |
| JWT 검증 실패 | `AUTH_INVALID_TOKEN` | 401 | Supabase Auth 검증 실패 |
| JWT 만료 | `AUTH_TOKEN_EXPIRED` | 401 | token 만료 |
| 사용자 정보 없음 | `AUTH_USER_NOT_FOUND` | 404 | token은 있으나 사용자 조회 실패 |
| 로그아웃 실패 | `AUTH_LOGOUT_FAILED` | 500 | Supabase logout 요청 실패 |
| Supabase Auth 응답 실패 | `SUPABASE_UNAVAILABLE` | 502 | 외부 인증 서비스 장애 |

## 로그 기준

| 이벤트 | 로그 레벨 | 포함 정보 | 제외 정보 |
| --- | --- | --- | --- |
| 회원가입 성공 | INFO | request_id, user_id, email masking | password, token |
| 로그인 성공 | INFO | request_id, user_id, email masking | password, access token, refresh token |
| 로그인 실패 | WARNING | request_id, email masking, error_code | password |
| JWT 검증 실패 | WARNING | request_id, path, error_code | Authorization 원문 |
| 로그아웃 성공 | INFO | request_id, user_id | token |
| Supabase Auth 실패 | ERROR | request_id, error_code, safe detail | token, stack trace 응답 노출 |

## 테스트 계획

| 섹션 | 테스트 항목 | 검증 내용 |
| --- | --- | --- |
| Auth API 기본 동작 | 회원가입 API | 정상 요청 시 Supabase signup 호출 및 공통 성공 응답 반환 |
| Auth API 기본 동작 | 로그인 API | 정상 요청 시 token, token_type, user 정보 반환 |
| Auth API 기본 동작 | 현재 사용자 조회 API | Bearer token 검증 후 현재 사용자 반환 |
| Auth API 기본 동작 | 로그아웃 API | 인증된 요청에서 logout 처리 |
| 인증 및 보안 | Authorization header 누락 | 401 공통 오류 응답 반환 |
| 인증 및 보안 | Bearer token 형식 오류 | 401 `AUTH_INVALID_TOKEN` 반환 |
| 인증 및 보안 | JWT 검증 실패 | 401 응답 및 warning 로그 기록 |
| 인증 및 보안 | 민감 정보 masking | password, token, Authorization 원문 미노출 |
| Supabase 연동 | Supabase Auth 오류 mapping | invalid credentials, unavailable, unexpected error 매핑 |
| Supabase 연동 | 통합 테스트 opt-in | 실제 Supabase Auth 계정으로 signup/login/me/logout 흐름 검증 |

## 통합 테스트 기준

실제 Supabase 프로젝트를 사용하는 테스트는 기본 테스트에서 제외하고 명시적으로만 실행한다.

```bash
pytest -m integration
```

필수 환경 변수:

```env
ENABLE_INTEGRATION_TESTS=true
SUPABASE_URL=...
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...
INTEGRATION_TEST_EMAIL=test+integration@example.com
INTEGRATION_TEST_PASSWORD=...
INTEGRATION_TEST_USER_ID=...
INTEGRATION_TEST_TITLE_PREFIX=[TEST]
```

주의사항:

- 테스트용 이메일은 실제 개인 계정과 분리
- 통합 테스트가 생성한 사용자는 식별 가능한 이메일 prefix 사용
- cleanup은 service role key로 테스트 데이터만 대상으로 수행
- auth user 삭제가 필요한 경우 Supabase Admin API 사용 여부를 별도 검토

## 완료 기준

- `/auth/signup`이 문서 기준 request/response를 만족함
- `/auth/login`이 Supabase Auth token을 정상 반환함
- `/auth/logout`이 인증 dependency를 통과한 요청에서 동작함
- `/auth/me`가 JWT 기반 현재 사용자 정보를 반환함
- 보호 API에 재사용 가능한 인증 dependency가 준비됨
- 인증 실패, token 오류, Supabase 오류가 공통 예외 응답으로 변환됨
- 로그에 password, access token, refresh token, Authorization 원문이 남지 않음
- 기본 pytest가 통과함
- coverage 90% 이상을 유지함
- 실제 Supabase 통합 테스트는 opt-in 방식으로 실행 가능함

## M3로 넘길 준비 사항

M2 완료 후 M3 목표 관리 기능에서는 다음 기준을 바로 사용할 수 있어야 한다.

- `current_user.id`를 `goals.user_id`로 설정
- 클라이언트가 보낸 `user_id` 무시
- 목표 조회, 수정, 삭제 조건에 `id = goal_id AND user_id = current_user.id` 적용
- 권한 없는 목표 접근은 `404 NOT_FOUND` 처리
- 목표 API 테스트에서 인증 dependency override 가능
