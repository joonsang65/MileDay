# ADR-0008: MileDay Multiturn Prompt Versioning

## Status

Accepted

## Purpose

이 문서는 `run-mileday-multiturn`에서 사용하는 MileDay 멀티턴 평가 프롬프트의 개선 이력을 기록한다. 기존 프롬프트는 삭제하지 않고 버전별 의도, 실패 원인, 수정 방향을 남긴다.

멀티턴 평가의 목표는 모델이 다음 조건을 안정적으로 만족하는지 확인하는 것이다.

- 사용자에게 보여줄 한국어 설명문 생성
- 이전 assistant 응답을 다음 turn에 반영
- 사용자가 요청한 부분만 수정
- 사용자의 가용 요일/시간 제약 준수
- DB 반영 전 사용자 확인 필요성 명시

현재 활성 버전은 `ACTIVE_MULTITURN_PROMPT_VERSION = "v11"`이다.

## v1

초기 버전이다. 설명문과 DB 반영 후보 JSON을 함께 생성하도록 했다.

한계:

- 필수 top-level field 누락이 자주 발생했다.
- `create`와 `partial_update`의 차이가 충분히 명확하지 않았다.
- `changes`, `unresolved_constraints`, `requires_confirmation` 계약이 약했다.
- milestone title에 시간 정보를 넣어야 한다는 규칙은 있었지만, 요일/시간 형식이 안정적이지 않았다.

## v2

출력 계약을 강화하고 `create`와 `partial_update` 규칙을 분리했다.

변경 사항:

- 필수 top-level key 6개를 명시했다.
- `create`에서는 `changes: []`를 요구했다.
- `unresolved_constraints: []` 기본값을 요구했다.
- `requires_confirmation: true`를 강제했다.
- `partial_update`에서는 이전 JSON을 기준으로 요청된 항목만 수정하도록 지시했다.

한계:

- 모델이 여전히 일부 field를 누락했다.
- create turn에서 fixture의 `min_milestones` 기준을 만족하지 못하는 경우가 있었다.
- 완료된 기존 milestone 보존 기준이 create와 partial_update에 같은 강도로 적용되어 평가가 과도하게 엄격했다.

## v3

v2 결과를 바탕으로 프롬프트와 deterministic validator 기준을 맞췄다.

변경 사항:

- create turn의 최소 milestone 기준을 3개로 완화했다.
- create turn에서 `changes`, `unresolved_constraints` 누락 시 `[]`로 normalize하고 warning 처리했다.
- 완료된 기존 milestone 미포함은 create에서는 warning, partial_update에서는 invalid로 분리했다.
- title prefix의 요일/시간이 availability와 맞는지 검증했다.
- `scheduled_date`의 실제 요일과 title prefix 요일이 일치하는지 검증했다.

관찰 결과:

- 모델이 JSON 구조는 대체로 따라왔지만 날짜와 요일을 직접 계산하면서 `availability_alignment` 실패가 반복됐다.

## v4

모델에게 날짜 계산을 맡기지 않고, harness가 계산한 허용 날짜 후보 중에서만 선택하도록 했다.

변경 사항:

- prompt에 기준 날짜와 허용 날짜 후보를 추가했다.
- `scheduled_date`와 `title_prefix`를 직접 만들지 말고 후보 값을 복사하도록 지시했다.
- 오늘 이전 날짜, 후보에 없는 날짜, 영어 weekday, 깨진 요일 문자열 사용을 금지했다.

한계:

- prompt가 길어지면서 출력 계약 누락과 extra field 생성이 다시 발생했다.
- 모델이 후보 값을 복사하는 과정에서도 한글 요일 prefix가 깨지는 경우가 있었다.

## v6

v4의 제약은 유지하되 프롬프트 길이를 줄였다. 또한 Gemini judge 호출에는 지수 백오프를 적용했다.

변경 사항:

- 긴 설명형 규칙을 `STRICT RULES` 목록으로 축약했다.
- prompt 마지막에 `[FINAL REMINDER]`를 추가했다.
- JSON top-level key 누락/추가 금지를 반복 지시했다.
- deterministic validator 기준은 완화하지 않았다.
- Gemini judge 재시도는 최대 3회, 대기 시간은 `0.5s`, `1.0s`, `2.0s`로 설정했다.

관찰 결과:

- `[EXPLANATION]`과 `[JSON]` 구조는 일부 개선됐지만, DB payload schema 위반이 계속 발생했다.
- 모델이 `goal_id`, `id`, `scheduled_date` 같은 DB row 형태를 top-level에 직접 출력하는 사례가 있었다.
- 한글 요일 prefix가 깨지거나, 문자열 quote가 누락되어 JSON 안정성이 떨어졌다.

## v7

v7은 설계를 바꿨다. 모델이 최종 DB payload를 직접 만들지 않고, `slot_id` 기반 일정 제안만 생성한다. DB 반영 가능한 `goal`/`milestones` payload는 harness가 rule-based로 생성한다.

변경 사항:

