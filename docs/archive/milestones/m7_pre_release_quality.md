# M7. 릴리즈 직전 품질 정리

## 문서 목적

M7 단계에서는 M1부터 M6.5.1까지 구현한 MVP 기능을 실제 사용 가능한 상태로 정리한다.

새로운 대형 기능을 추가하기보다 입력값 검증, 오류 메시지, 빈 상태, 로딩 상태, 위젯 UI 안정성, Windows 자동 실행 설정처럼 릴리즈 직전에 사용자 경험을 깨뜨릴 수 있는 부분을 마무리한다.

M9의 Electron 패키징과 배포 문서화는 별도 단계로 두고, M7에서는 개발 실행과 로컬 앱 사용 흐름에서 품질 기준을 만족하는지 검증한다.

## 기준 문서

| 문서 | 확인 내용 |
|---|---|
| `docs/requirements.md` | M7 요구사항 ERR-01~ERR-03, FE-01~FE-02, FE-06, WD-08 |
| `docs/error_logging.md` | 공통 오류 응답, HTTP status, frontend error code 매핑 기준 |
| `docs/api_spec.md` | API 요청/응답 형식과 오류 응답 구조 |
| `docs/data_flow.md` | 인증, 목표, 마일스톤, 캘린더, 설정 데이터 흐름 |
| `docs/db_schema.md` | goals, milestones, user_settings 저장 기준 |
| `docs/milestones/m6_widget_auth_ui.md` | 위젯 창 동작과 Electron 창 제어 기준 |
| `docs/milestones/m6_5_creation_ui.md` | 목표/마일스톤 생성 UI 기준 |
| `docs/milestones/m6_5_1_user_settings.md` | 설정 패널과 설정값 UI 반영 기준 |
| `docs/troubleshooting.md` | M3~M6.5.1 구현 중 발생한 실제 오류와 대응 |

## M7 요구사항 범위

| ID | 분류 | 기능 | 구현 기준 |
|---|---|---|---|
| ERR-01 | 오류 처리 | 입력값 검증 | 목표, 마일스톤, 설정, 인증 폼의 필수 입력과 날짜 범위를 프론트/백엔드에서 일관되게 검증한다. |
| ERR-02 | 오류 처리 | API 오류 메시지 | API 실패 시 raw error 대신 사용자가 이해할 수 있는 한글 메시지를 표시한다. |
| ERR-03 | 오류 처리 | 빈 데이터 처리 | 목표, 마일스톤, 오늘 할 일, 날짜 상세, 공휴일 데이터가 비어 있어도 화면이 깨지지 않는다. |
| FE-01 | UI/UX | 간결한 위젯 UI | 작은 위젯 창에서도 핵심 정보가 잘리지 않고 캘린더 중심으로 읽힌다. |
| FE-02 | UI/UX | 직관적인 설정 구조 | 설정, 로그아웃, 기본 view, 공휴일 표시, 언어 설정을 사용자가 쉽게 찾을 수 있다. |
| FE-06 | UI/UX | 로딩 상태 표시 | 조회, 생성, 수정, 삭제, 저장 중에는 사용자가 현재 상태를 알 수 있다. |
| WD-08 | 위젯 창 | Windows 시작 시 자동 실행 | 사용자가 설정에서 Windows 시작 시 자동 실행 여부를 켜고 끌 수 있다. |

## 구현 범위

### 1. 입력값 검증 정리

목표와 마일스톤 생성/수정 폼은 API 호출 전 기본 검증을 수행한다.

검증 기준:

- 제목은 공백만 입력할 수 없다.
- 날짜 필드는 비어 있을 수 없다.
- 목표 마감일과 마일스톤 예정일은 ISO date 형식으로 API에 전달한다.
- 마일스톤 생성 시 `goal_id`가 없으면 API를 호출하지 않는다.
- 반복 마일스톤 생성 시 종료일이 시작일보다 빠르면 API를 호출하지 않는다.
- 설정 저장 시 select 값은 백엔드 허용값과 같은 값만 전송한다.

