# MileDay - API 명세서

## 문서 메타데이터

- Notion 페이지: API 명세서
- 마일스톤: M0.계획하기
- 상태: 진행 중
- 스코프: 기능 범위
- 타입: SPEC, DESIGN
- 기준 시점: 2026-07-01

## 0. Postman 명세서 작성 방식

Postman에서 각 API 요청에는 다음 내용을 작성한다.

| 항목 | 작성 내용 |
| --- | --- |
| Name | API 이름. 예: 목표 생성 |
| Method | GET, POST, PATCH, DELETE |
| URL | {{base_url}}/goals |
| Authorization | Bearer Token |
| Headers | Content-Type: application/json |
| Body | Request JSON 예시 |
| Description | API 설명, 처리 기준, 주의사항 |
| Example Response | 성공/실패 응답 예시 |

---

### 0.1. Postman Environment 변수

Postman에서는 환경 변수를 사용하여 Local, Production 환경을 구분한다.

**[Local Environment]**

| 변수명 | 값 |
| --- | --- |
| base_url | http://localhost:8000 |
| access_token | 로그인 후 발급된 JWT |
| goal_id | 테스트용 목표 ID |
| milestone_id | 테스트용 마일스톤 ID |

## 1. API 명세서 개요

MileDay의 API 명세서는 프론트엔드 Electron/React 앱과 FastAPI 백엔드 간의 통신 규칙을 정의하기 위한 문서이다.

프론트엔드는 Supabase에 직접 접근하지 않고, 모든 데이터 요청을 FastAPI 서버로 전송한다. FastAPI는 Supabase Auth에서 발급한 JWT를 검증하고, JWT의 sub 값을 기준으로 사용자 ID를 추출하여 목표, 마일스톤, 사용자 설정 데이터를 처리한다.

API 명세서는 구현 전 설계 기준으로 먼저 작성하고, 실제 구현이 진행되면 Postman을 통해 요청/응답 예시와 테스트 결과를 갱신한다.

## 2. API 구분 기준

| 구분 | 설명 |
|---|---|
| Auth API | 회원가입, 로그인, 로그아웃, 현재 사용자 조회 |
| Goal API | 목표 생성, 조회, 수정, 삭제 |
| Milestone API | 마일스톤 생성, 조회, 수정, 삭제, 완료 처리 |
| Calendar API | 월간 캘린더, 날짜 상세, Today List 조회 |
| Settings API | 사용자 앱 설정 조회 및 수정 |
| Future API | 외부 캘린더 연동, AI 추천 기능 등 향후 확장 API |

## 3. 공통 규칙

### Base URL

| 환경 | Base URL |
|---|---|
| Local | http://localhost:8000 |
| Production | https://api.mileday.com |

프론트엔드에서는 `VITE_API_BASE_URL` 환경 변수를 통해 API 서버 주소를 관리한다.

### Authorization

로그인 이후 인증이 필요한 API는 Authorization Header에 Supabase Auth에서 발급받은 Access Token을 포함한다.

```http
Authorization: Bearer access_token
```

FastAPI는 요청 Header의 JWT를 검증하고, JWT의 sub 값을 현재 사용자의 user_id로 사용한다.
인증이 필요한 API는 기본적으로 현재 로그인한 사용자의 데이터만 조회, 생성, 수정, 삭제할 수 있다.

### Request Format

요청 본문은 기본적으로 JSON 형식을 사용한다.

```http
Content-Type: application/json
```

### Response Format

응답은 기본적으로 JSON 형식을 사용한다.

성공 응답 예시:

```json
{
  "success": true,
  "data": {
    "id": "uuid"
  }
}
```

### Error Response

오류 발생 시에는 공통된 형식의 에러 응답을 반환한다.

```json
{
  "success": false,
  "error": {
    "code": "UNAUTHORIZED",
    "message": "인증 정보가 유효하지 않습니다.",
    "detail": "Access token is missing or invalid."
  }
}
```

### 주요 에러 코드

| HTTP Status | Code | 설명 |
|---:|---|---|
| 400 | BAD_REQUEST | 요청 형식이 올바르지 않음 |
| 401 | UNAUTHORIZED | 인증 정보가 없거나 유효하지 않음 |
| 403 | FORBIDDEN | 접근 권한이 없음 |
| 404 | NOT_FOUND | 요청한 리소스를 찾을 수 없음 |
| 409 | CONFLICT | 중복 데이터 또는 충돌 발생 |
| 500 | INTERNAL_SERVER_ERROR | 서버 내부 오류 |

### Date Format

날짜 값은 `YYYY-MM-DD` 형식을 사용한다.

예시:

