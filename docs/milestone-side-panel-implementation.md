# 마일스톤 표시 및 오늘 사이드 패널 구현 보고

2026-10-15 현재 체크아웃된 작업 트리에 반영했다. 작업 시작 당시 기존 로컬 변경 사항은 없었으며, 변경 사항은 기능별 커밋과 문서 커밋으로 나눈다. 배포·운영 DB 변경은 수행하지 않았다.

## 기존 구조와 재사용한 로직

`App.tsx`는 월간·주간 캘린더 캐시와 날짜 상세 캐시를 관리하고, `handleToggleMilestone()`에서 완료 API를 호출한다. 백엔드의 기존 `complete_and_sync_goal` RPC가 마일스톤과 목표의 완료 상태를 함께 저장한다. 이 API와 RPC를 그대로 사용했다.

기존 `TodayList`는 단순한 마일스톤 목록이므로 목표 그룹, 날짜별 조회 상태, 재시도가 필요한 새 패널은 별도 `TodaySidePanel`로 구현했다. 완료 상태 변경은 기존 App 캐시 갱신 경로에 연결했고 별도 저장 API나 DB 경로를 추가하지 않았다. 기존 날짜 상세 오버레이와 전체 목표 관리 화면은 유지했다.

기존 목표 완료 추정은 현재 조회한 일부 마일스톤만 참조할 수 있어 제거했다. 마일스톤 저장 이후 기존 목표 조회로 서버의 목표 완료 상태를 다시 반영한다. 목표 관리 화면에는 App의 완료 변경과 저장 중인 ID를 전달한다.

## 기능별 변경

- 월간·주간 셀은 마일스톤을 각각 표시한다. 표시 제한은 텍스트 3개, 색상 점 5개를 유지하며, 긴 제목에 말줄임과 전체 제목 툴팁을 제공한다. 해당 날짜에 마일스톤이 없는 목표는 별도의 `마감:` 일정으로 표시한다.
- 일일 Web Push는 사용자 타임존 기준 오늘의 미완료 마일스톤만 대상으로 한다. 결정적인 순서로 최대 두 제목을 보여주며 각 제목을 35자 이내로 줄이고 나머지는 개수로 요약한다. 목표만 있거나 모든 마일스톤이 완료되면 발송을 생략한다. 시간 설정, 중복 발송 방지, Today 링크는 유지했다. 기존 Windows 네이티브 알림 경로는 없어 새로 만들지 않았다.
- `오늘의 사이드 패널` / `Today's side panel` 설정은 기본값 false다. 기존 Electron `ui-settings.json`에 저장되며 필드가 없는 이전 파일과 호환된다. 기존 글꼴·투명도·창 위치와 크기를 보존하며, 저장 실패 시 새 옵션만 되돌리고 오류를 표시한다.
- 패널은 선택한 날짜 및 달과 독립적으로 사용자 타임존의 오늘을 표시한다. 자정, 창 포커스, 표시 상태 복귀 시 날짜를 확인한다. 활성화 시 공유 날짜 캐시를 우선 사용하고 필요할 때 기존 날짜 조회 API를 호출한다. 생성·수정·삭제 이후에는 오늘 데이터도 갱신한다.
- 오늘 마감인 목표와 오늘 마일스톤의 상위 목표를 한 그룹씩 표시한다. 목표 제목은 읽기 전용이고 마일스톤에만 완료 토글을 제공한다. 진행 수치, 로딩, 빈 상태, 오류 및 재시도를 지원한다.
- 900px 이상에서는 패널을 오른쪽에 배치한다. 그보다 좁은 창에서는 캘린더 폭을 유지하고 오른쪽 패널을 펼치거나 접을 수 있다. 패널 내부 스크롤과 기존 창 크기 제한을 유지했다.
- 완료 토글은 즉시 모든 연결된 캐시에 반영하며 실패하면 해당 항목만 이전 상태로 되돌린다. 같은 ID의 중복 요청은 차단하고 다른 마일스톤은 계속 조작할 수 있다. 먼저 시작된 조회 응답과 이전 계정 응답을 검사해 변경 사항이나 새 계정 데이터를 덮어쓰지 못하게 한다. 저장 후에도 항목 순서를 유지한다.
- 기존 목표 선택 목록에서만 `deadline >= today`인 목표를 허용한다. 완료 여부와 선택 날짜는 필터에 영향을 주지 않는다. 만료·삭제된 선택은 초기화하고 제출을 막으며, 기한을 연장하면 다시 선택할 수 있다. 전체 목표 조회와 기존 마감일 자동 연장은 유지했다.

## 수정·생성 파일

