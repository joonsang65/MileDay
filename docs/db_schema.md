# MileDay - DB 스키마 정의

## 문서 메타데이터

- Notion 페이지: DB 스키마 정의
- 마일스톤: M0.계획하기
- 상태: 완료
- 스코프: 구조 정의
- 타입: SPEC, DESIGN
- 기준 시점: 2026-07-01

## DB 구성

MileDay의 DB는 Supabase PostgreSQL을 사용한다.

초기 MVP 기준 핵심 구조는 다음과 같다.

```text
auth.users
  └── goals
        └── milestones
```

## 1. Supabase Auth

사용자 계정 정보는 Supabase Auth에서 관리한다.

### 주요 역할

- 이메일/비밀번호 회원가입
- 로그인
- JWT Access Token 발급
- Refresh Token 발급
- 사용자 ID 관리

FastAPI는 Supabase Auth에서 발급한 JWT를 검증하고, JWT의 sub 값을 사용자 ID로 사용한다.

## 2. goals 테이블

사용자가 생성한 목표를 저장한다.

### 주요 필드

| 필드 | 설명 | 타입 | 비고 |
|---|---|---|---|
| id (PK) | 목표 고유 ID | uuid | default: gen_random_uuid() |
| user_id (FK) | 목표를 생성한 사용자 ID | uuid | auth.users.id 참조 |
| title | 목표 제목 | text | - |
| deadline | 목표 마감일 | date | - |
| is_recurring | 반복 여부 | boolean | default: FALSE |
| recurrence_type | 반복 유형 | text | default: None / 매일, 매주 등 |
| color | 목표 표시 색상 | text | HEX 형식 |
| created_at | 생성 시각 | timestamptz | now() |
| updated_at | 수정 시각 | timestamptz | now() |

### 설계 메모

- 목표는 사용자별로 분리되어야 하므로 user_id를 반드시 포함한다.
- 목표별 색상은 개별 목표의 속성에 가까우므로 goals 테이블의 color 필드에서 관리한다.
- 반복 일정 기능은 MVP에서 제한적으로 다루거나 후순위로 둘 수 있지만, 향후 확장을 고려하여 is_recurring, recurrence_type 필드를 포함한다.

## 3. milestones 테이블

목표 하위의 세부 작업을 저장한다.

### 주요 필드

| 필드 | 설명 | 타입 | 비고 |
|---|---|---|---|
| id (PK) | 마일스톤 고유 ID | uuid | default: gen_random_uuid() |
| goal_id (FK) | 연결된 목표 ID | uuid | goals.id 참조 |
| user_id (FK) | 마일스톤을 생성한 사용자 ID | uuid | auth.users.id 참조 |
| title | 마일스톤 제목 | text | - |
| color | 마일스톤 표시 색상 | text | HEX 형식 |
| scheduled_date | 수행 예정일 | date | - |
| is_completed | 완료 여부 | boolean | default: FALSE |
| created_at | 생성 시각 | timestamptz | now() |
| updated_at | 수정 시각 | timestamptz | now() |

### 설계 메모

- 마일스톤은 특정 목표에 속하므로 goal_id를 가진다.
- 사용자별 접근 제한을 위해 user_id도 함께 저장한다.
- goal_id를 통해 목표와 연결하고, user_id를 통해 사용자별 데이터 조회 및 RLS 적용을 단순하게 처리한다.

## 4. user_settings 테이블

사용자별 앱 사용 설정 값을 저장한다.

### 주요 필드

| 필드 | 설명 | 타입 | 비고 |
|---|---|---|---|
| user_id (PK, FK) | 사용자 ID | uuid | auth.users.id 참조 |
| calendar_view | 기본 캘린더 표시 기준 | text | 예: monthly, weekly |
| theme | 화면 테마 | text | 예: light, dark, system |
| accent_color | 기본 강조 색상 | text | 예: #4F46E5 |
| font_family | 글꼴 설정 | text | 예: Pretendard, Arial |
| font_size | 기본 글자 크기 | integer | 예: 14 |
| ai_suggestion | AI 추천 컴포넌트 사용 여부 | boolean | default: FALSE |
| holiday_display | 공휴일 표시 방식 | text | 예: normal, weekend_like, hidden |
| week_starts_on | 주 시작 요일 | integer | 0=일요일, 1=월요일 |
| completed_milestones | 완료된 마일스톤 표시 여부 | boolean | default: TRUE |
| default_goal_color | 목표 기본 색상 | text | 새 목표 생성 시 기본값 |
| default_milestone_color | 마일스톤 기본 색상 | text | 새 마일스톤 생성 시 기본값 |
| language | 언어 설정 | text | 예: ko, en |
| timezone | 사용자 시간대 | text | 예: Asia/Seoul |
| created_at | 생성 시각 | timestamptz | now() |
| updated_at | 수정 시각 | timestamptz | now() |