```text
2026-07-01
```

생성 시각과 수정 시각은 timestamptz 기준의 ISO 형식을 사용한다.

```text
2026-07-01T10:00:00+09:00
```

## 4. Auth API

사용자 회원가입, 로그인, 로그아웃, 현재 사용자 조회를 처리한다.

### Auth API 목록

| 기능 | Method | Endpoint | 인증 필요 | 설명 |
|---|---|---|---|---|
| 회원가입 | POST | /auth/signup | X | 이메일/비밀번호 기반 회원가입 |
| 로그인 | POST | /auth/login | X | Supabase Auth 로그인 요청 |
| 로그아웃 | POST | /auth/logout | O | 사용자 로그아웃 처리 |
| 현재 사용자 조회 | GET | /auth/me | O | JWT 기반 현재 사용자 정보 조회 |

### POST /auth/signup

사용자 이메일과 비밀번호를 기반으로 회원가입을 수행한다.

Request Body:

```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

Response Body:

```json
{
  "success": true,
  "data": {
    "user_id": "uuid",
    "email": "user@example.com"
  }
}
```

### POST /auth/login

사용자 이메일과 비밀번호를 기반으로 로그인한다.
FastAPI는 Supabase Auth에 로그인 요청을 전달하고, 발급된 Access Token과 Refresh Token을 프론트엔드에 반환한다.

Request Body:

```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

Response Body:

```json
{
  "success": true,
  "data": {
    "access_token": "jwt_access_token",
    "refresh_token": "refresh_token",
    "token_type": "bearer",
    "user": {
      "id": "uuid",
      "email": "user@example.com"
    }
  }
}
```

### POST /auth/logout

현재 사용자의 로그아웃을 처리한다.
클라이언트는 저장된 Access Token과 Refresh Token을 제거한다.

Response Body:

```json
{
  "success": true,
  "message": "로그아웃되었습니다."
}
```

### GET /auth/me

현재 JWT를 기준으로 로그인한 사용자 정보를 조회한다.

Response Body:

```json
{
  "success": true,
  "data": {
    "user_id": "uuid",
    "email": "user@example.com"
  }
}
```

## 5. Goal API

사용자가 생성한 목표 데이터를 관리한다.
목표 데이터는 goals 테이블에 저장되며, 모든 요청은 현재 로그인한 사용자의 user_id를 기준으로 처리한다.

### Goal API 목록

| 기능 | Method | Endpoint | 인증 필요 | 설명 |
|---|---|---|---|---|
| 목표 목록 조회 | GET | /goals | O | 현재 사용자의 목표 목록 조회 |
| 목표 상세 조회 | GET | /goals/{goal_id} | O | 특정 목표 상세 조회 |
| 목표 생성 | POST | /goals | O | 새 목표 생성 |
| 목표 수정 | PATCH | /goals/{goal_id} | O | 목표 정보 수정 |
| 목표 삭제 | DELETE | /goals/{goal_id} | O | 목표 삭제 |

### GET /goals

현재 사용자의 목표 목록을 조회한다.

Response Body:

```json
{
  "success": true,
  "data": [
    {
      "id": "uuid",
      "user_id": "uuid",
      "title": "AI 엔지니어 취업 준비",
      "deadline": "2026-09-30",
      "is_recurring": false,
      "recurrence_type": null,
      "color": "#4F46E5",
      "created_at": "2026-07-01T10:00:00+09:00",
      "updated_at": "2026-07-01T10:00:00+09:00"
    }
  ]
}
```

### GET /goals/{goal_id}

특정 목표의 상세 정보를 조회한다.

Path Parameter:

| 이름 | 타입 | 설명 |
|---|---|---|
| goal_id | uuid | 조회할 목표 ID |

Response Body:

```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "title": "AI 엔지니어 취업 준비",
    "deadline": "2026-09-30",
    "is_recurring": false,
    "recurrence_type": null,
    "color": "#4F46E5",
    "created_at": "2026-07-01T10:00:00+09:00",
    "updated_at": "2026-07-01T10:00:00+09:00"
  }
}
```

### POST /goals

새 목표를 생성한다.

Request Body:

```json
{
  "title": "AI 엔지니어 취업 준비",
  "deadline": "2026-09-30",
  "is_recurring": false,
  "recurrence_type": null,
  "color": "#4F46E5"
}
```

Response Body:

```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "title": "AI 엔지니어 취업 준비",
    "deadline": "2026-09-30",
    "is_recurring": false,
    "recurrence_type": null,
    "color": "#4F46E5",
    "created_at": "2026-07-01T10:00:00+09:00",
    "updated_at": "2026-07-01T10:00:00+09:00"
  }
}
```

