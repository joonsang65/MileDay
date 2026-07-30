# MileDay Backend

MileDay backend는 Electron/React 프론트엔드와 Supabase 사이에 있는 FastAPI API 서버입니다. 프론트엔드는 Supabase에 직접 접근하지 않고, 모든 인증 검증과 사용자 데이터 처리는 backend를 통해 수행합니다.

## 역할

Backend의 책임은 다음과 같습니다.

- Supabase Auth JWT 검증
- 현재 사용자 `user_id` 추출
- 목표, 마일스톤, 캘린더, 사용자 설정 API 제공
- 사용자별 데이터 소유권 검증
- Supabase PostgreSQL 접근
- 공통 응답 envelope 적용
- request_id 기반 로그 및 에러 추적
- FastAPI validation error를 MileDay 공통 오류 형식으로 변환

전체 애플리케이션 경계는 다음 구조를 따릅니다.

```text
Electron + React + TypeScript + Vite
        -> FastAPI backend
        -> Supabase Auth / Supabase PostgreSQL
```

## 아키텍처

Backend 코드는 다음 계층 흐름을 기준으로 구성합니다.

```text
Router -> Service -> Repository / Infrastructure -> Supabase
```

| 계층 | 위치 | 책임 |
|---|---|---|
| Router | `app/api/routers/` | HTTP path, query, body, dependency 처리 |
| Service | `app/services/` | 비즈니스 규칙, 권한 확인, 도메인 오류 변환 |
| Repository | `app/repositories/` | Supabase table query 실행 |
| Infrastructure/Core | `app/core/` | 설정, 인증 dependency, Supabase client, logging, middleware |
| Schema | `app/schemas/` | Pydantic request/response 모델 |
| Exception | `app/exceptions/` | 도메인별 예외와 공통 exception handler |

Router는 비즈니스 로직을 직접 처리하지 않고 Service를 호출합니다. Repository는 DB 접근만 담당하며, 사용자별 접근 제한 조건은 Service/Repository 흐름에서 `user_id` 기준으로 유지합니다.

## 디렉터리 구조

```text
backend/
  app/
    main.py
    api/
      routers/
    core/
    exceptions/
    repositories/
    schemas/
    services/
```

주요 파일:

| 파일 | 설명 |
|---|---|
| `app/main.py` | FastAPI app 생성, middleware, exception handler, router 등록 |
| `app/core/config.py` | `.env` 기반 backend 설정 로드 |
| `app/core/auth.py` | Bearer token 추출, Supabase Auth 기반 현재 사용자 dependency |
| `app/core/supabase.py` | Supabase client 생성 및 DB health check |
| `app/core/middleware.py` | request_id 생성, 응답 header 연결, request context 관리 |
| `app/core/logging.py` | 로그 포맷, 민감 정보 마스킹, 파일 로그 설정 |
| `app/exceptions/handlers.py` | MileDay 공통 에러 응답 변환 |

## 요청 처리 흐름

인증이 필요한 API는 다음 흐름으로 처리됩니다.

```text
HTTP request
  -> RequestContextMiddleware
  -> Router dependency
  -> get_bearer_token()
  -> get_current_user()
  -> Service method
  -> Repository query
  -> Supabase
  -> SuccessResponse / ErrorResponse
```

핵심 원칙:

- `Authorization: Bearer <access_token>` 형식만 허용합니다.
- 클라이언트가 보낸 `user_id`는 신뢰하지 않습니다.
- JWT의 `sub`를 현재 사용자 ID로 사용합니다.
- 조회, 수정, 삭제에는 현재 사용자 기준 조건을 포함합니다.
- 다른 사용자의 데이터 접근 실패는 일반적으로 `404 NOT_FOUND`로 처리합니다.

## API 라우터

현재 등록된 주요 라우터는 다음과 같습니다.

| 라우터 파일 | Prefix / Path | 설명 |
|---|---|---|
| `auth.py` | `/auth` | 회원가입, 로그인, 로그아웃, 현재 사용자 조회 |
| `goals.py` | `/goals` | 목표 CRUD |
| `milestones.py` | `/goals/{goal_id}/milestones`, `/milestones/*` | 마일스톤 CRUD, 오늘 할 일, 완료 처리 |
| `calender.py` | `/calendar` | 월간/주간/날짜별 캘린더 조회 |
| `settings.py` | `/settings` | 사용자 계정 기준 설정 조회/수정 |
| `external_calender.py` | Future 범위 | 외부 캘린더 연동용 라우터 |
| `schedule_assistant.py` | Future 범위 | 일정 보조 기능용 라우터 |

주의:

