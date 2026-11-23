# MileDay 폴더 구조와 리팩토링 우선순위

리팩토링 전 구조와 판단 근거를 담은 기록이다. 소스 링크는 현재 파일 위치를 가리킨다.

첫 코드 변경은 데스크톱 캘린더의 데이터 갱신 로직을 `App.tsx`에서 분리하는 작업으로 잡는다. 모바일 화면을 분리하기 전에는 기존 PWA 테스트와 빌드를 CI에 연결한다. 두 작업 모두 현재 API와 저장 형식을 유지한 채 진행할 수 있다.

## 현재 구조

| 위치 | 역할과 진입점 |
|---|---|
| `frontend/` | Electron 데스크톱 앱. [메인 프로세스](../frontend/electron/main.ts)가 창, 트레이, 로컬 설정을 관리하고, [React 앱](../frontend/src/App.tsx)이 캘린더와 작업 패널을 구성한다. |
| `mobile-pwa/` | 별도 React/Vite 앱. [진입점](../mobile-pwa/src/main.tsx)이 로그인, 오늘, 캘린더, 설정 화면을 구성한다. [월 캐시](../mobile-pwa/src/month-cache.ts)와 [웹 푸시](../mobile-pwa/src/push.ts)는 별도 모듈에 있다. |
| `backend/` | [FastAPI 진입점](../backend/app/main.py)이 라우터를 등록한다. 서비스가 업무 규칙을 적용하고 저장소가 Supabase를 조회한다. |
| `supabase/migrations/` | 목표·마일스톤·설정·푸시의 스키마 변경과 완료 상태 동기화 RPC를 관리한다. [완료 동기화 마이그레이션](../supabase/migrations/202608270001_add_completion_rpc_functions.sql) |
| `tests/`, 각 앱의 테스트, `.github/workflows/` | 백엔드 테스트는 루트 `tests/`에 있다. 데스크톱과 모바일은 각 패키지에서 테스트를 실행한다. [CI](../.github/workflows/ci.yml)는 백엔드와 데스크톱을 실행한다. |

## 먼저 분리할 부분

### 1. 데스크톱 캘린더의 데이터 갱신

