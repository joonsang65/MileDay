# Codex 실행 지시서: BMAD Lite + Harness Engineering 도입

## 0. 목적

현재 저장소에 **BMAD Lite 방식의 기획·작업 관리 체계**와 **Codex용 Harness Engineering 환경**을 도입한다.

이 문서는 Codex가 아래 작업을 실제 저장소에 적용하기 위한 실행 명세다.

핵심 역할은 다음과 같이 분리한다.

```text
BMAD Lite
→ 프로젝트 목적, 요구사항, 아키텍처, Epic, Story 정의

Codex
→ Story 단위 코드·테스트·문서 구현

Harness Engineering
→ Codex가 안정적으로 작업할 수 있도록
   지침, 문맥, 검증 명령, 상태 기록, 실패 분류, 완료 증거를 구성
```

대상 프로젝트는 한국어 및 멀티링구얼 로컬 LLM 5종을 다음 기준으로 평가하는 파이프라인이다.

- 공개 한국어 벤치마크 4종
  - KMMLU-Pro
  - KoBALT-700
  - CLIcK
  - IFEval-Ko
- 모델 추론·출력 성능
- MileDay 전용 테스트셋 평가
  - 구조화 출력 성공률
  - 일정 제약 준수율
  - 의미 적합도

---

# 1. 최우선 원칙

Codex는 작업을 시작하기 전에 반드시 현재 저장소를 조사해야 한다.

## 금지 사항

- 기존 파일 구조를 확인하지 않고 새 구조를 강제로 덮어쓰지 않는다.
- 존재하지 않는 모델 태그, 명령어, 데이터셋 필드를 추측하지 않는다.
- BMAD 관련 패키지나 CLI를 최신 상태라고 가정하지 않는다.
- 실제 실행하지 않은 테스트를 통과했다고 기록하지 않는다.
- 기존 명세를 삭제하거나 의미를 바꾸지 않는다.
- Story 범위 밖의 대규모 리팩터링을 하지 않는다.
- 테스트를 삭제하거나 약화하여 통과시키지 않는다.
- 생성되지 않은 평가 결과를 예시 수치처럼 작성하지 않는다.
- 사용자 확인 없이 기존 코드나 문서를 대량 삭제하지 않는다.

## 충돌 처리

기존 문서와 코드가 충돌하면 다음 순서로 판단한다.

1. 현재 Story의 Acceptance Criteria
2. 최신 Architecture Decision Record
3. Architecture 문서
4. PRD
5. Product Brief
6. 기존 코드

충돌이 해소되지 않으면 임의로 결정하지 말고 다음을 보고한다.

- 충돌한 파일
- 충돌 내용
- 가능한 선택지
- 추천안
- 작업을 진행할 수 있는 안전한 최소 범위

---

# 2. 실행 전 저장소 조사

먼저 아래 작업을 수행한다.

1. 저장소 루트와 주요 디렉터리를 확인한다.
2. 다음 파일이 존재하는지 확인한다.
   - `README.md`
   - `AGENTS.md`
   - `pyproject.toml`
   - `requirements.txt`
   - `package.json`
   - 기존 명세 문서
   - `.github/workflows/`
   - `_bmad/`
   - `_bmad-output/`
   - `.agents/skills/`
3. Git 상태를 확인한다.
4. 현재 테스트 명령을 확인한다.
5. 현재 lint, type check, formatter 설정을 확인한다.
6. 기존 평가 명세 파일을 찾아 내용을 읽는다.
7. BMAD가 이미 설치되어 있다면 버전과 생성 파일을 확인한다.

조사 후 코드 변경 전에 아래 형식으로 계획을 먼저 제시한다.

```md
## 저장소 조사 결과

- 현재 구조:
- 기존 BMAD 자산:
- 기존 Codex 지침:
- 기존 테스트 도구:
- 유지해야 할 파일:
- 예상 충돌:

## 작업 계획

1.
2.
3.

## 생성 또는 수정 예정 파일

-
-

## 위험 요소

-
-
```

---

# 3. 목표 디렉터리 구조

기존 구조와 충돌하지 않는 범위에서 다음 체계를 구성한다.