- 파일명에는 현재 `calender.py`, `external_calender.py`처럼 `calendar`가 아닌 `calender` 표기가 남아 있습니다.
- 실제 API prefix는 `/calendar`를 사용합니다.
- Future 범위 라우터는 존재하더라도, 실제 제품 범위에서는 사용자가 명시적으로 요청한 기능만 구현합니다.

## 응답 형식

성공 응답은 endpoint별 response model을 사용하되, 기본적으로 다음 envelope를 따릅니다.

```json
{
  "success": true,
  "data": {}
}
```

실패 응답은 `exceptions.handlers.error_payload()` 기준으로 통일합니다.

```json
{
  "success": false,
  "error": {
    "code": "BAD_REQUEST",
    "message": "Invalid request.",
    "detail": []
  },
  "request_id": "req_xxx"
}
```

FastAPI 기본 validation error인 `422`는 `400 BAD_REQUEST`로 변환합니다.

## 설정

Backend 설정은 프로젝트 루트의 `.env`를 기준으로 로드합니다. 다른 파일을 사용하려면 `ENV_FILE` 환경 변수를 지정합니다.

주요 환경 변수:

| 변수 | 기본값 | 설명 |
|---|---|---|
| `ENV` | `development` | 실행 환경 |
| `APP_NAME` | `MileDay` | FastAPI app 이름 |
| `API_HOST` | `127.0.0.1` | backend host |
| `API_PORT` | `8000` | backend port |
| `SUPABASE_URL` | 없음 | Supabase project URL |
| `SUPABASE_ANON_KEY` | 없음 | Supabase anon key |
| `SUPABASE_SERVICE_ROLE_KEY` | 없음 | backend 전용 service role key |
| `SUPABASE_DB_URL` | 없음 | DB 연결 문자열 |
| `CORS_ORIGINS` | localhost dev origins | 허용할 frontend origin 목록 |
| `LOG_LEVEL` | `INFO` | 로그 레벨 |
| `LOG_DIR` | `logs` | 로그 저장 위치 |
| `ENABLE_INTEGRATION_TESTS` | `false` | 실제 Supabase 통합 테스트 활성화 여부 |

민감 정보는 frontend에 두지 않습니다.

## 실행

프로젝트 루트에서 backend만 실행하려면 다음 명령을 사용합니다.

```powershell
$env:PYTHONPATH="backend\app"
cd backend\app
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

전체 개발 환경은 루트 스크립트를 사용합니다.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\dev.ps1
```

`scripts/dev.ps1`은 backend `/health`, `/health/db`를 확인한 뒤 frontend dev server를 실행합니다.

## Health Check

| Endpoint | 인증 | 설명 |
|---|---|---|
| `GET /health` | 불필요 | FastAPI 서버 상태 확인 |
| `GET /health/db` | 불필요 | Supabase DB 연결 상태 확인 |

`/health/db`는 Supabase 설정 또는 DB 접근 문제가 있으면 `503 SERVICE_UNAVAILABLE`을 반환합니다.

## 테스트

기본 backend 포함 테스트:

```powershell
pytest
```

backend coverage gate 포함 테스트:

```powershell
pytest -c pytest-backend.ini
```

실제 Supabase test project를 사용하는 integration test:

```powershell
pytest -m integration
```

주의:

- 기본 `pytest`는 `integration` marker를 제외합니다.
- integration test는 실제 Supabase test credential이 필요합니다.
- `ENABLE_INTEGRATION_TESTS=true`일 때는 `TEST_EMAIL`, `TEST_PASSWORD`, `TEST_USER_ID`, `SUPABASE_SERVICE_ROLE_KEY` 등 안전장치 환경 변수가 필요합니다.

## 보안 기준

- Frontend는 Supabase에 직접 접근하지 않습니다.
- Frontend에는 service role key, DB URL, DB password를 저장하지 않습니다.
- Backend는 JWT의 `sub`에서 현재 사용자 ID를 얻습니다.
- Repository query에는 현재 사용자 조건을 포함합니다.
- Supabase RLS는 DB 레벨의 추가 보안 경계로 유지합니다.
- 로그에는 password, access token, refresh token, Authorization header 원문을 남기지 않습니다.

## 구현 시 주의 사항

- 새 endpoint는 `Router -> Service -> Repository` 흐름을 유지합니다.
- Router에 DB query나 복잡한 비즈니스 규칙을 넣지 않습니다.
- 새 request/response body는 `app/schemas/`에 Pydantic 모델로 정의합니다.
- 도메인 오류는 `app/exceptions/`에 추가하고 공통 handler를 통해 응답합니다.
- 사용자 소유 데이터는 항상 `user_id` 조건으로 제한합니다.
- Future 범위 기능은 명시 요청 없이 실제 동작을 확장하지 않습니다.