- 출력 JSON에서 `db_payload` 생성을 금지했다.
- 새 필수 field는 `action`, `explanation`, `schedule_plan`, `changes`, `requires_confirmation`, `unresolved_constraints`이다.
- `schedule_plan[]`은 `slot_id`, `task`만 허용한다.
- `slot_id`는 `[ALLOWED_SLOTS]`에서 그대로 복사해야 한다.
- `task`에는 요일/시간 prefix를 넣지 않는다.
- harness가 `slot_id`를 `scheduled_date`, `title_prefix`로 변환하고, 최종 milestone title을 만든다.
- partial update도 변경 후의 전체 `schedule_plan`을 다시 출력하게 한다.

기대 효과:

- 모델의 날짜/요일 계산 오류를 제거한다.
- 한글 요일 prefix 깨짐이 DB payload에 반영되지 않게 한다.
- DB DTO field 누락/오염 문제를 rule-based builder로 통제한다.
- 모델은 일정 품질과 변경 의도 판단에 집중하고, 저장 가능한 payload는 코드가 책임진다.

남은 리스크:

- 모델이 `slot_id`를 invent하거나 중복 선택할 수 있다.
- partial update에서 이전 schedule_plan 보존은 여전히 judge와 deterministic 비교가 함께 필요하다.
- 사용자 요청이 allowed slot으로 충족 불가능한 경우 `clarify` 처리 정책을 제품 UX와 맞춰야 한다.

## v8

v8은 모델을 JSON 생성기가 아니라 일정 제안/의도 해석기로 사용한다. 모델 출력은 사용자에게 보여줄 설명과 slot 기반 PLAN만 포함하고, DB 반영 가능한 `goal`/`milestones` payload는 harness가 rule-based로 생성한다.

변경 사항:

- 실행 프롬프트를 `harness/mileday/multiturn_prompts.py`로 분리했다.
- v1~v7은 실행 코드가 아니라 `PROMPT_VERSION_HISTORY` 변경 이력으로 보관한다.
- 활성 프롬프트는 `ACTIVE_MULTITURN_PROMPT_VERSION = "v8"`로 고정한다.
- 출력 계약은 `[USER_MESSAGE]`, `[PLAN]`, `[/PLAN]`만 사용한다.
- PLAN 줄은 `- S001 | 작업명`처럼 slot_id와 task만 포함한다.
- 모델은 JSON, fenced code block, DB payload를 생성하지 않는다.
- parser는 PLAN을 읽어 `plan_items`를 만들고, slot_id를 allowed slot과 매핑해 rule-based DB payload를 생성한다.
- 우선 검증 범위는 `multiturn_schedule.pretty.json`의 첫 번째 case로 제한했다.

관찰 결과:

- 첫 번째 case 1턴은 v8 구조로 파싱되고 rule-based DB payload 생성이 가능했다.
- sandbox 내부 실행에서는 Gemini judge 네트워크 접근이 `WinError 10013`으로 실패했으나, 승인된 실행에서는 judge가 완료됐다.
- 승인된 실행 기준으로 1턴은 통과했고 2턴은 `milestone_count_valid`에서 invalid가 발생했다.
- 2턴 invalid는 prompt/validator가 이전 PLAN 전체 유지와 부분 변경 범위를 더 명시해야 함을 보여준다.
- 첫 번째 case 3턴의 일요일 오전 이동 요청은 현재 availability가 월/수/토 19:00-21:00만 허용하므로, 후속 검증 시 fixture 제약 충돌로 드러날 가능성이 높다.

## v9

v9는 partial update를 전체 PLAN 재출력이 아니라 PATCH 방식으로 바꿨다. 모델은 변경할 slot_id와 새 작업명만 출력하고, 이전 PLAN 보존과 최종 DB payload 생성은 harness가 처리한다.

변경 사항:

- 활성 프롬프트를 `ACTIVE_MULTITURN_PROMPT_VERSION = "v9"`로 변경했다.
- create 출력은 `[USER_MESSAGE]`와 `[PLAN]`을 사용한다.
- partial_update 출력은 `[USER_MESSAGE]`와 `[PATCH]`를 사용한다.
- PATCH는 기존 slot_id의 작업명만 변경할 수 있고, 날짜/요일/시간 이동은 직접 수행하지 못한다.
- PATCH를 이전 `plan_items`에 rule-based로 병합한다.
- “수요일은 ...”처럼 요일 단위 변경 요청이 들어오면, PATCH가 선택한 요일과 같은 기존 slot 전체에 변경 작업명을 확장 적용한다.
- 상태 보존 검증은 title 문자열이 아니라 slot_id 유지 여부를 기준으로 계산한다.
- 작업명에 문장형 영어가 들어가면 invalid 처리하되, `10km` 같은 단위 표기는 허용한다.
- 작업명에 slot과 다른 요일명이나 `오전/오후` 같은 시간 표현이 들어가면 invalid 처리한다.

관찰 결과:

- v9 run 15에서 turn 1과 turn 2는 통과했다.
- turn 2의 “수요일은 회복 위주” 요청은 모델이 S002 하나만 PATCH했지만, harness가 같은 수요일 slot 전체로 확장해 judge를 통과했다.
- turn 3은 “일요일 오전”이 availability에 없는데 모델이 토요일 slot 작업명에 “일요일 오전”을 넣어 judge reject가 발생했다.
- v9 run 16에서는 모델이 `19:00-21:00`을 `오전 7시부터 오후 9시`로 잘못 설명해 turn 1에서 judge reject가 발생했다.
- 이에 따라 USER_MESSAGE에서 시간은 `19:00-21:00` 같은 숫자 범위를 그대로 복사하고, 오전/오후 변환을 금지하는 규칙을 추가했다.

남은 판단:

- 현재 fixture의 turn 3은 실제 availability와 충돌하는 요청이다. 평가 목적이 “불가능한 요청 감지”라면 기대 결과를 empty PATCH + 제약 설명으로 명확히 해야 한다.
- 사용자 설명문까지 완전 안정화하려면 USER_MESSAGE도 모델 자유 생성이 아니라 rule-based 템플릿으로 생성하는 방향을 검토할 수 있다.

## v10

v10은 v9에서 남은 `USER_MESSAGE` 왜곡 문제를 제거하기 위해 모델 출력에서 사용자 설명문을 완전히 제외했다. 모델은 일정 의도 해석 결과인 PLAN/PATCH만 작성하고, 사용자에게 보여줄 설명문은 harness가 fixture와 parsed result를 기반으로 rule-based로 생성한다.

변경 사항:

- 활성 프롬프트를 `ACTIVE_MULTITURN_PROMPT_VERSION = "v10"`으로 변경했다.
- create 출력은 `[PLAN]`, `[/PLAN]`만 사용한다.
- partial_update 출력은 `[PATCH]`, `[/PATCH]`만 사용한다.
- 모델은 사용자 설명문, JSON, fenced code block, markdown table을 출력하지 않는다.
- `user_message`는 harness가 `goal`, `availability`, `plan_items`, `patch_items`를 기반으로 생성한다.
- availability 설명은 fixture의 `start_time`/`end_time`을 그대로 사용하므로 `19:00-21:00`이 `오전 7시부터 오후 9시`로 왜곡되지 않는다.

기대 효과:

- 사용자 설명문과 DB payload 사이의 시간 표현 불일치를 제거한다.
- judge 실패 원인을 모델의 자연어 설명 품질이 아니라 PLAN/PATCH 의미 정렬로 좁힌다.
- 작은 로컬 모델은 slot 선택과 작업명 판단에만 집중하고, 제품 응답 문장은 코드가 안정적으로 책임진다.

관찰 결과:

- 5개 case 전체 실행에서는 출력 계약 미준수, `slot_id` 환각, partial update 의미 반영 실패가 반복됐다.
- 특히 `S033`처럼 이전 PLAN에 없는 slot_id를 PATCH 대상으로 생성하는 문제가 발생했다.
- 이는 모델 크기만 키워서 해결하기보다 모델에게 내부 slot 선택을 맡기지 않는 구조가 필요하다는 판단으로 이어졌다.

## v11

v11은 모델을 slot 기반 계획 생성기가 아니라 일정 의도 해석기로 더 좁힌다. 모델은 어떤 대상을 어떻게 바꿀지와 작업명 후보만 작성하고, 실제 slot 선택, 날짜 매핑, 기존 일정 보존, DB payload 생성은 harness가 rule-based로 처리한다.

변경 사항:

- 활성 프롬프트를 `ACTIVE_MULTITURN_PROMPT_VERSION = "v11"`로 변경했다.
- 출력 계약은 `[일정_의도]`, `[/일정_의도]`만 사용한다.
- 모델 출력 field는 한글 key인 `행동`, `대상`, `변경`, `작업`으로 제한한다.
- 모델은 내부 식별자, 날짜, 제목 앞 시간표현, JSON, markdown table을 출력하지 않는다.
- 모델에게 보이는 기준 날짜, 목표, 가능 시간, 배정 가능 후보, 기존 일정 컨텍스트도 한글 key로 렌더링한다.
- 배정 가능 후보에서는 내부 slot id를 노출하지 않고 순번/날짜/요일/시간만 제공한다.
- create에서는 `tasks`를 allowed slot 앞쪽부터 rule-based로 배정한다.
- partial update에서는 `target`/`change`/현재 사용자 요청을 기준으로 harness가 이전 PLAN에서 수정 대상 slot을 선택한다.
- “수요일 일정 변경”처럼 요일이 명시되면 해당 요일의 이전 slot 전체를 코드가 선택한다.
- “마지막”, “최종” 요청은 조건에 맞는 이전 slot 중 가장 늦은 slot 하나를 코드가 선택한다.
- 요청한 이동 대상 요일이 현재 availability에 없으면 변경하지 않고, rule-based 사용자 메시지에서 바로 반영하기 어렵다고 안내한다.

기대 효과:

- 모델의 `slot_id` 환각을 제거한다.
- 내부 DB 변환 가능성은 모델 출력 안정성이 아니라 deterministic rule에 의해 보장한다.
- 작은 로컬 모델은 자연어 의도 해석과 작업명 제안에 집중한다.
- 제품 적용 시에도 사용자 요청 해석 결과와 DB 반영 로직을 분리해 장애 범위를 줄인다.