| 파일 | 역할 |
| --- | --- |
| `frontend/src/App.tsx` | 오늘 날짜·조회 상태, 공유 캐시 갱신, 완료 저장·롤백·동시성, 계정 초기화, 설정 저장 연결 |
| `frontend/src/components/TodaySidePanel.tsx` | 오늘 목표 그룹, 진행 수치, 완료 토글, 조회 상태 UI (신규) |
| `frontend/src/components/CalendarBoard.tsx` | 월간·주간 마일스톤 표시와 마감 목표 보조 표시 |
| `frontend/src/components/DateDetail.tsx` | 저장 중인 마일스톤 토글 비활성화 |
| `frontend/src/components/GoalListModal.tsx` | 공유 완료 변경과 저장 중 상태 반영, 전체 마일스톤 문맥 전달 |
| `frontend/src/components/ManualCreatePanel.tsx` | 유효한 기존 목표 선택, 선택 무효화 및 제출 차단 |
| `frontend/src/components/SettingsPanel.tsx` | 한영 옵션과 로컬 저장 실패 표시 |
| `frontend/src/types/localUiSettings.ts` | 로컬 설정 필드와 false 기본값 |
| `frontend/electron/main.ts` | 설정 읽기·쓰기·IPC, 이전 파일 호환 |
| `frontend/electron/preload.ts` | 새 설정 저장 IPC 노출 |
| `frontend/src/vite-env.d.ts` | Electron API 타입 확장 |
| `frontend/src/utils/date.ts` | 사용자 타임존의 날짜 키 계산 |
| `frontend/src/styles.css` | 넓은 창·좁은 창 패널, 스크롤과 완료 스타일 |
| `backend/app/services/notification_scheduler.py` | 미완료 마일스톤 제목 요약 알림 |
| `frontend/src/App.test.tsx` | 패널 및 완료 처리 통합 회귀 테스트 (신규) |
| `frontend/src/components/ManualCreatePanel.test.tsx` | 만료 목표·기한 연장·선택 삭제 검증 (신규) |
| `frontend/electron/uiSettings.test.ts` | 기존 설정 호환·재시작 복원·저장 실패 검증 (신규) |
| `frontend/src/components/CalendarBoard.test.tsx` | 새 표시 정책, 두 캘린더 모드와 마감 보조 표시 검증 |
| `frontend/src/components/SettingsPanel.test.tsx` | 로컬 옵션 호출 검증 |
| `frontend/src/utils/date.test.ts` | 사용자 타임존의 자정 경계 검증 |
| `tests/test_notification_scheduler.py` | 제목 요약·길이·정렬·미완료·타임존·발송 생략 검증 |
| `frontend/scripts/verify-today-panel-layout.mjs` | 실제 빌드 화면의 패널·스크롤·토글·접기 검증 (신규) |
| `docs/milestone-side-panel-implementation.md` | 구현 및 검증 보고 (신규) |

## API·DB·의존성

HTTP API, DB 스키마, Supabase 마이그레이션, 의존성 변경은 없다. 기존 `GET /calendar/date/{date}`, 월간·주간 캘린더 조회, 목표 조회 및 `PATCH /milestones/{id}/complete`를 사용한다. 로컬 Electron IPC와 UI 설정 필드만 확장했다.

## 검증 결과

| 검증 | 결과 |
| --- | --- |
| `npm.cmd run lint` (frontend) | 통과 |
| `npm.cmd test -- --reporter=dot --maxWorkers=2` (frontend) | 16개 파일, 81개 테스트 통과 |
| `npm.cmd run build` (frontend) | TypeScript `tsc --noEmit` 및 Electron main/preload/renderer 빌드 통과 |
| `python -m pytest -q` (저장소 루트) | 125개 통과, integration 1개 제외; 커버리지 90.90% |
| `node scripts/verify-compact-layout.mjs` (frontend) | 기존 compact 레이아웃 검증 통과 |
| `node scripts/verify-today-panel-layout.mjs` (frontend) | 420×300, 640×480, 980×760에서 패널 위치·캘린더 폭·내부 스크롤·완료 토글·접기 검증 통과 |
| `git diff --check` | 통과 |

새 테스트는 기본 비활성화, 다른 날짜와 달 선택, 목표 그룹 중복 방지, 낙관적 완료와 실패 롤백, ID별 중복 차단, 서로 다른 마일스톤 동시 성공·실패, 서버 최종 완료 값, 자정 전환, 조회 재시도, 설정 저장 실패 복원, 계정 전환 중 늦은 응답, 미래 날짜 선택 중 오늘 마일스톤 생성, 마일스톤 없는 마감 목표를 포함한다.

화면 검증 스크린샷은 `artifacts/today-panel/420x300.png`, `640x480.png`, `980x760.png`에 저장했다. 화면 검증에서는 Electron 브리지와 API를 모의 처리했으며 실제 빌드된 renderer를 사용했다.

## 미실행 항목과 적용 방법

실제 Supabase 통합 테스트는 프로젝트 기본 설정대로 제외했다. 운영 DB 저장 후 실제 앱 재실행, 설치된 Windows 앱의 네이티브 동작, 실제 휴대폰 Web Push 수신은 실행하지 않았다. Electron 설정 테스트에서는 파일 저장과 재시작을 모의 검증했고 기존 백엔드 완료 API/RPC 경로는 기존 단위 테스트로 검증했다.

새 환경 변수나 개발자 수동 마이그레이션은 필요 없다. 업데이트한 Windows 앱의 설정에서 `오늘의 사이드 패널`을 켜면 사용할 수 있다. 실제 사용자 환경에는 변경된 프론트엔드 및 백엔드의 기존 배포 절차를 적용해야 한다.

최종 자동 검증에서 남은 실패는 없다. 실제 기기와 운영 데이터에 대한 위 검증은 별도로 남아 있다.
