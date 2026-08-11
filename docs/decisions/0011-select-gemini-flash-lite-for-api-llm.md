# ADR 0011: API LLM 최종 선택

## 상태

Accepted

## 배경

MileDay 일정 생성 기능은 사용자의 목표, 마감일, 가능 시간, 기존 일정 맥락을 받아 DB 반영 전 확인 가능한 일정 계획을 생성해야 한다. 이 기능은 복잡한 장문 추론보다 다음 조건을 안정적으로 지키는 것이 더 중요하다.

- 사용자가 제공한 가능 요일과 시간 안에서만 일정을 생성한다.
- 마감일을 넘기지 않는다.
- 기존 일정이 있는 경우, 사용자가 요청한 대상만 수정한다.
- DB 반영 전에는 항상 사용자 확인이 필요하다는 상태를 유지한다.
- 설명과 실제 `db_payload`가 서로 모순되지 않아야 한다.

초기에는 로컬 SLM을 우선 검토했지만, 멀티턴 일정 수정에서는 안정성이 충분하지 않았다. 이후 API LLM 비교 대상으로 `gemini-3.5-flash-lite`와 `gemini-3.6-flash`를 선정해 평가했다.

가격 정보는 2026-08-11 기준 Google 공식 Gemini API pricing 문서를 기준으로 한다.

## 결정

MileDay API LLM의 기본 모델로 `gemini-3.5-flash-lite`를 사용한다.

`gemini-3.6-flash`가 일부 품질 지표에서는 더 높지만, 현재 MileDay 요구사항에서는 두 모델 사이의 안정성 차이가 제품 판단을 뒤집을 만큼 크지 않다. 반면 `gemini-3.5-flash-lite`는 토큰당 비용과 응답 지연이 훨씬 낮다. 대학생 개인 프로젝트로 운영 비용을 최소화해야 하는 현재 조건에서는 `gemini-3.5-flash-lite`가 더 합리적인 선택이다.

## 1차 테스트: 초기 로컬 후보 비교

초기 MileDay 20개 케이스에서는 `candidate-3`과 `candidate-5`를 비교했다.

| model | cases | passed | invalid | failed | judge completed | aligned rate | avg judge score |
|---|---:|---:|---:|---:|---:|---:|---:|
| candidate-3 | 20 | 6 | 14 | 0 | 11 | 30.0% | 0.727 |
| candidate-5 | 20 | 5 | 15 | 0 | 13 | 20.0% | 0.608 |

1차 결과에서는 `candidate-3`이 상대적으로 나았지만, 두 모델 모두 invalid가 매우 많았다. 즉 로컬 SLM만으로 바로 제품 적용하기에는 출력 형식과 일정 제약 준수 안정성이 부족했다.

## 2차 테스트: 공개 벤치마크 기반 후보 압축

공개 벤치마크 50개 샘플 평가에서는 `candidate-1`, `candidate-3`, `candidate-5`를 비교했다. 모델별 총 요청 수는 200개였다.

| model | passed | invalid | failed | weighted score | avg score | avg latency |
|---|---:|---:|---:|---:|---:|---:|
| candidate-1 | 51 | 149 | 0 | 0.120 | 0.075 | 10.09s |
| candidate-3 | 200 | 0 | 0 | 0.383 | 0.355 | 4.48s |
| candidate-5 | 200 | 0 | 0 | 0.305 | 0.320 | 5.53s |

2차 결과에서는 `candidate-3`이 가장 균형이 좋았다. `candidate-5`는 일부 객관식 지표에서 강점이 있었지만, weighted score와 latency 모두 `candidate-3`보다 낮았다. `candidate-1`은 parser error 성격의 invalid가 149건으로 많아 후보에서 제외했다.

## 3차 테스트: 로컬 SLM 최종 검증

3차 테스트는 `candidate-3`과 `candidate-5`만 남겨 IFEval-Ko와 KoBALT-700 전체 데이터셋에서 비교했다. 모델별 총 케이스 수는 1,042개였다.

