# Frontend

`frontend/`는 MileDay의 Electron + React + TypeScript 데스크톱 클라이언트입니다. 사용자는 이 화면에서 목표, 마일스톤, 캘린더, Today List, 로컬 창 설정을 조작합니다.

Frontend는 Supabase에 직접 접근하지 않습니다. 모든 제품 데이터 요청은 FastAPI backend를 통해 처리합니다.

## 구조

```text
frontend/
  electron/
  scripts/
  src/
    api/
    components/
    store/
    test/
    utils/
  package.json
  vite.config.ts
  electron.vite.config.ts
  tailwind.config.ts
```

| 경로 | 역할 |
|---|---|
| `electron/` | Electron main/preload, 창 옵션, 자동 실행 설정 |
| `src/api/` | FastAPI 호출 client와 API type 연결 |
| `src/components/` | React UI component |
| `src/store/` | Zustand 기반 frontend 상태 관리 |
| `src/utils/` | 날짜, 포맷, 공통 helper |
| `src/test/` | frontend test setup |
| `scripts/` | frontend 개발 실행 보조 script |

## 실행

프로젝트 루트에서 전체 개발 환경을 실행하는 방식이 기본입니다.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\dev.ps1
```

frontend만 실행하려면:

```powershell
cd frontend
npm run dev
```

## 환경 변수

`frontend/.env.example`을 기준으로 `frontend/.env`를 준비합니다.

Frontend에는 공개 가능한 값만 둡니다.

```env
VITE_API_BASE_URL=http://localhost:8000
```

금지:

- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_DB_URL`
- DB password
- backend 전용 secret
- 외부 API secret key

## 명령어

```powershell
cd frontend
npm test
npm run lint
npm run build
```

| 명령 | 설명 |
|---|---|
| `npm run dev` | Electron + Vite 개발 실행 |
| `npm test` | Vitest 단위 테스트 |
| `npm run lint` | ESLint 검사 |
| `npm run build` | TypeScript check 후 electron-vite build |
| `npm run preview` | build 결과 preview |

성능 측정 보조 명령도 package script에 남아 있습니다.

```powershell
npm run perf:goal:create
npm run perf:milestone:create
npm run perf:milestone:toggle
npm run perf:settings:update
npm run perf:date:select
npm run perf:cleanup
```

## Backend 연동 기준

- API base URL은 `VITE_API_BASE_URL`로만 관리합니다.
- 인증이 필요한 요청은 `Authorization: Bearer <access_token>`을 포함합니다.
- response는 backend 공통 envelope를 기준으로 처리합니다.

성공:

```json
{
  "success": true,
  "data": {}
}
```

실패:

```json
{
  "success": false,
  "error": {
    "code": "BAD_REQUEST",
    "message": "Invalid request."
  },
  "request_id": "req_xxx"
}
```

## Electron 로컬 설정

창 위치, 창 크기, opacity, always-on-top, startup, widget layout처럼 PC 환경에 종속되는 값은 Supabase `user_settings`에 저장하지 않습니다. Electron local storage 계층에서 관리합니다.

## 구현 기준

- 화면은 반복 사용을 전제로 조용하고 밀도 있게 구성합니다.
- Supabase 직접 접근 코드를 추가하지 않습니다.
- backend API type과 response envelope를 우회하지 않습니다.
- 날짜 값은 `YYYY-MM-DD` 형식을 사용합니다.
- 새로운 UI 상태는 component local state와 Zustand store 중 책임 범위를 먼저 분리합니다.
- frontend 변경 후에는 최소 `npm test`, `npm run lint`, 필요 시 `npm run build`를 실행합니다.
