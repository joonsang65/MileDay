# ADR 0012: API parser selector contract 도입

## 상태

Accepted

## 배경

`gemini-3.5-flash-lite` 기반 API 하네스는 자연어 사용자 요청을 받아 MileDay 목표와 마일스톤 DB payload로 변환한다. 초기 parser는 `add`, `remove`, `rename` 요청을 처리하기 위해 사용자 문장과 LLM 출력의 `target`, `change`, `tasks`를 함께 해석했다.

이 방식은 빠르게 동작을 만들기에는 유용했지만, remove 대상 선택에서 다음 문제가 생겼다.

- `부담`, `짧`, `중복`, `숙소 비교` 같은 한국어 표현이 parser 코드에 늘어났다.
- 테스트 fixture 표현에 맞춰 규칙이 커질 위험이 있었다.
- 실제 DB 삭제로 이어질 수 있는 remove에서 자연어 scoring이 지나치게 큰 책임을 갖게 되었다.
- flash-lite가 구조화할 수 있는 정보를 parser가 다시 추론하고 있었다.

따라서 parser는 자연어 의미 해석을 줄이고, LLM이 명시적으로 구조화한 selector를 검증하는 역할로 축소해야 한다.

## 결정

API prompt의 `[SCHEDULE_INTENT]` contract에 selector 필드를 추가한다.

```text
operation: add, remove, rename, or none
target_selector_type: slot_id, task_text, weekday, position, duration, or ambiguous
target_selector_value: selector value
target_selector_confidence: high, medium, or low
preserve_selector_type: none, slot_id_list, weekday, or latest_added
preserve_selector_values: comma-separated values or none
requires_clarification: true or false
```

parser는 selector를 우선 사용한다. selector가 명확하고 기존 `plan_items`에서 안전하게 resolve될 때만 `patch_items`, `add_items`, `remove_slot_ids`를 생성한다.

scoring 기반 자연어 fallback은 유지하지만, primary decision path가 아니라 selector가 없거나 불완전한 legacy 출력에 대한 보조 경로로 둔다. `target_selector_confidence=low`, `target_selector_type=ambiguous`, `requires_clarification=true`인 경우에는 DB mutation 후보를 만들지 않는다.

## 설계 원칙

| 영역 | 결정 |
|---|---|
| 자연어 해석 | flash-lite prompt가 selector로 구조화한다. |
| parser 역할 | selector resolution, 보존 조건 확인, DB payload 후보 생성에 집중한다. |
| scoring 역할 | legacy/fallback 보조 경로로 제한한다. |
| DB mutation | selector가 0개 또는 여러 개로 resolve되면 실행하지 않는다. |
| ambiguous 요청 | `operation=none` 또는 `requires_clarification=true`로 처리한다. |
| preserve 요청 | 명시 slot, 요일, latest-added 같은 강한 selector만 보호 조건으로 사용한다. |

## 구현 내용

- `api_prompt.py`
  - `[SCHEDULE_INTENT]` 출력 형식에 `operation`, `target_selector_*`, `preserve_selector_*`, `requires_clarification`을 추가했다.
  - `SELECTOR_RULES`를 추가해 flash-lite가 자연어 target을 구조화하도록 유도했다.

- `api_intent.py`
  - selector 관련 key를 line-based intent parser에서 읽도록 확장했다.
  - 기존 `action`, `target`, `change`, `tasks` contract는 유지했다.

- `api_plan_builder.py`
  - selector resolver를 추가했다.
  - remove는 selector를 우선 사용하고, low-confidence 또는 clarification 요청은 no-op으로 처리한다.
  - 기존 scoring remove는 fallback으로 남겼다.
  - ambiguous add/remove 요청은 add와 remove 모두에서 mutation item을 만들지 않는다.

- tests
  - selector parsing contract를 추가했다.
  - prompt에 selector contract가 포함되는지 검증했다.
  - selector가 scoring보다 우선되는지, low-confidence selector가 no-op으로 처리되는지, preserve selector가 mutation을 막는지 검증했다.

## 영향

