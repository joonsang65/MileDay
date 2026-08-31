# ADR-0009: MileDay 멀티턴 자체 테스트셋 설계

## Status

Draft

## Purpose

이 문서는 MileDay 멀티턴 일정 제안 기능을 검증하기 위한 자체 테스트셋 설계 기준을 정의한다. 테스트셋은 단순 일정 생성 능력보다, 실제 사용자가 연속 대화에서 요청하는 **부분 수정, 상태 보존, 불가능한 요청 처리, 사용자 승인 전 DB 반영 후보 생성 안정성**을 검증하는 데 초점을 둔다.

새 테스트셋은 총 30개 case로 구성한다. 각 case는 2~5개의 turn을 가지며, 전체 turn 수는 85~95개, 평균 turn 수는 2.8~3.2개로 고정한다. 현재 fixture는 30개 case와 90개 turn으로 구성한다.

## Definitions

| 용어 | 정의 |
|---|---|
| Plan | harness가 현재 turn까지 유지하는 slot 기반 일정 상태다. 내부적으로 `plan_items[]`로 표현한다. |
| Milestone | DB 반영 후보의 개별 일정 항목이다. 현재 DTO field는 `title`, `color`, `scheduled_date`만 허용한다. |
| Availability slot | 사용자가 제공한 요일/시간 조건에서 생성된 가능한 일정 후보 날짜다. |
| Canonical slot | harness가 `scheduled_date`, `day_of_week`, `start_time`, `end_time`, `title_prefix`를 deterministic하게 계산한 slot이다. |
| Partial update | 기존 plan을 기준으로 사용자가 요청한 일부 일정만 수정하는 turn이다. 현재 fixture에서는 `expected_action=partial_update`를 사용한다. |
| Preserved milestone | 사용자가 언급하지 않아 유지되어야 하는 milestone이다. |
| Protected milestone | 완료됐거나 fixture에서 보호 대상으로 지정되어 수정되면 안 되는 milestone이다. |
| Completed milestone | `existing_schedule[].is_completed=true`인 기존 milestone이다. |
| No-op | 요청 대상이 없거나 제약상 반영하면 안 되어 기존 plan을 유지하는 처리다. 현재 fixture에서는 `expected_action=partial_update`, `expected_operation=none`, `expected.effect.expected_no_op=true`로 표현한다. |
| Clarification | 대상 후보가 여러 개라 임의 선택하면 위험하므로 사용자 확인이 필요한 처리다. 현재 fixture에서는 `expected_operation=none`, `expected.effect.expected_clarification=true`로 표현한다. |
| DB-ready payload | rule-based planner가 생성한 `goal` / `milestones` payload가 DTO field, availability, deadline, 날짜·요일·시간 prefix 검증을 통과한 상태다. |
| Case completion | 해당 case의 마지막 turn까지 실행되어 최종 plan이 생성된 상태다. judge 통과 여부와 분리한다. |
| All-turn-pass case | case의 모든 turn이 deterministic validation과 Gemini judge를 모두 통과한 상태다. |
| Safety Gate | 일정 데이터를 잘못 수정할 수 있는 치명적 조건을 별도로 모은 필수 통과 기준이다. |
| Deterministic validation | schema, prefix, availability, deadline, DTO field, 상태 보존처럼 코드로 검증 가능한 항목이다. |
| Judge validation | 의미 정렬, 의도 반영, 자연어 요청 해석처럼 rule만으로 판단하기 어려운 항목을 Gemini가 보완 평가하는 단계다. |

## Background

MileDay는 사용자가 목표와 마일스톤을 관리하는 일정 계획 애플리케이션이다. 현재 멀티턴 LLM 평가에서는 사용자가 자연어로 목표, 마감일, 가용 요일/시간을 말하면 모델이 일정 의도를 해석하고, harness가 이를 rule-based로 DB 반영 가능한 `goal` / `milestones` payload로 변환하는 구조를 검증하고 있다.

이 구조는 처음부터 모델에게 완성된 JSON DB payload를 생성하게 하는 방식에서 출발했지만, 테스트 과정에서 다음 한계가 반복적으로 확인됐다.

- 모델이 JSON field를 누락하거나 허용되지 않은 field를 추가했다.
- 날짜, 요일, 시간 prefix를 모델이 직접 계산하면서 availability와 충돌했다.
- 부분 수정 요청에서 기존 plan에 없는 slot이나 작업을 임의로 변경했다.
- 사용자에게 보여줄 설명문과 실제 DB payload가 어긋나는 경우가 있었다.
- 작은 로컬 모델은 구조화된 DB payload 생성보다 자연어 의도 해석에 더 적합했다.

