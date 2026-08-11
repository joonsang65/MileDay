# ADR 0010: API 멀티턴 프롬프트 개선

## 상태

Accepted

## 배경

MileDay 멀티턴 API 평가는 로컬 LLM 하네스 태스크와 Gemini API 모델을 비교하기 위해 추가되었다. API 경로는 모델이 먼저 일정 변경 의도를 생성하고, 하네스의 규칙 기반 파서가 이를 바탕으로 `plan_items`, `patch_items`, `db_payload`를 구성하는 방식이다.

`gemini-mileday-multiturn-5`부터 `gemini-mileday-multiturn-8`까지의 실행 결과를 보면, intent-only 프롬프트 적용 이후 JSON 형식과 출력 계약은 대체로 안정화되었다. 하지만 부분 수정 요청에서 어떤 일정을 수정해야 하는지 판단하는 target selection 문제가 계속 주요 실패 원인으로 남았다.

관찰된 문제는 다음과 같다.

- `하나만`, `일정 중 하나만`: 사용자가 한 건만 변경하라고 했는데 모델 의도 또는 파서가 여러 슬롯을 수정 대상으로 확장했다.
- `두 번째 주`: judge가 기대하는 주차 범위와 다른 슬롯이 선택되는 문제가 있었다.
- `수요일`, `평일`: 범위가 넓거나 좁게 해석되어 일부만 수정되거나 잘못된 요일이 선택되었다.
- `평일 일정`, `주말 일정`: 그룹 범위 요청에는 평일/주말 기준을 명시적으로 적용할 필요가 있었다.
- `작업명만 다시 정리`: 단일 슬롯 수정이나 거절 케이스가 아니라, 날짜와 시간은 유지한 채 전체 작업명만 다시 쓰는 요청으로 처리해야 했다.

## 결정

로컬 멀티턴 프롬프트 `v11`과 별도로 API 전용 프롬프트 버전 `v12-api`를 추가한다.

API 프롬프트에는 다음 내용을 포함한다.

- 단일 대상, 평일/주말 그룹, 마지막 일정, 전체 작업명 재작성, 추가, 삭제 요청을 구분하는 `PARTIAL_UPDATE_SCOPE_MAP`.
- 이전 계획 컨텍스트가 있을 때 가능한 한 구체적인 `slot_id`를 target으로 사용하라는 `TARGET_RULES`.
- 5번부터 8번 실행에서 확인된 실패 패턴에 대한 예시.
- 삭제 요청을 제외하고, 변경할 target 수와 task 줄 수가 일치해야 한다는 규칙.

로컬 Ollama 멀티턴 명령은 기존 `v11`을 유지한다. Gemini API 명령은 `v12-api`를 사용하고, 해당 프롬프트 버전을 결과 메타데이터와 배치 요약에 기록한다.

## 근거

실패한 실행의 대부분은 JSON 파싱 실패나 출력 계약 위반이 아니었다. 로컬 구조는 유효했지만 의미적으로 잘못된 범위를 수정해서 judge가 거절한 경우가 많았다.

따라서 API 모델이 intent를 만들기 전에 부분 수정 범위를 명시적으로 분류하도록 프롬프트를 강화하면, 규칙 기반 파서가 더 안정적인 입력을 받을 수 있다.

API 프롬프트를 로컬 프롬프트와 분리한 이유는 API 비교 실험을 조정하는 동안 로컬 LLM 벤치마크 기준선을 흔들지 않기 위해서다.

## 현재 결과

8번 실행은 `v12-api`로 10개 케이스를 평가했다.

| model | passed | invalid | failed | skipped | all-turn-pass cases | avg latency ms |
|---|---:|---:|---:|---:|---:|---:|
| gemini-3.5-flash-lite | 24 | 3 | 0 | 3 | 7/10 | 1424.519 |
| gemini-3.6-flash | 26 | 4 | 0 | 0 | 6/10 | 6330.400 |

이 결과는 `v12-api`가 부분 수정 안정성을 개선했음을 보여준다. 다만 target disambiguation은 프롬프트만으로 완전히 해결되지 않았고, 파서와 검증기의 결정적 보완이 필요하다.

12번 실행에서는 judge 기준을 강화한 뒤 30개 케이스를 평가했다.