| model | passed | invalid | failed | invalid rate | weighted score | IFEval-Ko | KoBALT-700 | avg latency |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| candidate-3 | 1,042 | 0 | 0 | 0.0% | 0.389 | 0.564 | 0.126 | 4032ms |
| candidate-5 | 1,042 | 0 | 0 | 0.0% | 0.354 | 0.482 | 0.161 | 4935ms |

이 단계에서는 `candidate-3`이 로컬 SLM 최종 후보가 되었다. 하지만 MileDay 멀티턴 전용 grid 테스트에서는 결과가 좋지 않았다.

| run | best setting | passed | invalid | failed | skipped | turn2 passed | turn3 passed |
|---|---|---:|---:|---:|---:|---:|---:|
| candidate-3 grid 1 | temp 0.2 / top_p 1.0 | 0 | 0 | 3 | 6 | 0 | 0 |
| candidate-3 grid 2 | temp 0.1 / top_p 0.8 | 3 | 3 | 0 | 3 | 0 | 0 |
| candidate-3 grid 3 | temp 0.1 / top_p 0.8 | 2 | 3 | 0 | 4 | 0 | 0 |

로컬 SLM은 일반 벤치마크에서는 후보로 볼 수 있었지만, 실제 MileDay 멀티턴 일정 수정에서는 turn2 이후 안정성이 부족했다. 따라서 API LLM과 비교하는 단계로 전환했다.

## 4차 테스트: Gemini API 모델 비교

API 비교 대상은 `gemini-3.5-flash-lite`와 `gemini-3.6-flash`였다. 초기에는 `v11` 프롬프트로 시작했고, 부분 수정 실패를 줄이기 위해 API 전용 `v12-api` 프롬프트와 강화된 judge 기준을 도입했다.

### 주요 실행 결과

| run | cases | prompt | model | passed | invalid | failed | skipped | all-turn-pass | avg latency |
|---|---:|---|---|---:|---:|---:|---:|---:|---:|
| 5 | 3 | v11 | gemini-3.5-flash-lite | 3 | 3 | 0 | 3 | 0.0% | 1497ms |
| 5 | 3 | v11 | gemini-3.6-flash | 5 | 2 | 0 | 2 | 33.3% | 5128ms |
| 8 | 10 | v12-api | gemini-3.5-flash-lite | 24 | 3 | 0 | 3 | 70.0% | 1425ms |
| 8 | 10 | v12-api | gemini-3.6-flash | 26 | 4 | 0 | 0 | 60.0% | 6330ms |
| 9 | 5 | v12-api | gemini-3.5-flash-lite | 13 | 1 | 0 | 1 | 80.0% | 1403ms |
| 9 | 5 | v12-api | gemini-3.6-flash | 13 | 1 | 0 | 1 | 80.0% | 4747ms |
| 11 | 1 | v12-api | gemini-3.5-flash-lite | 3 | 0 | 0 | 0 | 100.0% | 1501ms |
| 11 | 1 | v12-api | gemini-3.6-flash | 3 | 0 | 0 | 0 | 100.0% | 4427ms |
| 12 | 30 | v12-api | gemini-3.5-flash-lite | 33 | 26 | 0 | 31 | 13.3% | 1409ms |
| 12 | 30 | v12-api | gemini-3.6-flash | 47 | 23 | 0 | 20 | 23.3% | 6988ms |

12번 실행은 30개 케이스 전체를 강화된 judge 기준으로 평가한 가장 엄격한 비교다.

| model | non-skipped records | scored records | avg judge score | passed avg | invalid avg |
|---|---:|---:|---:|---:|---:|
| gemini-3.5-flash-lite | 59 | 59 | 0.742 | 1.000 | 0.415 |
| gemini-3.6-flash | 70 | 69 | 0.780 | 1.000 | 0.309 |
| overall | 129 | 128 | 0.763 | - | - |

