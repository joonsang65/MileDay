# MileDay - 사용 기술 정리

## 문서 메타데이터

- Notion 페이지: 사용 기술 정리
- 마일스톤: M0.계획하기
- 상태: 완료
- 스코프: 기능 범위
- 타입: DESIGN
- 기준 시점: 2026-07-01

## 1. 전체 기술 스택 방향

MileDay는 Windows 데스크톱에서 동작하는 위젯형 플래너 앱을 목표로 한다.

- 프론트엔드는 데스크톱 앱 실행과 위젯 창 제어에 적합한 기술을 선택한다.
- 백엔드는 추후 AI 기능 확장과 API 중심 구조를 고려한다.

### 아키텍처 개요

```text
Electron + React (Frontend)
        ↓
FastAPI (Backend)
        ↓
Supabase PostgreSQL / Supabase Auth
```

### 선택 이유

- 프론트엔드/백엔드 역할을 명확히 분리한다.
- Electron은 Windows 위젯형 데스크톱 앱 구현에 용이하다.
- FastAPI는 인증, 목표/마일스톤 관리, 로그 기록을 백엔드에서 통합 관리하기 좋다.
- Supabase PostgreSQL + RLS로 사용자별 데이터 분리가 가능하다.
- 백엔드를 분리하면 AI 마일스톤 생성, 자연어 일정 수정, 외부 캘린더 연동 등을 백엔드 중심으로 확장하기 쉽다.

## 2. Frontend / Desktop App

프론트엔드는 Electron + React + TypeScript + Vite 조합으로 구성한다.

| 구분 | 사용 기술 | 역할 | 선정 이유 |
|---|---|---|---|
| Desktop Framework | Electron | Windows 데스크톱 앱 실행 및 위젯 창 구현 | 창 위치 저장, 크기 조정, 항상 위 토글, 시작 시 자동 실행 등 위젯 앱 요구사항 대응 |
| UI Library | React | 캘린더, Today List, 목표/마일스톤 화면 | 컴포넌트 단위 개발에 적합하고 상태 변화가 많은 UI에 유리 |
| Language | TypeScript | 타입 안정성 확보 | Goal, Milestone, User, API Response 등의 타입을 명확히 정의 가능 |
| Build Tool | Vite | 개발 서버 및 빌드 | 구성이 단순하고 개발 서버가 빠름 |
| Electron Build Tool | electron-vite | main/preload/renderer 관리 | Electron + Vite 조합에서 구조를 명확히 하고 개발을 단순화 |
| Styling | Tailwind CSS | 위젯 UI 스타일링 | 작은 창에서 빠르게 레이아웃 구성, 스타일 일관성 확보 |
| State Management | Zustand | 전역 상태 관리 | 선택 날짜, 현재 월, 모달, 로그인 상태 등 가벼운 전역 상태에 적합 |
| Date Utility | date-fns | 날짜 계산/포맷 | 월간 캘린더 생성, 오늘 비교, YYYY-MM-DD 포맷 처리에 유리 |

### 프론트엔드 주요 기능

- Windows 위젯 창 표시
- 로그인/회원가입 화면
- 월간 캘린더 렌더링
- Today List 표시
- 목표/마일스톤 CRUD UI
- FastAPI 백엔드 API 호출
- 로딩/빈 상태/에러 메시지 처리
- 창 위치/크기/위젯 설정 관리

### 데이터 접근 원칙

프론트엔드는 Supabase에 직접 접근하지 않는다.

- 프론트엔드 → FastAPI로 API 요청
- FastAPI → Supabase와 통신

## 3. Backend

백엔드는 Python + FastAPI 기반으로 구현한다.

