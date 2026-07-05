# MileDay Codex 작업 규칙

이 문서는 Codex가 MileDay 코드 생성을 진행할 때 반드시 따라야 하는 기준을 정리한 문서임

Notion의 개발 작업 계획서를 Codex 실행 지침으로 압축한 문서이며, 구현 중 임의 확장이나 구조 변경을 막기 위한 기준으로 사용함

## 1. 프로젝트 기준

- MileDay는 Windows 데스크톱에서 동작하는 Electron 기반 위젯형 플래너 앱임
- 사용자는 목표를 만들고, 목표 하위에 마일스톤을 만들고, 캘린더와 Today List에서 일정을 확인함
- 초기 MVP는 목표, 마일스톤, 캘린더, 사용자 설정, 로그인, 위젯 창 기본 동작 구현에 집중함
- 외부 캘린더 연동, AI 일정 도우미, 모바일 앱 연동은 Future 범위로 분리함
- Future 범위 코드는 사용자가 명시적으로 요청하지 않으면 실제 구현하지 않음

## 2. 전체 아키텍처

```text
Electron + React + TypeScript + Vite
        -> FastAPI
        -> Supabase PostgreSQL / Supabase Auth
```

- Frontend는 Supabase에 직접 접근하지 않음
- 모든 데이터 요청은 FastAPI API를 통해 처리함
- FastAPI는 인증, 권한, 비즈니스 로직, 예외 처리, 로깅, Supabase 접근을 담당함
- Supabase PostgreSQL은 goals, milestones, user_settings 등 사용자별 데이터를 저장함
- Supabase Auth는 회원가입, 로그인, Access Token, Refresh Token 발급을 담당함
- Supabase RLS는 DB 레벨에서 사용자별 데이터 접근을 제한함

## 3. 기술 스택

### Frontend / Desktop

- Electron을 사용해 Windows 데스크톱 앱과 위젯 창을 구현함
- React를 사용해 캘린더, Today List, 목표, 마일스톤, 설정 UI를 구현함
- TypeScript를 사용해 API 응답, Goal, Milestone, Settings 타입을 명확히 정의함
- Vite와 electron-vite 기반 구조를 사용함
- Tailwind CSS를 사용해 작은 위젯 화면에 맞는 UI를 구성함
- Zustand를 사용해 선택 날짜, 현재 월, 로그인 상태, 모달 상태 등 가벼운 전역 상태를 관리함
- date-fns를 사용해 날짜 계산, 월간 캘린더 생성, `YYYY-MM-DD` 포맷 처리를 수행함

### Backend

- Python + FastAPI 기반으로 구현함
- Pydantic을 사용해 요청과 응답 schema를 정의함
- python-dotenv 또는 프로젝트의 설정 모듈을 사용해 환경 변수를 관리함
- Python logging 기반으로 콘솔 로그와 파일 로그를 남김
- Supabase Python Client 기반으로 Supabase Auth와 PostgreSQL에 접근함

### Database / Auth

- Supabase PostgreSQL을 사용함
- Supabase Auth JWT를 단일 인증 기준으로 사용함
- FastAPI에서 별도 자체 JWT를 발급하지 않음
- SQL migration으로 테이블, RLS, 트리거 변경 이력을 관리함

## 4. 구현 범위 기준

### MVP에 포함함

- 회원가입, 로그인, 로그아웃, 현재 사용자 조회
- Supabase Auth JWT 검증
- 목표 CRUD
- 마일스톤 CRUD
- 마일스톤 완료 여부 변경
- 월간 캘린더 조회
- 날짜 상세 조회
- Today List 조회
- 사용자 설정 조회, 생성, 수정
- Electron 위젯 창 위치, 크기, 항상 위, 자동 실행 같은 로컬 설정 관리
- 공통 예외 처리와 로그 구조
- request_id 기반 요청 추적

### Future로 분리함

- 외부 캘린더 연동
- AI 마일스톤 생성
- AI 일정 추천
- 자연어 일정 수정
- 자동 리스케줄링
- 모바일 앱 연동
- 고급 위젯 투명도, 듀얼 모니터 위치 복원 등 복잡한 위젯 고도화

## 5. 데이터 모델 기준

### 핵심 구조

```text
auth.users
  -> goals
      -> milestones

auth.users
  -> user_settings
```

### goals

