# M4. 마일스톤 관리 로직 구현

## 문서 목적

M4 단계에서는 목표 하위의 마일스톤 생성, 조회, 수정, 삭제, 완료 처리 API를 실제 데이터 기준으로 구현한다.
M3에서 정한 목표 관리 인증/소유권 기준을 그대로 사용하고, 마일스톤은 항상 현재 사용자 ID와 목표 ID를 함께 기준으로 처리한다.

또한 M3에서 정리한 반복 목표 처리 방식을 M4 마일스톤 구현 기준에 반영한다.
반복 목표는 별도 반복 예외 테이블을 만들지 않고, 반복 날짜별 마일스톤을 실제 `milestones` row로 생성한다.
예외 날짜는 해당 날짜의 마일스톤을 생성하지 않거나 이미 생성된 마일스톤을 삭제하는 방식으로 처리한다.

## 기준 문서

| 문서 | 확인 내용 |
| --- | --- |
| `docs/requirements.md` | M4 요구사항 BE-04, MS-01~MS-06 |
| `docs/api_spec.md` | Milestone API endpoint, request/response 형식 |
| `docs/data_flow.md` | 마일스톤 생성, 조회, 완료 처리 흐름 |
| `docs/db_schema.md` | `milestones` 테이블 필드와 goal FK cascade |
| `docs/error_logging.md` | 마일스톤 예외 코드와 오류 응답 기준 |
| `docs/milestones/m3_goal_management.md` | 반복 목표의 날짜별 마일스톤 생성 기준 |

## M4 요구사항 범위

| ID | 분류 | 기능 | 구현 기준 |
| --- | --- | --- | --- |
| BE-04 | 백엔드 | 마일스톤 API 제공 | 마일스톤 생성, 조회, 수정, 삭제, 완료 처리 API를 실제 service/repository에 연결 |
| MS-01 | 마일스톤 관리 | 마일스톤 생성 | 현재 사용자가 소유한 목표 하위에만 마일스톤 생성 |
| MS-02 | 마일스톤 관리 | 마일스톤 날짜 지정 | `scheduled_date`를 기준으로 수행 예정일 저장 |
| MS-03 | 마일스톤 관리 | 마일스톤 조회 | 목표별 목록, 단건 상세, 오늘 예정 목록 조회 |
| MS-04 | 마일스톤 관리 | 마일스톤 수정 | 제목, 색상, 수행 예정일, 완료 여부 수정 |
| MS-05 | 마일스톤 관리 | 마일스톤 삭제 | 현재 사용자가 소유한 마일스톤만 삭제 |
| MS-06 | 마일스톤 관리 | 완료 여부 변경 | 마일스톤 완료/미완료 상태 변경 |

## 구현 대상 API

| 기능 | Method | Endpoint | 구현 기준 |
| --- | --- | --- | --- |
| 목표 하위 마일스톤 목록 조회 | GET | `/goals/{goal_id}/milestones` | `goal_id`가 현재 사용자의 목표인지 확인 후 목록 조회 |
| 마일스톤 생성 | POST | `/goals/{goal_id}/milestones` | 목표 소유권 확인 후 `user_id`, `goal_id`를 서버에서 설정 |
| 오늘 할 일 조회 | GET | `/milestones/today` | 현재 사용자 기준 오늘 `scheduled_date` 마일스톤 조회 |
| 마일스톤 상세 조회 | GET | `/milestones/{milestone_id}` | `id = milestone_id AND user_id = current_user.id` 조건 사용 |
| 마일스톤 수정 | PATCH | `/milestones/{milestone_id}` | 현재 사용자 소유 마일스톤만 수정 |
| 마일스톤 삭제 | DELETE | `/milestones/{milestone_id}` | 현재 사용자 소유 마일스톤만 삭제 |
| 마일스톤 완료 처리 | PATCH | `/milestones/{milestone_id}/complete` | 완료 여부만 명시적으로 변경 |

## 구현 원칙

- 프론트엔드는 `user_id`를 보내지 않는다.
- 백엔드는 인증 토큰에서 추출한 현재 사용자 ID를 `milestones.user_id`로 사용한다.
- 마일스톤 생성 전 반드시 `goal_id`가 현재 사용자의 목표인지 확인한다.
- 마일스톤 상세 조회, 수정, 삭제, 완료 처리에는 항상 `milestone_id`와 `user_id` 조건을 함께 사용한다.
- 다른 사용자의 목표나 마일스톤 접근 시 존재 여부를 노출하지 않고 `MILESTONE_NOT_FOUND` 또는 `GOAL_NOT_FOUND`로 처리한다.
- 목표 삭제 시 하위 마일스톤 삭제는 DB FK cascade 기준을 사용한다.

