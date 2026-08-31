# M9. 배포 준비와 문서화 진행 요약

M9는 정식 배포와 기술 문서 정리 단계다. 현재는 `v0.1.3`까지의 구현 내용을 기준으로 패키징 준비와 포트폴리오 문서화를 진행했고, 정식 운영 전환은 아직 대기 중이다.

## 상태

| 항목 | 상태 | 기준 |
|---|---|---|
| Electron 패키징 설정 | 진행 | `electron-builder`, Windows NSIS 설정, 앱 아이콘, package 검증 script를 준비했다. |
| 포트폴리오 README | 진행 | 루트/프론트엔드/백엔드 README와 스크린샷을 정리했다. |
| docs 구조 정리 | 진행 | 최신 기준 문서 6개와 archive 구조로 압축했다. |
| 성능 개선 기록 | 진행 | 전체 목표 조회, 완료 동기화, GET retry/cache/fallback 결과를 요약했다. |
| 정식 운영 배포 | 미진행 | main 반영은 완료했지만 운영 서버 전환과 smoke test는 아직 남아 있다. |
| Windows 승인 | 대기 | Windows 배포 또는 실행 과정에서 필요한 승인/검증 절차는 아직 완료되지 않았다. |

## v0.1.3 기준 포함 내용

- 목표/마일스톤 CRUD와 완료 처리
- 월간/주간 캘린더, 날짜 상세, 오늘 할 일
- 계정 설정과 로컬 UI 설정
- AI 일정 초안 생성과 Gemini 전송 동의
- 전체 목표 통합 조회와 완료 동기화 성능 개선
- Electron 위젯 창, tray, safeStorage token, 자동 실행 설정

## 운영 전환 전 확인

- 운영 Supabase에는 새 migration만 적용하고, 기존 migration 수정분은 직접 적용 대상으로 보지 않는다.
- `drop_unused_user_settings_columns`는 사용자 설정 데이터 삭제 가능성이 있어 안정화 후 별도 판단한다.
- main 서버를 기존 Supabase에 연결해 병렬 기동한 뒤 로그인, 조회, 생성, 수정, 완료, 설정, AI 초안 생성을 smoke test한다.
- smoke test 후 API 주소 또는 배포 target을 main으로 전환한다.
