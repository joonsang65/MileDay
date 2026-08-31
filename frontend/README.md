# MileDay Frontend

MileDay 프론트엔드는 Electron 기반 Windows 데스크톱 위젯 애플리케이션이다. React renderer가 캘린더와 일정 관리 UI를 담당하고, Electron main process가 창, 트레이, 로컬 설정, 암호화 토큰 저장 같은 데스크톱 기능을 담당한다.

## 역할

- Electron + React + TypeScript 기반 데스크톱 앱
- 월간/주간 캘린더와 날짜별 하루 보기
- Goal / Milestone 생성, 수정, 삭제, 완료 처리 UI
- AI 일정 초안 생성과 편집 UI
- 사용자 설정, 글자 크기, 창 크기, 투명도, 자동 실행 관리
- FastAPI 백엔드와만 통신하는 API client 제공

## Electron 구조

```text
Electron Main
  -> IPC handlers
Preload
  -> window.mileday API
React Renderer
  -> UI, Zustand state, FastAPI API client
```

| 파일 | 책임 |
|---|---|
| `electron/main.ts` | BrowserWindow 생성, tray, IPC handler, safeStorage, 창 이동/크기/위치 저장 |
| `electron/preload.ts` | renderer에 제한된 `window.mileday` API 노출 |
| `electron/autoLaunch.ts` | Windows 로그인 시 자동 실행 설정 |
| `electron/windowOptions.ts` | frameless widget 창 옵션과 크기 제한 |
| `src/types/localUiSettings.ts` | 로컬 UI 설정 타입과 기본값 |
| `src/types/windowResize.ts` | 창 resize direction 타입 |

## Windows 데스크톱 기능

현재 구현된 데스크톱 기능은 다음과 같다.

| 기능 | 구현 위치 | 설명 |
|---|---|---|
| 프레임 없는 위젯 창 | `electron/windowOptions.ts` | OS title bar 없이 `skipTaskbar`로 표시 |
| 트레이 메뉴 | `electron/main.ts` | 열기, 숨기기, 종료 메뉴와 더블클릭 열기 |
| 로그인 시 자동 실행 | `electron/autoLaunch.ts` | Electron login item 설정 사용 |
| 창 위치/크기 저장 | `electron/main.ts` | `ui-settings.json`에 bounds 저장 후 재실행 시 복원 |
| 창 이동/리사이즈 | `electron/main.ts`, `preload.ts` | renderer 이벤트를 IPC로 main process에 전달 |
| 투명도 설정 | `electron/main.ts` | `setOpacity()`와 로컬 설정 저장 |
| 글자 크기 설정 | `electron/main.ts`, `src/types/localUiSettings.ts` | base/goal font size를 1~25 범위로 정규화 |
| 토큰 저장 | `electron/main.ts` | `safeStorage`로 access token 암호화 저장 |
| Windows 패키징 | `package.json` | electron-builder NSIS installer 생성 |

## Renderer 구조

| 영역 | 주요 파일 |
|---|---|
| 앱 조립 | `src/App.tsx` |
| API 통신 | `src/api/client.ts`, `src/api/types.ts` |
| 캘린더 상태 | `src/store/calendarStore.ts` |
| 오버레이 상태 | `src/store/uiStore.ts` |
| 캘린더 UI | `src/components/CalendarHeader.tsx`, `src/components/CalendarBoard.tsx` |
| 하루 보기 | `src/components/DateDetail.tsx`, `src/components/TodayList.tsx` |
| 일정 생성 | `src/components/ManualCreatePanel.tsx`, `src/components/QuickActionPopover.tsx` |
| AI 일정 | `src/components/AiSchedulePanel.tsx` |
| 설정 | `src/components/SettingsPanel.tsx` |

`src/api/client.ts`는 기본적으로 `http://localhost:8000`을 사용하고, `VITE_API_BASE_URL`이 있으면 해당 값을 사용한다. 인증 토큰은 Electron 환경에서는 `window.mileday.authToken`을 통해 safeStorage에 저장하고, 브라우저형 테스트 환경에서는 localStorage fallback을 사용한다.

## UX 개선 흐름

[docs/changelog.md](../docs/changelog.md)와 [피드백 원문](../docs/archive/reference/user_feedback_changes.md)에 기록된 사용자 피드백 기반 개선 중 프론트엔드와 직접 연결되는 내용은 다음과 같다.

- 날짜 선택은 Zustand 상태를 즉시 바꿔 사용자가 선택한 날짜 반응을 빠르게 보게 한다.
- GET 요청은 API client에서 502/503/504 또는 네트워크 오류에 한해 최대 3회 재시도한다.
- 목표/마일스톤 완료 처리에는 낙관적 UI 갱신과 실패 시 rollback 흐름을 사용한다.
- 전체 목표 화면은 목표별 순차 조회 대신 `/goals/with-milestones` 통합 API를 사용한다.
- 하루 보기는 별도 하단 영역보다 floating panel 중심으로 정리해 작은 창에서 스크롤 부담을 줄였다.
- 작은 창에서는 캘린더 셀의 핵심 정보가 먼저 보이도록 표시 밀도를 조정한다.
- AI 일정은 초안 생성, 사용자 편집, 최종 저장을 분리해 사용자가 확인하기 전 DB write가 일어나지 않게 한다.

## 실행

프론트엔드만 실행할 때는 `frontend`에서 실행한다.

```powershell
cd frontend
npm install
npm run dev
```

`npm run dev`는 `scripts/dev.mjs`를 통해 `electron-vite dev -w -- --disable-gpu-sandbox`를 실행한다. 이 설정은 renderer HMR, main/preload watch 재시작, Electron GPU sandbox 비활성화를 함께 적용한다.

루트에서 백엔드 health check 후 프론트엔드까지 실행하려면 다음 명령을 사용한다.

```powershell
.\dev.cmd
```

## 테스트와 빌드

`frontend/package.json` 기준 주요 script는 다음과 같다.

| 명령 | 내용 |
|---|---|
| `npm run dev` | Electron 개발 모드 실행 |
| `npm run lint` | ESLint 검사 |
| `npm test` | Vitest 단위 테스트 |
| `npm run build` | TypeScript 검사 후 electron-vite build |
| `npm run dist` | build, package API 검증, Windows NSIS installer 생성 |
| `npm run pack` | 설치 파일 없이 Windows 패키지 디렉터리 생성 |

패키징 전에는 `npm run build`와 `npm run verify:package-api`가 통과해야 한다.
