# M6.5. 목표와 마일스톤 생성 UI

## 문서 목적

M6.5 단계에서는 M3, M4에서 구현된 목표/마일스톤 생성 API를 Electron 프론트엔드에 연결한다.
M5와 M6에서 만든 캘린더 위젯은 조회, 날짜 상세, Today List, 완료 처리 중심이었기 때문에 사용자가 앱 안에서 새 목표나 마일스톤을 만들 수 없었다.
이 문서는 생성 UI의 범위, API 연결 기준, 검증 기준을 정의한다.

## 기준 문서

| 문서 | 확인 내용 |
| --- | --- |
| `docs/api_spec.md` | `POST /goals`, `POST /goals/{goal_id}/milestones`, `GET /goals` |
| `docs/milestones/m3_goal_management.md` | 목표 생성/수정/삭제 백엔드 기준 |
| `docs/milestones/m4_milestone_management.md` | 마일스톤 생성/완료 처리 백엔드 기준 |
| `docs/milestones/m5_calendar_ui.md` | 캘린더 조회, 날짜 상세, Today List UI |
| `docs/milestones/m6_widget_auth_ui.md` | 위젯형 Electron UI 기준 |

## M6.5 요구사항 범위

| ID | 분류 | 기능 | 구현 기준 |
| --- | --- | --- | --- |
| CREATE-01 | 목표 | 목표 생성 UI | 제목, 마감일, 색상, 반복 여부, 반복 주기를 입력할 수 있다. |
| CREATE-02 | 목표 | 목표 생성 API 연동 | `POST /goals`를 호출하고 성공 시 캘린더를 다시 조회한다. |
| CREATE-03 | 목표 | 반복 설정 검증 | 반복 목표는 반복 주기를 반드시 포함하고, 반복이 아니면 `recurrence_type`을 `null`로 보낸다. |
| CREATE-04 | 마일스톤 | 마일스톤 생성 UI | 부모 목표, 제목, 예정일, 색상을 입력할 수 있다. |
| CREATE-05 | 마일스톤 | 마일스톤 생성 API 연동 | `POST /goals/{goal_id}/milestones`를 호출하고 성공 시 캘린더를 다시 조회한다. |
| CREATE-06 | 마일스톤 | 목표 목록 조회 | 마일스톤 생성 폼에서 선택할 목표 목록을 `GET /goals`로 조회한다. |
| CREATE-07 | UX | 선택 날짜 기본값 | 목표 마감일과 마일스톤 예정일은 현재 선택 날짜를 기본값으로 사용한다. |
| CREATE-08 | UX | 위젯형 화면 유지 | 별도 전체 화면 라우트로 이동하지 않고 현재 캘린더 위젯 안에서 생성한다. |
| CREATE-09 | UX | 오류 표시 | 생성 실패, 목표 목록 없음, 필수값 누락을 한글 메시지로 표시한다. |

## UI 배치 기준

생성 UI는 기존 사이드 패널 상단에 `빠른 추가` 패널로 배치한다.
위젯 화면의 밀도를 유지하기 위해 모달 대신 작은 패널과 탭 전환 방식을 사용한다.

구성:

- `목표` 탭
  - 제목
  - 마감일
  - 색상
  - 반복 여부
  - 반복 주기
- `마일스톤` 탭
  - 부모 목표 선택
  - 제목
  - 예정일
  - 색상

선택 날짜를 기준으로 기본값을 채우면 사용자는 캘린더에서 날짜를 클릭한 뒤 바로 일정을 추가할 수 있다.

## API 연동 기준

### 목표 목록 조회

```http
GET /goals
Authorization: Bearer access_token
```

성공 응답:

```json
{
  "success": true,
  "data": [
    {
      "id": "uuid",
      "title": "포트폴리오 준비",
      "deadline": "2026-07-31",
      "is_recurring": false,
      "recurrence_type": null,
      "color": "#0F766E"
    }
  ]
}
```

### 목표 생성

```http
POST /goals
Authorization: Bearer access_token
Content-Type: application/json
```

요청 본문:

```json
{
  "title": "포트폴리오 준비",
  "deadline": "2026-07-31",
  "is_recurring": false,
  "recurrence_type": null,
  "color": "#0F766E"
}
```

반복 목표 요청 본문:

```json
{
  "title": "운동",
  "deadline": "2026-07-31",
  "is_recurring": true,
  "recurrence_type": "daily",
  "color": "#0F766E"
}
```

### 마일스톤 생성

```http
POST /goals/{goal_id}/milestones
Authorization: Bearer access_token
Content-Type: application/json
```

요청 본문:

```json
{
  "title": "이력서 초안 작성",
  "scheduled_date": "2026-07-10",
  "color": "#D97706"
}
```

## 구현 계획

1. `frontend/src/api/types.ts`에 생성 요청 타입을 추가한다.
2. `frontend/src/api/client.ts`에 `listGoals`, `createGoal`, `createMilestone`을 추가한다.
3. `CreationPanel` 컴포넌트를 추가한다.
4. `App`에서 목표 목록 상태를 관리하고 캘린더 조회와 함께 최신 목표 목록을 가져온다.
5. 목표 생성 성공 시 생성 폼을 초기화하고 `loadCalendar()`를 다시 호출한다.
6. 마일스톤 생성 성공 시 생성 폼을 초기화하고 `loadCalendar()`를 다시 호출한다.
7. 목표 목록이 비어 있으면 마일스톤 생성 버튼을 비활성화하고 목표를 먼저 만들도록 안내한다.
8. 생성 관련 테스트를 추가한다.

## 테스트 계획

| 테스트 범위 | 검증 내용 |
| --- | --- |
| API client | `GET /goals`가 인증 헤더와 함께 호출되는지 검증 |
| API client | `POST /goals` 요청 본문이 백엔드 스키마와 일치하는지 검증 |
| API client | `POST /goals/{goal_id}/milestones` 요청 본문이 백엔드 스키마와 일치하는지 검증 |
| 생성 UI | 목표 탭에서 제목, 날짜, 색상을 입력하면 목표 생성 핸들러가 호출되는지 검증 |
| 생성 UI | 반복 체크 시 반복 주기가 payload에 포함되는지 검증 |
| 생성 UI | 마일스톤 탭에서 부모 목표와 예정일을 포함해 생성 핸들러가 호출되는지 검증 |
| 생성 UI | 목표가 없으면 마일스톤 생성 버튼이 비활성화되는지 검증 |
| 통합 흐름 | 생성 성공 후 캘린더와 목표 목록을 다시 조회하는지 검증 |

## 완료 기준

- 사용자가 프론트엔드에서 목표를 생성할 수 있다.
- 사용자가 프론트엔드에서 특정 목표 아래 마일스톤을 생성할 수 있다.
- 생성된 목표와 마일스톤이 캘린더와 날짜 상세에 다시 표시된다.
- 반복 목표 요청이 백엔드 검증 규칙과 일치한다.
- 목표가 없을 때 마일스톤 생성 UI가 잘못된 요청을 보내지 않는다.
- 프론트엔드 테스트, 빌드, 린트가 통과한다.
- 구현 중 추가한 주석은 한글로 작성한다.
