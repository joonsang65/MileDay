# ADR 0013: Structured Output 기반 flash-lite prompt 개선 계획

## 상태

Accepted

## 배경

현재 `prompt-tune` 브랜치는 모델 비교가 아니라 `gemini-3.5-flash-lite`를 MileDay 제품 기능에 적용 가능한 수준까지 끌어올리는 것을 목표로 한다.

기존 ADR 0012에서는 parser가 자연어를 직접 해석하지 않고, flash-lite가 출력한 selector contract를 검증해 DB mutation 후보를 만드는 방향을 결정했다. 이제 다음 단계는 이 구조를 전제로 prompt tuning 방식을 정리하는 것이다.

핵심 방향은 긴 Chain-of-Thought를 출력하게 만드는 것이 아니라, Gemini Structured Output과 selector contract를 사용해 parser와 DB 실행이 신뢰할 수 있는 구조화 출력을 만드는 것이다.

참고 기준:

- Gemini Structured Output: https://ai.google.dev/gemini-api/docs/generate-content/structured-output
- Gemini Thinking: https://ai.google.dev/gemini-api/docs/thinking

## 제품 적용 기준

flash-lite prompt/parser 개선의 제품 적용 기준은 ADR 0011의 기준을 따른다.

| 지표 | 최소 기준 | 목표 기준 |
|---|---:|---:|
| deterministic validation pass | 100% | 100% |
| critical failure | 0건 | 0건 |
| Turn1 create pass rate | 95% 이상 | 98% 이상 |
| Turn2/3 partial update pass rate | 85% 이상 | 90% 이상 |
| all-turn-pass case rate | 70% 이상 | 80% 이상 |
| skipped 제외 평균 judge score | 0.85 이상 | 0.90 이상 |
| 평균 latency | 2.5초 이하 | 2.0초 이하 |

## 결정

프롬프트 개선 순서는 다음으로 고정한다.

1. Gemini Structured Output / JSON Schema 적용
2. Selector Contract 강화
3. CoT 대신 짧은 self-check 필드 적용
4. 최소 few-shot 예시 정리
5. negative example 추가
6. thinking level / verbosity 최소화
7. 테스트 결과 기반 반복 개선

이 순서를 사용하는 이유는 출력 schema가 먼저 고정되어야 selector contract와 parser validation이 안정화되고, 그 이후에 예시와 negative example을 실패 유형에 맞춰 최소 단위로 조정할 수 있기 때문이다.

## Structured Output 적용 계획

현재 `[SCHEDULE_INTENT]` line-based block은 즉시 제거하지 않는다. 기존 parser와 테스트가 이 형식을 기준으로 동작하고 있으므로, 다음 단계에서 Gemini `responseSchema` 기반 JSON 출력으로 점진 전환한다.

전환 대상 schema의 필수 필드는 다음을 기준으로 한다.

```text
action
operation
selected_slot_ids
target_selector_type
target_selector_value
target_selector_confidence
preserve_selector_type
preserve_selector_values
requires_clarification
tasks
mutation_safety_check
```

Structured Output은 syntax와 key shape를 안정화하기 위한 장치다. schema를 통과한 출력이라도 실제 DB write 전에 parser의 semantic validation을 반드시 통과해야 한다.

검증 책임은 다음처럼 유지한다.

| 영역 | 책임 |
|---|---|
| Gemini responseSchema | key 누락, 타입 오류, enum 오류 감소 |
| api_intent/api_parser | schema 결과를 parser 내부 intent로 변환 |
| api_plan_builder | selector를 plan/add/remove/rename 후보로 변환 |
| api_validation | mutation 결과와 DB payload safety 검증 |
| api_db_client | 검증된 operation만 실제 DB에 반영 |

## Selector Contract 강화 계획

flash-lite는 자연어 요청을 DB mutation으로 직접 실행하지 않는다. 대신 자연어 해석 결과를 selector로 구조화한다.

parser는 다음 조건을 만족할 때만 mutation 후보를 만든다.

- `operation`이 `add`, `remove`, `rename` 중 하나로 명확함
- `requires_clarification=false`
- `target_selector_confidence`가 `high` 또는 허용 가능한 `medium`
- remove/rename은 selector가 정확히 1개 slot으로 resolve됨
- preserve selector와 충돌하지 않음

다음 경우에는 mutation을 만들지 않는다.

- `target_selector_type=ambiguous`
- `target_selector_confidence=low`
- selector가 0개 slot으로 resolve됨
- selector가 여러 slot으로 resolve됨
- 사용자 요청에 임의 선택 금지 또는 확인 필요 의도가 있음

이 정책은 특히 remove/delete 계열에서 오삭제를 막기 위한 안전 기준이다.

## CoT 적용 방침

긴 Chain-of-Thought 출력은 사용하지 않는다.

이유는 다음과 같다.

