# MileDay Changelog

이 문서는 사용자 피드백과 성능 개선 중심의 변경 이력 요약이다.

현재 `frontend/package.json` 버전은 `0.1.3`이다. `v0.1.4` 항목은 다음 릴리스 후보 또는 진행 중 변경으로 관리한다.

## v0.1.0

- 마일스톤 완료 처리 후 UI 흔들림을 줄이기 위해 낙관적 갱신과 rollback을 적용했다.
- 관련 원문: [archive/reference/user_feedback_changes.md](archive/reference/user_feedback_changes.md)

## v0.1.1

- 헤더/달력 영역 sticky 처리로 스크롤 중 날짜 맥락을 유지했다.
- 전체 목표 관리 모달을 추가했다.
- 글자 크기 설정 범위와 목표/마일스톤 색상 동기화를 개선했다.

## v0.1.2

- 작은 노트북 화면과 Windows 배율에서 UI가 깨지는 문제를 줄였다.
- 하루 보기를 floating panel 흐름으로 정리했다.
- 전체 목표 조회를 `/goals/with-milestones` 통합 API로 개선했다.

## v0.1.3

- 전체 목표 통합 조회와 완료 처리 성능을 측정했다.

## v0.1.4 후보

- 주요 패널 글자 확대 옵션을 추가했다.
- 캘린더 최소 창 크기를 `420x300`으로 낮췄다.
- 일요일 시작 기본값과 토요일/일요일 색상 구분을 정리했다.
- Gemini 전송 동의와 계정 삭제 API를 추가했다.

## 성능 개선 요약

- GET API 재시도와 cache/fallback으로 사용자-facing 5xx를 줄였다.
- 설정 조회와 월간 캘린더 조회에 TTL cache를 적용했다.
- 목표 완료와 마일스톤 완료 동기화를 RPC와 UI 갱신 흐름으로 보강했다.
- 원문은 [archive/reference/user_feedback_changes.md](archive/reference/user_feedback_changes.md), [archive/performance/](archive/performance/)에 보관한다.