- 사용자가 생성한 목표를 저장함
- 반드시 `user_id`를 포함함
- `user_id`는 클라이언트가 보낸 값을 사용하지 않고 JWT의 `sub` 값으로 서버에서 설정함
- 목표별 색상은 `goals.color`에서 관리함
- 반복 일정 확장을 고려해 `is_recurring`, `recurrence_type` 필드를 둘 수 있음

주요 필드:

- `id`
- `user_id`
- `title`
- `deadline`
- `is_recurring`
- `recurrence_type`
- `color`
- `created_at`
- `updated_at`

### milestones

- 목표 하위의 세부 작업을 저장함
- 반드시 `goal_id`와 `user_id`를 함께 포함함
- 마일스톤 생성 전 `goal_id`가 현재 사용자의 목표인지 확인함
- 캘린더 조회는 `milestones.scheduled_date`를 기준으로 처리함

주요 필드:

- `id`
- `goal_id`
- `user_id`
- `title`
- `color`
- `scheduled_date`
- `is_completed`
- `created_at`
- `updated_at`

### user_settings

- 사용자 계정 기준으로 유지되어야 하는 설정을 저장함
- 사용자 1명당 설정 row는 1개만 필요하므로 `user_id`를 PK로 사용함

주요 필드:

- `user_id`
- `calendar_view`
- `theme`
- `accent_color`
- `font_family`
- `font_size`
- `ai_suggestion`
- `holiday_display`
- `week_starts_on`
- `completed_milestones`
- `default_goal_color`
- `default_milestone_color`
- `language`
- `timezone`
- `created_at`
- `updated_at`

### external_calendar_connections

- Future 범위임
- 초기 MVP에서는 실제 동기화 로직을 구현하지 않음
- access_token, refresh_token 같은 민감 정보는 일반 설정값처럼 저장하지 않음
- 실제 구현 시 암호화 저장 또는 별도 보안 저장 방식을 검토함

## 6. 로컬 저장 기준

현재 PC와 모니터 환경에 종속되는 값은 DB가 아니라 Electron 로컬 저장소에 저장함

로컬 저장 대상:

- `window_x`
- `window_y`
- `window_width`
- `window_height`
- `always_on_top`
- `opacity`
- `launch_on_startup`
- `last_selected_date`
- `last_opened_month`
- `sidebar_collapsed`
- `widget_layout`

이 값들은 로그인 계정이 아니라 현재 PC 환경에 종속되므로 다른 PC로 자동 동기화하지 않음

## 7. 인증 및 권한 기준

- 인증 기준은 Supabase Auth에서 발급한 JWT Access Token임
- 인증이 필요한 API는 `Authorization: Bearer <access_token>` 헤더를 요구함
- FastAPI는 요청마다 JWT를 검증함
- JWT의 `sub` 값을 현재 사용자의 `user_id`로 사용함
- 클라이언트가 전달한 `user_id`는 신뢰하지 않음
- 데이터 생성 시 `current_user.id`를 서버에서 직접 `user_id`로 설정함
- 조회, 수정, 삭제 시 항상 `user_id = current_user.id` 조건을 포함함
- 다른 사용자의 데이터 접근 시도는 데이터 존재 여부를 숨기기 위해 `404 NOT_FOUND`로 처리함
- RLS 기본 정책은 `auth.uid() = user_id` 기준으로 적용함

인증 없이 접근 가능한 API:

- `GET /health`
- `POST /auth/signup`
- `POST /auth/login`

인증이 필요한 API:

- `POST /auth/logout`
- `GET /auth/me`
- `/goals`
- `/milestones`
- `/calendar`
- `/settings`
- Future 범위의 `/external-calendars`
- Future 범위의 `/ai`

## 8. Backend 계층 기준

FastAPI 코드는 다음 책임 분리를 우선함

```text
Router -> Service -> Repository / Infrastructure -> Supabase
```

- Router는 Path, Query, Body를 받고 Service를 호출함
- Router는 비즈니스 규칙을 직접 처리하지 않음
- Service는 비즈니스 규칙, 권한 검증, 데이터 소유 여부 검증을 담당함
- Repository 또는 Infrastructure는 Supabase 요청과 외부 서비스 연결을 담당함
- Global Exception Handler는 Custom Exception을 공통 ErrorResponse로 변환함
- Middleware는 request_id 생성, 요청 시간 측정, 공통 로그 context 관리를 담당함

## 9. API 공통 규칙