이에 따라 현재 방향은 모델을 **일정 의도 해석기**로 제한하고, 실제 일정 데이터 생성과 수정 병합은 deterministic rule로 처리하는 방식이다. 새 자체 테스트셋은 이 설계가 실제 사용자 시나리오에서도 충분히 안정적인지 확인하기 위해 필요하다.

## Problem Statement

현재 5개 멀티턴 fixture는 기능 방향성을 검증하기에는 충분했지만, 실제 서비스 도입 판단에는 범위가 좁다. 특히 대학생과 사회 초년생이 실제로 사용할 법한 다양한 일정 관리 상황을 충분히 포함하지 못한다.

현재 풀어야 할 문제는 다음과 같다.

1. **테스트 범위 부족**

   기존 fixture는 case 수가 적어 특정 prompt 또는 rule이 우연히 통과하는지, 다양한 사용자 요청에서도 안정적으로 동작하는지 판단하기 어렵다.

2. **부분 수정 안정성 검증 부족**

   실제 서비스에서 중요한 것은 새 일정을 한 번 생성하는 능력보다, 사용자가 “이 일정만 바꿔줘”, “이건 빼줘”, “다른 건 유지해줘”라고 요청했을 때 기존 상태를 안전하게 보존하는 능력이다.

3. **불가능한 요청 처리 기준 부족**

   사용자가 availability 밖 시간, deadline 이후 날짜, 이전 plan에 없는 일정 변경을 요청할 수 있다. 이때 시스템은 임의로 다른 일정을 수정하면 안 되며, no-op 또는 사용자 확인 요청으로 처리해야 한다.

4. **서비스 위험도 판단 부족**

   일정 데이터는 사용자의 실제 계획에 영향을 준다. 따라서 단순 pass rate만으로는 부족하고, 잘못된 DB 반영 가능성이 있는 failure를 별도로 드러내야 한다.

5. **사용자군 대표성 부족**

   MileDay의 초기 사용 시나리오는 대학생과 사회 초년생에게 가깝다. 수업, 시험, 과제, 동아리, 취업 준비, 퇴근 후 자기계발, 운동, 생활 관리처럼 서로 다른 시간 제약을 가진 상황을 테스트셋에 반영해야 한다.

## Testset Goal

새 30개 테스트셋의 목적은 다음 질문에 답하는 것이다.

- 모델이 사용자의 목표와 가용 시간을 자연어에서 안정적으로 해석하는가
- 후속 turn에서 이전 일정을 기억하고 필요한 부분만 바꾸는가
- 사용자가 언급하지 않은 milestone을 유지하는가
- 완료된 milestone을 보호하는가
- 불가능하거나 애매한 요청을 임의로 반영하지 않는가
- rule-based planner가 DB 반영 가능한 payload를 안정적으로 생성하는가
- 사용자 승인 전 제안 기능으로 실제 서비스에 붙일 수 있는 수준인가

## Target Users

테스트셋의 주요 사용자는 대학생과 사회 초년생이다. 두 그룹은 일정 관리 방식과 제약이 다르므로, 테스트셋에서 모두 다룬다.

| 사용자군 | 주요 상황 | 테스트 포인트 |
|---|---|---|
| 대학생 | 수업, 과제, 시험, 동아리, 자격증, 운동 | 불규칙한 요일 제약, 마감일 기반 역산, 시험/과제 병행 |
| 사회 초년생 | 출퇴근, 자기계발, 이직 준비, 운동, 재무/생활 관리 | 퇴근 후 시간 제약, 주말 집중 일정, 피로도 고려, 반복 습관 |

## Dataset Size

| 항목 | 기준 |
|---|---:|
| 전체 case 수 | 30 |
| case당 turn 수 | 2~5 |
| 전체 turn 수 | 85~95, 현재 90 |
| 평균 turn 수 | 2.8~3.2, 현재 3.0 |
| 기준 실행 모델 | 현재 `candidate-3` |
| fixture 성격 | 모델 비종속 |
| 평가 방식 | deterministic validation + Gemini LLM-as-Judge |

fixture는 특정 모델에 종속되지 않는다. 현재 CLI의 기준 실행 모델은 `candidate-3`이지만, report에는 실제 실행한 `candidate`와 model tag를 기록해야 하며, 후속 작업에서 다른 candidate 비교가 가능해야 한다.

