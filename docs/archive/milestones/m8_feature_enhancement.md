# M8. 기능 고도화 진행 요약

M8은 MVP 이후 기능 고도화 범위다. 현재는 AI 일정 초안 생성만 구현하고, 자동 수정 계열 기능은 제품 범위에서 제외했다.

## 상태

| 항목 | 상태 | 기준 |
|---|---|---|
| AI 일정 초안 생성 | 구현 | 사용자가 목표/조건을 입력하면 Gemini 기반 초안을 만들고, 저장 전 사용자가 편집/확인한다. |
| Gemini 전송 동의 | 구현 | `gemini_data_consent=true`일 때만 AI 요청을 허용한다. |
| 자연어 일정 수정 | 제외 | 기존 일정을 AI가 직접 수정하지 않는다. |
| 자동 리스케줄링 | 제외 | 미완료 작업을 자동 재배치하지 않는다. |
| 외부 캘린더 연동 | 후속 | Google Calendar 등 외부 캘린더 동기화는 이후 단계로 둔다. |

## 구현 위치

- Backend: `backend/app/api/routers/schedule_assistant.py`, `backend/app/services/ai_schedule_service.py`, `backend/app/infrastructure/gemini_client.py`
- Frontend: `frontend/src/components/AiSchedulePanel.tsx`, `frontend/src/App.tsx`, `frontend/src/api/client.ts`
- 문서 기준: `docs/ai.md`, `docs/api.md`

## 완료 기준

- AI 결과는 DB에 직접 반영되지 않는다.
- 저장은 기존 Goal/Milestone API를 통해 사용자 확인 후 수행한다.
- 실패/경고 코드는 backend validation 결과를 기준으로 UI에 표시한다.

## 재평가 기준

최종 기능 기준 모델 평가는 [../../ai.md](../../ai.md)의 평가 기준을 따르고, SLM/API 재평가 결과는 [../decisions/0022-최종_AI_초안_모델_재평가.md](../decisions/0022-최종_AI_초안_모델_재평가.md)에 기록한다.

| 지표 | 목적 |
|---|---|
| Draft validity | 저장 가능한 초안 비율 확인 |
| Constraint pass | 날짜, 마감일, availability 제약 준수 확인 |
| Preference adherence | 계획 강도와 선호 요일 반영 확인 |
| Avg edit count | 사용자 수정 비용 확인 |
| Latency | 실제 사용 지연 확인 |
| Cost | API/로컬 실행 비용 비교 |
