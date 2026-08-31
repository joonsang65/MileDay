# MileDay Docs

이 폴더는 MileDay의 최신 문서 입구다. 평소에는 아래 6개 문서만 읽고, 과거 의사결정과 상세 로그는 `archive/`에서 확인한다.

## 현재 기준 문서

| 문서 | 책임 |
|---|---|
| [product.md](product.md) | 제품 목표와 범위 |
| [architecture.md](architecture.md) | 시스템 구조, 저장소, 인증/권한, 안정성 원칙 |
| [api.md](api.md) | 현재 FastAPI endpoint |
| [ai.md](ai.md) | AI 일정 초안의 책임 경계 |
| [operations.md](operations.md) | 실행, 테스트, 패키징, 문제 해결 |
| [changelog.md](changelog.md) | 변경 이력과 성능 개선 요약 |

## 보관 문서

| 위치 | 내용 |
|---|---|
| [archive/reference/](archive/reference/) | 기존 요구사항, 데이터 흐름, DB, API, 로그, troubleshooting, 작업 규칙 문서 |
| [archive/decisions/](archive/decisions/) | ADR 원문 |
| [archive/milestones/](archive/milestones/) | 마일스톤별 구현 계획과 결과 |
| [archive/performance/](archive/performance/) | 성능 리포트 원문 |

## 관리 기준

- 최신 기준은 top-level 문서 6개에만 둔다.
- archive 문서는 과거 판단 근거로 보관하고, 새 구현 기준으로 직접 수정하지 않는다.
- API endpoint는 `api.md`, DB/인증 구조는 `architecture.md`, AI 경계는 `ai.md`, 실행법은 `operations.md`만 갱신한다.