## Case Distribution

30개 case는 아래 비율로 구성한다.

| 그룹 | 개수 | 목적 |
|---|---:|---|
| 기본 생성 | 6 | 목표, 마감일, 가용 시간을 바탕으로 첫 일정 생성 |
| 부분 수정 | 7 | 기존 일정 중 특정 요일, 특정 작업, 특정 강도만 변경 |
| 일정 추가/제외 | 5 | 기존 plan을 유지하면서 일부 일정 추가 또는 제외 |
| 불가능/충돌 요청 | 5 | 가용 시간 밖 이동, 없는 일정 변경, 마감일 초과 요청 처리 |
| 상태 보존 | 4 | 완료된 milestone과 언급하지 않은 milestone 보존 |
| 모호한 요청 | 3 | “조금 더 가볍게”, “주말 위주로” 같은 추상적 요청 처리 |

이 분포는 성공 케이스뿐 아니라 실패해야 하는 상황을 의도적으로 포함한다. 실제 서비스에서는 잘못된 일정 생성보다 **잘못된 일정 수정**이 더 위험하므로, 부분 수정과 충돌 요청 비중을 높게 둔다.

## Domain Coverage

대학생과 사회 초년생의 실제 사용 맥락을 반영하기 위해 다음 도메인을 섞는다.

| 도메인 | 예시 목표 |
|---|---|
| 학업 | 중간고사 준비, 팀 프로젝트, 졸업 논문, 과제 제출 |
| 취업/커리어 | 이력서 정리, 포트폴리오 개선, 면접 준비, 코딩 테스트 |
| 자기계발 | 영어 회화, 자격증, 독서, 블로그 작성 |
| 운동/건강 | 러닝, 헬스, 요가, 수면 루틴, 건강검진 준비 |
| 생활 관리 | 이사 준비, 여행 준비, 가계부 정리, 방 정리 |
| 반복 습관 | 이번 30개 fixture에서는 제외 |

현재 planner는 `is_recurring`과 `recurrence_type` 값을 goal DTO에 보존할 수는 있지만, 반복 series 생성, occurrence 단위 수정, 전체 반복 규칙 변경을 deterministic하게 지원하지 않는다. 따라서 이번 30개 테스트셋에서는 `is_recurring=false`, `recurrence_type=null`로 고정하고 반복 습관은 후속 ADR/fixture에서 분리한다.

## Case Schema Policy

각 case는 현재 `MileDayMultiTurnCase` schema를 따른다. DB schema는 변경하지 않는다.

고정해야 하는 주요 필드는 다음과 같다.

```json
{
  "case_id": "multiturn-001",
  "input": {
    "initial_goal": {
      "title": "목표명",
      "deadline": "YYYY-MM-DD",
      "is_recurring": false,
      "recurrence_type": null,
      "color": "#4F46E5"
    },
    "availability": [
      {
        "day_of_week": "monday",
        "start_time": "19:00",
        "end_time": "21:00"
      }
    ],
    "existing_schedule": []
  },
  "turns": [
    {
      "turn_id": 1,
      "content": "사용자 요청",
      "expected_action": "create",
      "expected_operation": null
    }
  ],
  "expected": {
    "effect": {
      "target_milestone_ids": [],
      "preserved_milestone_ids": [],
      "protected_milestone_ids": [],
      "allowed_changed_fields": ["task_text"],
      "forbidden_changed_fields": ["scheduled_date", "time_slot"],
      "expected_added_count": 0,
      "expected_removed_count": 0,
      "expected_no_op": false,
      "expected_clarification": false,
      "preserve_unmentioned": true,
      "safety_gate_tags": []
    },
    "constraints": {
      "min_milestones": 3,
      "max_milestones": 6,
      "latest_allowed_date": "YYYY-MM-DD"
    }
  }
}
```

시간 정보는 DB 별도 필드가 아니라 milestone title prefix로만 반영한다.

예:

```text
[월 19:00-21:00] 코딩 테스트 배열 문제 풀이
```

title prefix 표준 형식은 `[월 19:00-21:00] 작업명` 하나로 고정한다. 모델은 prefix를 직접 만들지 않는다. planner가 canonical formatter로 생성하고, validator는 같은 parser로 prefix를 읽는다. 다음 형식은 허용하지 않는다.

