# M5. 캘린더 UI 및 날짜별 조회 구현

## 문서 목적

M5 단계에서는 사용자가 월간/주간 캘린더, Today List, 날짜 상세 화면에서 목표와 마일스톤 일정을 확인하고 완료 상태를 변경할 수 있도록 구현한다.
M3의 목표 관리와 M4의 마일스톤 관리 구현 결과를 기반으로 하며, 반복 목표는 이미 날짜별 `milestones` row로 생성되어 있다는 전제를 사용한다.

현재 저장소의 구현 표면은 FastAPI 백엔드가 중심이므로, 이 문서는 백엔드 API 구현 기준과 이후 프론트엔드 UI 구현 기준을 함께 정리한다.

## 기준 문서

| 문서 | 확인 내용 |
| --- | --- |
| `docs/requirements.md` | M5 요구사항 BE-05, CAL-01~CAL-07, TODO-01~TODO-04, VIEW-01~VIEW-03 |
| `docs/api_spec.md` | Calendar API, Today List API, 날짜 상세 응답 형식 |
| `docs/data_flow.md` | 캘린더 조회 흐름, Today List 갱신 흐름 |
| `docs/db_schema.md` | `goals.deadline`, `milestones.scheduled_date` 기준 |
| `docs/milestones/m3_goal_management.md` | 반복 목표 처리 기준 |
| `docs/milestones/m4_milestone_management.md` | 마일스톤 CRUD와 Today List 구현 기준 |

## M5 요구사항 범위

| ID | 분류 | 기능 | 구현 기준 |
| --- | --- | --- | --- |
| BE-05 | 백엔드 | 날짜별 조회 API 제공 | 특정 월/주/날짜의 목표 마감일과 마일스톤을 함께 조회 |
| CAL-01 | 캘린더 | 월간 캘린더 표시 | 월 단위 날짜 격자와 일정 표시 데이터 제공 |
| CAL-02 | 캘린더 | 주간 캘린더 표시 | 주 단위 날짜 목록과 일정 표시 데이터 제공 |
| CAL-03 | 캘린더 | 이전/다음 달 이동 | `year`, `month` 또는 기준 날짜 query로 이동 가능 |
| CAL-04 | 캘린더 | 오늘 날짜 강조 | 응답에 오늘 날짜 판별이 가능하도록 날짜 값을 명확히 제공 |
| CAL-05 | 캘린더 | 선택 날짜 표시 | 선택 날짜 상세 API와 UI 상태로 처리 |
| CAL-06 | 캘린더 | 목표 마감일 표시 | `goals.deadline` 기준으로 날짜별 목표 표시 |
| CAL-07 | 캘린더 | 마일스톤 예정일 표시 | `milestones.scheduled_date` 기준으로 날짜별 마일스톤 표시 |
| TODO-01 | Today List | 오늘의 마일스톤 표시 | 오늘 `scheduled_date`인 마일스톤 목록 조회 |
| TODO-02 | Today List | 부모 목표 표시 | Today List 각 항목에 `goal_title` 포함 |
| TODO-03 | Today List | 오늘 할 일 완료 처리 | M4의 마일스톤 완료 처리 API 사용 |
| TODO-04 | Today List | 빈 상태 표시 | 오늘 예정 마일스톤이 없으면 빈 배열 반환, UI에서 빈 상태 표시 |
| VIEW-01 | 날짜 상세 | 날짜별 목표 조회 | 특정 날짜가 `deadline`인 목표 조회 |
| VIEW-02 | 날짜 상세 | 날짜별 마일스톤 조회 | 특정 날짜가 `scheduled_date`인 마일스톤 조회 |
| VIEW-03 | 날짜 상세 | 날짜 상세 내 완료 처리 | M4의 완료 처리 API를 날짜 상세에서도 사용 |

## 구현 대상 API

현재 코드에는 `/calendar/month`, `/calendar/date/{date}`, `/milestones/today`가 존재한다.
문서 기준에는 `/calendar/monthly`, `/calendar/weekly`, `/calendar/dates/{date}`, `/calendar/today`도 언급되어 있어, M5에서 endpoint 기준을 정리해야 한다.

MVP에서는 기존 코드와 `api_spec.md`에 맞춰 다음 endpoint를 우선 사용한다.