백엔드는 기존 Pydantic schema와 service 검증을 유지하되, FastAPI validation error는 `400 BAD_REQUEST` 공통 오류 응답으로 내려야 한다.

### 2. 오류 메시지 매핑

프론트엔드는 API에서 받은 `error.code`를 우선 사용해 사용자 메시지를 결정한다.

기본 메시지 기준:

| 상황 | 사용자 메시지 |
|---|---|
| 인증 만료 | 다시 로그인해 주세요. |
| 목표 생성 실패 | 목표를 추가하지 못했습니다. |
| 목표 수정 실패 | 목표를 수정하지 못했습니다. |
| 목표 삭제 실패 | 목표를 삭제하지 못했습니다. |
| 마일스톤 생성 실패 | 작업을 추가하지 못했습니다. |
| 마일스톤 수정 실패 | 작업을 수정하지 못했습니다. |
| 마일스톤 삭제 실패 | 작업을 삭제하지 못했습니다. |
| 완료 상태 변경 실패 | 완료 상태를 변경하지 못했습니다. |
| 설정 저장 실패 | 설정을 저장하지 못했습니다. |
| 캘린더 조회 실패 | 캘린더를 불러오지 못했습니다. |
| 네트워크 실패 | 서버에 연결하지 못했습니다. |

`detail`은 개발자가 원인을 확인하기 위한 정보로만 사용한다.
사용자 화면에는 내부 SQL, Supabase 원문 오류, stack trace, service key 관련 메시지를 그대로 노출하지 않는다.

### 3. 빈 상태와 fallback UI

데이터가 없거나 외부 API fallback이 발생해도 빈 화면처럼 보이지 않아야 한다.

빈 상태 기준:

| 화면 | 빈 상태 기준 |
|---|---|
| 캘린더 날짜 칸 | 목표/작업이 없으면 카운터나 일정 텍스트 없이 날짜만 표시 |
| 날짜 상세 | 해당 날짜의 목표와 작업이 없으면 각각 빈 상태 문구 표시 |
| Today List | 오늘 예정 작업이 없으면 빈 상태 문구 표시 |
| 목표 선택 | 목표가 없으면 마일스톤 생성 UI를 숨기거나 목표 생성 안내 표시 |
| 설정 패널 | 저장된 설정 row가 없으면 백엔드 기본값 생성 결과 표시 |
| 공휴일 | API 키가 없거나 호출 실패 시 주말 표시만 유지 |

빈 상태 문구는 `language` 설정이 `ko`이면 한글, `en`이면 영어로 표시한다.

### 4. 로딩 상태와 중복 제출 방지

사용자가 같은 작업을 여러 번 제출하지 않도록 mutation 중 버튼을 잠근다.

적용 대상:

- 로그인
- 회원가입
- 목표 생성, 수정, 삭제
- 마일스톤 생성, 수정, 삭제
- 마일스톤 완료 상태 변경
- 설정 저장
- 캘린더 새로고침

로딩 상태 기준:

- 버튼에는 저장 중, 추가 중, 삭제 중 같은 현재 동작을 표시한다.
- mutation 중 같은 버튼을 다시 누를 수 없어야 한다.
- 조회 실패 후 재시도 버튼 또는 새로고침 버튼으로 복구할 수 있어야 한다.
- 로딩 표시 때문에 캘린더 그리드 크기가 흔들리지 않아야 한다.

### 5. 위젯 UI 안정화

M7에서는 위젯이 실제 사용 크기에서 읽기 어렵거나 잘리는 문제를 정리한다.

검증 기준:

- 기본 창 크기에서 목표 생성 패널 하단이 잘리지 않는다.
- 설정 패널 하단의 로그아웃 버튼이 항상 접근 가능하다.
- 날짜 칸 안에서 목표/작업 요약 텍스트가 다른 UI와 겹치지 않는다.
- 월간/주간 전환 시 캘린더 높이와 사이드 영역이 비정상적으로 흔들리지 않는다.
- `language=en`으로 변경해도 버튼 텍스트가 부모 영역을 벗어나지 않는다.
- `week_starts_on` 변경 후 요일 라벨과 날짜 배치가 일치한다.

### 6. Windows 시작 시 자동 실행

자동 실행은 계정 기준 `user_settings`에 저장하지 않는다.
이 값은 PC 로컬 환경에 종속되므로 Electron 로컬 저장소 또는 Electron API로 처리한다.

구현 기준:

- 설정 패널에 `Windows 시작 시 자동 실행` 토글을 추가한다.
- Electron main process에서 `app.setLoginItemSettings`를 사용해 자동 실행을 켜고 끈다.
- renderer는 IPC를 통해 현재 자동 실행 상태 조회와 변경을 요청한다.
- 백엔드 `/settings` API에는 자동 실행 값을 보내지 않는다.
- 웹 renderer 테스트에서는 IPC adapter를 mock 처리한다.

권장 IPC 계약:

```ts
type AutoLaunchState = {
  openAtLogin: boolean;
};

window.mileday.autoLaunch.get(): Promise<AutoLaunchState>;
window.mileday.autoLaunch.set(openAtLogin: boolean): Promise<AutoLaunchState>;
```

Electron main 기준:

```ts
app.setLoginItemSettings({
  openAtLogin,
  path: process.execPath,
});
```

개발 모드와 패키징 모드는 실행 경로가 다를 수 있다.
M7에서는 개발 환경에서 IPC 흐름과 설정 저장 동작을 검증하고, M9 패키징 단계에서 설치본 기준 자동 실행 경로를 다시 검증한다.

## API 변경 기준

M7에서 백엔드 API를 크게 추가하지 않는다.

허용되는 변경:

- 기존 API validation 강화
- 공통 오류 응답 일관성 보정
- 오류 code/message 보강
- 로딩/빈 상태 처리를 위한 응답 필드 누락 보정

허용하지 않는 변경:

- 새로운 외부 캘린더 연동 API
- AI 추천 API
- 모바일 앱 연동 API
- 자동 실행 값을 `user_settings` 테이블에 저장하는 변경

## 프론트엔드 변경 기준

주요 변경 위치:

| 파일 | 변경 기준 |
|---|---|
| `frontend/src/App.tsx` | 전역 loading/error 상태와 설정 패널 흐름 보정 |
| `frontend/src/api/client.ts` | API 오류 code/detail 보존과 사용자 메시지 매핑에 필요한 구조 정리 |
| `frontend/src/components/AuthPanel.tsx` | 로그인/회원가입 입력 검증과 로딩 상태 |
| `frontend/src/components/CreationPanel.tsx` | 목표/마일스톤 생성 검증, 중복 제출 방지 |
| `frontend/src/components/DateDetail.tsx` | 수정/삭제 로딩 상태와 빈 상태 보정 |
| `frontend/src/components/SettingsPanel.tsx` | 자동 실행 토글, 설정 저장 로딩 상태, 로그아웃 위치 유지 |
| `frontend/src/components/TodayList.tsx` | 완료 토글 로딩 상태와 빈 상태 보정 |
| `frontend/src/styles.css` | 작은 위젯 창에서 잘림/겹침 방지 |
| `frontend/electron/main.ts` | 자동 실행 IPC와 Electron login item 설정 |
| `frontend/electron/preload.ts` | renderer에 안전한 자동 실행 API 노출 |

## 테스트 계획

### 백엔드