```text
project-root/
├─ AGENTS.md
├─ _bmad/
├─ _bmad-output/
│  ├─ planning-artifacts/
│  │  ├─ product-brief.md
│  │  ├─ prd.md
│  │  ├─ architecture.md
│  │  └─ epics.md
│  └─ implementation-artifacts/
│     ├─ sprint-status.yaml
│     ├─ stories/
│     └─ completion-reports/
├─ .agents/
│  └─ skills/
│     └─ bmad-implement-story/
│        ├─ SKILL.md
│        └─ templates/
│           └─ completion-report.md
├─ docs/
│  └─ decisions/
├─ src/
├─ tests/
├─ artifacts/
└─ .github/
   └─ workflows/
      └─ evaluation-harness.yml
```

## 주의

- 기존 프로젝트 구조가 다르면 현재 구조에 맞게 경로를 조정한다.
- 경로를 조정한 경우 모든 문서 링크와 `AGENTS.md`를 함께 수정한다.
- BMAD 공식 설치 결과가 다른 폴더를 사용하면 실제 생성 구조를 존중한다.
- 빈 디렉터리만 만들지 말고 필요한 최소 문서를 함께 작성한다.

---

# 4. BMAD 적용 수준

BMAD 전체 프로세스를 무겁게 도입하지 않는다. 아래 네 가지 산출물만 우선 구성한다.

```text
Product Brief
PRD
Architecture
Epic / Story
```

이를 **BMAD Lite**로 정의한다.

## 역할

| 산출물 | 목적 |
|---|---|
| Product Brief | 프로젝트의 문제, 사용자, 목표, 성공 기준 |
| PRD | 기능 요구사항, 비기능 요구사항, 범위 |
| Architecture | 시스템 구조, 모듈 경계, 데이터 흐름, 기술 결정 |
| Epic / Story | Codex가 한 번에 수행할 수 있는 구현 단위 |

---

# 5. 기존 명세 분해

현재 저장소에 있는 로컬 LLM 평가 명세를 읽고 다음 문서로 분해한다.

## 5.1 `product-brief.md`

포함할 내용:

- 프로젝트 배경
- 해결하려는 문제
- 대상 사용자
- 왜 로컬 LLM을 평가하는가
- 왜 한국어 평가가 필요한가
- 평가 대상 모델 5종
- 최종 의사결정 목표
- 성공 기준
- 제외 범위

### 성공 기준 예시

- 동일 조건에서 5개 모델 평가 가능
- 공개 벤치마크 4종 실행 가능
- 시스템 성능 측정 가능
- MileDay 테스트셋 3개 핵심 지표 계산 가능
- 재현 가능한 artifact 생성
- Hard Gate 기반 최종 후보 선정 가능

---

## 5.2 `prd.md`

포함할 내용:

### 기능 요구사항

- 모델 registry
- Ollama runtime
- 공개 benchmark adapter
- 성능 monitor
- MileDay dataset loader
- deterministic validator
- semantic evaluator
- 결과 저장
- resume
- report 생성
- CLI

### 비기능 요구사항

- 재현성
- 구성 가능성
- 장애 복구
- raw output 보존
- Windows 호환
- 단위 테스트
- 모델 및 데이터셋 버전 기록
- 낮은 결합도
- 런타임 확장 가능성

### 범위 외

- 모델 파인튜닝
- 운영 서비스 배포
- 다중 GPU 최적화
- 실제 사용자 트래픽 A/B 테스트
- 자동 모델 다운로드 및 라이선스 승인

---

## 5.3 `architecture.md`

포함할 내용:

```text
CLI
 ↓
Evaluation Orchestrator
 ├─ Runtime Adapter
 │   └─ Ollama Runtime
 ├─ Benchmark Adapter
 │   ├─ KMMLU-Pro
 │   ├─ KoBALT
 │   ├─ CLIcK
 │   └─ IFEval-Ko
 ├─ MileDay Evaluator
 │   ├─ Schema Validator
 │   ├─ Constraint Validator
 │   └─ Semantic Judge
 ├─ Performance Monitor
 │   ├─ GPU Monitor
 │   └─ RAM Monitor
 └─ Reporter
     ├─ Raw Result
     ├─ Summary
     └─ Markdown Report
```

아래 내용을 문서화한다.

- 모듈 책임
- 데이터 흐름
- 요청 단위 결과 스키마
- 설정 파일 구조
- 에러 분류
- 재시도 정책
- resume key
- artifact 구조
- 공식 평가와 Ollama 생성 평가의 차이
- 향후 llama.cpp/vLLM 확장 방식

---

## 5.4 `epics.md`

다음 Epic을 기본으로 구성한다.

### Epic 1: 프로젝트 기반 및 공통 하네스

- 저장소 규칙
- 설정 로더
- 모델 registry
- 결과 스키마
- CLI 기반
- preflight