- 요청 본문은 JSON을 기본으로 사용함
- `Content-Type: application/json`을 사용함
- 날짜 값은 `YYYY-MM-DD` 형식을 사용함
- 생성 시각과 수정 시각은 timestamptz 기준 ISO 형식을 사용함
- 성공 응답은 `{ "success": true, "data": ... }` 형식을 사용함
- 실패 응답은 공통 ErrorResponse 형식을 사용함
- Frontend는 `VITE_API_BASE_URL`로 API 서버 주소를 관리함
- Local 기본 주소는 `http://localhost:8000`임
- Production 기본 주소는 `https://api.mileday.com` 기준으로 문서화함

## 10. API 엔드포인트 기준

### Auth

- `POST /auth/signup`
- `POST /auth/login`
- `POST /auth/logout`
- `GET /auth/me`

### Goals

- `GET /goals`
- `GET /goals/{goal_id}`
- `POST /goals`
- `PATCH /goals/{goal_id}`
- `DELETE /goals/{goal_id}`

### Milestones

- `GET /milestones`
- `GET /goals/{goal_id}/milestones`
- `GET /milestones/{milestone_id}`
- `POST /goals/{goal_id}/milestones`
- `PATCH /milestones/{milestone_id}`
- `PATCH /milestones/{milestone_id}/completion`
- `DELETE /milestones/{milestone_id}`

### Calendar

- `GET /calendar/monthly`
- `GET /calendar/weekly`
- `GET /calendar/dates/{date}`
- `GET /calendar/today`

MVP에서는 월간 캘린더, 날짜 상세, Today List를 우선 구현함

### Settings

- `GET /settings`
- `POST /settings`
- `PATCH /settings`

### Future

- `GET /external-calendars`
- `POST /external-calendars/{provider}/connect`
- `DELETE /external-calendars/{connection_id}`
- `POST /external-calendars/{connection_id}/sync`
- `GET /external-calendars/{connection_id}/status`
- `POST /ai/milestones/generate`
- `POST /ai/schedule/suggest`
- `POST /ai/schedule/edit`
- `POST /ai/schedule/reschedule`

Future API는 사용자가 명시적으로 요청하지 않으면 mock 또는 실제 구현을 추가하지 않음

## 11. 기능별 처리 기준

### 목표 생성

- FE는 `title`, `deadline`, `is_recurring`, `recurrence_type`, `color`만 전달함
- BE는 JWT를 검증하고 `current_user.id`를 추출함
- BE는 request body를 검증함
- BE는 `current_user.id`를 `goals.user_id`로 설정함
- 저장 후 목표 목록과 캘린더 표시 데이터가 갱신될 수 있는 응답을 반환함

### 목표 조회, 수정, 삭제

- 항상 `id = goal_id AND user_id = current_user.id` 조건을 사용함
- 권한이 없거나 존재하지 않으면 `404 NOT_FOUND`로 처리함

### 마일스톤 생성

- 생성 전 `goal_id`가 현재 사용자의 목표인지 확인함
- 목표 소유자가 현재 사용자가 아니면 `404 NOT_FOUND`로 처리함
- 저장 시 `goal_id`와 `current_user.id`를 함께 저장함

### 마일스톤 조회, 수정, 삭제, 완료 처리

- 항상 `id = milestone_id AND user_id = current_user.id` 조건을 사용함
- 완료 여부 변경은 `is_completed` 값만 명확히 변경함

### 캘린더 조회

- `milestones.scheduled_date`를 기준으로 날짜별 작업을 묶음
- 모든 조회 조건에 `user_id = current_user.id`를 포함함
- 화면에서 별도 계산을 줄이기 위해 goal title, milestone title, color, completion 상태를 함께 내려줄 수 있음

### 사용자 설정

- 설정 조회 시 row가 없으면 기본값 응답 또는 기본 row 생성 기준을 명확히 유지함
- 설정 수정은 현재 사용자의 `user_settings.user_id`에 대해서만 수행함
- 창 위치, 창 크기, 자동 실행 같은 PC 환경 값은 user_settings에 저장하지 않음

## 12. 예외 처리 기준

예외 처리는 Router에서 직접 `HTTPException`을 남발하지 않고, Custom Exception을 던진 뒤 Global Exception Handler에서 공통 응답으로 변환함

공통 실패 응답:

```json
{
  "success": false,
  "error": {
    "code": "GOAL_CREATE_FAILED",
    "message": "목표를 생성하지 못했습니다",
    "detail": "Goal insert failed"
  },
  "request_id": "req_20260705_abcd1234"
}
```

필드 기준:

- `success`는 실패 시 `false`로 고정함
- `error.code`는 Frontend 메시지 매핑 기준으로 사용함
- `error.message`는 기본 사용자 안내 메시지임
- `error.detail`은 개발자 확인용 상세 원인임
- `request_id`는 요청 추적용 고유 ID임

