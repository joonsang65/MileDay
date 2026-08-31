# MileDay API

이 문서는 현재 FastAPI 구현 기준의 API 요약이다.

## 공통 규칙

- Local base URL: `http://localhost:8000`
- 인증: `Authorization: Bearer <access_token>`
- 요청/응답: JSON
- 날짜: `YYYY-MM-DD`
- 오류 응답: `success=false`, `error.code`, `error.message`, `error.detail`, `request_id`
- `/`는 hidden health root다.

## Endpoint

| 영역 | Method | Path | 설명 |
|---|---|---|---|
| Health | GET | `/health` | 서버 상태 |
| Health | GET | `/health/db` | Supabase DB와 핵심 column 확인 |
| Auth | POST | `/auth/signup` | 회원가입 |
| Auth | POST | `/auth/login` | 로그인 |
| Auth | POST | `/auth/logout` | 로그아웃 |
| Auth | GET | `/auth/me` | 현재 사용자 |
| Auth | DELETE | `/auth/account` | 계정 삭제 |
| Goals | GET | `/goals` | 목표 목록 |
| Goals | GET | `/goals/with-milestones` | 목표와 하위 마일스톤 통합 조회 |
| Goals | GET | `/goals/{goal_id}` | 목표 상세 |
| Goals | POST | `/goals` | 목표 생성 |
| Goals | PATCH | `/goals/{goal_id}` | 목표 수정 |
| Goals | PATCH | `/goals/{goal_id}/complete` | 목표 완료 처리 |
| Goals | DELETE | `/goals/{goal_id}` | 목표 삭제 |
| Milestones | GET | `/goals/{goal_id}/milestones` | 목표 하위 마일스톤 목록 |
| Milestones | POST | `/goals/{goal_id}/milestones` | 마일스톤 생성 |
| Milestones | GET | `/milestones/today` | 오늘 할 일 |
| Milestones | GET | `/milestones/{milestone_id}` | 마일스톤 상세 |
| Milestones | PATCH | `/milestones/{milestone_id}` | 마일스톤 수정 |
| Milestones | PATCH | `/milestones/{milestone_id}/complete` | 마일스톤 완료 처리 |
| Milestones | DELETE | `/milestones/{milestone_id}` | 마일스톤 삭제 |
| Calendar | GET | `/calendar/month?year={year}&month={month}` | 월간 캘린더 |
| Calendar | GET | `/calendar/week?start_date={date}` | 주간 캘린더 |
| Calendar | GET | `/calendar/date/{target_date}` | 날짜 상세 |
| Settings | GET | `/settings` | 사용자 설정 조회 |
| Settings | PATCH | `/settings` | 사용자 설정 수정 |
| AI | POST | `/ai/schedule/draft` | AI 일정 초안 생성 |

`/external-calenders` 라우터는 endpoint 없는 placeholder다. 외부 캘린더 연동은 아직 구현 범위가 아니다.

## 주요 Payload

| 영역 | 핵심 field |
|---|---|
| Goal | `title`, `deadline`, `is_completed`, `is_recurring`, `recurrence_type: daily\|weekly\|monthly\|null`, `color` |
| Milestone | `title`, `scheduled_date`, `is_completed`, `color` |
| Settings | `calendar_view: month\|week`, `holiday_display: normal\|weekend_like\|hidden`, `week_starts_on: 0\|1`, `language: ko\|en`, `timezone`, `gemini_data_consent` |
| AI draft request | `prompt`, `today`, `timezone`, `availability[]` |
| AI draft response | `goal`, `milestones[]`, `planning_preference`, `validation`, `create_goal_payload.write_policy=user_confirmation_required` |

## API 관리 기준

- 새 endpoint를 추가하면 이 문서를 먼저 갱신한다.
- 상세 request/response 예시는 코드의 Pydantic schema를 우선한다.
- 프론트엔드 API client는 `GET` 요청만 502/503/504와 네트워크성 오류에 제한적으로 retry한다.
- 오래된 endpoint 이름은 archive에 남아 있어도 이 문서에는 현재 구현만 둔다.

상세 과거 명세는 [archive/reference/api_spec.md](archive/reference/api_spec.md)에 보관한다.