```text
[월요일 7시-9시]
[월 19시~21시]
월요일 19:00 작업명
[Mon 19:00-21:00]
```

task rename에서는 prefix를 보존한다. reschedule이 지원되는 경우에는 planner가 prefix 전체를 다시 생성해야 한다. prefix parsing 실패는 invalid로 처리한다.

## Action and Expected Effect Contract

현재 v11 모델 출력 계약은 모델을 DB payload 생성기가 아니라 **일정 의도 해석기**로 제한한다. 모델은 `[일정_의도]` 안에 `행동`, `대상`, `변경`, `작업`만 작성한다. 실제 slot 선택, 날짜 계산, 기존 plan 병합, title prefix 생성, DB DTO 생성은 harness가 처리한다.

fixture의 turn action은 현재 구현과의 호환성을 위해 다음 값을 사용한다.

| field | 값 | 의미 |
|---|---|---|
| `expected_action` | `create` | 새 일정 생성 |
| `expected_action` | `partial_update` | 기존 plan 기반 수정, 추가, 제외, no-op, clarification을 포함하는 후속 turn |
| `expected_action` | `clarify` | schema상 허용하지만 현재 30개 fixture에서는 직접 사용하지 않음 |
| `expected_operation` | `add` | 일정 하나 추가 |
| `expected_operation` | `remove` | 일정 하나 제외 |
| `expected_operation` | `rename` | 작업명만 변경 |
| `expected_operation` | `reschedule` | 날짜·시간 변경 요청. 현재 planner 지원 범위가 제한적이므로 Safety Gate 검증 대상 |
| `expected_operation` | `soften` | 강도 완화. slot 보존은 deterministic, 표현 완화 여부는 judge 보완 |
| `expected_operation` | `none` | no-op 또는 clarification 기대 |

no-op과 clarification은 action enum을 늘려 모델 출력 계약을 복잡하게 만들지 않고, fixture 평가용 `expected.effect.expected_no_op`, `expected.effect.expected_clarification`으로 구분한다.

`expected.effect`는 DB DTO가 아니라 fixture 평가 전용 metadata다. 실제 DB payload에는 포함하지 않는다.

## Milestone Identification Policy

milestone 식별 우선순위는 다음과 같다.

1. 기존 DB 또는 fixture milestone ID
2. fixture 전용 stable ID인 `fixture_milestone_id`
3. canonical availability slot의 `scheduled_date + day_of_week + start_time + end_time`
4. semantic title matching

배열 index나 title 전체 문자열만으로 milestone을 식별하지 않는다.

사용자가 “월요일 코딩 테스트 일정”처럼 ID를 직접 말하지 않으면 planner는 canonical slot과 task keyword로 후보를 좁힌다. 동일 날짜에 milestone이 여러 개 있거나 같은 task명이 반복되어 target 후보가 2개 이상이면 임의 선택하지 않고 clarification을 기대한다. target이 존재하지 않으면 no-op이 기본이다.

## Turn Design Rules

각 case는 다음 흐름 중 하나 이상을 포함한다.

1. 첫 turn은 새 일정 생성 요청이다.
2. 후속 turn은 이전 일정 일부만 수정한다.
3. 사용자가 언급하지 않은 milestone은 유지되어야 한다.
4. 완료된 milestone은 수정하지 않아야 한다.
5. 불가능한 요청은 임의로 반영하지 않고, 기존 plan을 유지하거나 사용자 확인이 필요하다고 안내해야 한다.
6. 사용자가 “가용 시간 중 일부만 사용”하겠다고 하면, 전체 availability 중 필요한 개수만 선택해야 한다.

## Required Negative Cases

다음 유형은 반드시 포함한다.

| 유형 | 기대 동작 |
|---|---|
| 이전 plan에 없는 일정 변경 요청 | 기존 plan 유지 또는 사용자 확인 요청 |
| 완료된 milestone 변경 요청 | 완료 milestone 미수정 |
| availability 밖 시간으로 이동 요청 | 변경하지 않거나 가능한 후보만 제안 |
| deadline 이후 일정 생성 요청 | deadline 이하 일정만 생성 |
| “주 4일 가능하지만 2일만 해줘” | 가능한 slot 중 2개만 선택 |
| 특정 일정 제외 요청 | 해당 일정만 제외하고 나머지 유지 |
| 일정 하나 추가 요청 | 기존 일정 유지 + 가능한 slot에 1개 추가 |
| 작업명만 변경 요청 | 날짜/시간 유지, task만 변경 |
| 강도 낮추기 요청 | 날짜/시간 유지, task 표현만 완화 |
| 모호한 요청 | 과도한 임의 변경 없이 보수적으로 수정 |

