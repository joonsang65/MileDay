# M1. 개발 환경 구축하기

## 문서 목적

M1은 MileDay의 이후 기능 구현을 가능하게 만드는 기반 단계임
목표 CRUD, 마일스톤 CRUD, 캘린더, 설정 기능을 바로 만들기 전에 FastAPI 실행 구조, Supabase DB, RLS, 공통 응답, 예외 처리, 로그 기준을 먼저 고정함

이 문서는 기능 단위로 순차 진행하기 위한 세부 스코프와 선후 관계를 정리함

## 참조 문서

| 문서 | 확인 기준 |
|---|---|
| `docs/codex_rules.md` | 전체 구현 규칙, 금지 사항, 계층 구조 기준 |
| `docs/requirements.md` | M1 상세 요구사항 ID와 범위 |
| `docs/db_schema.md` | goals, milestones, user_settings, RLS 기준 |
| `docs/api_spec.md` | 공통 응답 형식, 인증 헤더, API 기본 규칙 |
| `docs/error_logging.md` | ErrorResponse, custom exception, request_id, 로그 기준 |
| `docs/data_flow.md` | Frontend -> FastAPI -> Supabase 데이터 흐름 |

## M1 요구사항 범위

| ID | 분류 | 기능명 | M1에서의 처리 기준 |
|---|---|---|---|
| BE-01 | 백엔드 | FastAPI 서버 구성 | 앱 실행, router 등록, health check, 설정 로딩 구조를 고정함 |
| BE-02 | 백엔드 | API 기반 데이터 처리 | Frontend가 Supabase에 직접 접근하지 않는 전제의 backend 계층 구조를 만듦 |
| BE-06 | 백엔드 | CORS 설정 | Electron/React 개발 서버에서 FastAPI 호출이 가능하도록 허용 origin을 설정함 |
| BE-07 | 백엔드 | API 응답 통일 | 성공 응답과 실패 응답 schema를 공통화함 |
| BE-08 | 백엔드 | 백엔드 로그 기록 | 요청 처리, 주요 성공 이벤트, 오류 이벤트를 로그로 남기는 기반을 만듦 |
| BE-09 | 백엔드 | 에러 로그 분리 | 콘솔 로그와 파일 로그, 일반 로그와 에러 로그 구분 기준을 준비함 |
| DB-01 | 데이터베이스 | 사용자 데이터 저장 | Supabase PostgreSQL을 기준 DB로 사용하도록 연결 구조를 준비함 |
| DB-02 | 데이터베이스 | 목표 테이블 관리 | goals 테이블 migration 기준을 작성함 |
| DB-03 | 데이터베이스 | 마일스톤 테이블 관리 | milestones 테이블 migration 기준을 작성함 |
| DB-04 | 데이터베이스 | 사용자별 데이터 분리 | 모든 사용자 데이터에 user_id를 포함하고 JWT sub 기준으로 처리하도록 설계함 |
| DB-05 | 데이터베이스 | 목표 삭제 시 마일스톤 삭제 | goals 삭제 시 milestones가 함께 삭제되도록 FK cascade 기준을 정함 |
| ERR-04 | 오류 처리 | 예외 처리 공통화 | MileDayBaseException과 Global Exception Handler 구조를 만듦 |
| SC-01 | 보안 | RLS 적용 | goals, milestones, user_settings에 auth.uid() = user_id 기준 RLS를 적용함 |
| SC-02 | 보안 | 민감 정보 보호 | Supabase URL, key, DB 정보는 backend env에서만 관리함 |
| SC-04 | 보안 | 백엔드 권한 검증 | RLS와 별개로 service layer에서 user_id 조건을 항상 포함하도록 기준을 만듦 |

## 구축 전략 요약

M1은 바로 기능 API를 완성하는 단계가 아니라, 기능 API가 올라갈 수 있는 공통 바닥을 만드는 단계임
따라서 DB와 보안 기준을 먼저 고정하고, 그 위에 backend 계층, 응답 형식, 예외 처리, 로그를 얹는 순서로 진행함