`calendarStore.ts`는 보기 모드, 표시 날짜, 선택 날짜, 주 시작 요일을 보관한다. 검토 당시 월·주 조회, 날짜 상세 캐시, 사전 로딩, 늦게 도착한 응답 차단은 `App.tsx`에 있었다. 목표나 마일스톤을 수정하면 같은 파일에서 화면 데이터와 캐시를 함께 갱신했다. [보기 상태](../frontend/src/store/calendarStore.ts#L7) · [조회와 사전 로딩](../frontend/src/calendar/useCalendarData.ts#L262) · [완료 상태 갱신](../frontend/src/calendar/calendarUpdates.ts#L182)

1. 먼저 목표·마일스톤 변경을 달력과 날짜 상세 데이터에 반영하는 순수 함수를 캘린더 모듈로 옮긴다. 함수 입력과 결과를 유지한 채 옮기면 조회 타이밍이나 화면 상태를 건드리지 않고 검증할 수 있다.
2. 다음 변경에서 조회·캐시·사전 로딩·무효화를 하나의 캘린더 데이터 모듈에서 관리한다. 보기 상태는 기존 `calendarStore.ts`에 둔다. 데이터 모듈은 월·주 키, 주 시작 요일, 사용자 전환 시 캐시 초기화, 변경 도중 시작된 조회의 결과를 버리는 규칙을 함께 다룬다.

기존 테스트로 날짜가 바뀌어도 탐색 중인 월이 유지되는지, 낙관적 변경이 실패하면 해당 항목만 복구되는지, 이전 계정의 응답이 폐기되는지 확인한다. 월·주 화면, 날짜 상세, 오늘 패널에 같은 변경이 반영되어야 한다. [데스크톱 앱 테스트](../frontend/src/App.test.tsx) · [성능 비교 스크립트](../scripts/perf.ps1)

### 2. 모바일 빌드를 CI에 추가하고 화면을 분리

`main.tsx` 한 파일에서 세션 복원과 초기 데이터 로딩을 조율하고, 로그인·오늘·캘린더·설정 화면을 렌더링한다. 설정 화면에는 브라우저 푸시 권한, 구독 설정, 테스트 알림, 로그아웃 처리도 들어 있다. 모바일 패키지에 테스트와 빌드 명령이 있지만 현재 CI는 실행하지 않는다. [앱 초기화](../mobile-pwa/src/App.tsx#L28) · [설정 화면](../mobile-pwa/src/screens/SettingsView.tsx#L9) · [모바일 명령](../mobile-pwa/package.json) · [CI](../.github/workflows/ci.yml)

모바일 작업은 CI에서 `npm ci`, `npm test`, `npm run build`를 실행하는 것부터 시작한다. 이후 `SettingsView`를 먼저 옮기고, 로그인·오늘·캘린더 화면을 차례로 분리한다. `main.tsx`는 React 마운트를 맡고, 앱 컴포넌트는 세션 복원, 초기 로딩, 탭 전환을 맡는다. 기존 `api.ts`, `month-cache.ts`, `push.ts`는 각 화면에서 사용한다.

기존 테스트는 세션 갱신·계정 전환·캐시·자정 전환을 확인한다. 화면을 옮긴 뒤에는 해시 주소로 탭 열기, 초기 로딩 실패 후 재시도, 설정의 푸시 켜기·끄기와 테스트 알림도 확인한다. [모바일 테스트](../mobile-pwa/tests/mobile.test.mjs) · [PWA 동작과 운영](mobile-pwa.md)

## 다음 순서

### 3. Gemini 초안의 입력 경계와 검증 분리

`ai_schedule_service.py`가 Gemini 요청, 프롬프트, 공급자용 응답 스키마, JSON 정규화, 일정 규칙 검증, 편집용 필드를 한곳에서 처리한다. 파서와 검증 함수는 모두 `dict[str, Any]`를 다루고, HTTP 응답에는 별도의 Pydantic 모델이 있다. [AI 초안 서비스](../backend/app/services/ai_schedule_service.py#L28) · [HTTP 스키마](../backend/app/schemas/ai_schedule_schemas.py)

공급자 응답을 읽고 필드 형태를 확인하는 코드를 한곳에 둔다. 파싱이 끝나면 날짜 제약과 선호 요일 같은 일정 규칙은 타입이 정해진 초안을 받아 검사한다. 서비스에는 Gemini 호출과 편집용 응답 조립 순서를 남긴다. 기존 실패 코드, 경고, 동의 확인, 사용자 확인 후 저장하는 흐름을 유지한다. [서비스 테스트](../tests/test_ai_schedule_service.py) · [라우터 테스트](../tests/test_ai_schedule_routes.py) · [AI 초안 저장 책임](ai.md)

### 4. 두 클라이언트의 공통 API 응답 타입

데스크톱과 모바일이 `AuthSession`, `Goal`, `Milestone`, 월·날짜별 캘린더 응답을 각각 선언한다. 서버 필드가 바뀌면 두 선언과 두 호출부를 확인해야 한다. FastAPI 스키마를 기준으로 두 앱이 쓰는 응답부터 비교하고, 동일한 응답만 OpenAPI에서 파생한 타입으로 맞춘다. 생성 결과가 실제 배포 빌드와 두 테스트에서 소비되는지 확인한 뒤 범위를 넓힌다. [데스크톱 타입](../frontend/src/api/types.ts) · [모바일 타입](../mobile-pwa/src/types.ts) · [서버 캘린더 스키마](../backend/app/schemas/calendar_schemas.py)

세션과 날짜는 앱마다 상이한 동작을 유지한다. 데스크톱은 Electron 보안 저장소와 사용자 설정 시간대를 사용한다. 모바일은 브라우저 저장소, 탭 간 갱신 잠금, 기기의 날짜를 사용한다. [데스크톱 API 클라이언트](../frontend/src/api/client.ts) · [데스크톱 날짜 유틸](../frontend/src/utils/date.ts) · [모바일 API 클라이언트](../mobile-pwa/src/api.ts) · [모바일 날짜 유틸](../mobile-pwa/src/date.ts)

### 5. 캘린더 라우터 파일명 정리

Python 파일명 `calender.py`와 공개 경로 `/calendar`의 철자가 다르다. 해당 라우터를 수정할 때 파일과 `main.py`의 import 이름, 백엔드 README의 경로를 함께 정리한다. 공개 경로는 유지하고 라우터 테스트로 확인한다. `external_calender.py`에는 엔드포인트가 없다. 제거 여부는 외부 캘린더 기능을 결정할 때 다룬다. [캘린더 라우터](../backend/app/api/routers/calendar.py) · [라우터 등록](../backend/app/main.py#L97) · [API 문서](api.md)

## 변경 범위

데스크톱, 모바일, 백엔드, SQL 마이그레이션의 현재 패키지 구분은 유지한다. 각 단계는 기존 앱에서 동작을 확인할 수 있는 단위로 진행한다. 캘린더 갱신과 AI 초안 정리는 API 응답이나 DB 스키마 변경 없이 진행할 수 있다. 기존 목표·마일스톤 완료 동기화는 사용자 범위를 적용하는 서버 RPC에 남긴다. [현재 아키텍처](architecture.md)