## Evaluation Focus

테스트셋은 다음 항목을 측정한다.

| 평가 항목 | 설명 |
|---|---|
| 실행 안정성 | 전체 turn 중 passed/invalid/failed/skipped 비율 |
| 형식 안정성 | 모델 출력이 현재 v11 의도 계약을 만족하는지 |
| 상태 유지 | 이전 plan의 slot과 task가 불필요하게 사라지지 않는지 |
| 부분 수정 범위 | 사용자가 지정한 일정만 변경되는지 |
| 완료 일정 보호 | 완료된 기존 milestone을 변경하지 않는지 |
| 가용 시간 준수 | milestone title의 요일/시간이 availability 안에 있는지 |
| deadline 준수 | 모든 scheduled_date가 latest_allowed_date 이하인지 |
| judge alignment | Gemini judge가 사용자 요청과 결과의 의미 정렬을 통과시키는지 |
| DB 반영 가능성 | rule-based payload가 goal/milestone DTO field만 포함하는지 |
| 날짜·요일·시간 정합성 | scheduled_date, title prefix, canonical availability slot의 요일/시간이 일치하는지 |

## Metric Definitions

| 지표 | 계산식 | 설명 |
|---|---|---|
| Turn pass rate | `passed_turns / total_turns` | 전체 평가 대상 turn 중 최종 status가 `passed`인 비율 |
| Case completion rate | `last_turn_executed_cases / total_cases` | 마지막 turn까지 중단 없이 실행된 case 비율. judge 실패 여부와 분리한다. |
| All-turn-pass case rate | `all_turn_pass_cases / total_cases` | case의 모든 turn이 deterministic validation과 judge를 모두 통과한 비율 |
| DB-ready case rate | `db_ready_cases / total_cases` | 마지막 turn의 최종 payload가 DTO schema, availability, deadline, 날짜·요일·시간 prefix, Safety Gate를 모두 통과한 case 비율 |
| Critical failure rate | `(failed_turns + invalid_turns) / total_turns` | 제품 위험 또는 실행 실패가 있는 turn 비율 |

기존 report의 `case_completion_rate`가 all-turn-pass 의미로 사용된 경우에는 향후 report에서 `case_completion_rate`와 `all_turn_pass_case_rate`를 분리해야 한다.

## Safety Gate

Safety Gate는 평균 pass rate나 judge score와 무관하게 반드시 별도 통과해야 하는 조건이다. 다음 위반은 전체 테스트셋에서 각각 0건이어야 한다.

| Safety Gate 항목 | 기대 |
|---|---|
| 완료된 milestone 변경 | 0건 |
| 존재하지 않는 milestone을 다른 milestone에 임의 매핑 | 0건 |
| availability 밖 날짜 또는 시간 생성 | 0건 |
| deadline 이후 일정 생성 | 0건 |
| 사용자가 요청하지 않은 milestone 삭제 | 0건 |
| 사용자가 요청하지 않은 milestone 날짜·시간 변경 | 0건 |
| 사용자 승인 이전 실제 DB write | 0건 |
| no-op 또는 clarification 필요 상황에서 임의 변경 | 0건 |

Safety Gate 위반이 한 건이라도 발생하면 평균 pass rate나 judge 점수와 관계없이 자동 DB 반영 후보로 판단하지 않는다.

현재 멀티턴 harness는 실제 DB write를 수행하지 않고 payload 생성까지만 검증한다. 사용자 승인 전 persistence 차단은 별도의 application integration test에서 검증해야 한다.

## Result Status Criteria

멀티턴 평가의 turn별 결과는 `passed`, `invalid`, `failed`, `skipped` 중 하나로 기록한다. 이 문서에서 설계하는 30개 테스트셋은 단순히 정답/오답을 가르는 것이 아니라, 어떤 failure가 제품 위험으로 이어지는지 분리해서 드러내야 한다.

