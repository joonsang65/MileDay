# MileDay AI

MileDay AI는 일정 초안 생성만 담당한다. 검증, 저장 payload 생성, DB write는 애플리케이션 코드가 책임진다.

## 현재 제품 흐름

```text
자연어 요청
  -> Gemini Structured Output
  -> JSON parsing
  -> deterministic validation
  -> editable draft
  -> 사용자 수정/확인
  -> 기존 Goal/Milestone API 저장
```

## 책임 경계

| 영역 | 책임 |
|---|---|
| Gemini | 목표 해석, 제목 제안, 마감일 해석, 마일스톤 분해, 선호 강도 해석 |
| Backend | schema 요청, JSON parsing, 날짜/중복/availability 검증, draft payload 구성 |
| Frontend | 초안 표시, 선택/삭제/추가/수정, 저장 전 UI validation |
| Goal/Milestone API | 사용자 확인 후 실제 저장 |

AI는 Supabase에 접근하지 않고 `goal_id`, `milestone_id`, SQL, DB mutation을 생성하지 않는다.

## 입출력 계약

- `/ai/schedule/draft`는 사용자 설정의 `gemini_data_consent=true`일 때만 동작한다.
- request: `prompt` 1 ~ 2000자, `today`, `timezone` 기본 `Asia/Seoul`, `availability[]` 1 ~ 90개 날짜
- response: `goal`, `milestones[]`, `planning_preference`, `validation`, `create_goal_payload`
- `create_goal_payload.write_policy`는 항상 `user_confirmation_required`다.

| field | 설명 |
|---|---|
| `goal` | 목표 제목과 마감일 후보 |
| `milestones[]` | `client_id`, 제목, 예정일, 선택 여부 |
| `planning_preference` | `intensity: relaxed\|balanced\|intensive`, `preferred_days[]` |
| `validation` | 저장 가능 여부, 실패 코드, 경고 |
| `create_goal_payload` | 확인 후 기존 Goal/Milestone API에 넘길 payload |

## Validation

- 실패: `EMPTY_GOAL_TITLE`, `INVALID_DEADLINE`, `DEADLINE_NOT_FUTURE`, `NO_MILESTONES`, `INVALID_MILESTONE_SHAPE`, `EMPTY_MILESTONE_TITLE`, `INVALID_MILESTONE_DATE`, `MILESTONE_AFTER_DEADLINE`, `MILESTONE_OUTSIDE_AVAILABILITY`, `DUPLICATE_MILESTONE`, `INVALID_INTENSITY`, `INVALID_PREFERRED_DAYS`
- 경고: `MILESTONE_COUNT_HIGH`, `PREFERRED_DAYS_NOT_REFLECTED`
- 동의 누락: `GEMINI_DATA_CONSENT_REQUIRED`

## Failure taxonomy

AI 초안 실패는 validator code와 LLM-as-judge 판정을 함께 본다. Validator는 저장 가능한 형식과 날짜 제약을 막고, judge는 사용자가 실제로 고쳐야 하는 의미 품질을 본다.

| 유형 | 기준 | 탐지 |
|---|---|---|
| Invalid JSON/schema | JSON object가 아니거나 필수 field가 없음 | parser, Pydantic schema |
| Deadline violation | 마감일이 없거나 오늘 이전, 또는 milestone이 마감일 이후 | `INVALID_DEADLINE`, `DEADLINE_NOT_FUTURE`, `MILESTONE_AFTER_DEADLINE` |
| Availability violation | milestone이 사용 가능 날짜 밖에 배치됨 | `MILESTONE_OUTSIDE_AVAILABILITY` |
| Duplicate milestone | 같은 제목과 날짜의 milestone이 반복됨 | `DUPLICATE_MILESTONE` |
| Preference mismatch | 선호 요일이나 계획 강도가 초안에 반영되지 않음 | `PREFERRED_DAYS_NOT_REFLECTED`, judge |
| Over-decomposition | 단순 목표를 지나치게 많은 milestone으로 쪼갬 | `MILESTONE_COUNT_HIGH`, judge |
| Title quality failure | 제목이 깨졌거나 사용자가 이해하기 어려움 | judge |
| Intent mismatch | 저장 가능한 초안이지만 요청한 목표와 다른 계획을 만듦 | judge |
| Unsafe mutation scope | AI가 id, SQL, DB mutation 책임을 넘겨받으려 함 | prompt/schema 차단, code review |

## 모델 기준

제품 기본 API LLM은 비용과 지연을 고려해 `GEMINI_SCHEDULE_MODEL`로 지정하며, 기본값은 `gemini-3.5-flash-lite`다. Gemini 요청은 JSON response schema, temperature `0.2`, timeout `30s`를 사용한다.

## 평가 기준

최종 AI 기능은 "편집 가능한 일정 초안" 품질로 평가한다. 모델이 DB write까지 책임지는지보다, 사용자가 저장 전 고쳐야 하는 비용을 얼마나 줄이는지가 핵심이다.

| 지표 | 의미 | 판정 기준 |
|---|---|---|
| Draft validity | 초안이 저장 후보로 성립하는지 | 필수 field와 schema가 맞고 `validation.is_valid=true` |
| Constraint pass | 날짜 제약을 지켰는지 | 마감일이 미래이고 마일스톤이 마감일/availability 범위 안에 있음 |
| Preference adherence | 사용자 선호를 반영했는지 | 계획 강도와 선호 요일이 초안에 반영됨 |
| Avg edit count | 사용자가 고쳐야 할 양 | 제목, 날짜, 삭제/추가 등 저장 전 수정 횟수 |
| Latency | 응답 지연 | 초안 생성 요청부터 response 수신까지의 시간 |
| Cost | 호출 비용 | 모델별 입력/출력 token 기준 예상 비용 |

SLM과 API LLM 비교는 위 지표를 같은 제품 태스크에 적용한다. 결과는 "어떤 모델이 더 강한가"보다 "현재 책임 경계에서 어떤 모델이 사용자 편집 비용, 지연, 비용의 균형을 맞추는가"를 기준으로 해석한다.

최종 초안 기능 기준의 SLM/API 재평가 기준과 결과 표는 [archive/decisions/0022-최종_AI_초안_모델_재평가.md](archive/decisions/0022-최종_AI_초안_모델_재평가.md)에서 관리한다.

코드 위치: `backend/app/api/routers/schedule_assistant.py`, `backend/app/services/ai_schedule_service.py`, `backend/app/infrastructure/gemini_client.py`, `backend/app/schemas/ai_schedule_schemas.py`, `frontend/src/components/AiSchedulePanel.tsx`

과거 평가 원문은 [archive/decisions/](archive/decisions/)에 보관한다.