이 결정은 parser가 모든 한국어 표현을 직접 이해하려는 방향을 멈추게 한다. 앞으로 prompt를 개선할 때는 새로운 한국어 키워드를 parser에 추가하는 대신, flash-lite가 더 정확한 selector를 출력하도록 contract와 examples를 조정한다.

DB write와 SQL preview 단계에서는 selector resolution 결과만 신뢰해야 한다. 자연어 fallback scoring 결과는 낮은 신뢰의 보조 경로이므로, 실제 DB 삭제나 대규모 수정으로 확장할 때는 더 엄격한 guard를 적용해야 한다.

## 후속 구현: DB 적재와 SQL 실행 경계 정리

selector contract 도입 이후, flash-lite 개선 순서를 다음처럼 고정했다.

1. parser 기반 DB 적재 설계
2. parser 결과 기반 SQL / DB 실행
3. flash-lite 프롬프트 엔지니어링

이 순서를 채택한 이유는 DB 적재 구조가 먼저 정해져야 실제 SQL 실행 단위가 결정되고, SQL 실행 단위가 확정되어야 flash-lite에게 요구할 구조화 출력도 명확해지기 때문이다.

각 단계는 완료 후 계획 대비 비판적 검증을 수행하며, 최소 95% 이상 달성했을 때만 다음 단계로 넘어간다. 구현 목표는 가능한 100% 달성으로 둔다.

### Stage 1. Parser 기반 DB 적재 설계

parser의 `db_payload`는 기존 호환성을 위해 `goal`, `milestones` shape를 유지하면서 다음 필드를 추가했다.

```text
operation: create, add, remove, rename, partial_update, or none
mutations:
  operation
  requires_goal_id
  requires_milestone_id
  add
  remove
  rename
  no_op
  requires_clarification
```

operation별 의미는 다음과 같다.

| operation | DB 적재 후보 |
|---|---|
| create | goal 1개와 milestone N개 생성 |
| add | 기존 goal 아래 새 milestone 생성 |
| remove | 기존 milestone 삭제 |
| rename | 기존 milestone title 수정 |
| none | DB mutation 없음 |

deterministic validation은 문장 유사도보다 mutation 결과를 기준으로 판단한다.

- add: 이전 plan 대비 slot 수 증가
- remove: 이전 plan 대비 slot 수 감소
- rename: slot 유지, title 변경
- none/clarify: `patch_items`, `add_items`, `remove_slot_ids` 모두 비어 있어야 함

### Stage 2. Parser 결과 기반 SQL / DB 실행

`api_db_payload.py`의 SQL preview는 operation별로 확장했다.

- create: `INSERT INTO public.goals`, `INSERT INTO public.milestones`
- add: `INSERT INTO public.milestones`
- remove: `DELETE FROM public.milestones`
- rename: `UPDATE public.milestones SET title = ..., updated_at = now()`
- none: SQL mutation 없음

실제 DB write는 Supabase client 경로에서 수행한다.

- add는 `goal_id`, `user_id`를 포함해 milestone row를 insert한다.
- remove는 `id`, `goal_id`, `user_id` 조건으로 milestone row를 delete한다.
- rename은 `id`, `goal_id`, `user_id` 조건으로 milestone title을 update한다.
- none/clarify는 DB write와 manifest append를 하지 않는다.

runner는 각 turn이 passed일 때 즉시 DB write를 수행하고, partial update 후 다음 turn에서 사용할 in-memory DB state를 갱신한다.

- add: `milestone_slot_ids`, `milestone_titles`에 새 slot을 추가
- remove: 삭제된 slot을 state에서 제거
- rename: 기존 slot의 title만 갱신

cleanup은 manifest와 `TEST_USER_ID` 기준으로 동작한다. create record의 goal 삭제가 최종 안전망이며, add/remove/rename record는 operation 특성에 맞게 처리한다.

### Stage 3. flash-lite 프롬프트 엔지니어링

Stage 1, 2에서 확정된 DB mutation 요구사항을 prompt에 반영했다.

`[DB_MUTATION_RULES]`를 추가해 flash-lite가 다음 경계를 지키도록 했다.