| status | 의미 | 대표 원인 | 제품 관점 |
|---|---|---|---|
| `passed` | 실행, deterministic validation, Gemini judge를 모두 통과 | 출력 계약 충족, DB payload 생성 가능, judge aligned | 사용자 승인 전 제안으로 검토 가능 |
| `invalid` | 모델 응답은 생성됐지만 평가 기준을 만족하지 못함 | parser 불가, 제약 위반, judge reject | 제품에 그대로 연결하면 잘못된 일정 제안/수정 위험 |
| `failed` | 평가 실행 자체가 정상 완료되지 못함 | Ollama 오류, timeout, Gemini judge 실패, API key 없음 | 모델 품질 문제가 아니라 실행 환경/외부 의존성 문제 |
| `skipped` | 이전 turn 실패로 같은 case의 후속 turn을 실행하지 않음 | 앞 turn이 `invalid` 또는 `failed` | 멀티턴 연속성 상실 |

### Invalid Criteria

`invalid`는 **모델 또는 rule-based planner가 결과를 만들었지만, 결과를 신뢰할 수 없는 경우**에 사용한다. 실행 자체는 끝났으므로 latency, raw output, parsed result는 artifact에 남는다.

현재 멀티턴 평가에서 `invalid`로 판단될 수 있는 기준은 다음과 같다.

| 기준 | 설명 | 예시 |
|---|---|---|
| 출력 계약 누락 | 활성 프롬프트가 요구하는 `[일정_의도] ... [/일정_의도]` 블록을 찾을 수 없고 freeform fallback도 실패함 | 모델이 일반 설명문만 출력 |
| intent parse 실패 | `행동`, `대상`, `변경`, `작업`을 해석할 수 없거나 명시된 행동이 허용값이 아님 | `행동: 삭제`, `action: remove` |
| expected action 불일치 | fixture의 `expected_action`과 parsed action이 맞지 않음 | `partial_update` turn에서 새 계획 생성으로 해석 |
| 이전 plan 없음 | `partial_update`인데 이전 turn의 parsed `plan_items`가 없음 | turn 1 실패 후 turn 2를 강제로 평가 |
| plan/patch schema 오류 | `plan_items` 또는 `patch_items`가 list of object 형태가 아님 | 문자열 하나로만 plan 생성 |
| unknown slot | rule-based 변환 후 존재하지 않는 slot을 참조 | `S999` 같은 허용되지 않은 slot |
| patch 대상 오류 | `partial_update`에서 이전 plan에 없던 slot을 수정 대상으로 사용 | 이전 plan에 없는 날짜/작업을 임의 변경 |
| 중복 slot | 같은 slot에 여러 작업을 배정 | `S002`가 두 번 등장 |
| 빈 task | 작업명이 비어 있음 | `task: ""` |
| task prefix 오염 | task에 요일/시간 prefix가 직접 들어감 | `[월 19:00-21:00] 러닝` |
| 시간 표현 오염 | task에 `19:00`, `오전`, `오후` 같은 시간 표현이 들어감 | `오후 러닝 연습` |
| 요일 불일치 | task 안에 적힌 요일과 실제 slot 요일이 다름 | 수요일 slot에 `토요일 발표 준비` |
| 영어 문장 오염 | 한국어 task가 아니라 영어 문장형 작업명이 들어감 | `Prepare final presentation` |
| milestone 수 범위 위반 | 최종 milestone 개수가 case의 min/max 기준을 벗어남 | create인데 1개만 생성, max 6인데 8개 생성 |
| availability 위반 | milestone title의 요일/시간 prefix가 사용자 가용 시간 밖임 | 월/수만 가능한데 금요일 일정 생성 |
| 날짜-요일 불일치 | `scheduled_date`의 실제 요일과 title prefix 요일이 다름 | `2026-08-05`인데 `[월 ...]` prefix |
| deadline 위반 | `scheduled_date`가 `latest_allowed_date` 이후임 | 마감일 이후 일정 생성 |
| judge reject | deterministic validation은 통과했지만 Gemini가 의미 정렬 실패로 판단 | 없는 일정을 변경하거나, 요청하지 않은 milestone을 바꿈 |

현재 failure taxonomy는 다음 code를 사용한다.

```text
INTENT_PARSE_ERROR
INTENT_CONTRACT_ERROR
INVALID_ACTION
TARGET_NOT_FOUND
AMBIGUOUS_TARGET
UNREQUESTED_MODIFICATION
UNREQUESTED_DELETION
STATE_LOSS
COMPLETED_ITEM_MODIFIED
AVAILABILITY_VIOLATION
DEADLINE_VIOLATION
DATE_WEEKDAY_MISMATCH
TIME_PREFIX_MISMATCH
PREFIX_PARSE_ERROR
PAYLOAD_SCHEMA_ERROR
PAYLOAD_EXTRA_FIELD
EXPLANATION_PAYLOAD_MISMATCH
APPROVAL_GUARD_VIOLATION
JUDGE_OUTPUT_ERROR
JUDGE_REJECTION
```

