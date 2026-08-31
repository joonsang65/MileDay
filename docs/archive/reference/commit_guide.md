# Commit Message Guide for Codex

이 문서는 Codex가 MileDay 프로젝트에서 자동 커밋을 생성할 때 따라야 하는 커밋 메시지 작성 규칙이다.

커밋 메시지는 Conventional Commits 형식을 기반으로 작성하되, 설명은 한국어로 작성한다.

---

## 1. 기본 형식

```txt
<type>(<scope>): <summary>

<description>
```

### 필수 규칙

- `type`은 변경의 성격을 나타낸다.
- `scope`는 변경된 영역을 나타낸다.
- `summary`는 한 줄로 변경 내용을 요약한다.
- `description`은 1~2줄로 변경 이유와 주요 내용을 설명한다.
- `summary`와 `description`은 한국어로 작성한다.
- 커밋 메시지는 과거형보다 현재형에 가깝게 작성한다.
- 너무 추상적인 표현을 피하고, 실제 변경 내용을 기준으로 작성한다.

---

## 2. 커밋 메시지 템플릿

```txt
<type>(<scope>): <한 줄 요약>

<변경 이유 또는 목적을 한 줄로 작성>
<주요 변경 내용을 한 줄로 작성>
```

### 예시

```txt
feat(auth): 로그인 라우터 골격 추가

FastAPI 기반 인증 API 명세 작성을 위해 auth 라우터 추가
회원가입, 로그인, 로그아웃, 현재 사용자 조회 endpoint의 기본 응답 구조 정의
```

---

## 3. Type 규칙

아래 type 중 하나만 사용한다.

| Type | 사용 상황 | 예시 |
|---|---|---|
| `feat` | 새로운 기능 추가 | `feat(goals): 목표 생성 API 추가` |
| `fix` | 버그 수정 | `fix(calendar): 오늘 날짜 비교 오류 수정` |
| `refactor` | 기능 변화 없이 코드 구조 개선 | `refactor(api): 라우터 등록 구조 정리` |
| `docs` | 문서 추가 또는 수정 | `docs(api): API 명세서 초안 추가` |
| `style` | 포맷팅, 세미콜론, 공백 등 코드 의미 없는 수정 | `style(frontend): 컴포넌트 포맷 정리` |
| `test` | 테스트 코드 추가 또는 수정 | `test(goals): 목표 API 테스트 추가` |
| `chore` | 설정, 패키지, 빌드, 기타 유지보수 | `chore(env): 개발 환경 변수 예시 추가` |
| `build` | 빌드 시스템 또는 패키지 의존성 변경 | `build(frontend): electron-vite 설정 추가` |
| `ci` | CI/CD 설정 변경 | `ci(github): 백엔드 테스트 워크플로우 추가` |
| `perf` | 성능 개선 | `perf(calendar): 월간 일정 조회 로직 최적화` |
| `revert` | 이전 커밋 되돌리기 | `revert(api): 목표 라우터 변경 사항 되돌림` |

---

## 4. Scope 규칙

`scope`는 변경된 영역을 짧게 작성한다.

MileDay 프로젝트에서는 아래 scope를 우선 사용한다.

| Scope | 의미 |
|---|---|
| `project` | 프로젝트 전체 구조 |
| `env` | 개발 환경, 실행 환경, 환경 변수 |
| `backend` | FastAPI 백엔드 전체 |
| `frontend` | Electron/React 프론트엔드 전체 |
| `electron` | Electron main/preload/window 관련 코드 |
| `auth` | 회원가입, 로그인, 로그아웃, JWT 인증 |
| `goals` | 목표 관리 기능 |
| `milestones` | 마일스톤 관리 기능 |
| `calendar` | 캘린더, 날짜별 조회, Today List |
| `settings` | 사용자 설정, 위젯 설정 |
| `db` | DB 스키마, migration, RLS |
| `api` | API 라우터, 응답 형식, 공통 API 구조 |
| `ui` | 화면 구성, 스타일, 컴포넌트 UI |
| `docs` | 문서, README, 설계서 |
| `test` | 테스트 코드 |
| `config` | 설정 파일, lint, formatter, tsconfig 등 |