- flash-lite 선택 이유가 비용과 latency이므로 긴 reasoning 출력은 목표와 충돌한다.
- DB mutation workflow에서는 추론 설명보다 schema 안정성과 semantic validation이 더 중요하다.
- 긴 free-form reasoning은 structured output 안정성을 흔들 수 있다.

대신 짧은 self-check 필드를 사용한다.

```text
mutation_safety_check: single_target_matched, no_target_matched, multiple_targets_matched, ambiguous_request, create_scope_checked
requires_clarification: true or false
target_selector_confidence: high, medium, or low
```

reasoning은 모델 내부에 맡기고, 최종 출력에는 DB 실행 가능 여부를 판단할 수 있는 최소 신호만 남긴다.

## Few-shot / Negative Example 정책

few-shot은 실패 유형을 줄이는 데 필요한 최소 수만 둔다.

기본 예시는 다음 4개로 제한한다.

| 예시 | 목적 |
|---|---|
| create | 날짜/시간/작업을 slot에 정확히 배정 |
| add | 기존 goal 아래 새 milestone만 추가 |
| remove | 단일 target selector가 resolve될 때만 삭제 |
| none/clarify | 모호한 요청은 mutation 없이 확인 필요 처리 |

`rename` 예시는 실패가 반복될 때만 추가한다. 예시 수가 늘어나면 prompt가 길어지고 특정 fixture 표현에 과적합될 수 있으므로, 실패 유형이 반복될 때만 추가한다.

negative example은 다음 위험을 막는 데 집중한다.

- remove 대상이 모호한데 임의 삭제하는 경우
- subset 요청에서 가능한 slot 전체를 사용하는 경우
- add 요청에서 기존 milestone title을 덮어쓰는 경우
- rename 요청에서 날짜나 시간을 함께 바꾸는 경우
- confirmation이 필요한 요청인데 DB mutation 후보를 만드는 경우

## Gemini Config 운영 방침

flash-lite는 비용 민감 모델로 선택했으므로 thinking과 verbosity는 최소화한다.

- thinking은 `minimal` 또는 모델 기본 최소 수준을 우선 사용한다.
- structured output과 deterministic parser validation을 우선 개선한다.
- thinking level 증가는 반복 실패가 reasoning 부족으로 확인될 때만 검토한다.
- temperature, top-p, top-k 같은 sampling 설정은 deterministic task에 맞게 낮게 유지하거나 Gemini 권장 기본값을 따른다.
- 출력은 DB 실행에 필요한 필드만 포함하고 설명문, markdown, 장문 reasoning은 금지한다.

## 반복 개선 절차

프롬프트 개선은 test result 기반으로만 진행한다.

1. `test_api --write-no`로 prompt/parser 품질을 먼저 확인한다.
2. deterministic validation 실패는 parser/schema/validation 문제로 분류한다.
3. judge reject는 prompt contract 또는 example 문제로 분류한다.
4. DB write 실패는 payload/client/manifest state 문제로 분류한다.
5. 같은 실패 유형이 반복될 때만 prompt example 또는 negative example을 추가한다.
6. 변경 후 전체 하네스 테스트와 `test_api` 결과를 함께 비교한다.

프롬프트에 한국어 키워드를 계속 추가하는 방식은 피한다. 자연어 다양성은 flash-lite의 selector 출력으로 흡수하고, parser는 selector resolution과 mutation safety 검증을 담당한다.

## 검증 계획

문서 반영 후에는 코드 변경 없이 다음 항목을 확인한다.

- ADR 0011의 제품 적용 기준과 이 문서의 목표 수치가 일치하는지 확인
- ADR 0012의 parser/selector/DB mutation 순서와 이 문서의 prompt tuning 순서가 충돌하지 않는지 확인
- `api_prompt.py`의 현 contract가 이 문서의 향후 schema 필드와 대응되는지 확인

향후 구현 단계에서는 다음 순서로 검증한다.

```powershell
pytest tests/harness/mileday/test_api_prompt.py
pytest tests/harness/mileday/test_api_intent.py
pytest tests/harness/mileday/test_api_parser.py
pytest tests/harness/mileday/test_api_validation.py
pytest tests/harness
python -m harness.cli test_api --write-no
```

실제 DB write 검증이 필요한 경우에만 다음 명령을 실행한다.

```powershell
python -m harness.cli test_api
```

## 영향

이 문서는 ADR 0012를 대체하지 않는다. ADR 0012는 parser와 DB mutation 경계 결정이고, 이 문서는 그 경계를 기준으로 flash-lite prompt를 제품 기준까지 개선하기 위한 실행 계획이다.

앞으로 prompt tuning 작업은 다음 원칙을 따른다.

- 먼저 schema와 selector contract를 안정화한다.
- 그 다음 실패 유형별로 examples를 최소 보강한다.
- CoT 출력은 사용하지 않고, 짧은 self-check 필드만 사용한다.
- 제품 적용 여부는 정성 판단이 아니라 ADR 0011의 수치 기준으로 판단한다.