`gemini-3.6-flash`가 pass 수와 평균 judge score에서 더 높다. 하지만 judge 평균 차이는 `0.038`이고, 두 모델 모두 주요 실패 원인이 모델 지식 부족보다는 partial update scope와 parser 매핑 문제에 집중되어 있었다. 특히 `PAYLOAD_EXPLANATION_MISMATCH`, `WRONG_TARGET_SCOPE`, `OVER_PATCHED_SINGLE_TARGET` 계열은 프롬프트와 후처리 로직으로 추가 개선 가능한 영역이다.

## 비용 비교

Google 공식 Gemini API pricing 기준, Standard paid tier의 토큰당 비용은 다음과 같다.

| model | input price / 1M tokens | output price / 1M tokens | input cost ratio | output cost ratio |
|---|---:|---:|---:|---:|
| gemini-3.5-flash-lite | $0.30 | $2.50 | 1.0x | 1.0x |
| gemini-3.6-flash | $1.50 | $7.50 | 5.0x | 3.0x |

단순히 입력 1M + 출력 1M 토큰을 같은 양으로 사용한다고 보면:

| model | input 1M + output 1M cost | relative cost |
|---|---:|---:|
| gemini-3.5-flash-lite | $2.80 | 1.0x |
| gemini-3.6-flash | $9.00 | 3.21x |

즉 `gemini-3.5-flash-lite`는 입력 토큰 기준 80.0% 저렴하고, 출력 토큰 기준 66.7% 저렴하며, 단순 합산 기준으로도 약 68.9% 저렴하다.

## 속도 비교

12번 전체 실행 기준 평균 지연은 다음과 같다.

| model | avg latency | relative latency |
|---|---:|---:|
| gemini-3.5-flash-lite | 1409ms | 1.0x |
| gemini-3.6-flash | 6988ms | 4.96x |

`gemini-3.5-flash-lite`는 `gemini-3.6-flash`보다 약 5배 빠르게 응답했다. 일정 생성 기능은 사용자가 대화형으로 결과를 확인하는 흐름이므로, 이 지연 차이는 실제 사용감에 직접 영향을 준다.

## 최종 판단

`gemini-3.6-flash`는 더 높은 품질 지표를 보였다.

- 12번 실행 기준 passed: `47` vs `33`
- all-turn-pass: `23.3%` vs `13.3%`
- skipped 제외 평균 judge score: `0.780` vs `0.742`

하지만 현재 MileDay의 요구사항은 복잡한 장문 추론이 아니라 제한된 일정 제약을 안정적으로 JSON 의도와 payload에 반영하는 것이다. 12번 실행에서 드러난 주요 실패는 모델의 일반 지능 차이보다는 부분 수정 범위 판별과 후처리 매핑 로직에서 발생했다. 따라서 `gemini-3.6-flash`를 쓰더라도 parser와 validator 개선 없이는 핵심 실패가 완전히 사라지지 않는다.

반면 `gemini-3.5-flash-lite`는 다음 장점이 분명하다.

- 입력 토큰 비용이 `gemini-3.6-flash`의 1/5이다.
- 출력 토큰 비용이 `gemini-3.6-flash`의 1/3이다.
- 입력 1M + 출력 1M 기준 총 비용이 약 68.9% 낮다.
- 12번 실행 기준 평균 지연이 1409ms로, `gemini-3.6-flash`의 6988ms보다 약 5배 빠르다.
- 8번과 9번 실행에서는 all-turn-pass가 `gemini-3.6-flash`와 같거나 더 높았다.
- 실패 유형이 구조적으로 비슷하므로, 비용이 큰 모델로 바꾸는 것보다 프롬프트/파서/validator 개선의 효율이 더 크다.

따라서 현재 개인 개발 및 대학생 운영 비용 제약을 고려하면 `gemini-3.5-flash-lite`를 기본 API LLM으로 선택하는 것이 합리적이다.

## 운영 방침

기본 모델은 `gemini-3.5-flash-lite`로 둔다.

추후 다음 조건이 명확해질 때만 `gemini-3.6-flash` 전환 또는 fallback 전략을 재검토한다.