### scope 선택 기준

- 특정 기능만 바뀌면 해당 기능명을 사용한다.
- 여러 기능이 함께 바뀌면 더 넓은 scope를 사용한다.
- 백엔드 전반 변경이면 `backend`를 사용한다.
- 프론트엔드 전반 변경이면 `frontend`를 사용한다.
- API 구조 변경이면 `api`를 사용한다.
- 문서만 수정하면 `docs`를 사용한다.

---

## 5. Summary 작성 규칙

`summary`는 커밋 제목에 해당한다.

### 형식

```txt
<type>(<scope>): <한글 요약>
```

### 작성 원칙

- 50자 이내를 권장한다.
- 마침표를 붙이지 않는다.
- “수정함”, “추가함”보다 “수정”, “추가”처럼 간결하게 작성한다.
- 변경 파일명이 아니라 변경 목적을 작성한다.
- 너무 넓은 표현을 피한다.

### 좋은 예시

```txt
feat(api): FastAPI 라우터 기본 구조 추가
```

```txt
docs(db): MileDay DB 스키마 설명 추가
```

```txt
chore(env): 백엔드 환경 변수 예시 파일 추가
```

### 나쁜 예시

```txt
feat: 수정
```

```txt
update: 파일 변경
```

```txt
fix: 이것저것 고침
```

---

## 6. Description 작성 규칙

`description`은 커밋 본문에 해당한다.

### 형식

```txt
<변경 이유 또는 목적>
<주요 변경 내용>
```

### 작성 원칙

- 1~2줄로 작성한다.
- 첫 줄에는 변경 목적이나 배경을 작성한다.
- 두 번째 줄에는 실제 변경 내용을 작성한다.
- 구현하지 않은 내용을 구현한 것처럼 쓰지 않는다.
- 추후 구현 예정인 내용은 “추후 구현 예정”이라고 명확히 쓴다.

### 예시

```txt
API 명세서 작성을 위해 백엔드 라우터의 기본 골격 추가
auth, goals, milestones, calendar, settings 라우터를 등록하고 mock 응답 정의
```

---

## 7. 자동 커밋 생성 절차

Codex는 커밋 메시지를 만들기 전에 다음 순서로 변경 내용을 확인한다.

1. `git status`로 변경된 파일 목록을 확인한다.
2. `git diff --staged` 또는 `git diff`로 실제 변경 내용을 확인한다.
3. 변경 목적에 맞는 `type`을 선택한다.
4. 가장 적절한 `scope`를 선택한다.
5. 변경 내용을 한 줄 summary로 요약한다.
6. description을 1~2줄로 작성한다.
7. 변경 내용과 무관한 과장된 표현을 사용하지 않는다.

---

## 8. 자동 커밋 시 판단 기준

### 새 기능이 추가된 경우

```txt
feat(<scope>): <기능 요약>

<기능이 필요한 이유를 작성한다.>
<추가된 주요 파일 또는 동작을 설명한다.>
```

예시:

```txt
feat(calendar): Today List 조회 라우터 추가

캘린더 화면에서 오늘 수행할 마일스톤을 조회하기 위한 API 골격 추가
/calendar/today endpoint를 등록하고 기본 응답 구조 정의
```

### 버그를 수정한 경우

```txt
fix(<scope>): <수정 내용 요약>

<문제가 발생한 원인을 간단히 작성한다.>
<수정한 내용을 설명한다.>
```

예시:

```txt
fix(auth): 로그인 응답 필드명 불일치 수정

프론트엔드에서 기대하는 token_type 필드와 백엔드 응답명이 달라 인증 상태 저장이 실패함
로그인 응답 스키마의 필드명을 API 명세서 기준에 맞게 수정
```

### 코드 구조만 개선한 경우

```txt
refactor(<scope>): <구조 개선 요약>

<구조를 변경한 이유를 작성한다.>
<기능 변경 없이 정리한 내용을 설명한다.>
```

예시:

```txt
refactor(api): 라우터 등록 구조 분리

기능별 API 라우터를 명확히 구분하기 위해 main.py의 라우터 등록 코드 정리
기존 동작은 유지하고 auth, goals, milestones, calendar, settings 라우터를 별도 파일로 분리한다.
```