### Epic 2: 로컬 추론 런타임

- Ollama runtime
- streaming
- TTFT
- token usage
- timeout
- 오류 처리

### Epic 3: 공개 벤치마크

- 공통 MCQ adapter
- KMMLU-Pro
- KoBALT
- CLIcK
- IFEval-Ko

### Epic 4: MileDay 테스트셋 평가

- dataset schema
- output schema
- structured output
- constraint validator
- semantic rubric

### Epic 5: 시스템 성능

- CPU/RAM monitor
- NVML GPU monitor
- cold/warm 측정
- latency percentile
- tok/s

### Epic 6: 결과 집계와 보고서

- Parquet/CSV
- summary
- 오류 분석
- chart
- Markdown report
- 최종 모델 선정

각 Epic은 Codex가 한 번에 완료할 수 있는 Story로 나눈다.

---

# 6. Story 문서 형식

Story 파일은 아래 경로에 둔다.

```text
_bmad-output/implementation-artifacts/stories/
```

파일명 예시:

```text
EVAL-001-project-foundation.md
EVAL-002-model-registry.md
EVAL-003-ollama-runtime.md
```

각 Story는 다음 템플릿을 따른다.

```md
# Story EVAL-XXX: 제목

## Status

ready

## Goal

이 Story에서 달성할 목적.

## Context

관련 배경과 참조 문서.

## Acceptance Criteria

- [ ] 검증 가능한 조건 1
- [ ] 검증 가능한 조건 2
- [ ] 검증 가능한 조건 3

## Out of Scope

- 이번 Story에서 하지 않을 작업

## Expected Files

- 생성 또는 수정할 것으로 예상되는 파일

## Verification

```powershell
실제 실행할 검증 명령
```

## Completion Evidence

완료 시 다음을 기록한다.

- 변경 파일
- 테스트 결과
- Acceptance Criteria별 증거
- 생성 artifact
- 알려진 한계
- 후속 Story
```

---

# 7. 초기 Story 생성

최소 다음 Story를 생성한다.

## EVAL-001: 프로젝트 기반 구조

Acceptance Criteria:

- 프로젝트 패키지 구조가 존재한다.
- 기본 설정 로더가 존재한다.
- 공통 Pydantic schema가 존재한다.
- Typer CLI가 실행된다.
- 기본 단위 테스트가 통과한다.

## EVAL-002: 모델 Registry

Acceptance Criteria:

- 5개 모델이 YAML에서 관리된다.
- 모델 태그가 코드에 하드코딩되지 않는다.
- 필수 필드 누락 시 명확한 validation error가 발생한다.
- 설치 여부를 확인할 수 있다.
- 존재하지 않는 모델을 자동 대체하지 않는다.

## EVAL-003: Ollama Streaming Runtime

Acceptance Criteria:

- 공통 runtime interface를 구현한다.
- streaming 응답을 지원한다.
- TTFT를 기록한다.
- 전체 latency를 기록한다.
- Ollama token/duration metadata를 보존한다.
- timeout과 HTTP 오류를 구분한다.
- mock 기반 단위 테스트가 존재한다.

## EVAL-004: 성능 모니터

Acceptance Criteria:

- 시스템 RAM 사용량을 측정한다.
- 가능하면 Ollama 프로세스 RSS를 측정한다.
- NVML로 VRAM을 샘플링한다.
- peak metric을 계산한다.
- NVML이 없을 때 명확하게 degrade한다.
- 100~250ms 샘플링 간격을 설정 가능하게 한다.

## EVAL-005: 공통 MCQ Adapter

Acceptance Criteria:

- 문제와 선택지 prompt를 생성한다.
- A~J 선택지를 파싱한다.
- 모호한 복수 답변은 invalid 처리한다.
- 정답률과 invalid rate를 계산한다.
- benchmark별 category aggregate를 지원한다.
- parser 단위 테스트가 존재한다.

## EVAL-006 이후

나머지 benchmark와 MileDay 평가 Story도 동일한 형식으로 만든다.

---

# 8. `AGENTS.md` 작성

저장소 루트에 Codex용 공통 지침을 작성한다.

최소 내용은 다음과 같다.