```text
1. 환경 변수와 설정 구조 정리
2. FastAPI 앱 구조와 CORS 구성
3. Supabase 연결 모듈 준비
4. DB migration 기준 작성
5. RLS와 user_id 보안 기준 적용
6. backend 계층 구조 정리
7. 공통 응답 schema 정의
8. custom exception과 global handler 구현
9. request_id middleware와 logging 구성
10. M1 검증 시나리오 실행
```

## 단계별 세부 스코프

### 1단계. 환경 변수와 설정 구조 정리

목적:

- backend가 실행 환경별 설정을 코드와 분리해서 읽을 수 있게 함
- Supabase 민감 정보가 frontend나 repository에 노출되지 않게 함

포함 작업:

| 작업 | 내용 |
|---|---|
| 환경 변수 목록 정의 | Supabase URL, Supabase anon key 또는 backend용 key, 로그 레벨, CORS origin, 실행 환경을 정의함 |
| config 모듈 정리 | `backend/app/core/config.py`에서 환경 변수를 읽고 앱 전체에서 재사용함 |
| `.env.example` 정리 | 실제 secret 없이 필요한 변수명만 예시로 남김 |
| 민감 정보 기준 고정 | service role key, DB password, access token, refresh token은 frontend에 두지 않음 |

완료 기준:

- FastAPI 실행 시 설정 객체를 정상 로드함
- 설정 누락 시 명확한 오류가 발생함
- frontend 디렉터리나 public 설정에 Supabase secret이 없음

선행 조건:

- 없음

후속 단계:

- 2단계 FastAPI 앱 구성
- 3단계 Supabase 연결 모듈 구성

### 2단계. FastAPI 앱 구조와 CORS 구성

목적:

- MileDay backend의 진입점과 router 등록 방식을 고정함
- Electron/React 개발 환경에서 API 요청이 가능하게 함

포함 작업:

| 작업 | 내용 |
|---|---|
| 앱 진입점 정리 | `backend/app/main.py`에서 FastAPI app 생성, router 등록, middleware 등록 순서를 정리함 |
| health check 추가 | backend 실행 상태를 확인할 수 있는 최소 endpoint를 둠 |
| CORS 설정 | 개발 origin과 운영 origin을 config 기반으로 관리함 |
| router prefix 확인 | auth, goals, milestones, calendar, settings, future router의 prefix를 문서 기준과 맞춤 |

완료 기준:

- `GET /health` 또는 이에 준하는 endpoint로 서버 상태를 확인할 수 있음
- 개발 origin에서 API 호출이 차단되지 않음
- router 등록 위치와 prefix가 한 곳에서 확인 가능함

선행 조건:

- 1단계 환경 변수와 설정 구조

후속 단계:

- 6단계 backend 계층 구조 정리
- 7단계 공통 응답 schema 정의

### 3단계. Supabase 연결 모듈 준비

목적:

- backend가 Supabase Auth와 PostgreSQL에 접근하는 통로를 한 곳으로 모음
- 이후 service/repository에서 직접 client 생성이 반복되지 않게 함

포함 작업:

| 작업 | 내용 |
|---|---|
| Supabase client factory 정의 | config 값을 사용해 Supabase Python Client를 생성함 |
| Auth 접근 기준 정리 | 회원가입, 로그인, JWT 검증에서 사용할 client 접근 방식을 분리함 |
| DB 접근 기준 정리 | goals, milestones, user_settings repository가 사용할 client 접근 방식을 정리함 |
| 오류 변환 기준 준비 | Supabase 오류를 MileDay custom exception으로 변환할 수 있게 경계를 둠 |

완료 기준:

- Supabase client 생성 코드가 한 모듈에 모여 있음
- service나 router에서 환경 변수를 직접 읽지 않음
- Supabase 원본 오류를 router에서 직접 처리하지 않도록 기준이 잡힘

선행 조건:

- 1단계 환경 변수와 설정 구조

후속 단계:

- 4단계 DB migration 기준 작성
- 8단계 custom exception과 global handler 구현

### 4단계. DB migration 기준 작성