HTTP Status 기준:

- 입력값 누락 또는 잘못된 입력은 `400 BAD_REQUEST`로 통일함
- FastAPI Validation Error 기본 422는 `400 BAD_REQUEST`로 변환함
- 인증 정보 없음 또는 JWT 오류는 `401 UNAUTHORIZED`로 처리함
- 권한 없는 데이터 접근은 `404 NOT_FOUND`로 처리함
- 현재 사용자 기준 리소스 없음은 `404 NOT_FOUND`로 처리함
- 중복 데이터는 `409 CONFLICT`로 처리함
- Supabase Auth 또는 외부 서비스 장애는 `502 BAD_GATEWAY`로 처리함
- 외부 서비스 일시 장애는 필요 시 `503 SERVICE_UNAVAILABLE`로 처리함
- 예상하지 못한 서버 오류는 `500 INTERNAL_SERVER_ERROR`로 처리함

## 13. 에러 코드 기준

에러 코드는 대문자 스네이크 케이스를 사용함

공통 코드:

- `BAD_REQUEST`
- `UNAUTHORIZED`
- `NOT_FOUND`
- `CONFLICT`
- `INTERNAL_SERVER_ERROR`
- `EXTERNAL_SERVICE_ERROR`

Auth:

- `AUTH_INVALID_CREDENTIALS`
- `AUTH_TOKEN_EXPIRED`
- `AUTH_INVALID_TOKEN`
- `AUTH_USER_NOT_FOUND`
- `AUTH_LOGOUT_FAILED`

Goal:

- `GOAL_NOT_FOUND`
- `GOAL_CREATE_FAILED`
- `GOAL_UPDATE_FAILED`
- `GOAL_DELETE_FAILED`
- `GOAL_INVALID_DEADLINE`

Milestone:

- `MILESTONE_NOT_FOUND`
- `MILESTONE_CREATE_FAILED`
- `MILESTONE_UPDATE_FAILED`
- `MILESTONE_DELETE_FAILED`
- `MILESTONE_INVALID_SCHEDULED_DATE`

Calendar:

- `CALENDAR_INVALID_MONTH`
- `CALENDAR_INVALID_DATE`
- `CALENDAR_QUERY_FAILED`

Settings:

- `SETTINGS_NOT_FOUND`
- `SETTINGS_UPDATE_FAILED`
- `SETTINGS_INVALID_VALUE`

Future:

- `EXTERNAL_CALENDAR_PROVIDER_UNSUPPORTED`
- `EXTERNAL_CALENDAR_AUTH_FAILED`
- `EXTERNAL_CALENDAR_SYNC_FAILED`
- `EXTERNAL_CALENDAR_TOKEN_ERROR`
- `AI_REQUEST_INVALID`
- `AI_PROVIDER_FAILED`
- `AI_SUGGESTION_FAILED`
- `AI_RESULT_REQUIRES_CONFIRMATION`

## 14. 로그 기준

- 모든 요청에 `request_id`를 부여함
- `request_id`는 Middleware에서 생성함
- 클라이언트가 `X-Request-ID`를 보내면 재사용할 수 있음
- 응답 Header에 `X-Request-ID`를 포함함
- 에러 응답 body에도 `request_id`를 포함함
- 모든 로그에 `request_id`를 포함함

로그 포함 정보:

- `timestamp`
- `level`
- `request_id`
- `method`
- `path`
- `status_code`
- `user_id`
- `error_code`
- `message`
- `duration_ms`

로그에 남기지 않는 정보:

- `password`
- `access_token`
- `refresh_token`
- `Authorization` header 원문
- 외부 캘린더 토큰
- AI 요청 원문 전체

마스킹 기준:

- `password`는 `[MASKED]`
- `access_token`은 `[MASKED]`
- `refresh_token`은 `[MASKED]`
- `authorization`은 `[MASKED]`
- `email`은 `no***@gmail.com` 형태로 마스킹함
- `ai_prompt`는 기본적으로 `[OMITTED]` 처리함

로그 레벨:

- `INFO`: 서버 시작, 서버 종료, 로그인 성공, 주요 생성/수정 성공, 배치성 동기화 완료
- `WARNING`: 로그인 실패, JWT 검증 실패, 권한 없는 데이터 접근 시도, 잘못된 입력 반복
- `ERROR`: DB 저장 실패, Supabase 요청 실패, 외부 캘린더 API 실패, AI Provider 실패
- `CRITICAL`: 서버 부팅 실패, 필수 환경 변수 누락, DB 연결 불가