각 failure는 가능하면 `failure_code`, `severity`, `case_id`, `turn_id`, `message`, `target milestone`, `before`, `after`, `validator_source`, `safety_gate` 여부를 포함한다.

`invalid`는 테스트 실패이지만 실행 실패는 아니다. 따라서 `invalid`가 많이 발생하면 모델 서버보다 prompt, parser, planner, fixture 기대값 중 무엇이 문제인지 분석해야 한다.

### Failed Criteria

`failed`는 **모델 품질 평가 전에 실행 환경이나 외부 의존성이 깨진 경우**에 사용한다. 이 상태는 모델의 일정 이해 능력을 직접 의미하지 않는다.

현재 멀티턴 평가에서 `failed`로 판단될 수 있는 기준은 다음과 같다.

| 기준 | 설명 | 대표 category |
|---|---|---|
| Ollama 미가동 | 로컬 Ollama 서버에 연결할 수 없음 | `OLLAMA_UNAVAILABLE` |
| 모델 미설치/실행 불가 | registry에는 있지만 로컬 runtime에서 생성 실패 | `MODEL_NOT_INSTALLED`, `EXTERNAL_DEPENDENCY` |
| timeout | 지정 시간 안에 모델 응답을 받지 못함 | `TIMEOUT` |
| runtime error | Ollama generate 중 예외 발생 | `EXTERNAL_DEPENDENCY`, `CODE_ERROR` |
| Gemini API key 없음 | 멀티턴 judge가 필수인데 `GEMINI_API_KEY`가 없음 | `EXTERNAL_DEPENDENCY` |
| Gemini judge 호출 실패 | Gemini API가 4xx/5xx, 네트워크 오류, quota 오류 등으로 실패 | `EXTERNAL_DEPENDENCY` |
| judge adapter 미지원 | 설정된 judge 객체가 `evaluate_multiturn`을 제공하지 않음 | `CODE_ERROR` |
| 내부 코드 예외 | parser, validator, store 처리 중 예상하지 못한 코드 오류 | `CODE_ERROR` |

`failed`는 fixture 품질이나 모델 응답 품질을 판단하기 어렵다. 따라서 30개 테스트셋을 평가할 때 `failed`가 발생하면 먼저 실행 환경을 복구한 뒤 같은 run을 다시 수행해야 한다.

### Skipped Criteria

`skipped`는 같은 case 안에서 이전 turn이 `passed`가 아니어서 후속 turn을 실행하지 않은 상태다.

예를 들어 3-turn case에서 turn 1이 `invalid`이면 turn 2와 turn 3은 이전 정상 상태가 없으므로 `skipped` 처리한다. 이는 멀티턴 평가에서 정상적인 방어 동작이다.

`skipped`가 많다는 것은 다음 중 하나를 의미한다.

- 첫 turn 생성 안정성이 낮다.
- fixture의 첫 요청이 과도하게 어렵다.
- parser/validator 기준이 너무 엄격하다.
- judge가 초기 계획을 자주 reject한다.

30개 case에서는 `skipped` 자체보다 **어떤 첫 실패가 연쇄 skip을 만들었는지**를 함께 기록해야 한다.

### Warning Criteria

일부 문제는 즉시 `invalid`로 보지 않고 warning으로 기록한다. warning은 통과 가능하지만, 서비스 도입 전 검토가 필요한 신호다.

대표적으로 create turn에서 기존 completed milestone이 새 PLAN 출력에 포함되지 않는 경우가 있다. create는 새 계획 생성이므로 기존 완료 일정을 반드시 다시 출력하지 않아도 되지만, 제품 UX에서는 사용자가 기존 완료 일정을 어떻게 볼지 별도 정책이 필요하다.

warning은 다음 판단에 사용한다.

- pass는 했지만 제품 UX에서 설명이 필요한가
- validator가 과도하게 엄격하지는 않은가
- 추후 DB merge 정책에서 보완할 필요가 있는가

## Judge Policy

Gemini judge는 필수로 사용한다. judge는 모델 응답의 문장 품질만 보는 것이 아니라, 다음 항목을 평가한다.