| model | passed | invalid | failed | skipped | all-turn-pass cases | avg latency ms |
|---|---:|---:|---:|---:|---:|---:|
| gemini-3.5-flash-lite | 33 | 26 | 0 | 31 | 4/30 | 1409.390 |
| gemini-3.6-flash | 47 | 23 | 0 | 20 | 7/30 | 6987.900 |

`skipped`를 제외한 LLM judge 평균은 다음과 같다.

| model | non-skipped records | scored records | avg judge score | passed avg | invalid avg |
|---|---:|---:|---:|---:|---:|
| gemini-3.5-flash-lite | 59 | 59 | 0.742 | 1.000 | 0.415 |
| gemini-3.6-flash | 70 | 69 | 0.780 | 1.000 | 0.309 |
| overall | 129 | 128 | 0.763 | - | - |

`gemini-3.6-flash`는 `skipped` 제외 70건 중 1건이 deterministic validation에서 먼저 `invalid` 처리되어 judge score가 없었다. 따라서 평균 계산에서는 69건만 사용했다.

## 후속 작업

권장되는 파서 및 검증기 개선 방향은 다음과 같다.

- 부분 수정 요청을 `single_target`, `weekday_scope`, `weekday_group_scope`, `last_target`, `rewrite_all_tasks`, `add`, `remove`로 분류한다.
- target 선택을 느슨한 target 문자열 검색이 아니라 classifier 결과에 의존하도록 바꾼다.
- judge 호출 전에 부분 수정 범위를 deterministic validation으로 먼저 검증한다.
- `작업명만 다시 정리` 요청은 날짜와 시간을 보존한 전체 작업명 재작성으로 처리한다.
- `두 번째 주` 같은 주차 bucket 계산을 파서와 judge 기대 기준 사이에서 일치시킨다.
- 여러 target과 여러 task가 함께 나오는 경우, task를 target slot에 1:1로 매핑한다.
- `A 또는 B 중 하나` 요청은 add/remove를 동시에 수행하지 못하도록 제한한다.

## Judge 기준 강화

기존 Gemini judge는 사용자-facing 일정 수정에 적용하기에는 통과 기준이 다소 후했다. 이에 따라 다음 기준을 채택했다.

- 통과하려면 `score >= 0.9`를 만족해야 한다.
- 통과하려면 `critical_failures`가 비어 있어야 한다.
- judge가 `is_aligned=true`를 반환하더라도, 점수나 critical failure 조건을 만족하지 못하면 통과로 보지 않는다.
- target/scope 오류 디버깅을 위해 judge 응답에 `dimension_scores`를 보존한다.

치명 실패 코드는 다음과 같다.

- `WRONG_TARGET_SCOPE`
- `OVER_PATCHED_SINGLE_TARGET`
- `UNDER_PATCHED_SCOPE`
- `PRESERVED_ITEM_CHANGED`
- `DATE_TIME_CHANGED`
- `UNSUPPORTED_REFUSAL`
- `PAYLOAD_EXPLANATION_MISMATCH`

## 현재 브랜치 구현 상태

현재 `prompt-tune` 브랜치에서는 API prompt/parser 개선에 집중하기 위해 flash-lite 전용 경로만 유지한다.

- 실행 명령은 `python -m harness.cli test_api`이다.
- API 모델은 `gemini-3.5-flash-lite`로 고정한다.
- `--model-id`, `--sleep-seconds`, `--mode`는 사용하지 않는다.
- sleep time은 코드 상수 `3.0`초로 고정한다.
- run id는 `prompt-test-<n>` 형식이다.
- Gemini 관련 환경 변수는 `GEMINI_API_KEY` 하나만 사용한다.
- generation과 judge는 동일한 API key를 사용한다.
- API prompt는 `harness/mileday/api_prompt.py`에서 관리한다.
- parser orchestration은 `harness/mileday/api_parser.py`의 `evaluate_api_multiturn_record()`가 담당한다.
- intent parsing, plan 생성, validation, DB payload, summary는 각각 별도 API 모듈로 분리한다.
- 실제 DB write는 하지 않고, DB payload와 SQL preview 생성 가능한 순수 함수까지만 둔다.