| 구분 | 사용 기술 | 역할 | 선정 이유 |
|---|---|---|---|
| Backend Framework | FastAPI | API 서버 구현 | Python 기반으로 빠르게 API 구성, AI 확장에도 유리 |
| Server | Uvicorn | 실행 서버 | 로컬/배포 환경에서 FastAPI 실행 |
| Schema Validation | Pydantic | 요청/응답 검증 | body, 응답 형식, 입력값을 명확히 정의 가능 |
| Config Management | python-dotenv | 환경 변수 관리 | Supabase URL/API Key/DB URL 등을 코드에서 분리 |
| Logging | Python logging | 로그 기록 | 오류 및 주요 흐름 기록으로 디버깅 용이 |
| DB Access | Supabase Python Client 또는 psycopg | DB 접근 | 목표/마일스톤/사용자 데이터 조회 및 수정 |

### 백엔드 주요 역할

- 회원가입/로그인 처리
- Supabase Auth 기반 JWT 검증
- 현재 사용자 정보 확인
- 목표/마일스톤 CRUD API
- 날짜별 목표/마일스톤 조회 API
- Today List 조회 API
- 사용자별 데이터 접근 검증
- 예외 처리 및 에러 로그 기록
- 외부 캘린더 연동 등 확장 구조 제공

백엔드는 단순 DB 프록시가 아니라 인증, 권한, 비즈니스 로직, 예외 처리, 로깅을 담당하는 중심 계층이다.

## 4. Database / Auth

데이터베이스와 인증은 Supabase PostgreSQL + Supabase Auth를 사용한다.

| 구분 | 사용 기술 | 역할 | 선정 이유 |
|---|---|---|---|
| Database | Supabase PostgreSQL | 목표/마일스톤/사용자 데이터 저장 | 안정적인 관계형 데이터 모델 구성 가능 |
| Auth | Supabase Auth | 회원가입/로그인/JWT 발급 | 이메일/비밀번호 기반 인증과 세션 관리 구현이 빠름 |
| Security | Supabase RLS | 사용자별 데이터 접근 제한 | 본인 데이터만 접근하도록 제한 가능 |
| Migration | SQL Migration | 스키마 변경 관리 | 테이블/RLS/트리거 등을 버전 관리하기 쉬움 |
| Migration Runner | Python Script | 마이그레이션 실행 자동화 | SQL 파일 순차 실행 및 적용 이력 관리 |

### 초기 데이터 모델

```text
auth.users
  └── goals
        └── milestones
```

| 테이블 | 역할 |
|---|---|
| users | Supabase Auth에서 관리하는 사용자 정보 |
| goals | 사용자가 생성한 목표 정보 |
| milestones | 목표 하위의 세부 마일스톤 |

### 보안 원칙

- 프론트엔드에 Supabase service role key를 노출하지 않는다.
- 프론트엔드에 DB URL을 저장하지 않는다.
- JWT에서 추출한 사용자 ID(sub)를 기준으로 데이터 접근을 처리한다.
- Supabase RLS로 1차 제한하고, 백엔드에서도 본인 소유 데이터인지 2차 검증한다.

## 5. Authentication / JWT

인증은 Supabase Auth에서 발급하는 JWT를 사용한다.
FastAPI에서 자체 JWT를 발급하기보다 Supabase 로그인 결과의 access token / refresh token을 활용한다.

### 인증 흐름

```text
1) 사용자가 프론트엔드에서 이메일/비밀번호 입력
2) 프론트엔드가 FastAPI 로그인 API 호출
3) FastAPI가 Supabase Auth에 로그인 요청
4) Supabase Auth가 access token / refresh token 발급
5) 프론트엔드가 토큰 저장
6) 이후 API 요청 시 Authorization 헤더에 access token 포함
7) FastAPI가 JWT 검증
8) JWT의 sub 값을 user_id로 사용
9) user_id 기준으로 목표/마일스톤 데이터 처리
```

### 추가 설계 포인트

- access token 저장 위치
- refresh token 저장 위치
- 자동 로그인 지원 여부
- 토큰 만료 시 갱신 방식
- 로그아웃 시 토큰 제거 방식
- 백엔드 JWT 검증 방식
- Supabase RLS와 백엔드 권한 검증의 역할 분리