| 기능 | Method | Endpoint | 구현 기준 |
| --- | --- | --- | --- |
| 월간 캘린더 조회 | GET | `/calendar/month?year={year}&month={month}` | 해당 월의 목표 마감일과 마일스톤 예정일 조회 |
| 날짜 상세 조회 | GET | `/calendar/date/{date}` | 해당 날짜의 목표와 마일스톤 조회 |
| 오늘 할 일 조회 | GET | `/milestones/today` | 오늘 예정 마일스톤 조회. M4 구현 사용 |
| 마일스톤 완료 처리 | PATCH | `/milestones/{milestone_id}/complete` | Today List와 날짜 상세에서 공통 사용 |

주간 캘린더는 M5 문서 범위에 포함하되, 현재 API 명세에 endpoint가 고정되어 있지 않으므로 다음 기준으로 후속 구현한다.

```text
GET /calendar/week?start_date=YYYY-MM-DD
```

## 데이터 조회 기준

캘린더 조회는 반복 규칙을 다시 계산하지 않는다.
M4에서 반복 목표가 날짜별 마일스톤으로 생성되므로, 캘린더는 다음 저장 데이터를 직접 조회한다.

| 데이터 | 날짜 기준 |
| --- | --- |
| 목표 | `goals.deadline` |
| 마일스톤 | `milestones.scheduled_date` |
| 오늘 할 일 | `milestones.scheduled_date = today` |

모든 조회는 현재 사용자 ID를 기준으로 제한한다.

```text
goals.user_id = current_user.id
milestones.user_id = current_user.id
```

## 권장 응답 구조

월간 캘린더 응답은 UI가 날짜별 표시를 쉽게 할 수 있도록 평면 목록과 날짜별 요약을 함께 고려한다.
현재 schema는 `goals`, `milestones` 목록을 반환하지만, M5 구현 시 날짜별 요약 필드를 추가하면 프론트 계산을 줄일 수 있다.

권장 구조:

```json
{
  "success": true,
  "data": {
    "year": 2026,
    "month": 7,
    "days": [
      {
        "date": "2026-07-10",
        "is_today": false,
        "goal_count": 1,
        "milestone_count": 2,
        "completed_milestone_count": 1,
        "goals": [],
        "milestones": []
      }
    ]
  }
}
```

날짜 상세 응답은 해당 날짜의 목표와 마일스톤을 함께 반환한다.
마일스톤에는 부모 목표 제목을 포함한다.

```json
{
  "success": true,
  "data": {
    "date": "2026-07-10",
    "goals": [],
    "milestones": [
      {
        "id": "uuid",
        "goal_id": "uuid",
        "goal_title": "포트폴리오 준비",
        "title": "이력서 초안 작성",
        "color": "#F97316",
        "scheduled_date": "2026-07-10",
        "is_completed": false
      }
    ]
  }
}
```

Today List는 `/milestones/today`를 사용하되, M5에서는 부모 목표 제목 포함이 필요하다.
현재 M4 마일스톤 응답은 `goal_title`을 포함하지 않으므로, M5 구현 시 join/select 기준을 보강한다.

## 백엔드 구현 계획

1. `CalendarRepository` 추가
2. 월 범위 계산 helper 추가
3. 주 범위 계산 helper 추가
4. 날짜 문자열 검증 helper 추가
5. 현재 사용자 기준 목표 마감일 조회 구현
6. 현재 사용자 기준 마일스톤 예정일 조회 구현
7. 마일스톤 응답에 부모 목표 제목 포함
8. `/calendar/month` placeholder 제거
9. `/calendar/date/{date}` placeholder 제거
10. 필요 시 `/calendar/week` 추가
11. Today List 응답에 `goal_title` 포함하도록 M4 service/repository 확장
12. 캘린더/날짜 상세/Today List 테스트 작성

## 프론트엔드 UI 구현 기준

프론트엔드가 추가될 때는 다음 기준을 따른다.

- 첫 화면은 실제 캘린더와 Today List가 보이는 작업 화면이어야 한다.
- 월간 캘린더는 날짜 셀 안에서 목표 마감일과 마일스톤 예정일을 구분해 표시한다.
- 주간 캘린더는 한 주의 날짜별 일정을 빠르게 스캔할 수 있어야 한다.
- 오늘 날짜와 선택 날짜는 서로 다른 상태로 시각적으로 구분한다.
- 날짜 클릭 시 날짜 상세 영역이 갱신된다.
- Today List와 날짜 상세에서 마일스톤 완료 상태를 바로 변경할 수 있어야 한다.
- 오늘 예정 마일스톤이 없을 경우 빈 상태 메시지를 표시한다.
- 반복 목표는 별도 반복 규칙 UI로 다시 계산하지 않고, 생성된 마일스톤 목록 기준으로 표시한다.

