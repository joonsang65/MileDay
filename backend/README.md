# MileDay Backend

MileDay 백엔드는 Electron/React 프론트엔드와 Supabase 사이에 있는 FastAPI REST API 서버다. 프론트엔드는 Supabase에 직접 접근하지 않고, 백엔드는 Supabase Auth JWT를 검증한 뒤 현재 사용자 기준으로 Goal, Milestone, Calendar, Settings, AI 일정 초안 요청을 처리한다.

## 역할

- FastAPI 기반 REST API 제공
- Supabase Auth 토큰 검증과 사용자별 접근 제한
- Goal, Milestone, Calendar, Settings 비즈니스 로직 처리
- Gemini API 기반 AI 일정 초안 생성
- Supabase transient 오류에 대한 제한적 재시도와 공통 예외 응답 처리

## 구조

```text
app/api/routers
  -> app/services
  -> app/repositories 또는 app/infrastructure
  -> Supabase / Gemini
```

| 계층 | 책임 |
|---|---|
| `app/api/routers/` | HTTP endpoint, request/response schema 연결, dependency 주입 |
| `app/services/` | 사용자 권한 기준, 비즈니스 규칙, 캐시와 검증 |
| `app/repositories/` | Supabase PostgreSQL 테이블 조회와 변경 |
| `app/infrastructure/` | Gemini 같은 외부 API client |
| `app/schemas/` | Pydantic 요청/응답 모델 |
| `app/exceptions/` | 기능별 예외와 공통 에러 응답 변환 |
| `app/core/` | 설정, 인증 dependency, logging, middleware, Supabase client |

## 주요 API

| 영역 | 라우터 | 기능 |
|---|---|---|
| Auth | `app/api/routers/auth.py` | 회원가입, 로그인, 로그아웃, 현재 사용자, 계정 삭제 |
| Goals | `app/api/routers/goals.py` | 목표 CRUD, 완료 처리, 목표+마일스톤 통합 조회 |
| Milestones | `app/api/routers/milestones.py` | 마일스톤 CRUD, 오늘 할 일, 완료 처리 |
| Calendar | `app/api/routers/calender.py` | 월간, 주간, 날짜 상세 조회 |
| Settings | `app/api/routers/settings.py` | 사용자 설정 조회/수정 |
| AI | `app/api/routers/schedule_assistant.py` | AI 일정 초안 생성 |

상세 API 계약은 [docs/api_spec.md](../docs/api_spec.md)를 함께 본다. 현재 구현 기준의 대표 endpoint는 `/goals`, `/goals/with-milestones`, `/calendar/month`, `/calendar/week`, `/calendar/date/{target_date}`, `/settings`, `/ai/schedule/draft`다.

## AI 일정 초안 생성

AI 일정 생성은 `POST /ai/schedule/draft`에서 시작한다.

```text
사용자 자연어 요청
  -> Gemini Structured Output
  -> JSON parsing
  -> deterministic validation
  -> editable draft 반환
  -> 사용자 확인/수정
  -> 기존 Goal/Milestone API로 저장
```

관련 파일:

- `app/api/routers/schedule_assistant.py`
- `app/services/ai_schedule_service.py`
- `app/infrastructure/gemini_client.py`
- `app/schemas/ai_schedule_schemas.py`

현재 구조에서 AI는 DB를 직접 수정하지 않는다. Gemini는 목표 제목, 마감일, 마일스톤 제목과 날짜, 계획 강도와 선호 요일을 포함한 초안을 반환하고, 백엔드는 다음 항목을 검증한다.

| 검증 항목 | 코드상 failure/warning |
|---|---|
| 목표 제목 비어 있음 | `EMPTY_GOAL_TITLE` |
| 마감일 형식 오류 또는 오늘 이전/당일 | `INVALID_DEADLINE`, `DEADLINE_NOT_FUTURE` |
| 마일스톤 없음 또는 제목 비어 있음 | `NO_MILESTONES`, `EMPTY_MILESTONE_TITLE` |
| 마일스톤 날짜 형식 오류 | `INVALID_MILESTONE_DATE` |
| 마일스톤이 마감일 이후 | `MILESTONE_AFTER_DEADLINE` |
| 가능 날짜 밖 추천 | `MILESTONE_OUTSIDE_AVAILABILITY` |
| 같은 제목+날짜 중복 | `DUPLICATE_MILESTONE` |
| 계획 강도/선호 요일 형식 오류 | `INVALID_INTENSITY`, `INVALID_PREFERRED_DAYS` |
| 선호 요일 미반영 | `PREFERRED_DAYS_NOT_REFLECTED` warning |

응답에는 편집 가능한 `client_id`, `selected` 필드와 `create_goal_payload` 미리보기가 포함된다. 저장은 프론트엔드에서 사용자가 `일정에 추가`를 선택한 뒤 기존 목표/마일스톤 생성 API를 호출하는 흐름이다.

## 안정성 보강

[docs/performance_report._v3.md](../docs/performance_report._v3.md) 기준으로 현재 코드에서 확인되는 보강은 다음과 같다.

- Supabase Auth 호출은 retryable 오류에 한해 최대 3회 재시도하고, 100ms/300ms backoff를 적용한다.
- Auth 재시도 전 기본 Supabase client cache를 reset해 깨진 연결 재사용 가능성을 줄인다.
- Supabase DB read는 `execute_supabase_read()`로 retryable 오류를 재시도할 수 있다.
- `/settings` 조회는 사용자별 60초 TTL cache를 사용한다.
- `/calendar/month`는 최근 성공한 월간 조회 결과를 60초 cache에 보관하고, 조회 실패 시 fallback으로 반환할 수 있다.
- 공통 middleware는 `X-Request-ID`를 응답 header에 포함하고 로그 context를 유지한다.

## 개발 실행

루트에서 백엔드와 프론트엔드를 함께 실행하려면 다음 명령을 사용한다.

```powershell
.\dev.cmd
```

백엔드만 실행할 때는 `backend/app`에서 실행한다.

```powershell
cd backend\app
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

의존성은 루트 `requirements.txt`를 사용한다.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

필수 환경 변수는 루트 `.env.example`을 기준으로 설정한다. AI 일정 초안을 사용하려면 `GEMINI_API_KEY`도 필요하다.

## 테스트

백엔드 테스트는 루트에서 실행한다.

```powershell
pytest
```

`pytest.ini`는 `tests/`를 대상으로 하고, `integration` marker는 기본 제외한다. 통합 테스트가 필요할 때는 실제 Supabase 프로젝트 환경 변수를 준비한 뒤 marker 조건을 별도로 지정한다.