- create는 goal과 selected milestone rows를 만든다.
- add는 기존 goal 아래 새 milestone만 추가한다.
- remove는 resolve된 기존 milestone만 삭제 대상으로 삼고, tasks는 비운다.
- rename은 날짜와 시간을 옮기지 않고 title만 바꾼다.
- none은 SQL을 만들지 않는다.
- flash-lite는 `goal_id`, `milestone_id`를 만들지 않는다. DB id는 parser/runner가 `slot_id`와 manifest로 resolve한다.

또한 add/remove/rename/none 예시를 prompt에 추가했다. 앞으로 프롬프트 개선은 parser에 한국어 키워드를 계속 추가하는 방식이 아니라, flash-lite가 더 정확한 `operation`과 selector를 출력하도록 contract와 examples를 조정하는 방향으로 진행한다.

## 후속 구현: prompt-test-6 분석 반영

`prompt-test-6`에서는 3개 case, 6개 turn을 실행했고 결과는 다음과 같았다.

| 항목 | 결과 |
|---|---:|
| passed | 1 |
| invalid | 3 |
| skipped | 2 |
| failed | 0 |
| all-turn-pass case | 0 |
| judge reject | 3 |

실패는 deterministic validation이 아니라 모두 LLM judge reject였다. 즉 parser schema와 DB payload 생성은 통과했지만, 사용자 요구사항 반영 품질이 부족했다.

분석 결과, 다음 문제가 확인됐다.

| case/turn | 문제 | 원인 |
|---|---|---|
| `multiturn-101-turn-2` | `자료 시각화 점검` add 요청이 목표명 추가로 바뀜 | add parser가 intent task보다 request fallback을 우선함 |
| `multiturn-102-turn-1` | 짧은 시간/긴 시간 task 배치가 반대로 됨 | create에서 slot별 task 매핑 contract가 부족함 |
| `multiturn-103-turn-1` | 월수금 중 2일만 선택 요청에서 3요일을 모두 사용함 | subset slot 선택이 구조화되지 않음 |

이에 따라 다음 4개 개선을 반영했다.

1. add task 우선순위 수정
   - `add_items` 생성 시 intent의 `tasks[0]`를 우선 사용한다.
   - intent task가 없을 때만 request 기반 fallback을 사용한다.
   - 이로써 flash-lite가 `자료 시각화 점검`을 올바르게 출력한 경우 parser가 목표명으로 덮어쓰지 않는다.

2. create slot 선택 contract 추가
   - `[SCHEDULE_INTENT]`에 `selected_slot_ids`를 추가했다.
   - create에서는 `selected_slot_ids` 순서와 `tasks` 순서가 1:1로 대응한다.
   - parser는 `selected_slot_ids`가 있으면 기본 순차 slot 배정보다 이를 우선 사용한다.

3. subset 선택 deterministic validation 추가
   - create 요청에서 `2일만`, `주말 중 하루`, `월수금 중 2일` 같은 subset 요구를 검사한다.
   - 선택된 slot의 요일 집합이 요청한 allowed day subset과 day count를 만족하지 않으면 `CREATE_SUBSET_SCOPE_MISMATCH`로 실패시킨다.
   - 이 검증은 judge 이전에 잘못된 slot 선택을 명확히 분류하기 위한 안전장치다.

4. prompt slot-task 대응 규칙 보강
   - create prompt에 `selected_slot_ids`와 `tasks`가 같은 순서여야 한다고 명시했다.
   - 일부 요일만 선택하는 요청은 선택된 subset만 사용하도록 했다.
   - `2일만`, `주말 중 하루` 같은 요구는 distinct weekday count로 지키도록 했다.
   - 짧은 slot은 가벼운 복습/점검, 긴 slot은 핵심 작업에 배정하도록 했다.

이 개선 이후 create/add 단계의 책임 경계는 다음처럼 정리된다.

| 영역 | 책임 |
|---|---|
| flash-lite | 사용자 요구를 `selected_slot_ids`, `operation`, selector, tasks로 구조화 |
| parser | 구조화된 slot/task를 plan item으로 변환 |
| deterministic validation | subset, slot/task schema, mutation effect 검증 |
| judge | 사용자 의도 반영 품질 최종 평가 |

## 검증

다음 테스트로 selector contract와 기존 parser 흐름을 확인했다.