## 입력값 검증 기준

| 항목 | 검증 기준 |
| --- | --- |
| `year` | 1 이상의 정수 |
| `month` | 1~12 정수 |
| `date` | `YYYY-MM-DD` 형식의 실제 날짜 |
| `start_date` | 주간 조회 기준 날짜. `YYYY-MM-DD` 형식 |
| 인증 | 모든 캘린더/Today List API는 현재 사용자 ID 필요 |

잘못된 월 또는 날짜 요청은 `BAD_REQUEST` 또는 캘린더 전용 오류 코드로 처리한다.

## 예외 처리 기준

| 상황 | Error Code | HTTP Status |
| --- | --- | --- |
| 잘못된 월 조회 조건 | `CALENDAR_INVALID_MONTH` | 400 |
| 잘못된 날짜 형식 | `CALENDAR_INVALID_DATE` | 400 |
| 캘린더 조회 실패 | `CALENDAR_QUERY_FAILED` | 500 |
| 인증 누락 | `UNAUTHORIZED` | 401 |
| 마일스톤 완료 처리 대상 없음 | `MILESTONE_NOT_FOUND` | 404 |

## 테스트 계획

| 테스트 범위 | 검증 내용 |
| --- | --- |
| 월간 조회 | 월 시작일/마지막일 범위로 목표와 마일스톤 조회 |
| 월간 조회 | 현재 사용자 데이터만 반환 |
| 월간 조회 | 잘못된 month 값은 400 반환 |
| 날짜 상세 | 특정 날짜의 목표와 마일스톤 반환 |
| 날짜 상세 | 마일스톤에 부모 목표 제목 포함 |
| 날짜 상세 | 잘못된 날짜 형식은 400 반환 |
| Today List | 오늘 예정 마일스톤만 반환 |
| Today List | 빈 결과는 빈 배열로 반환 |
| 완료 처리 | 날짜 상세와 Today List에서 같은 완료 처리 API 사용 |
| 반복 일정 | 반복 목표에서 생성된 마일스톤이 캘린더에 일반 마일스톤처럼 표시 |
| repository | Supabase query에 `user_id`, 날짜 범위 조건 적용 |

## 완료 기준

- 캘린더 API가 더 이상 placeholder 응답을 반환하지 않는다.
- 월간 캘린더 조회가 현재 사용자 기준 목표 마감일과 마일스톤 예정일을 반환한다.
- 날짜 상세 조회가 해당 날짜의 목표와 마일스톤을 반환한다.
- Today List가 오늘 예정 마일스톤과 부모 목표 제목을 반환한다.
- 완료 처리는 M4 마일스톤 완료 API와 동일한 동작을 사용한다.
- 반복 목표로 생성된 마일스톤이 캘린더와 날짜 상세에 별도 계산 없이 표시된다.
- 기본 `pytest`가 통과하고 coverage 90% 이상을 유지한다.

## 구현 결과

M5 백엔드 범위는 다음과 같이 구현했다.

| 파일 | 구현 내용 |
| --- | --- |
| `backend/app/repositories/calendar.py` | 현재 사용자 기준 목표 마감일과 마일스톤 예정일을 월 범위 또는 특정 날짜로 조회하는 repository 추가 |
| `backend/app/services/calendar_service.py` | 월 시작일/마지막일 계산, 날짜별 요약 생성, 목표/마일스톤 집계, `goal_title` 평탄화 구현 |
| `backend/app/api/routers/calender.py` | placeholder 응답 제거, `/calendar/month`, `/calendar/week`, `/calendar/date/{target_date}`를 인증 사용자 기준 service 호출로 변경 |
| `backend/app/schemas/calendar_schemas.py` | 월간 `days` 요약, 날짜 상세 `goals`, `milestones`, 집계 필드 응답 DTO 추가 |
| `backend/app/repositories/milestones.py` | Today List 조회 시 부모 목표 제목을 함께 가져오도록 `goals(title)` select 적용 |
| `backend/app/services/milestone_service.py` | Today List 응답에서 Supabase join 결과를 `goal_title`로 평탄화 |
| `backend/app/schemas/milestone_schemas.py` | Today List에서 부모 목표 제목을 내려줄 수 있도록 `goal_title` optional 필드 추가 |
| `tests/test_calendar_repository.py` | Supabase query의 `user_id`, 날짜 범위, 특정 날짜 필터 검증 |
| `tests/test_calendar_service.py` | 월간/주간 날짜 요약, 날짜 상세, 완료 수 집계, `goal_title` 평탄화, 타 사용자 데이터 제외 검증 |
| `tests/test_app_routes.py` | 캘린더 API 인증 필수 조건과 service 호출 응답 검증 |

