# MileDay Codex Context Guide

이 폴더는 Notion에 정리된 MileDay 프로젝트 문서를 Codex에게 전달하기 위한 Markdown context 패키지이다.

## 권장 투입 순서

Codex에게 한 번에 모든 파일을 넣기보다, 작업 종류에 따라 아래 순서로 넣는 것을 권장한다.

### 1. 프로젝트 전체 이해가 필요한 경우
1. `01_project_problem_and_scope.md`
2. `02_milestone_plan_and_dev_env.md`
3. `03_tech_stack.md`
4. `04_db_schema.md`
5. `05_service_architecture.md`
6. `06_api_spec.md`
7. `07_requirements_database.md`

### 2. 백엔드/FastAPI 구현을 시킬 경우
1. `01_project_problem_and_scope.md`
2. `03_tech_stack.md`
3. `04_db_schema.md`
4. `05_service_architecture.md`
5. `06_api_spec.md`
7. `07_requirements_database.md`

Codex에게는 다음과 같이 지시하면 좋다.

```text
아래 Markdown 문서들은 MileDay 프로젝트의 설계 context이다.
문서에 없는 기능은 임의로 확장하지 말고, MVP 범위와 Future 범위를 구분해서 구현해줘.
특히 프론트엔드는 Supabase에 직접 접근하지 않고, 모든 데이터 요청은 FastAPI를 통해 처리해야 한다.
RLS, JWT 검증, user_id 기반 데이터 접근 원칙을 반드시 지켜줘.
```

### 3. 프론트엔드/Electron 구현을 시킬 경우
1. `01_project_problem_and_scope.md`
2. `02_milestone_plan_and_dev_env.md`
3. `03_tech_stack.md`
4. `05_service_architecture.md`
5. `06_api_spec.md`

Codex에게는 다음과 같이 지시하면 좋다.

```text
MileDay는 Windows 데스크톱에서 실행되는 Electron + React + TypeScript + Vite 기반 위젯형 플래너 앱이다.
React Renderer는 UI와 API Client를 담당하고, Main Process는 창 생성/크기/위치/자동 실행/로컬 설정을 담당한다.
운영체제 기능은 Preload Script를 통해 제한적으로 연결하고, React Renderer가 직접 Node/Electron 기능에 접근하지 않도록 구현해줘.
```

### 4. DB/마이그레이션 구현을 시킬 경우
1. `04_db_schema.md`
2. `03_tech_stack.md`
3. `05_service_architecture.md`
4. `07_requirements_database.md`

Codex에게는 다음과 같이 지시하면 좋다.

```text
Supabase PostgreSQL 기준으로 migrations SQL을 작성해줘.
goals, milestones, user_settings, external_calendar_connections는 user_id를 가지고, RLS 기본 정책은 auth.uid() = user_id로 설계해줘.
초기 MVP에서는 external_calendar_connections는 Future 범위로 분리하고, goals/milestones/user_settings를 우선 구현해줘.
```

## Context 사용 원칙

- 문서에 명시된 MVP 범위를 우선한다.
- AI 일정 도우미, 외부 캘린더 연동, 모바일 앱은 Future 범위로 본다.
- 프론트엔드는 Supabase service role key, DB URL, DB Password를 절대 보유하지 않는다.
- 모든 데이터 요청은 FastAPI 백엔드를 통해 처리한다.
- FastAPI는 Supabase Auth JWT를 검증하고, JWT의 sub 값을 user_id로 사용한다.
- DB 레벨에서는 RLS로 사용자별 데이터 접근을 제한한다.
- 로컬 PC 환경에 종속되는 설정은 Electron Store 등 로컬 저장소에 저장한다.
- 계정 기준 설정은 user_settings 테이블에 저장한다.

## 누락 검증 메모

노션에서 주요 페이지 본문은 가져왔지만, `요구사항 명세 및 마일스톤` 데이터베이스의 전체 행 조회는 도구 제한으로 완전히 열람하지 못했다. 검색으로 확인된 항목과 데이터베이스 스키마는 `07_requirements_database.md`에 정리했다. 구현 전 Notion DB의 전체 CSV 또는 Export를 한 번 더 Codex context에 추가하면 가장 안전하다.