목적:

- M1에서 필요한 핵심 테이블과 관계를 Supabase PostgreSQL 기준으로 고정함
- 목표와 마일스톤 기능 구현 전에 데이터 모델을 안정화함

포함 작업:

| 작업 | 내용 |
|---|---|
| goals 테이블 작성 | id, user_id, title, deadline, is_recurring, recurrence_type, color, created_at, updated_at을 정의함 |
| milestones 테이블 작성 | id, goal_id, user_id, title, color, scheduled_date, is_completed, created_at, updated_at을 정의함 |
| user_settings 테이블 작성 | user_id를 PK로 두고 계정 기준 설정 필드를 정의함 |
| FK 관계 정의 | goals.user_id, milestones.user_id, milestones.goal_id, user_settings.user_id 관계를 정의함 |
| cascade 기준 정의 | goal 삭제 시 하위 milestone도 삭제되도록 `ON DELETE CASCADE`를 적용함 |
| updated_at 기준 정의 | 수정 시 updated_at이 갱신되도록 trigger 또는 application 기준을 정함 |

완료 기준:

- migration 파일만 보고도 핵심 테이블을 생성할 수 있음
- goal과 milestone 관계가 DB 레벨에서 보장됨
- 사용자의 데이터 분리를 위해 user_id가 필요한 테이블에 모두 포함됨

선행 조건:

- 3단계 Supabase 연결 모듈 준비

후속 단계:

- 5단계 RLS와 user_id 보안 기준 적용

### 5단계. RLS와 user_id 보안 기준 적용

목적:

- DB 레벨에서 사용자가 본인 데이터만 접근하도록 제한함
- backend 권한 검증과 RLS를 이중 안전장치로 둠

포함 작업:

| 작업 | 내용 |
|---|---|
| RLS 활성화 | goals, milestones, user_settings 테이블에 RLS를 활성화함 |
| 기본 정책 작성 | `auth.uid() = user_id` 기준으로 select, insert, update, delete 정책을 작성함 |
| insert 정책 확인 | user_id가 현재 인증 사용자와 다르면 insert가 실패하도록 함 |
| service layer 기준 작성 | 조회, 수정, 삭제 시 항상 `user_id = current_user.id` 조건을 포함함 |
| 클라이언트 user_id 무시 | 요청 body의 user_id는 신뢰하지 않고 JWT sub 값으로 서버에서 설정함 |

완료 기준:

- 다른 사용자의 goal, milestone, settings에 접근할 수 없음
- RLS와 backend 조건이 같은 user_id 기준을 사용함
- user_id를 클라이언트 입력값으로 받지 않는 원칙이 코드에 반영됨

선행 조건:

- 4단계 DB migration 기준 작성

후속 단계:

- 6단계 backend 계층 구조 정리
- M2 인증 토큰 검증 구현

### 6단계. backend 계층 구조 정리

목적:

- router에 비즈니스 로직과 Supabase 접근 코드가 섞이지 않게 함
- 이후 목표, 마일스톤, 캘린더 기능을 같은 패턴으로 확장할 수 있게 함

권장 구조:

```text
backend/app
  api/
    routers/
  core/
    config.py
    logging.py
    middleware.py
  schemas/
  services/
  repositories/
  exceptions/
```

포함 작업:

| 계층 | 역할 |
|---|---|
| Router | HTTP endpoint, request schema, response schema 연결 |
| Schema | Pydantic request/response 모델 정의 |
| Service | 인증 사용자 기준 비즈니스 로직과 권한 검증 |
| Repository | Supabase 테이블 접근 |
| Core | config, logging, middleware 등 공통 기반 |
| Exceptions | MileDayBaseException과 기능별 custom exception |

완료 기준:

- router가 Supabase client를 직접 호출하지 않음
- service 계층에서 user_id 권한 조건을 관리함
- repository 계층은 데이터 접근만 담당함

선행 조건:

- 2단계 FastAPI 앱 구조
- 5단계 RLS와 user_id 보안 기준

후속 단계:

- 7단계 공통 응답 schema 정의
- M3 이후 기능 API 구현