MVP에서는 기본 로그인 + JWT 검증을 우선 구현하고, 자동 로그인/보안 저장소 적용은 후순위로 둔다.

## 6. Build / Packaging / 실행 환경

MileDay는 Windows 데스크톱 위젯 앱이므로, MVP 완성 후 Windows 실행 파일 형태로 패키징한다.

| 구분 | 사용 기술 | 역할 | 선정 이유 |
|---|---|---|---|
| App Packaging | electron-builder | Windows 실행 파일 패키징 | .exe 또는 설치 파일 형태로 배포 |
| Startup Setting | Electron app API | 시작 시 자동 실행 | PC 부팅 시 자동 실행 설정 가능 |
| Environment Config | .env | 환경 변수 분리 | 프론트/백 설정을 분리 관리 |
| Version Control | Git / GitHub | 코드/버전 관리 | 마일스톤 단위 개발 이력 및 릴리즈 관리 |

### 폴더 구조 예시

```text
frontend/   # Electron + React + TypeScript
backend/    # FastAPI
migrations/ # Supabase SQL migrations
scripts/    # Python migration runner
```

### 개발 시 실행

- frontend 개발 서버 실행
- backend FastAPI 서버 실행
- Supabase PostgreSQL 연결

## 7. Development Tools / Code Quality

| 구분 | 사용 기술 | 역할 | 선정 이유 |
|---|---|---|---|
| Frontend Lint | ESLint | 프론트엔드 코드 검사 | 문법 오류/스타일 문제 사전 탐지 |
| Frontend Format | Prettier | 코드 포맷 통일 | 스타일 일관성 유지 |
| Backend Lint | Ruff | 백엔드 코드 검사 | 문법/import/스타일 문제를 빠르게 탐지 |
| Backend Format | Black | 백엔드 포맷 통일 | Python 코드 스타일 일관성 |
| API Test | Postman 또는 Bruno | API 테스트 | FE 연결 전 수동 테스트에 유리 |
| DB Management | Supabase Dashboard | DB 확인/관리 | 테이블/데이터/RLS 정책 확인 |
| Diagram | PlantUML | 구조도 작성 | 데이터 흐름/인증 흐름 시각화 |
| Log Check | Python logging | 로그 확인 | 오류 및 처리 흐름 디버깅 |

## 8. Environment Variables

환경 변수는 프론트엔드와 백엔드를 분리해 관리한다.

### Frontend `.env`

프론트엔드에는 백엔드 API 주소만 둔다.

```env
VITE_API_BASE_URL=http://localhost:8000
```

프론트엔드에 아래 값은 절대 저장하지 않는다.

- SUPABASE_SERVICE_ROLE_KEY
- SUPABASE_DB_URL
- SUPABASE_DB_PASSWORD

### Backend `.env`

백엔드에는 Supabase 연결 정보와 로그 설정을 둔다.

```env
SUPABASE_URL=your_supabase_project_url
SUPABASE_ANON_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key
SUPABASE_DB_URL=your_supabase_postgres_connection_string
LOG_LEVEL=INFO
ENV=development
```

### 관리 원칙

- `.env` 파일은 Git에 올리지 않는다.
- `.env.example`로 필요한 변수 목록만 공유한다.
- 프론트엔드에는 공개 가능한 값만 저장한다.
- 백엔드 민감 정보는 배포 환경에서 안전하게 관리한다.
- DB 마이그레이션 연결 문자열은 로컬/서버 환경에서만 사용한다.

## 9. 서버 운영

### 1. 초기 MVP

Supabase Free + 로컬 FastAPI

MVP부터 서버를 설정하지 말고, 기능 구현에 집중한다.

### 2. 포트폴리오 공개

Supabase Free + Render Free

사용자 리뷰를 받기 위해 외부 서버를 사용한다.

### 3. 실제 장기 운영

Supabase Free + Railway Hobby 또는 DigitalOcean Droplet

실제 배포 시에는 always-on으로 동작하게 설정한다.