### PATCH /goals/{goal_id}

특정 목표 정보를 수정한다.

Request Body:

```json
{
  "title": "AI 엔지니어 포트폴리오 준비",
  "deadline": "2026-10-15",
  "color": "#22C55E"
}
```

Response Body는 수정된 목표 객체를 반환한다.

### DELETE /goals/{goal_id}

특정 목표를 삭제한다.
목표 삭제 시 동일한 goal_id를 갖는 하위 마일스톤도 함께 삭제한다.
구현 방식은 DB의 `ON DELETE CASCADE` 또는 서비스 레이어의 명시적 삭제 중 하나로 통일한다.

## 6. Milestone API

목표 하위의 마일스톤 데이터를 관리한다.
마일스톤은 goal_id로 목표에 연결되고 user_id로 사용자 접근을 제한한다.

### Milestone API 목록

| 기능 | Method | Endpoint | 인증 필요 | 설명 |
|---|---|---|---|---|
| 목표 하위 마일스톤 목록 조회 | GET | /goals/{goal_id}/milestones | O | 특정 목표의 마일스톤 목록 조회 |
| 마일스톤 상세 조회 | GET | /milestones/{milestone_id} | O | 특정 마일스톤 상세 조회 |
| 마일스톤 생성 | POST | /goals/{goal_id}/milestones | O | 목표 하위 마일스톤 생성 |
| 마일스톤 수정 | PATCH | /milestones/{milestone_id} | O | 마일스톤 제목, 색상, 수행일 등 수정 |
| 마일스톤 삭제 | DELETE | /milestones/{milestone_id} | O | 마일스톤 삭제 |
| 마일스톤 완료 처리 | PATCH | /milestones/{milestone_id}/complete | O | 완료 여부 변경 |

### 권장 Request / Response 필드

Request Body 예시:

```json
{
  "title": "이력서 초안 작성",
  "color": "#F97316",
  "scheduled_date": "2026-07-05"
}
```

Response Body 예시:

```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "goal_id": "uuid",
    "user_id": "uuid",
    "title": "이력서 초안 작성",
    "color": "#F97316",
    "scheduled_date": "2026-07-05",
    "is_completed": false,
    "created_at": "2026-07-01T10:00:00+09:00",
    "updated_at": "2026-07-01T10:00:00+09:00"
  }
}
```

## 7. Calendar API

월간 캘린더, 날짜 상세, Today List 조회를 담당한다.

### Calendar API 목록

| 기능 | Method | Endpoint | 인증 필요 | 설명 |
|---|---|---|---|---|
| 월간 캘린더 조회 | GET | /calendar/month?year={year}&month={month} | O | 특정 월의 목표/마일스톤 표시 데이터 조회 |
| 날짜 상세 조회 | GET | /calendar/date/{date} | O | 특정 날짜의 목표/마일스톤 상세 조회 |
| 오늘 할 일 조회 | GET | /milestones/today | O | 오늘 수행 예정인 마일스톤 목록 조회 |

### 날짜 상세 조회 예시

```json
{
  "success": true,
  "data": {
    "date": "2026-07-01",
    "milestones": [
      {
        "id": "uuid",
        "goal_id": "uuid",
        "goal_title": "AI 엔지니어 취업 준비",
        "title": "이력서 초안 작성",
        "color": "#F97316",
        "is_completed": false
      }
    ]
  }
}
```

## 8. Settings API

사용자 계정 기준 앱 설정을 관리한다.
로컬 PC 환경에 종속되는 값은 Electron Store에 저장하고, 계정 기준 설정만 user_settings 테이블에 저장한다.

### Settings API 목록

| 기능 | Method | Endpoint | 인증 필요 | 설명 |
|---|---|---|---|---|
| 설정 조회 | GET | /settings | O | 현재 사용자의 앱 설정 조회 |
| 설정 수정 | PATCH | /settings | O | 현재 사용자의 앱 설정 수정 |

### 설정 필드 예시

- calendar_view
- theme
- accent_color
- font_family
- font_size
- ai_suggestion
- holiday_display
- week_starts_on
- completed_milestones
- default_goal_color
- default_milestone_color
- language
- timezone

## 9. Future API

초기 MVP에서는 구현하지 않는다.

### 외부 캘린더 연동

- Google Calendar
- Apple / iOS Calendar
- Galaxy / Samsung Calendar

### AI 추천 / AI 일정 도우미

- 자연어 기반 일정 수정
- 목표 입력 시 AI 마일스톤 후보 생성
- 미완료 작업 자동 리스케줄링
- 마감일 기반 일정 재배치 제안