성공 로그는 큰 단위 이벤트만 남김

- 서버 시작은 기록함
- 로그인 성공은 기록함
- 목표 생성 성공은 기록함
- 마일스톤 생성 성공은 기록함
- 사용자 설정 수정 성공은 기록함
- 단순 조회 성공은 기록하지 않음
- 캘린더 조회 성공은 기본적으로 기록하지 않음

파일 로그 기준:

- 콘솔과 파일 로그를 함께 사용함
- 파일 로그는 날짜별로 분리함
- 최근 7일 보관을 기본으로 함
- 일정 용량 초과 시 회전 처리함
- 민감 정보는 저장하지 않거나 마스킹함

Electron 로컬 로그:

- 사용자 PC에도 최근 7일 기준 로컬 앱 로그를 남김
- 네트워크 연결 실패, API Base URL 설정 오류, 토큰 저장 실패, Electron Store 저장 실패, Frontend 예외를 확인하기 위함
- 로컬 로그에도 민감 정보는 저장하지 않음

## 15. 환경 변수 기준

Frontend에는 백엔드 API 주소만 둠

```text
VITE_API_BASE_URL=http://localhost:8000
```

Frontend에 저장하면 안 되는 값:

- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_DB_URL`
- `SUPABASE_DB_PASSWORD`

Backend에는 Supabase 연결 정보와 로그 설정을 둠

```text
SUPABASE_URL=your_supabase_project_url
SUPABASE_ANON_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key
SUPABASE_DB_URL=your_supabase_postgres_connection_string
LOG_LEVEL=INFO
ENV=development
```

관리 원칙:

- `.env` 파일은 Git에 올리지 않음
- `.env.example`에는 필요한 변수 이름만 공유함
- 프론트엔드에는 공개 가능한 값만 저장함
- 백엔드 민감 정보는 배포 환경에서 안전하게 관리함

## 16. 구현 전 확인 규칙

Codex는 구현 전에 다음을 확인해야 함

- 현재 코드의 라우터 prefix와 문서 기준 API가 다르면 사용자에게 알리고 정렬 방향을 제안함
- 문서 기준은 `/external-calendars`이며 `calender` 같은 오타성 이름은 새 코드에서 확산하지 않음
- 문서 기준은 `/calendar`이며 기존 코드에 `calender`가 있으면 수정 범위를 명확히 확인함
- 문서 기준 완료 처리 API는 `/milestones/{milestone_id}/completion`임
- 기존 코드가 mock 응답 중심이면 실제 구현 시 Service Layer 분리를 우선함
- 보호 API에는 JWT 검증 dependency를 적용함
- DB 접근에는 항상 현재 사용자 기준 조건을 포함함
- RLS 정책과 Backend 권한 검증을 둘 다 유지함
- Future 범위 기능은 사용자가 명시적으로 요청하지 않으면 실제 구현하지 않음

## 17. Codex 금지 사항

- Frontend에서 Supabase에 직접 접근하는 코드를 만들지 않음
- Frontend에 Supabase service role key, DB URL, DB password를 두지 않음
- 클라이언트가 전달한 `user_id`를 신뢰하지 않음
- 다른 사용자 데이터 접근 실패를 `403`으로 노출하지 않음
- FastAPI Validation Error를 기본 422로 방치하지 않음
- Router에 비즈니스 로직을 과도하게 넣지 않음
- 예외마다 응답 형식을 다르게 만들지 않음
- 로그에 password, token, Authorization header 원문을 남기지 않음
- 단순 조회 성공 로그를 과도하게 남기지 않음
- MVP 범위를 넘어 외부 캘린더, AI, 모바일 기능을 임의로 구현하지 않음
- 사용자가 요청하지 않은 대규모 리팩터링을 진행하지 않음

## 18. Codex 작업 시 우선순위

1. Notion 설계와 이 문서 기준을 먼저 따름
2. 기존 코드 구조와 네이밍을 확인함
3. 문서 기준과 코드가 충돌하면 충돌 내용을 사용자에게 알림
4. MVP 범위를 우선 구현함
5. 인증, 권한, RLS, 로그, 예외 처리 기준을 보존함
6. 작은 단위로 구현하고 검증 가능한 테스트 또는 실행 확인을 남김
7. Future 기능은 확장 가능한 구조만 남기고 실제 동작은 요청 시 구현함