| 테스트 범위 | 검증 내용 |
|---|---|
| validation | 목표/마일스톤/설정 요청의 잘못된 값이 `400` 공통 오류 응답으로 변환되는지 검증 |
| auth | 인증 없는 요청이 `401`로 처리되고 사용자 데이터 존재 여부를 노출하지 않는지 검증 |
| error response | 예외 응답에 `success=false`, `error.code`, `error.message`, `request_id`가 포함되는지 검증 |
| empty data | 목표/마일스톤/Today List가 비어도 빈 배열과 카운트가 일관되게 반환되는지 검증 |
| fallback | 공휴일 API 실패 시 캘린더 조회가 실패하지 않는지 검증 |

### 프론트엔드

| 테스트 범위 | 검증 내용 |
|---|---|
| AuthPanel | 필수 입력 누락, 비밀번호 불일치, 로딩 중 중복 제출 방지 |
| CreationPanel | 제목/날짜 누락, goal_id 누락, 반복 종료일 오류 시 API 미호출 |
| DateDetail | 빈 목표/작업 표시, 수정/삭제 중 버튼 비활성화 |
| TodayList | 빈 상태, 완료 토글 실패 메시지, 로딩 상태 |
| SettingsPanel | 설정 저장 로딩, 로그아웃 위치, 자동 실행 토글 IPC 호출 |
| CalendarBoard | `week_starts_on`, `holiday_display`, `language` 변경 후 표시 유지 |
| API client | error.code/detail 보존, 네트워크 실패 메시지 매핑 |
| Electron | 자동 실행 IPC handler가 `app.getLoginItemSettings`, `app.setLoginItemSettings`를 호출하는지 검증 |

### 수동 검증

| 검증 항목 | 확인 내용 |
|---|---|
| 첫 실행 | 로그인/회원가입 화면에서 오류 메시지와 로딩 상태가 자연스러운지 확인 |
| 목표/작업 CRUD | 생성, 수정, 삭제, 완료 처리 후 캘린더와 날짜 상세이 즉시 갱신되는지 확인 |
| 빈 상태 | 새 계정에서 캘린더, 날짜 상세, Today List가 깨지지 않는지 확인 |
| 설정 반영 | week starts on, language, holiday display, default view가 즉시 반영되는지 확인 |
| 위젯 크기 | 기본 창 크기에서 하단 버튼과 패널 내용이 잘리지 않는지 확인 |
| 자동 실행 | Windows 시작 시 자동 실행 토글을 켜고 끈 뒤 상태가 유지되는지 확인 |

## 검증 명령

M7 구현 후 다음 명령을 실행한다.

```powershell
pytest
```

```powershell
cd frontend
npx tsc --noEmit
npm run lint
npm test
npm run build
```

Electron 실제 동작은 개발 실행으로 확인한다.

```powershell
.\scripts\dev.ps1
```

## 완료 기준

- 목표, 마일스톤, 설정, 인증 폼에서 필수 입력 검증이 동작한다.
- API 실패 시 사용자가 이해할 수 있는 메시지가 표시된다.
- 빈 목표, 빈 마일스톤, 빈 Today List 상태에서도 화면이 깨지지 않는다.
- 생성, 수정, 삭제, 저장 중 중복 제출이 방지된다.
- 작은 위젯 창에서 주요 버튼과 텍스트가 잘리지 않는다.
- 설정 패널에서 Windows 시작 시 자동 실행을 켜고 끌 수 있다.
- 자동 실행 값은 백엔드 `user_settings`가 아니라 Electron 로컬 동작으로 처리된다.
- 모든 자동 테스트와 프론트엔드 빌드가 통과한다.
- 구현 중 추가하는 주석은 한글로 작성한다.

## M7에서 하지 않는 일

- Electron 설치 파일 생성과 배포는 M9에서 처리한다.
- 모바일 앱 연동은 M8 이후 범위로 둔다.
- Google Calendar, Apple Calendar, Samsung Calendar 연동은 M8 이후 범위로 둔다.
- AI 마일스톤 생성, 자연어 일정 수정, 자동 리스케줄링은 M8 이후 범위로 둔다.
- Windows 네이티브 레이어를 직접 조작해 바탕화면 아이콘 레이어에 붙이는 구현은 하지 않는다.