```powershell
pytest tests/harness/mileday/test_api_intent.py tests/harness/mileday/test_api_prompt.py tests/harness/mileday/test_api_plan_builder.py tests/harness/mileday/test_api_parser.py tests/harness/mileday/test_api_validation.py
```

결과:

```text
36 passed
```

후속 구현 이후 전체 하네스 회귀 테스트를 수행했다.

```powershell
pytest tests/harness
python -m harness.cli test_api --help
```

결과:

```text
137 passed
test_api help 정상 출력
```

계획 대비 검토 결과:

| 단계 | 달성률 판단 | 근거 |
|---|---:|---|
| Stage 1. Parser 기반 DB 적재 설계 | 95% 이상 | operation별 `db_payload.mutations` shape와 deterministic validation이 테스트로 검증됨 |
| Stage 2. SQL / DB 실행 | 95% 이상 | SQL preview, Supabase add/remove/rename/no-op, runner state 갱신이 테스트로 검증됨 |
| Stage 3. 프롬프트 엔지니어링 | 95% 이상 | DB mutation rules와 operation별 예시가 prompt contract에 반영되고 테스트로 검증됨 |

남은 리스크는 실제 flash-lite 호출 결과가 새 selector contract를 얼마나 안정적으로 따르는지이다. 이는 다음 `test_api` 실험 결과에서 pass/fail 원인과 함께 별도로 평가한다.

`prompt-test-6` 개선 반영 후에는 다음 단위 검증을 추가했다.

```powershell
pytest tests/harness/mileday/test_api_intent.py tests/harness/mileday/test_api_plan_builder.py tests/harness/mileday/test_api_validation.py tests/harness/mileday/test_api_prompt.py tests/harness/mileday/test_api_parser.py
```

결과:

```text
44 passed
```

## 후속 구현: parser / plan builder / validation 논리 충돌 처리

Structured Output과 selector contract를 적용한 뒤, `prompt-test-13`부터 `prompt-test-17`까지의 결과를 다시 보면서 다음 논리 충돌을 확인했다.

| 문제 | 처리 방향 |
|---|---|
| parser가 `parsed.action`을 expected 값으로 덮어써 모델의 잘못된 action을 가림 | `intent_action_valid`를 deterministic validation에 추가 |
| expected operation과 모델 operation이 달라도 mutation 결과만 맞으면 통과 가능 | `intent_operation_valid`를 deterministic validation에 추가 |
| JSON schema 실패 후 freeform fallback이 schema 성공처럼 보임 | `fallback_used`를 parsed output, validation, summary에 별도 기록 |
| add 요청에서 preserve selector scope를 깨는 slot을 추가할 수 있음 | `add_preserve_scope_valid`를 추가하고 scope 밖 selected slot은 mutation 생성 금지 |
| remove/rename 다중 target이 DB mutation으로 이어질 위험 | selector가 정확히 1개 slot으로 resolve될 때만 remove/rename 허용 |
| rename에서 모델이 준 `tasks[0]`가 한글 fallback에 의해 덮어써짐 | rename task 추출은 `tasks[0]`를 최우선으로 사용 |
| 짧은/긴 시간 요청이 judge reject에만 의존 | `schedule_progression_valid`로 명시적 short/long create 요청의 duration 분포를 검증 |
| judge reject, fallback, self-check mismatch가 하나의 실패 흐름으로 섞임 | summary에 schema fallback, self-check mismatch, time/difficulty mismatch를 분리 집계 |

이번 구현의 핵심 원칙은 parser가 한국어 의미 해석을 더 늘리는 것이 아니라, flash-lite가 출력한 structured intent와 selector contract를 우선 검증하는 것이다. 기존 한글 keyword fallback은 legacy 보조 경로로 유지하지만, 제품 기준 판단에서는 schema JSON, selector resolution, deterministic mutation validation을 우선한다.

검증 명령:

```powershell
pytest tests/harness/mileday/test_api_validation.py tests/harness/mileday/test_api_plan_builder.py tests/harness/mileday/test_api_parser.py tests/harness/mileday/test_api_intent.py
pytest tests/harness
python -m harness.cli --help
python -m harness.cli test_api --help
```

결과:

```text
62 passed
162 passed
CLI help 정상 출력
```