### 설계 메모

- 사용자별 앱 설정 값을 저장한다.
- 캘린더 표시 기준, 테마, 글꼴, 공휴일 표시 방식, AI 추천 컴포넌트 사용 여부처럼 계정 기준으로 유지되어야 하는 설정을 관리한다.
- 사용자 1명당 설정 데이터는 1개만 필요하므로 user_id를 PK로 사용한다.
- 목표별 색상은 사용자 전체 설정이 아니라 개별 목표의 속성이므로 goals.color에서 관리한다.

## 5. external_calendar_connections 테이블

외부 캘린더 연동 정보를 저장한다.

이 테이블은 M8.Future 범위이다.

### 주요 필드

| 필드 | 설명 | 타입 | 비고 |
|---|---|---|---|
| id (PK) | 외부 캘린더 연동 고유 ID | uuid | default: gen_random_uuid() |
| user_id (FK) | 사용자 ID | uuid | auth.users.id 참조 |
| provider | 외부 캘린더 제공자 | text | 예: google, apple, samsung |
| account_email | 연동된 외부 계정 이메일 | text | 외부 계정 식별용 |
| is_enabled | 연동 사용 여부 | boolean | default: TRUE |
| sync_status | 동기화 상태 | text | 예: active, paused, error |
| last_synced_at | 마지막 동기화 시각 | timestamptz | nullable |
| created_at | 생성 시각 | timestamptz | now() |
| updated_at | 수정 시각 | timestamptz | now() |

### 설계 메모

- 외부 캘린더 연동 정보를 저장하는 테이블이다.
- 초기 MVP에서는 외부 캘린더 연동을 제외하지만, 향후 확장을 고려하여 별도 테이블로 분리한다.
- 사용자는 여러 외부 캘린더를 연동할 수 있으므로 user_id 하나에 여러 연동 정보가 연결될 수 있는 구조로 설계한다.
- access_token, refresh_token 같은 민감한 인증 정보는 일반 설정값처럼 저장하지 않고, 실제 구현 시 암호화 저장 또는 별도 보안 저장 방식을 검토한다.

## 6. 앱 내부 로컬 저장 값

Electron 앱 내부에는 사용자 계정 기준이 아니라 현재 PC 환경에 종속되는 설정 값을 저장한다.

### 로컬 저장 값 - Electron Store 기준

| 항목 | 설명 | 비고 |
|---|---|---|
| window_x | 창의 X 좌표 | 모니터 위치에 따라 달라짐 |
| window_y | 창의 Y 좌표 | 모니터 위치에 따라 달라짐 |
| window_width | 창 너비 | PC 화면 크기에 종속 |
| window_height | 창 높이 | PC 화면 크기에 종속 |
| always_on_top | 항상 위 표시 여부 | 위젯 창 동작 설정 |
| opacity | 창 투명도 | 모니터/사용 환경별 설정 |
| launch_on_startup | Windows 시작 시 자동 실행 여부 | 해당 PC의 시작 프로그램 설정 |
| last_selected_date | 마지막으로 선택한 날짜 | 단순 UI 상태 |
| last_opened_month | 마지막으로 열었던 월 | 단순 UI 상태 |
| sidebar_collapsed | 사이드바 접힘 여부 | 현재 화면 구성 상태 |
| widget_layout | 위젯 내부 레이아웃 | 창 크기와 화면 환경에 영향 받음 |

### 설계 메모

- 로컬 저장 값은 로그인 계정이 아니라 현재 사용 중인 PC 환경에 종속되는 값이다.
- 창 위치, 창 크기, 투명도, 항상 위 표시 여부, Windows 시작 시 자동 실행 여부는 모니터 구성이나 운영체제 환경에 따라 달라질 수 있으므로 DB가 아니라 앱 내부에 저장한다.
- Electron에서는 로컬 저장소를 통해 관리 가능하다.
- 로컬 저장 값은 다른 PC로 자동 동기화되지 않지만, 현재 데스크톱 위젯 환경을 유지하는 데 적합하다.

## 7. RLS

Supabase PostgreSQL에는 RLS를 적용한다.

RLS는 사용자가 본인 데이터만 접근할 수 있도록 제한하는 역할을 한다.

### 기본 정책

```sql
auth.uid() = user_id
```

로그인한 사용자의 ID와 데이터의 user_id가 일치할 때만 CRUD 동작이 가능하도록 설정한다.

FastAPI에서도 JWT를 검증하고 user_id를 기준으로 데이터를 처리하지만, DB 레벨에서도 RLS를 적용하여 이중으로 보호한다.

### RLS 적용 대상

- goals
- milestones
- user_settings
- external_calendar_connections