```md
# AGENTS.md

## Project Purpose

이 저장소는 한국어 및 멀티링구얼 로컬 LLM 5개를
공개 벤치마크, 시스템 성능, MileDay 전용 테스트셋으로 평가한다.

## Source of Truth

작업 전 다음 문서를 순서대로 확인한다.

1. 현재 Story
2. `docs/decisions/`의 관련 ADR
3. `_bmad-output/planning-artifacts/architecture.md`
4. `_bmad-output/planning-artifacts/prd.md`
5. `_bmad-output/planning-artifacts/product-brief.md`
6. `_bmad-output/implementation-artifacts/sprint-status.yaml`

## Required Workflow

1. 현재 Story를 읽는다.
2. Acceptance Criteria를 실행 체크리스트로 변환한다.
3. 관련 코드와 테스트를 조사한다.
4. 변경 전에 구현 계획을 제시한다.
5. 최소 범위로 구현한다.
6. 테스트와 검증 명령을 실행한다.
7. 완료 증거를 작성한다.
8. sprint status를 갱신한다.

## Required Verification

프로젝트에 실제 존재하는 도구만 사용한다.

예시:

```powershell
pytest
ruff check .
mypy src
python -m llm_eval preflight
```

벤치마크 변경 시 sample smoke test를 실행한다.

## Constraints

- 모델 태그와 dataset schema를 추측하지 않는다.
- raw 결과를 삭제하거나 덮어쓰지 않는다.
- 공개 benchmark와 자체 test set 결과를 혼합하지 않는다.
- 파싱 실패를 조용히 수정하지 않는다.
- Story 범위 밖의 리팩터링을 하지 않는다.
- 실행하지 않은 테스트를 통과했다고 보고하지 않는다.
- 실제 측정하지 않은 점수를 작성하지 않는다.

## Completion Report

반드시 다음을 포함한다.

- 변경 파일
- 실행한 명령
- 통과한 테스트
- 실패하거나 실행하지 못한 테스트
- Acceptance Criteria별 완료 증거
- 생성 artifact
- 남은 위험과 한계
```

## 중요

- 실제 저장소의 실행 명령을 조사한 뒤 예시를 확정한다.
- 존재하지 않는 `ruff`, `mypy` 등을 무조건 추가하지 않는다.
- 도입하기로 결정했다면 `pyproject.toml`과 CI도 함께 구성한다.

---

# 9. Codex Skill 작성

다음 경로에 Skill을 만든다.

```text
.agents/skills/bmad-implement-story/SKILL.md
```

내용:

```md
---
name: bmad-implement-story
description: BMAD Story를 Acceptance Criteria 기반으로 구현하고 검증한다.
---

# Trigger

사용자가 특정 Story 구현을 요청하거나
`bmad-implement-story`를 명시했을 때 사용한다.

# Workflow

1. 저장소 루트의 `AGENTS.md`를 읽는다.
2. 지정된 Story 문서를 읽는다.
3. 관련 Architecture와 ADR만 추가로 읽는다.
4. Acceptance Criteria를 체크리스트로 변환한다.
5. 기존 코드와 테스트를 조사한다.
6. 변경 계획을 먼저 제시한다.
7. 최소 변경으로 구현한다.
8. Story에 지정된 검증 명령을 실행한다.
9. 실패 원인을 분류한다.
10. completion report를 작성한다.
11. sprint status를 갱신한다.

# Failure Categories

- CODE_ERROR
- TEST_FAILURE
- CONFIG_ERROR
- MODEL_NOT_INSTALLED
- OLLAMA_UNAVAILABLE
- DATASET_UNAVAILABLE
- DATASET_SCHEMA_CHANGED
- PARSER_ERROR
- TIMEOUT
- RESOURCE_EXHAUSTED
- EXTERNAL_DEPENDENCY
- NOT_EXECUTED

# Never

- 테스트를 삭제하거나 약화해 통과시키지 않는다.
- Story 범위를 넘어 대규모 리팩터링하지 않는다.
- 실행하지 않은 명령을 실행했다고 주장하지 않는다.
- 모델 태그나 데이터셋 필드를 추측하지 않는다.
- raw output을 제거하지 않는다.
- 오류를 정상 결과처럼 변환하지 않는다.

# Completion

완료 보고는 `templates/completion-report.md` 형식을 사용한다.
```

---

# 10. Completion Report 템플릿

다음 파일을 만든다.

```text
.agents/skills/bmad-implement-story/templates/completion-report.md
```

내용:

```md
# Story Completion Report

## Story

- ID:
- Title:
- Final Status:

## Summary

수행한 작업 요약.

## Files Changed

- `path`: 변경 내용

## Commands Run

```text
실행 명령
```

## Verification Results

| 검증 | 결과 | 증거 |
|---|---|---|
| Unit tests | PASS/FAIL/NOT_EXECUTED | |
| Lint | PASS/FAIL/NOT_EXECUTED | |
| Type check | PASS/FAIL/NOT_EXECUTED | |
| Smoke test | PASS/FAIL/NOT_EXECUTED | |

## Acceptance Criteria

- [x] AC 1: 증거
- [ ] AC 2: 미완료 이유

## Artifacts

- 생성 파일 경로

## Failures

- Category:
- Description:
- Reproduction:
- Recommended Action:

## Known Risks

-

## Follow-up

-
```

---

# 11. Sprint 상태 관리

다음 파일을 만든다.

```text
_bmad-output/implementation-artifacts/sprint-status.yaml
```

예시:

```yaml
project: local-llm-evaluation
updated_at: null

epics:
  epic_1:
    title: 프로젝트 기반 및 공통 하네스
    status: planned
    stories:
      EVAL-001: ready
      EVAL-002: backlog

  epic_2:
    title: 로컬 추론 런타임
    status: planned
    stories:
      EVAL-003: backlog

  epic_3:
    title: 공개 벤치마크
    status: planned
    stories:
      EVAL-005: backlog
```

상태 enum:

```text
backlog
ready
in_progress
blocked
review
done
```

Codex는 Story 작업 시작 시 `in_progress`, 검증 완료 시 `done`, 외부 문제로 중단되면 `blocked`로 변경한다.

---

# 12. ADR 도입

중요한 설계 결정은 다음 경로에 기록한다.

```text
docs/decisions/
```

초기 ADR:

```text
0001-use-ollama-as-default-runtime.md
0002-separate-official-and-generation-evaluation.md
0003-preserve-raw-model-output.md
0004-use-deterministic-schedule-validation.md
0005-use-bmad-lite-with-codex-harness.md
```

ADR 형식:

```md
# ADR-XXXX: 제목

## Status

accepted

## Context

## Decision

## Consequences

### Positive

### Negative

## Alternatives Considered
```

---

# 13. 하네스 검증 계층

Codex가 구현 완료를 주장하기 전에 다음 계층을 통과하도록 구성한다.

```text
정적 검사
→ 단위 테스트
→ 설정 검증
→ dataset schema 검사
→ mock integration test
→ 실제 Ollama smoke test
→ artifact schema 검사
```

## CI에서 실행할 항목

GPU와 Ollama가 없어도 실행 가능해야 한다.

- unit tests
- lint
- type check
- config validation
- fixture 기반 dataset adapter test
- report schema test

## 로컬 전용 항목

- 실제 Ollama 연결
- 모델 설치 확인
- 실제 추론
- VRAM 측정
- full benchmark
- cold/warm performance

CI에서 GPU가 없다는 이유로 실패하지 않도록 테스트 marker를 분리한다.

예시:

```text
unit
integration
requires_ollama
requires_gpu
slow
```

---

# 14. GitHub Actions

프로젝트에 GitHub Actions를 사용 중이라면 기존 workflow와 충돌하지 않게 통합한다.

파일:

```text
.github/workflows/evaluation-harness.yml
```

목표:

- Python 설치
- 의존성 설치
- lint
- type check
- unit test
- config validation
- offline dataset fixture test

실제 Ollama와 GPU가 필요한 작업은 제외한다.

Codex는 현재 패키지 관리 방식을 확인하여 `pip`, `uv`, `poetry` 중 기존 방식을 유지한다.

---

# 15. 실패 분류와 기록

모든 실패를 다음 enum 중 하나로 기록한다.

```text
CODE_ERROR
TEST_FAILURE
CONFIG_ERROR
MODEL_NOT_INSTALLED
OLLAMA_UNAVAILABLE
DATASET_UNAVAILABLE
DATASET_SCHEMA_CHANGED
PARSER_ERROR
TIMEOUT
RESOURCE_EXHAUSTED
EXTERNAL_DEPENDENCY
NOT_EXECUTED
```

완료 보고서와 실행 artifact에서 동일한 enum을 사용한다.

오류 메시지는 다음 내용을 포함한다.

- 작업 단계
- 모델 또는 benchmark
- case ID
- 원인
- 재현 방법
- 자동 재시도 여부
- 권장 조치

---

# 16. 하네스 효과 측정

BMAD와 Harness Engineering 도입 효과를 확인하기 위해 Story별로 아래 메타데이터를 기록한다.