## 반복 목표와 마일스톤 생성 기준

M4에서는 반복 목표를 추상 규칙으로만 저장하지 않고, 반복 날짜별 마일스톤으로 실제 생성하는 기준을 문서화한다.
구현은 마일스톤 service 내부 helper 또는 별도 반복 일정 helper로 분리한다.

### 반복 마일스톤 생성 흐름

1. 반복 목표 생성 또는 반복 설정 변경 요청을 받는다.
2. 반복 시작일, 마감일, `recurrence_type`으로 반복 날짜 목록을 계산한다.
3. 예외 날짜 목록이 있으면 해당 날짜를 반복 날짜 목록에서 제외한다.
4. 남은 각 날짜마다 `milestones` row를 생성한다.
5. 생성된 마일스톤은 일반 마일스톤과 동일하게 조회, 수정, 삭제, 완료 처리한다.

### 예외 날짜 처리 기준

반복 예외 날짜는 별도 테이블로 저장하지 않는다.
예외 처리는 다음 중 하나로 처리한다.

- 생성 전 예외 날짜가 지정된 경우: 해당 날짜의 마일스톤을 생성하지 않는다.
- 이미 생성된 반복 마일스톤을 예외 처리하는 경우: 해당 날짜의 마일스톤을 삭제한다.

이 기준을 사용하면 캘린더, 날짜 상세, Today List는 반복 규칙을 다시 계산하지 않고 `milestones.scheduled_date`만 조회하면 된다.

### 반복 설정 수정 기준

반복 설정 변경 시 이미 지나간 마일스톤과 완료된 마일스톤은 보존한다.
아직 완료되지 않은 미래 마일스톤만 삭제 후 재생성한다.

다만 현재 `milestones` 스키마에는 자동 생성 마일스톤과 사용자가 직접 만든 마일스톤을 구분하는 필드가 없다.
따라서 M4 구현 시에는 다음 중 하나를 선택해야 한다.

- MVP 기준: 반복 목표 하위의 미완료 미래 마일스톤을 모두 재생성 대상으로 본다.
- 보강 기준: `milestones`에 `source` 또는 `is_auto_generated` 같은 필드를 추가해 자동 생성 마일스톤만 재생성한다.

현재 스키마 변경을 최소화하려면 MVP 기준을 우선 적용한다.

## 입력값 검증 기준

| 항목 | 검증 기준 |
| --- | --- |
| `title` | 빈 문자열 불가 |
| `color` | HEX 색상 문자열 기준 사용 |
| `scheduled_date` | 필수 날짜. 목표 마감일 이후 날짜 허용 여부는 정책 확정 필요 |
| `is_completed` | boolean 값만 허용 |
| `goal_id` | 현재 사용자가 소유한 목표여야 함 |
| `milestone_id` | 현재 사용자가 소유한 마일스톤이어야 함 |

마일스톤 수행일이 목표 마감일 이후일 때 차단할지, 경고만 할지는 M4 구현 전에 확정한다.
일정 도구 성격상 MVP에서는 차단보다 허용이 더 유연하지만, 기본 검증 테스트에는 정책을 명시해야 한다.

## 예외 처리 기준

| 상황 | Error Code | HTTP Status |
| --- | --- | --- |
| 목표가 없거나 현재 사용자 소유가 아님 | `GOAL_NOT_FOUND` | 404 |
| 마일스톤이 없거나 현재 사용자 소유가 아님 | `MILESTONE_NOT_FOUND` | 404 |
| 마일스톤 생성 실패 | `MILESTONE_CREATE_FAILED` | 500 |
| 마일스톤 수정 실패 | `MILESTONE_UPDATE_FAILED` | 500 |
| 마일스톤 삭제 실패 | `MILESTONE_DELETE_FAILED` | 500 |
| 잘못된 수행 예정일 | `MILESTONE_INVALID_SCHEDULED_DATE` | 400 |
| 요청 body 검증 실패 | `BAD_REQUEST` | 400 |

## 권장 구현 순서