- 이전 일정 상태가 현재 turn에 반영됐는가
- 사용자가 요청한 부분만 바뀌었는가
- 불가능하거나 애매한 요청을 임의로 처리하지 않았는가
- 설명문과 rule-based DB payload가 서로 충돌하지 않는가
- 실제 서비스에서 사용자 승인 전 제안으로 보여줘도 되는가

judge 실패는 해당 turn의 통과로 보지 않는다.

현재 judge 입력은 case, turn id, 현재 사용자 요청, expected action, goal, availability, existing schedule, previous plan, rule-based user message, current parsed payload를 포함한다. Gemini 호출은 `temperature=0`, JSON response schema, 최대 3회 지수 백오프 재시도 정책을 사용한다. judge 호출 실패는 모델 품질 invalid가 아니라 `failed`로 기록한다.

권장 judge 평가 가중치는 다음과 같다. 현재 구현은 단일 `score`와 `is_aligned`를 반환하므로, 이 가중치는 prompt와 향후 schema 확장의 기준으로 사용한다.

| 항목 | 가중치 |
|---|---:|
| request fulfillment | 0.30 |
| state preservation | 0.25 |
| modification scope | 0.20 |
| conflict handling | 0.15 |
| explanation/payload alignment | 0.10 |

turn judge pass 기준은 score 0.85 이상, 상태 보존과 충돌 처리에 치명 문제가 없음, Safety Gate 위반 없음이다. 현재 parser는 Gemini 결과의 `score >= 0.8`을 통과 기준으로 사용하므로, 30개 fixture 평가 전 threshold 조정 여부를 별도 작업으로 검토한다.

## Success Criteria

30개 case 기준 1차 목표는 다음과 같다.

| 기준 | 목표값 |
|---|---:|
| turn pass rate | 90% 이상 |
| case completion rate | 85% 이상 |
| all-turn-pass case rate | 80% 이상 |
| failed turn | 0 |
| invalid turn | 전체 turn의 2% 이하 |
| skipped turn | 5% 이하 |
| judge average score | 0.90 이상 |
| DB-ready case rate | 85% 이상 |
| critical failure rate | 2% 이하 |

실제 서비스 자동 반영 후보로 보려면 아래 조건을 추가로 만족해야 한다.

- 없는 일정 변경 요청에서 임의 수정이 발생하지 않을 것
- 완료된 milestone이 변경되지 않을 것
- availability 밖 일정이 생성되지 않을 것
- 사용자가 승인하기 전 DB에 반영하지 않을 것

## Implementation Plan

1. 이 설계 문서를 기준으로 30개 case 목록을 작성한다.
2. `tests/fixtures/mileday/multiturn_schedule.jsonl`을 30개 case로 확장한다.
3. 같은 내용을 보기 좋은 `multiturn_schedule.pretty.json`으로 동기화한다.
4. loader/schema test에서 전체 30개 case와 turn 수 범위를 검증한다.
5. `metadata.primary_group`, `metadata.user_segment`, `metadata.domain`, `metadata.tags`를 기준으로 distribution과 required negative tag 최소 개수를 검증한다.
6. `python -m harness.cli run-mileday-multiturn`으로 전체 실행한다.
7. `report.md`와 `report.html`에서 실패 유형을 분석한다.
8. 실패가 반복되는 유형은 prompt보다 rule-based planner와 validator 기준을 우선 보강한다.

## Out of Scope

이번 30개 fixture와 ADR 범위에서 제외하는 항목은 다음과 같다.

- 최적의 학습 계획 또는 생산성 계획 품질 자체
- 사용자의 장기 생산성 향상 측정
- 의료적 피로도 또는 건강 상태 추론
- 외부 캘린더 동기화
- 복잡한 캘린더 충돌 자동 해결
- timezone 이동
- 자연어 문체의 미적 품질
- 실제 운영 DB write
- 반복 일정 series/occurrence 생성 및 수정
- 완전 자유 형식 일정 최적화
- 사용자 승인 이후 최종 persistence workflow

## Decision

MileDay 멀티턴 자체 테스트셋은 대학생과 사회 초년생의 실제 일정 관리 상황을 중심으로 30개 case를 구성한다. 각 case는 2~5개 turn, 평균 3개 turn을 목표로 한다. 테스트셋은 모델의 창의적인 일정 제안 능력보다, 실제 서비스에서 중요한 상태 보존, 부분 수정 안전성, 가용 시간 준수, 사용자 승인 전 DB payload 생성 가능성을 검증하는 방향으로 설계한다.
