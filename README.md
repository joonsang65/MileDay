# MileDay

MileDay는 목표와 마일스톤을 캘린더 위에서 관리하는 Windows 데스크톱 플래너입니다. 큰 목표를 날짜가 있는 작은 실행 단위로 나누고, 오늘 해야 할 마일스톤을 위젯형 Electron 앱에서 바로 확인할 수 있도록 설계했습니다.

## 주요 기능

- 이메일 기반 회원가입, 로그인, 로그아웃
- 목표 생성, 조회, 수정, 삭제
- 목표별 마일스톤 생성, 조회, 수정, 삭제, 완료 처리
- 월간/주간 캘린더 전환
- 날짜별 목표 마감일과 마일스톤 일정 표시
- Today List를 통한 오늘의 마일스톤 확인 및 완료 처리
- 목표/마일스톤 색상 지정
- 사용자별 캘린더 보기, 공휴일 표시 방식, 주 시작 요일, 언어 설정
- Windows 시작 시 자동 실행 설정
- Supabase Auth/JWT 기반 사용자 데이터 분리
- FastAPI 공통 응답, 예외 처리, 요청 로그 기록

## 기술 스택

| 영역 | 기술 |
| --- | --- |
| Desktop | Electron, electron-vite |
| Frontend | React, TypeScript, Vite, Tailwind CSS, Zustand |
| Backend | Python, FastAPI, Uvicorn, Pydantic |
| Database/Auth | Supabase PostgreSQL, Supabase Auth |
| Test | Pytest, Vitest, Testing Library, Playwright |

## 아키텍처

```text
Electron + React
       |
       | HTTP API
       v
FastAPI Backend
       |
       | Supabase client / JWT validation
       v
Supabase Auth + PostgreSQL
```

프론트엔드는 Supabase에 직접 접근하지 않고 FastAPI API를 통해서만 데이터를 처리합니다. 백엔드는 JWT에서 사용자 ID를 확인하고, 목표와 마일스톤 데이터를 사용자별로 분리해 다룹니다.

## 시작하기

### 요구 사항

- Python 3.11 이상
- Node.js 20 이상 권장
- npm
- Supabase 프로젝트
- Windows 환경 권장

### 환경 변수 설정

루트 환경 변수 파일을 준비합니다.

```powershell
Copy-Item .env.example .env
```

`.env`에 Supabase와 공휴일 API 정보를 입력합니다.

```env
APP_NAME=MileDay
ENV=development
API_HOST=127.0.0.1
API_PORT=8000

SUPABASE_URL=your_supabase_project_url
SUPABASE_ANON_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key
SUPABASE_DB_URL=your_supabase_postgres_connection_string

HOLIDAY_API_SERVICE_KEY=your_public_data_portal_service_key
```

프론트엔드 성능 테스트를 사용할 경우 `frontend/.env.example`을 참고해 `frontend/.env`도 준비합니다.

### 의존성 설치

백엔드 의존성을 설치합니다.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

프론트엔드 의존성을 설치합니다.

```powershell
cd frontend
npm install
cd ..
```

### 데이터베이스 마이그레이션

Supabase CLI 또는 Supabase SQL Editor에서 `supabase/migrations`의 SQL을 순서대로 적용합니다.

```text
supabase/migrations/
```

## 실행

백엔드 상태 확인까지 포함해 데스크톱 앱을 실행하려면 루트에서 다음 스크립트를 사용합니다.

```powershell
.\scripts\dev.ps1
```

수동으로 실행할 수도 있습니다.

```powershell
cd backend/app
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

```powershell
cd frontend
npm run dev
```

기본 API 주소는 `http://localhost:8000`입니다.

## 테스트

백엔드 테스트:

```powershell
pytest
```

프론트엔드 테스트:

```powershell
cd frontend
npm test
```

프론트엔드 린트:

```powershell
cd frontend
npm run lint
```

프론트엔드 빌드:

```powershell
cd frontend
npm run build
```

## API 개요

| 기능 | Endpoint |
| --- | --- |
| Auth | `/auth/signup`, `/auth/login`, `/auth/logout`, `/auth/me` |
| Goals | `/goals`, `/goals/{goal_id}` |
| Milestones | `/goals/{goal_id}/milestones`, `/milestones/{milestone_id}` |
| Calendar | `/calendar/month`, `/calendar/week`, `/calendar/date/{date}` |
| Today | `/milestones/today` |
| Settings | `/settings` |
| Health | `/health`, `/health/db` |

자세한 API, DB, 데이터 흐름 문서는 `docs/`에서 확인할 수 있습니다.

## 프로젝트 구조

```text
MileDay/
├── backend/              # FastAPI 애플리케이션
│   └── app/
│       ├── api/          # API 라우터
│       ├── core/         # 설정, 로깅, 미들웨어, Supabase 클라이언트
│       ├── repositories/ # 데이터 접근 계층
│       ├── schemas/      # Pydantic 스키마
│       └── services/     # 비즈니스 로직
├── frontend/             # Electron + React 앱
│   ├── electron/         # Electron main/preload 코드
│   └── src/              # React UI, API client, store, utils
├── supabase/migrations/  # DB 스키마 및 마이그레이션
├── tests/                # 백엔드, 통합, 성능 테스트
├── docs/                 # API/DB/흐름/운영 문서
└── scripts/              # 개발 및 성능 측정 스크립트
```

## 로드맵

- AI 기반 마일스톤 후보 생성
- 자연어 기반 일정 수정
- 미완료 마일스톤 자동 리스케줄링
- Google Calendar, Apple/iOS Calendar, Samsung Calendar 연동
- Windows 실행 파일 패키징

## 문서

- `docs/api_spec.md`: API 명세
- `docs/db_schema.md`: 데이터베이스 스키마
- `docs/data_flow.md`: 데이터 흐름
- `docs/error_logging.md`: 에러 및 로깅 정책
- `docs/troubleshooting.md`: 문제 해결 가이드
- `docs/commit_guide.md`: 커밋 가이드

## 라이선스

현재 라이선스 파일이 포함되어 있지 않습니다. 공개 배포 전 `LICENSE` 파일을 추가하고 이 섹션을 갱신하세요.