1. `MilestoneRepository` 추가
2. `MilestoneService` 추가
3. 목표 소유권 확인을 위해 `GoalService` 또는 `GoalRepository` 재사용
4. 마일스톤 라우터 placeholder 제거
5. 모든 마일스톤 API에 `require_current_user_id` 적용
6. 일반 마일스톤 CRUD 구현
7. 오늘 할 일 조회 구현
8. 반복 날짜 계산 helper 작성
9. 반복 목표 생성/수정 시 마일스톤 일괄 생성 기준 연결
10. 반복 예외 날짜는 마일스톤 미생성 또는 삭제 방식으로 처리
11. 단위 테스트, 라우터 테스트, repository query 조건 테스트 작성

## 테스트 계획

| 테스트 범위 | 검증 내용 |
| --- | --- |
| 라우터 인증 | 인증 없이 마일스톤 API 호출 시 401 반환 |
| 목표 소유권 | 다른 사용자 목표 하위 마일스톤 생성 차단 |
| 마일스톤 생성 | `user_id`, `goal_id`가 서버 기준으로 설정되는지 확인 |
| 목표별 목록 | 현재 사용자와 목표 ID 조건이 적용되는지 확인 |
| 상세 조회 | 다른 사용자 마일스톤 접근 시 404 반환 |
| 수정 | 제목, 색상, 수행 예정일, 완료 여부 부분 수정 |
| 완료 처리 | 완료/미완료 상태 변경 |
| 삭제 | 현재 사용자 소유 마일스톤만 삭제 |
| 오늘 할 일 | 오늘 날짜의 현재 사용자 마일스톤만 조회 |
| 반복 날짜 계산 | `daily`, `weekly`, `monthly` 날짜 목록 계산 |
| 반복 예외 | 예외 날짜 마일스톤 미생성 또는 삭제 |
| 반복 수정 | 미완료 미래 마일스톤만 재생성 |
| repository | Supabase query에 `id`, `goal_id`, `user_id`, `scheduled_date` 조건 적용 |

## 완료 기준

- 마일스톤 API가 더 이상 placeholder 응답을 반환하지 않는다.
- 모든 보호 API가 현재 사용자 ID 기준으로 동작한다.
- 현재 사용자 소유가 아닌 목표/마일스톤 접근이 404로 처리된다.
- 마일스톤 생성, 조회, 수정, 삭제, 완료 처리가 실제 repository/service를 통해 동작한다.
- 오늘 할 일 조회가 `scheduled_date` 기준으로 동작한다.
- 반복 목표의 날짜별 마일스톤 생성 기준과 예외 날짜 처리 기준이 테스트로 검증된다.
- 기본 `pytest`가 통과하고 coverage 90% 이상을 유지한다.

## 구현 결과

이번 M4 구현에서 다음 파일을 추가하거나 변경했다.

| 파일 | 내용 |
| --- | --- |
| `backend/app/api/routers/milestones.py` | placeholder 응답 제거, 인증 사용자 기준 service 호출로 변경 |
| `backend/app/repositories/milestones.py` | Supabase `milestones` 테이블 접근 계층 추가 |
| `backend/app/services/milestone_service.py` | 마일스톤 CRUD, 오늘 할 일 조회, 완료 처리, 반복 날짜 계산 helper 추가 |
| `backend/app/schemas/milestone_schemas.py` | 마일스톤 요청 body의 extra 필드 차단과 빈 문자열 검증 추가 |
| `backend/app/exceptions/milestones.py` | 잘못된 수행 예정일 예외 클래스 추가 |
| `tests/test_app_routes.py` | 마일스톤 라우터 인증, CRUD, 404 검증 추가 |
| `tests/test_milestone_repository.py` | Supabase query 조건 검증 추가 |
| `tests/test_milestone_service.py` | 소유권, CRUD, 완료 처리, 반복 날짜 계산, 예외 날짜 제외 검증 추가 |

반복 목표의 날짜별 마일스톤 생성은 `MilestoneService.create_recurring_milestones`와 `calculate_recurring_dates`로 구현했다.
현재 목표 생성 API에는 반복 시작일과 예외 날짜 입력 필드가 없으므로, 목표 생성 라우터와의 자동 연결은 후속 API 입력 기준 확정 후 진행한다.

최신 로컬 검증 결과:

```text
49 passed, 1 deselected
Total coverage: 95.80%
```
