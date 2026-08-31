# MileDay Docs

이 폴더는 MileDay의 요구사항, 설계, 구현 결정, 성능 개선, 사용자 피드백, 장애 대응 기록을 모아 둔 문서 인덱스다. 처음 프로젝트를 보는 사람은 루트 README로 제품 개요를 본 뒤, 이 문서에서 관심 영역의 상세 문서로 이동하면 된다.

## 추천 읽기 순서

1. [requirements.md](requirements.md): MVP 기능 범위와 마일스톤 기준
2. [data_flow.md](data_flow.md): 프론트엔드, 백엔드, Supabase 사이의 데이터 흐름
3. [db_schema.md](db_schema.md): Supabase Auth, goals, milestones, user_settings 구조
4. [api_spec.md](api_spec.md): 프론트엔드와 FastAPI 사이의 API 계약
5. [decisions/README.md](decisions/README.md): AI, 프롬프트, UI, 성능 관련 의사결정 흐름
6. [performance_report._v3.md](performance_report._v3.md): 최신 성능 개선 결과
7. [user_feedback_changes.md](user_feedback_changes.md): 사용자 피드백 기반 변경 이력
8. [troubleshooting.md](troubleshooting.md): 실제 문제 증상, 원인, 대응 기록

## 문서 분류

| Category | Documents | Purpose |
|---|---|---|
| Requirements | [requirements.md](requirements.md), [milestones/](milestones/) | 기능 범위와 단계별 구현 계획 |
| Architecture | [data_flow.md](data_flow.md), [db_schema.md](db_schema.md) | 앱, API, DB, 로컬 저장소의 구조 |
| API | [api_spec.md](api_spec.md) | FastAPI endpoint와 요청/응답 계약 |
| AI / ADR | [decisions/](decisions/), [decisions/README.md](decisions/README.md) | 모델 평가, 프롬프트, AI 일정 생성 구조, 주요 설계 결정 |
| Performance | [performance_report._v1.md](performance_report._v1.md), [performance_report._v2.md](performance_report._v2.md), [performance_report._v3.md](performance_report._v3.md) | 사용자 체감 성능, API 안정성, 개선 전후 측정 |
| Feedback | [user_feedback_changes.md](user_feedback_changes.md) | 실제 피드백에서 출발한 UI/UX 및 기능 개선 |
| Reliability | [troubleshooting.md](troubleshooting.md), [error_logging.md](error_logging.md) | 장애 원인 분석, 예외 처리, 로그 기준 |
| Collaboration | [codex_rules.md](codex_rules.md), [commit_guide.md](commit_guide.md) | Codex 작업 규칙과 커밋 메시지 기준 |

## 빠른 링크

### AI Engineering

- [ADR 인덱스](decisions/README.md)
- [API LLM 최종 선택](decisions/0011-API_LLM_선정.md)
- [Structured Output 기반 flash-lite prompt 개선 계획](decisions/0013-구조화_출력_프롬프트.md)
- [AI 일정 생성 UI 구현 계획](decisions/0014-AI_일정_생성_UI_구현_계획.md)

### Performance

- [성능 개선 보고서 v3](performance_report._v3.md)
- [전체 목표 조회 및 완료 처리 최적화](decisions/0021-전체_목표_조회_및_완료_처리_최적화.md)

### Product Improvement

- [사용자 피드백 기반 변경 이력](user_feedback_changes.md)
- [물리 화면 대응 크기 조정 및 중복 정의 정리](decisions/0020-물리_화면_대응_크기_조정_및_중복_정리.md)
- [트러블 슈팅 기록](troubleshooting.md)

## 문서 사용 기준

- 실제 구현 확인은 `backend/`, `frontend/`, `supabase/migrations/` 코드를 우선한다.
- 과거 설계 문서에는 현재 endpoint명과 다른 초안 표현이 남아 있을 수 있다.
- 변경 작업 전에는 관련 ADR과 troubleshooting 항목을 먼저 확인하면 같은 문제를 반복할 가능성을 줄일 수 있다.