```yaml
story_id:
started_at:
completed_at:
codex_iterations:
human_interventions:
files_changed:
tests_added:
tests_failed_initially:
tests_passed_finally:
scope_violation_detected:
rework_reason:
completion_status:
```

집계 대상:

- Story 완료율
- 첫 구현 테스트 통과율
- 평균 수정 반복 횟수
- 인간 개입 횟수
- 범위 외 변경 발생률
- 재작업 원인
- Acceptance Criteria 누락률
- 작업당 추가된 테스트 수

이 정보는 추후 포트폴리오에서 하네스 도입 효과를 설명하는 근거로 사용한다.

---

# 17. 구현 순서

Codex는 다음 순서로 작업한다.

## Phase 1: 조사 및 계획

- 저장소 구조 조사
- 기존 명세 확인
- BMAD 설치 여부 확인
- 변경 계획 제시

## Phase 2: Planning Artifacts

- Product Brief
- PRD
- Architecture
- Epics

## Phase 3: Harness Foundation

- `AGENTS.md`
- Skill
- Completion Report
- Sprint Status
- ADR

## Phase 4: Initial Stories

- EVAL-001~EVAL-005 생성
- Story 간 의존성 기록
- 첫 Story를 `ready`로 설정

## Phase 5: Validation

- 문서 링크 검증
- YAML 파싱 검증
- Markdown code fence 검토
- AGENTS 지침과 Skill 충돌 확인
- 기존 테스트 실행

## Phase 6: 보고

- 생성·수정 파일
- 검증 결과
- 보류 항목
- 사용자에게 필요한 입력
- 다음 실행할 Story 추천

---

# 18. 완료 조건

아래를 모두 만족하면 이번 도입 작업을 완료로 본다.

- [ ] 기존 저장소 조사가 수행됨
- [ ] Product Brief 생성
- [ ] PRD 생성
- [ ] Architecture 생성
- [ ] Epic 문서 생성
- [ ] 초기 Story 최소 5개 생성
- [ ] 루트 `AGENTS.md` 생성 또는 개선
- [ ] `bmad-implement-story` Skill 생성
- [ ] Completion Report 템플릿 생성
- [ ] Sprint Status 생성
- [ ] 초기 ADR 생성
- [ ] CI 또는 검증 명령 정리
- [ ] 문서 경로와 링크가 유효함
- [ ] 기존 테스트를 실행했거나 실행하지 못한 이유가 기록됨
- [ ] 기존 코드를 불필요하게 변경하지 않음
- [ ] 다음 구현 Story가 명확하게 지정됨

---

# 19. Codex 작업 시작 프롬프트

이 문서를 전달한 뒤 다음 요청으로 실행한다.

```text
이 문서를 기준으로 현재 저장소에 BMAD Lite와 Harness Engineering을 도입해줘.

먼저 저장소 전체 구조, 기존 명세, 테스트 도구, BMAD 설치 여부를 조사해.
코드를 변경하기 전에 조사 결과와 상세 계획을 먼저 보여줘.

기존 프로젝트 구조와 충돌하지 않는 범위에서 다음을 수행해:
1. 기존 로컬 LLM 평가 명세를 Product Brief, PRD, Architecture, Epic으로 분해
2. 초기 Story 생성
3. AGENTS.md 작성
4. bmad-implement-story Codex Skill 작성
5. Completion Report와 Sprint Status 작성
6. ADR 작성
7. 검증 하네스와 CI 구조 정리

존재하지 않는 모델 태그, 데이터셋 필드, 명령은 추측하지 마.
실제로 실행한 테스트와 실행하지 못한 테스트를 구분해 보고해.
기존 코드는 이번 작업에 꼭 필요한 경우가 아니면 수정하지 마.
```

---

# 20. 다음 단계

이번 도입 작업이 끝난 뒤 Codex에게 다음과 같이 Story 단위로 지시한다.

```text
bmad-implement-story 절차를 사용해서
`_bmad-output/implementation-artifacts/stories/EVAL-001-project-foundation.md`
Story를 구현해줘.

먼저 관련 문서와 기존 코드를 읽고 계획을 제시한 뒤 작업해.
Acceptance Criteria별 완료 증거와 실제 테스트 결과를 보고해.
```

이후 Story를 순차적으로 수행한다.

```text
EVAL-001 → EVAL-002 → EVAL-003 → EVAL-004 → EVAL-005
```

한 번에 전체 평가 시스템을 구현하도록 요청하지 않는다.