반복 목표는 M4 기준대로 이미 생성된 `milestones.scheduled_date`를 조회한다.
M5 캘린더 구현은 반복 규칙을 다시 계산하지 않는다.

검증 결과:

```text
56 passed, 1 deselected
Total coverage: 95.89%
```

## 프론트엔드 구현 결과

M5 UI 범위는 별도 `frontend/` 패키지로 구현했다.
기존 백엔드 파일과 충돌하지 않도록 루트 설정은 변경하지 않았다.

| 파일 | 구현 내용 |
| --- | --- |
| `frontend/package.json` | Electron + React + TypeScript + Vite 실행 스크립트와 의존성 정의 |
| `frontend/electron.vite.config.ts` | Electron main/preload/renderer 빌드 설정 |
| `frontend/electron/main.ts` | Windows 데스크톱 앱 창 생성, 최소 창 크기 설정 |
| `frontend/electron/preload.ts` | renderer에 최소 platform 정보만 노출 |
| `frontend/src/api/client.ts` | FastAPI 전용 API client, 로그인, 캘린더 조회, Today List, 완료 처리 구현 |
| `frontend/src/store/calendarStore.ts` | Zustand 기반 표시 모드, 선택 날짜, 표시 날짜 상태 관리 |
| `frontend/src/App.tsx` | 로그인 상태, 월간/주간 캘린더, 날짜 상세, Today List 데이터 흐름 연결 |
| `frontend/src/components/*` | 로그인, 캘린더 헤더, 캘린더 보드, 날짜 상세, Today List 컴포넌트 구현 |
| `frontend/src/styles.css` | Tailwind 기반 기본 스타일과 실제 화면 레이아웃 정의 |
| `frontend/src/**/*.test.*` | 날짜 계산, API client, 캘린더 보드 동작 테스트 작성 |

프론트엔드는 Supabase에 직접 접근하지 않고 `VITE_API_BASE_URL`의 FastAPI만 호출한다.
`SUPABASE_SERVICE_ROLE_KEY`, DB URL, DB password 같은 민감 정보는 프론트엔드에 두지 않는다.

프론트엔드 검증 결과:

```text
npm test
3 test files passed
7 tests passed

npm run build
electron-vite build passed
```

## 개발 실행 자동화

루트 경로에서 백엔드와 프론트엔드 개발 서버를 순서대로 실행할 수 있도록 `scripts/dev.ps1`을 추가했다.

동작 순서:

1. `http://127.0.0.1:8000/health`를 먼저 확인한다.
2. 이미 백엔드가 실행 중이면 새 백엔드를 띄우지 않는다.
3. 백엔드가 실행 중이 아니면 `backend/app`에서 `python -m uvicorn main:app --reload`를 숨김 프로세스로 시작한다.
4. health check가 성공할 때까지 대기한다.
5. 성공하면 `frontend`로 이동해 `npm run dev`를 실행한다.
6. 스크립트가 직접 띄운 백엔드는 종료 시 프로세스 트리까지 함께 정리한다.

현재 개발 셸에 `ELECTRON_RUN_AS_NODE=1`이 설정되어 있으면 Electron이 앱 런타임이 아니라 Node 모드로 실행되어 `electron.app`이 비어 있을 수 있다.
이를 막기 위해 `frontend/scripts/dev.mjs`와 `scripts/dev.ps1`에서 dev 실행 전 `ELECTRON_RUN_AS_NODE`를 제거한다.

실행 명령:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\dev.ps1
```

옵션:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\dev.ps1 -BackendHost 127.0.0.1 -BackendPort 8000 -HealthTimeoutSeconds 30
```

백엔드 로그:

```text
logs/dev_backend.out.log
logs/dev_backend.err.log
```
