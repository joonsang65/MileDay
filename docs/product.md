# MileDay Product

MileDay는 Windows 바탕화면에 띄워 두는 개인 일정 위젯이다. 사용자는 목표를 만들고, 목표를 마일스톤으로 나누고, 캘린더에서 날짜별 할 일을 확인한다.

## 목표

- 목표와 마감일을 캘린더에서 바로 확인한다.
- 목표 아래 마일스톤을 날짜별로 배치한다.
- 작은 데스크톱 위젯 창에서도 핵심 일정이 보이게 한다.
- AI는 자동 실행자가 아니라 사용자가 편집할 일정 초안을 만드는 보조 도구로 둔다.

## 범위

| 영역 | 포함 |
|---|---|
| Auth | 계정 생성, 로그인, 로그아웃, 계정 삭제 |
| Goal | 목표 CRUD와 완료 처리 |
| Milestone | 마일스톤 CRUD와 완료 처리 |
| Calendar | 월간/주간 캘린더, 날짜 상세, 오늘 할 일 |
| Settings | 계정 기준 앱 설정과 로컬 UI 설정 |
| Desktop | Windows 위젯 창과 tray |
| AI | 편집 가능한 일정 초안 생성 |

## 제외 또는 후순위

- 외부 캘린더 실시간 동기화
- AI의 자동 DB 수정
- 복잡한 반복 일정 occurrence 편집
- 팀/공유 캘린더
- 모바일 앱

## 제품 원칙

- 작은 화면에서도 캘린더와 하루 보기가 먼저 읽혀야 한다.
- AI 결과는 사용자가 확인하고 수정한 뒤에만 저장한다.
- 사용자 피드백은 기능 추가보다 사용 흐름 단순화에 우선 반영한다.

상세 API는 [api.md](api.md), AI 책임 경계는 [ai.md](ai.md), 피드백 상세는 [archive/reference/user_feedback_changes.md](archive/reference/user_feedback_changes.md)에 둔다.