### 7단계. 공통 응답 schema 정의

목적:

- Frontend가 모든 API 응답을 같은 방식으로 처리하게 함
- 성공/실패 응답이 기능별로 달라지지 않게 함

포함 작업:

| 작업 | 내용 |
|---|---|
| SuccessResponse 정의 | `{ "success": true, "data": ... }` 형식을 기준으로 함 |
| ErrorResponse 정의 | `{ "success": false, "error": { ... }, "request_id": ... }` 형식을 기준으로 함 |
| ErrorCode enum 정리 | frontend가 `error.code`로 메시지를 매핑할 수 있도록 함 |
| Validation Error 기준 반영 | FastAPI validation error를 400으로 변환하는 구조를 준비함 |

완료 기준:

- 성공 응답과 실패 응답 형식이 문서 기준과 일치함
- 실패 응답에는 `error.code`, `error.message`, `error.detail`, `request_id`가 포함됨
- validation error는 422가 아니라 400으로 내려갈 준비가 되어 있음

선행 조건:

- 2단계 FastAPI 앱 구조
- 6단계 backend 계층 구조

후속 단계:

- 8단계 custom exception과 global handler 구현

### 8단계. custom exception과 global handler 구현

목적:

- 기능별 오류를 router에서 직접 HTTPException으로 흩뿌리지 않게 함
- service/repository에서 custom exception을 던지고 global handler에서 공통 응답으로 변환함

포함 작업:

| 작업 | 내용 |
|---|---|
| MileDayBaseException 정의 | status_code, error_code, message, detail을 포함함 |
| 기능별 exception 준비 | Auth, Permission, Validation, NotFound, Conflict, Supabase 오류를 분리함 |
| Global Exception Handler 구현 | custom exception을 ErrorResponse로 변환함 |
| Validation Error handler 구현 | FastAPI RequestValidationError를 400 BAD_REQUEST로 변환함 |
| 예상 못한 오류 handler 구현 | 서버 내부 오류를 INTERNAL_SERVER_ERROR로 변환하고 stack trace는 로그에만 남김 |

완료 기준:

- router마다 반복적인 try/except가 늘어나지 않음
- 사용자 응답에는 안전한 메시지만 내려감
- 상세 오류와 stack trace는 로그 기준에 맞게 남음

선행 조건:

- 7단계 공통 응답 schema 정의
- 3단계 Supabase 연결 모듈 준비

후속 단계:

- 9단계 request_id middleware와 logging 구성

### 9단계. request_id middleware와 logging 구성

목적:

- 요청 단위 추적이 가능하도록 모든 응답과 로그에 request_id를 포함함
- 운영 환경에서도 콘솔과 파일 로그를 남겨 원인 추적이 가능하게 함

포함 작업:

| 작업 | 내용 |
|---|---|
| request_id middleware 구현 | 요청 시작 시 request_id를 생성하거나 header 값을 이어받음 |
| duration_ms 측정 | 요청 시작/종료 시간을 기준으로 처리 시간을 계산함 |
| logging formatter 구성 | request_id, user_id, method, path, status_code, duration_ms를 포함함 |
| 로그 파일 구성 | 콘솔 + 파일 로그를 설정하고 날짜별 회전과 7일 보관 기준을 둠 |
| 요청 body 마스킹 유틸 구현 | password, token, refresh_token, Authorization 원문을 로그에 남기지 않음 |
| 성공 로그 기준 적용 | 로그인 성공, 주요 생성/수정/삭제 성공 등 큰 단위만 INFO로 남김 |

완료 기준:

- 모든 에러 응답에 request_id가 포함됨
- 같은 request_id로 요청 로그와 에러 로그를 연결해 볼 수 있음
- 민감 정보가 로그에 저장되지 않음
- 단순 조회 성공 로그가 과도하게 쌓이지 않음

선행 조건:

- 8단계 custom exception과 global handler 구현

후속 단계:

- 10단계 M1 검증 시나리오 실행

### 10단계. M1 검증 시나리오 실행

목적:

- M1 기반 구조가 이후 기능 구현에 사용할 수 있는 상태인지 확인함

검증 항목:

| 검증 항목 | 확인 방법 |
|---|---|
| 서버 실행 | FastAPI 서버가 설정 누락 없이 실행되는지 확인함 |
| health check | health endpoint가 정상 응답하는지 확인함 |
| CORS | 개발 origin에서 API 요청이 허용되는지 확인함 |
| DB migration | Supabase에 핵심 테이블이 생성되는지 확인함 |
| FK cascade | goal 삭제 시 하위 milestone 삭제 기준이 존재하는지 확인함 |
| RLS | 다른 user_id 데이터 접근이 차단되는지 확인함 |
| 공통 응답 | 성공/실패 응답 형식이 문서와 일치하는지 확인함 |
| validation error | 잘못된 request가 400으로 변환되는지 확인함 |
| request_id | 응답 header/body와 로그에서 request_id를 확인할 수 있는지 확인함 |
| 로그 마스킹 | password, token, Authorization 원문이 로그에 남지 않는지 확인함 |

완료 기준:

- M1 요구사항 ID 전체가 구현 또는 구현 기준 문서화 상태임
- M2 회원가입 기능 구현 전에 필요한 backend, DB, 보안, 예외, 로그 기반이 준비됨
- 검증 실패 항목은 M2로 넘기지 않고 M1에서 해결함

## 선후 관계 기준

| 선행 작업 | 후속 작업 | 이유 |
|---|---|---|
| 환경 변수와 config | FastAPI, Supabase, logging | 모든 공통 모듈이 config를 참조함 |
| FastAPI 앱 구조 | middleware, handler, router | 앱 등록 순서가 middleware와 handler 동작에 영향을 줌 |
| Supabase 연결 | DB repository, Auth 연동 | 데이터 접근 경계가 먼저 필요함 |
| DB migration | RLS | 정책은 테이블과 user_id 필드가 있어야 적용 가능함 |
| RLS 기준 | service 권한 검증 | backend 권한 조건과 DB 정책을 같은 기준으로 맞춰야 함 |
| 공통 응답 schema | global handler | handler가 변환할 응답 형식이 먼저 필요함 |
| custom exception | logging | 어떤 error_code를 로그에 남길지 먼저 정해야 함 |
| request_id middleware | error logging | request_id가 있어야 로그와 응답을 연결할 수 있음 |

## M1 완료 산출물

| 산출물 | 설명 |
|---|---|
| backend 설정 구조 | 환경 변수 기반 config와 `.env.example` |
| FastAPI 기본 앱 | app 생성, router 등록, CORS, health check |
| Supabase 연결 모듈 | Auth/DB 접근에 사용할 공통 client 구성 |
| DB migration | goals, milestones, user_settings, FK, cascade, updated_at 기준 |
| RLS 정책 | user_id 기준 select, insert, update, delete 정책 |
| 공통 schema | SuccessResponse, ErrorResponse, ErrorCode |
| 예외 처리 구조 | MileDayBaseException, custom exception, global handler |
| 로그 구조 | request_id middleware, formatter, 콘솔/파일 로그, 마스킹 유틸 |
| 검증 기록 | M1 검증 항목 통과 여부 |

## Codex 구현 지시 기준

M1 작업을 Codex에게 맡길 때는 한 번에 전체를 구현시키지 않고 아래 순서로 요청함

1. 환경 변수와 FastAPI 앱 구조를 먼저 정리함
2. Supabase 연결 모듈과 DB migration을 작성함
3. RLS와 user_id 보안 기준을 적용함
4. backend 계층 구조를 정리함
5. 공통 응답 schema를 정의함
6. custom exception과 global handler를 구현함
7. request_id middleware와 logging을 구현함
8. M1 검증 시나리오를 실행하고 실패 항목을 수정함

각 단계는 이전 단계가 정상 동작한 뒤 다음 단계로 넘어감
단계 중 문서 기준과 코드가 충돌하면 구현을 멈추고 충돌 내용을 먼저 정리함
