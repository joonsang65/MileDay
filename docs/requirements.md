# MileDay - 요구사항 명세 및 마일스톤 DB 정리

## 문서 메타데이터

- Notion 데이터베이스: 요구사항 명세 및 마일스톤
- 상위 페이지: 마일스톤 계획 및 개발 환경 정의
- 기준 시점: 2026-06-30

> 주의: Notion DB 전체 행 조회는 도구 제한으로 완전히 가져오지 못했다. 아래에는 데이터베이스 스키마, 마일스톤 옵션, 검색으로 확인된 행, 그리고 다른 설계 문서에서 확인된 요구사항을 통합해 Codex용으로 정리했다. 구현 전 Notion DB를 CSV로 Export해서 추가 context로 넣으면 가장 안전하다.

## 1. 데이터베이스 스키마

| 속성 | 타입 | 설명 |
|---|---|---|
| ID | title | 요구사항 ID |
| 기능명 | text | 기능 이름 |
| 기능상세 | text | 기능 상세 설명 |
| 대상 | select | 사용자 / 시스템 등 요구사항 대상 |
| 마일스톤 | select | M1~M9 또는 스코프/비고 |
| 분류 | text | 요구사항 분류 |

## 2. 대상 옵션

- 대상
- 사용자
- 시스템

## 3. 마일스톤 옵션

- 스코프/비고
- M1
- M2
- M3
- M4
- M5
- M6
- M7
- M8
- M9

## 4. 검색으로 확인된 요구사항 행

| ID | 확인된 내용 | 비고 |
|---|---|---|
| DB-01 | 목표와 마일스톤 데이터는 Supabase Postgres에 저장된다. | 검색 결과에서 확인 |
| DB-02 | goals 테이블은 목표 제목, 마감일, 반복 여부, 반복 유형을 저장한다. | 검색 결과에서 확인 |
| BE-07 | API 응답 통일 | 검색 결과에서 확인 |
| INT-01 | 사용자는 Google Calendar 계정을 연결하여 MileDay의 목표 또는 마일스톤 일정을 Google Calendar와 동기화할 수 있다. | Future 범위로 해석 |
| INT-04 | Google Calendar API, Apple/iCloud Calendar, CalDAV, ICS export, Android Calendar Provider 중 MileDay에 적합한 연동 방식을 검토한다. | Future 범위로 해석 |

## 5. 설계 문서 기반 요구사항 재구성

### Auth / 사용자 관리

- 로그인 시스템으로 사용자를 관리한다.
- 회원가입, 로그인, 로그아웃 기능을 구현한다.
- Supabase Auth를 사용한다.
- Supabase Auth에서 발급한 JWT를 FastAPI가 검증한다.
- JWT의 sub 값을 user_id로 사용한다.
- 사용자 정보 기반 RLS 동작을 검증한다.

### Goal / 목표 관리

- 사용자가 직접 목표를 생성하고 관리한다.
- 목표 CRUD를 구현한다.
- 목표에는 제목, 마감일, 반복 여부, 반복 유형, 색상 필드가 포함된다.
- 목표별 색상은 goals.color에서 관리한다.
- 반복 일정 기능은 MVP에서 제한적으로 구현하거나 후순위로 둘 수 있다.

### Milestone / 마일스톤 관리

- 목표 안에는 세부 마일스톤을 둔다.
- 마일스톤 CRUD를 구현한다.
- 마일스톤은 goal_id로 목표에 연결된다.
- 마일스톤에도 user_id를 저장하여 사용자별 접근 제한을 단순화한다.
- 마일스톤에는 제목, 색상, 수행 예정일, 완료 여부가 포함된다.
- 완료 여부 변경 기능을 구현한다.

### Calendar / Today List

- TODO와 마일스톤은 캘린더에서 확인할 수 있어야 한다.
- 날짜를 선택하면 해당 날짜에 사용자가 설정한 내용을 확인할 수 있어야 한다.
- 캘린더 아래에 오늘 할 일 리스트를 확인할 수 있어야 한다.
- 월간 캘린더 렌더링, 날짜별 상세 조회, Today List 조회 API를 구현한다.

### Widget / Electron Desktop

- 앱은 Windows에서 실행되는 Electron 기반 데스크톱 위젯 앱이다.
- MileDay.exe 실행으로 접근한다.
- Main Process는 창 생성, 크기 조정, 위치 저장, 실행 위치 복원, Windows 시작 시 자동 실행 설정, 로컬 위젯 설정을 담당한다.
- Preload Script는 Main Process와 React Renderer를 안전하게 연결한다.
- React Renderer는 캘린더, Today List, 목표 폼, 마일스톤 폼, 설정 화면을 표시한다.
- 창 위치, 창 크기, 항상 위 표시 여부 등 PC 환경에 종속되는 값은 로컬 저장소에 저장한다.

### Settings / 사용자 설정

- 설정 화면은 직관적으로 구성한다.
- 계정 기준 설정은 user_settings 테이블에 저장한다.
- 캘린더 표시 기준, 테마, 강조 색상, 글꼴, 글자 크기, AI 추천 컴포넌트 사용 여부, 공휴일 표시 방식, 주 시작 요일, 완료된 마일스톤 표시 여부, 기본 목표 색상, 기본 마일스톤 색상, 언어, 시간대를 관리한다.
- PC 환경 기준 설정은 Electron Store에 저장한다.

### Backend / API

- FastAPI 기반 백엔드를 구현한다.
- 프론트엔드 요청은 백엔드가 관리한다.
- 프론트엔드는 Supabase에 직접 접근하지 않는다.
- FastAPI는 Supabase Client를 통해 Supabase Auth와 PostgreSQL에 접근한다.
- API Router Layer, Service Layer, Infrastructure Layer로 분리한다.
- 인증, 권한, 비즈니스 로직, 예외 처리, 로깅을 백엔드에서 담당한다.
- API 응답 형식은 success/data 또는 success/error 형태로 통일한다.

### DB / 보안

- DB는 Supabase PostgreSQL을 사용한다.
- 목표, 마일스톤, 사용자 설정 테이블로 구분한다.
- RLS를 적용해서 사용자 간 데이터가 섞이지 않도록 한다.
- 기본 RLS 정책은 auth.uid() = user_id이다.
- FastAPI에서도 JWT 검증과 user_id 기반 데이터 처리를 수행하여 이중으로 보호한다.

### Logging / Error

- 동작 과정에서 에러가 발생하는 부분을 로그로 확인 가능하게 설정한다.
- 로그인 실패, JWT 검증 실패, 권한 없는 데이터 접근, 목표 생성 실패, 마일스톤 수정 실패, Supabase 연결 오류, 예상하지 못한 서버 오류를 로깅한다.
- FE에는 사용자가 이해할 수 있는 메시지를 반환하고, 자세한 원인은 백엔드 로그에서 확인한다.

### Future / 확장 기능

- 외부 캘린더 연동은 MVP 이후 기능으로 분리한다.
- Google Calendar, Apple/iOS Calendar, Galaxy/Samsung Calendar 연동을 검토한다.
- 초기에는 양방향 동기화보다 MileDay에서 외부 캘린더로 내보내는 단방향 연동부터 검토한다.
- AI 일정 도우미는 MVP 이후 기능이다.
- 자연어 기반 일정 수정, AI 마일스톤 후보 생성, 미완료 작업 자동 리스케줄링, 마감일 기반 일정 재배치 제안을 고려한다.
- 모바일 앱은 추후 연동 가능성을 고려한다.
