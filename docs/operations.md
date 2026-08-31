# MileDay Operations

이 문서는 개발 실행, 테스트, 패키징, 환경 변수, 문제 해결, 커밋 기준만 다룬다.

## 개발 실행

루트에서 backend health check 후 frontend를 실행한다.

```powershell
.\dev.cmd
```

`dev.cmd`는 `/health`, `/health/db` 통과 후 frontend dev script를 실행한다.

Backend:

```powershell
cd backend\app
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Frontend:

```powershell
cd frontend
npm run dev
```

## 테스트와 빌드

| 영역 | 명령 |
|---|---|
| Backend | `pytest` |
| Frontend test | `cd frontend` 후 `npm test` |
| Frontend watch | `cd frontend` 후 `npm run test:watch` |
| Frontend lint | `cd frontend` 후 `npm run lint` |
| Frontend build | `cd frontend` 후 `npm run build` |
| Windows installer | `cd frontend` 후 `npm run dist` |
| Unpacked package | `cd frontend` 후 `npm run pack` |
| Preview | `cd frontend` 후 `npm run preview` |

`pytest.ini`는 기본적으로 `integration` marker를 제외한다. 통합 테스트는 전용 환경 변수와 테스트 계정을 갖춘 뒤 실행한다.

## 성능 스크립트

- `npm run perf:goal:create`
- `npm run perf:milestone:create`
- `npm run perf:milestone:toggle`
- `npm run perf:settings:update`
- `npm run perf:date:select`
- `npm run perf:cleanup`

## 환경 변수

| 영역 | 변수 |
|---|---|
| Backend 기본 | `ENV`, `APP_NAME`, `API_HOST`, `API_PORT`, `CORS_ORIGINS` |
| Supabase | `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_DB_URL` |
| Holiday API | `HOLIDAY_API_SERVICE_KEY`, `HOLIDAY_API_BASE_URL` |
| Gemini | `GEMINI_API_KEY`, `GEMINI_API_BASE_URL`, `GEMINI_SCHEDULE_MODEL` |
| Test | `ENABLE_INTEGRATION_TESTS`, `TEST_EMAIL`, `TEST_PASSWORD`, `TEST_USER_ID`, `TEST_TITLE_PREFIX` |
| Logging | `LOG_LEVEL`, `LOG_DIR`, `LOG_RETENTION_DAYS` |
| Frontend | `VITE_API_BASE_URL` |

Backend는 루트 `.env`를 읽고, 다른 파일은 `ENV_FILE`로 지정한다. Frontend 기본 API URL은 `http://localhost:8000`이다.

## 문제 해결 기준

- DB 연결 문제는 `/health/db`와 Supabase migration 적용 여부를 먼저 확인한다.
- Electron 개발 실행 문제는 `frontend/scripts/dev.mjs`와 GPU sandbox flag를 확인한다.
- UI 깨짐은 작은 창 크기, Windows 배율, `frontend/scripts/verify-compact-layout.mjs`를 함께 본다.
- 과거 문제 해결 원문은 [archive/reference/troubleshooting.md](archive/reference/troubleshooting.md)에 보관한다.

## 커밋 기준

- 문서만 바꾸면 `docs(...)` type을 사용한다.
- 기능 변경과 문서 변경이 섞이면 가능하면 커밋을 나눈다.
- 커밋 메시지는 한글 summary를 짧게 쓴다.

상세 커밋 규칙 원문은 [archive/reference/commit_guide.md](archive/reference/commit_guide.md)에 보관한다.
