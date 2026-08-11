# ADR-0007: MileDay 멀티턴 프롬프트 버전 관리

## 상태

Accepted

## 배경

`run-mileday-multiturn`은 `candidate-3`가 사용자의 이전 일정 상태를 유지하면서 부분 수정 요청을 처리할 수 있는지 평가한다. 1차 실행에서는 `[EXPLANATION]`과 fenced JSON 구조는 대체로 생성했지만, 필수 field 누락과 create/partial_update 기준 혼선이 있었다.

관찰된 실패 패턴:

- `changes` 또는 `unresolved_constraints` 누락
- create turn에서 fixture의 높은 `min_milestones`를 만족하지 못함
- create turn에서 기존 완료 milestone을 DB payload에 다시 포함하지 않음
- title의 요일/시간이 availability와 일치하지 않거나 `scheduled_date` 실제 요일과 불일치
- Gemini judge 503 같은 외부 의존성 실패

## 결정

프롬프트는 덮어쓰지 않고 버전으로 관리한다.

- `v1`: 최초 멀티턴 프롬프트. 기존 동작 재현과 비교를 위해 보존한다.
- `v2`: top-level field 누락을 줄이기 위해 필수 key와 create/partial_update 규칙을 강화한 프롬프트.
- `v3`: v2 결과를 바탕으로 validator 정책과 프롬프트를 정렬한 프롬프트.

현재 활성 버전은 `MILEDAY_MULTITURN_PROMPT_VERSION = "v3"`이다.

## v3 개선 내용

- create 기준을 명확히 했다.
  - milestone 최소 3개
  - `changes: []`
  - 기존 완료 일정은 변경하지 말고 새 제안과 구분
- partial_update 기준을 명확히 했다.
  - 이전 JSON 기준으로 요청받은 항목만 변경
  - `changes` 1개 이상
  - 언급되지 않은 milestone의 title/date 유지
- 요일/시간 품질 기준을 명시했다.
  - title prefix는 availability 안의 요일/시간만 사용
  - title prefix 요일과 `scheduled_date` 실제 요일 일치
  - 불가능한 요일/시간은 `unresolved_constraints`에 기록
- top-level key 6개는 계속 항상 요구한다.
  - `action`
  - `explanation`
  - `db_payload`
  - `changes`
  - `requires_confirmation`
  - `unresolved_constraints`

## Validator 정렬

v3부터 deterministic validator도 프롬프트 정책과 맞춘다.

- create turn에서 `changes`가 없으면 `[]`로 normalize하고 warning 처리한다.
- `unresolved_constraints`가 없으면 `[]`로 normalize하고 warning 처리한다.
- create turn의 minimum milestone 기준은 3개로 본다.
- 기존 완료 milestone 미포함은 create에서는 warning, partial_update에서는 invalid로 처리한다.
- title prefix의 요일/시간이 availability에 없는 경우 invalid 처리한다.
- title prefix 요일과 `scheduled_date` 실제 요일이 다르면 invalid 처리한다.

## Judge 호출 정책

Gemini judge 호출 전 0.5초 sleep을 둔다. 이는 연속 호출 시 외부 API demand/rate 문제를 완화하기 위한 최소 지연이다. 503 같은 외부 의존성 실패는 결과에서 `EXTERNAL_DEPENDENCY`로 별도 집계한다.

## 측정 기준

프롬프트 버전 비교 시 다음 값을 우선 본다.

- `prompt_version`
- `required_fields_present`
- `db_payload_schema_valid`
- `requires_confirmation_valid`
- `milestone_count_valid`
- `availability_alignment`
- `weekday_date_alignment`
- `deadline_compliance`
- `partial_update_scope_valid`
- `state_regression_count`
- `warnings`
- `judge_score`
- `case_completion_rate`

## 영향

`run-mileday-multiturn` 결과에는 `prompt_version`이 저장된다. 같은 fixture와 같은 모델을 사용해도 prompt version별 결과를 비교할 수 있다.

제품 DB schema는 변경하지 않는다. 시간 정보는 계속 milestone title에 포함한다.