- partial update parser와 validator 개선 이후에도 `gemini-3.5-flash-lite`가 제품 기준 통과율을 만족하지 못하는 경우
- 실제 사용자 로그에서 일정 수정 실패가 반복적으로 확인되는 경우
- 운영 비용보다 품질 개선이 더 중요한 유료 사용자 시나리오가 생기는 경우

## 참조

- Google Gemini API pricing: https://ai.google.dev/gemini-api/docs/pricing
- API 프롬프트 개선 기록: `docs/decisions/0010-api-multiturn-prompt-improvement.md`
- 12번 API 실행 요약: `artifacts/runs/gemini-mileday-multiturn-12-summary.md`
- 3차 로컬 벤치마크 요약: `artifacts/runs/third-benchmark-batch-2-summary.md`

## 제품 적용 기준

MileDay 일정 생성은 DB 반영 전 사용자 확인을 요구하지만, 잘못된 일정 후보를 반복적으로 보여주면 제품 신뢰도가 떨어진다. 따라서 평균 점수 하나만으로 판단하지 않고, deterministic validation, judge score, critical failure, turn별 통과율을 함께 본다.

제품 적용 최소 기준은 다음과 같이 둔다.

| 기준 | 최소선 | 목표선 |
|---|---:|---:|
| runtime failed | 0건 | 0건 |
| deterministic validation pass | 100% | 100% |
| critical failure | 0건 | 0건 |
| Turn1 create pass rate | 95% 이상 | 98% 이상 |
| Turn2/3 partial update pass rate | 85% 이상 | 90% 이상 |
| all-turn-pass case rate | 70% 이상 | 80% 이상 |
| skipped 제외 average judge score | 0.85 이상 | 0.90 이상 |
| average latency | 2.5초 이하 | 2.0초 이하 |

단계별 판단 기준은 다음과 같이 운용한다.

| 단계 | 기준 |
|---|---|
| 개발 실험 통과 | all-turn-pass 50% 이상, skipped 제외 average judge score 0.80 이상 |
| 내부 사용 가능 | all-turn-pass 70% 이상, average judge score 0.85 이상, critical failure 0건 |
| 제품 기본 적용 | all-turn-pass 80% 이상, average judge score 0.90 이상, deterministic validation 100% |
| 자동 DB 반영 후보 | all-turn-pass 90% 이상, critical failure 0건을 여러 batch에서 반복 달성 |

12번 실행 기준으로는 `gemini-3.5-flash-lite`와 `gemini-3.6-flash` 모두 아직 제품 적용 최소 기준에는 도달하지 못했다.

| model | all-turn-pass | skipped 제외 avg judge score | avg latency | 현재 판단 |
|---|---:|---:|---:|---|
| gemini-3.5-flash-lite | 13.3% | 0.742 | 1.409초 | 속도는 기준 충족, 품질은 개선 필요 |
| gemini-3.6-flash | 23.3% | 0.780 | 6.988초 | 품질은 더 높지만 기준 미달, 속도 기준 미달 |

따라서 모델 선택은 `gemini-3.5-flash-lite`로 확정하되, 제품 적용 전에는 프롬프트, parser, validator 개선을 통해 위 최소 기준을 만족하는지 다시 검증한다.

## 현재 브랜치 적용 범위

현재 브랜치는 모델 재비교가 아니라 `gemini-3.5-flash-lite`의 제품 기준 통과율을 끌어올리기 위한 prompt/parser 개선 브랜치다.

- 비교 대상 모델 실행 경로는 제거하고 flash-lite 단일 실행으로 고정한다.
- `test_api`는 전체 fixture 또는 `--limit`으로 제한된 fixture만 실행한다.
- summary는 단일 flash-lite 결과만 기록한다.
- parser 결과는 `plan_items`, `patch_items`, `add_items`, `remove_slot_ids`, `db_payload`, `requires_confirmation` shape를 유지한다.
- DB 적재는 아직 실행하지 않고, parser output에서 DB payload와 SQL preview까지 이어지는 구조만 검증한다.
- 현재 상세 실행 가이드는 `docs/harness_guide.md`를 기준으로 본다.