### 문서를 수정한 경우

```txt
docs(<scope>): <문서 변경 요약>

<문서를 수정한 이유를 작성한다.>
<추가 또는 수정한 문서 내용을 설명한다.>
```

예시:

```txt
docs(api): API 명세서 초안 작성

FastAPI 라우터 골격을 기준으로 프론트엔드와 백엔드 간 통신 규칙을 정리한다.
Auth, Goal, Milestone, Calendar, Settings API의 endpoint와 응답 형식을 문서화한다.
```

### 설정 또는 환경을 변경한 경우

```txt
chore(<scope>): <설정 변경 요약>

<설정 변경 목적을 작성한다.>
<변경된 설정 파일이나 실행 방식을 설명한다.>
```

예시:

```txt
chore(env): 백엔드 개발 환경 설정 추가

로컬 FastAPI 실행을 위해 개발 환경 변수 예시 추가
.env.example에 Supabase 연결 정보와 로그 레벨 설정 항목 정의
```

---

## 9. 여러 변경이 섞인 경우

하나의 커밋에는 가능한 한 하나의 목적만 담는다.

### 권장

```txt
feat(api): 백엔드 라우터 기본 구조 추가
```

```txt
docs(api): API 명세서 초안 추가
```

```txt
chore(env): 로컬 개발 환경 설정 추가
```

### 비권장

```txt
feat(project): 라우터 추가 및 문서 작성 및 환경 설정 수정
```

여러 목적이 섞여 있으면 Codex는 가능한 범위에서 변경 파일을 나누어 여러 커밋으로 분리한다.
단, 사용자가 하나의 커밋을 명시적으로 요청한 경우 가장 넓은 type과 scope를 선택한다.

---

## 10. MileDay 프로젝트 초기 단계 권장 커밋 예시

### 개발 환경 구축

```txt
chore(env): 로컬 개발 환경 기본 설정 추가

MileDay 백엔드와 프론트엔드를 로컬에서 실행하기 위한 기본 설정을 추가한다.
환경 변수 예시와 실행 구조를 정리해 이후 API 명세 작성의 기준을 마련한다.
```

### FastAPI 앱 생성

```txt
feat(backend): FastAPI 앱 기본 구조 추가

API 명세서 작성과 라우터 확장을 위해 FastAPI 앱의 초기 구조를 추가한다.
main.py, config, router 디렉터리를 구성하고 health check endpoint를 정의한다.
```

### 라우터 골격 추가

```txt
feat(api): MVP API 라우터 골격 추가

MileDay MVP 기능 흐름을 기준으로 API endpoint의 기본 구조를 추가한다.
auth, goals, milestones, calendar, settings 라우터를 등록하고 mock 응답을 정의한다.
```

### DB 스키마 문서 추가

```txt
docs(db): DB 스키마 설계 문서 추가

Supabase PostgreSQL 기반의 MileDay 핵심 데이터 구조 문서화
goals, milestones, user_settings, external_calendar_connections 테이블의 역할과 필드를 정리
```

### API 명세서 추가

```txt
docs(api): API 명세서 초안 추가

프론트엔드와 백엔드 간 통신 규칙을 정의하기 위해 API 명세서 초안 작성
공통 응답 형식, 인증 방식, MVP endpoint 목록과 요청/응답 예시 정리
```

---

## 11. 금지 규칙

Codex는 아래와 같은 커밋 메시지를 작성하지 않는다.

```txt
update: 수정
```

```txt
fix: 버그 수정
```

```txt
feat: 기능 추가
```

```txt
작업함
```

```txt
커밋
```

```txt
wip
```

단, 사용자가 명시적으로 임시 저장 목적의 커밋을 요청한 경우에만 `chore(project): 작업 중 변경 사항 임시 저장` 형식을 사용할 수 있다.

---

## 12. 최종 출력 규칙

Codex가 커밋 메시지를 제안할 때는 아래 형식만 출력한다.

```txt
<type>(<scope>): <summary>

<description line 1>
<description line 2>
```

다른 설명, 분석, 변경 요약은 커밋 메시지 안에 포함하지 않는다.

