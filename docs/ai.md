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
- request: `prompt` 1~2000자, `today`, `timezone` 기본 `Asia/Seoul`, `availability[]` 1~90개 날짜
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

## 모델 기준

제품 기본 API LLM은 비용과 지연을 고려해 `GEMINI_SCHEDULE_MODEL`로 지정하며, 기본값은 `gemini-3.5-flash-lite`다. Gemini 요청은 JSON response schema, temperature `0.2`, timeout `30s`를 사용한다.

코드 위치: `backend/app/api/routers/schedule_assistant.py`, `backend/app/services/ai_schedule_service.py`, `backend/app/infrastructure/gemini_client.py`, `backend/app/schemas/ai_schedule_schemas.py`, `frontend/src/components/AiSchedulePanel.tsx`

과거 평가 원문은 [archive/decisions/](archive/decisions/)에 보관한다.
