# ADR 0006: 2차 모델 평가 후보 선정

- 날짜: 2026-07-29
- 상태: Accepted
- 관련 문서:
  - `configs/models.yaml`
  - `docs/harness_guide.md`
  - `_bmad-output/planning-artifacts/product-brief.md`
  - `_bmad-output/planning-artifacts/prd.md`

## 배경

MileDay는 한국어 일정 계획, 마일스톤 생성, 자연어 일정 수정 기능에 사용할 로컬 LLM 후보를 비교하고 있다. 평가 리포트는 단순한 모델 실행 기록보다, 후보를 좁히는 기준과 평가 설계가 재현 가능하게 설명되어야 한다.

초기 후보는 다음 5개 모델이다.

| candidate | model_tag | 주요 역할 가정 |
|---|---|---|
| candidate-1 | `ingu627/exaone4.0:1.2b` | 한국계 소형 모델 기준선 |
| candidate-2 | `hf.co/pathcosmos/frankenstallm:Q4_K_M` | 한국어 특화 3B 후보 |
| candidate-3 | `granite4.1:3b` | 안정적인 다국어/구조화 출력 후보 |
| candidate-4 | `qwen3.5:4b` | 최신 멀티링구얼 고성능 후보 |
| candidate-5 | `ministral-3:3b` | 경량 다국어/구조화 출력 후보 |

## 현재까지 확인한 실행 지표

아래 수치는 기존 MileDay smoke 실행 artifact의 `parsed/results*.json*`에 기록된 `metrics.latency_ms`, `status`, `error.category`를 집계한 값이다. 공개 benchmark 전체 성능이 아니라, 모델 후보를 2차 평가로 넘길지 판단하기 위한 초기 로컬 실행 안정성 근거다.

| candidate | 기록 case 수 | passed | invalid | failed | 주요 오류 | 평균 latency | 평균 TTFT | 평균 tok/s |
|---|---:|---:|---:|---:|---|---:|---:|---:|
| candidate-1 | 10 | 0 | 10 | 0 | `PARSER_ERROR=10` | 8.40초 | 4.24초 | 199.18 |
| candidate-2 | 10 | 0 | 0 | 10 | `MODEL_NOT_INSTALLED=5`, `EXTERNAL_DEPENDENCY=5` | 3.82초 | 없음 | 없음 |
| candidate-3 | 45 | 16 | 29 | 0 | `PARSER_ERROR=29` | 9.34초 | 3.85초 | 84.97 |
| candidate-4 | 15 | 4 | 11 | 0 | `PARSER_ERROR=11` | 58.80초 | 54.28초 | 64.77 |
| candidate-5 | 40 | 13 | 27 | 0 | `PARSER_ERROR=27` | 7.73초 | 3.72초 | 86.24 |

## 결정

2차 benchmark 비교 대상은 `candidate-1`, `candidate-3`, `candidate-5`로 제한한다.

`candidate-2`는 Ollama 실행 호환 안정성이 낮아 2차 dataset 비교에서 제외한다. 초기 실행에서 모든 case가 `failed` 상태였고, 오류가 `MODEL_NOT_INSTALLED`와 `EXTERNAL_DEPENDENCY`로 기록되었다. 또한 로컬에서 `ollama run hf.co/pathcosmos/frankenstallm:Q4_K_M` 실행 시 `400 Bad Request`가 발생한 이력이 있어, 모델 품질 평가 전에 runtime compatibility 문제가 먼저 해결되어야 한다.

`candidate-4`는 응답 품질 가능성은 남아 있지만, 현재 로컬 환경에서 평균 latency가 58.80초로 다른 후보 대비 매우 높다. `candidate-1`, `candidate-3`, `candidate-5`의 평균 latency가 약 7.73초에서 9.34초 범위인 것과 비교하면 case당 49초 이상 느리다. 1차/2차 비교는 여러 dataset을 반복 실행해야 하므로, 현재 단계에서는 시간 비용이 과도하다고 판단한다.

`candidate-1`은 요구 형식에 맞지 않는 답변이 반복되어 `PARSER_ERROR`가 발생했지만, 한국계 1.2B 모델 기준선으로서 비교 가치가 있다. 최종 후보가 되지 않더라도, 작은 한국어 모델이 실제 제품형 평가에서 어떤 한계를 보이는지 설명하는 baseline 역할을 할 수 있다.

## 2차 평가 계획

2차 평가는 자체 MileDay 테스트셋을 제외하고, 공개 benchmark 4개 dataset을 대상으로 dataset별 50개 샘플을 사용한다. MileDay 자체 일정 생성 평가는 별도 product-specific 평가로 분리하고, 이번 2차 benchmark 비교의 가중치에는 포함하지 않는다.

| 평가 family | dataset | 샘플 수 | scoring 방식 | 평가 목적 |
|---|---|---:|---|---|
| Instruction following | IFEval-Ko | 50 | deterministic instruction evaluator | 한국어 지시 준수 및 형식 제약 |
| Korean reasoning | KoBALT-700 | 50 | deterministic scoring | 한국어 상식/추론 안정성 |
| Korean reading/context | CLIcK | 50 | deterministic MCQ scoring | 한국어 문맥 이해 |
| Knowledge benchmark | KMMLU-Pro | 50 | deterministic MCQ scoring | 한국어 전문지식/시험형 문제 해결 |

후보 3개와 공개 benchmark dataset 4개를 모두 실행하면 총 실행량은 다음과 같다.

| 항목 | 계산 |
|---|---:|
| dataset별 샘플 수 | 50 |
| dataset 수 | 4 |
| candidate 수 | 3 |
| 총 generation 수 | 600 |

기존 평균 latency 기준 예상 소요 시간은 다음과 같다.

| candidate | 평균 latency | 200 cases 예상 시간 |
|---|---:|---:|
| candidate-1 | 8.40초 | 약 28분 |
| candidate-3 | 9.34초 | 약 31분 |
| candidate-5 | 7.73초 | 약 26분 |
| 합계 | - | 약 1시간 25분 |

IFEval-Ko, KoBALT-700, CLIcK, KMMLU-Pro는 재현성과 비용 관리를 위해 deterministic scoring을 유지한다. Gemini LLM-as-Judge는 이번 공개 benchmark 2차 비교에는 사용하지 않고, MileDay 자체 일정 생성 평가에서만 별도로 사용한다.

## 평가 리포트 관점

이번 2차 평가는 모델 성능을 하나의 accuracy로만 판단하지 않는다. MileDay의 실제 요구사항에 맞춰 다음 지표를 함께 본다.

| 지표 | 설명 | 평가 리포트에서 보여줄 의미 |
|---|---|---|
| dataset별 score | 각 benchmark의 deterministic score | 모델별 강점과 약점 분리 |
| parser error rate | 출력 형식 불일치 비율 | 구조화 출력 안정성 |
| failure rate | runtime/model/API 실패 비율 | 운영 안정성 |
| latency p50/p95/avg | 로컬 inference 시간 | 데스크톱 앱 적용 가능성 |
| tokens/sec | 처리량 | 로컬 실행 효율 |
| weighted score | 공개 benchmark 가중치 반영 | 최종 모델 선정 근거 |

2차 공개 benchmark 평가 가중치는 다음과 같이 둔다.

| 평가 항목 | 가중치 |
|---|---:|
| IFEval-Ko | 40% |
| KoBALT-700 | 30% |
| CLIcK | 15% |
| KMMLU-Pro | 15% |

## 결과

2차 평가 대상은 `candidate-1`, `candidate-3`, `candidate-5`로 확정한다. `candidate-2`는 runtime compatibility 문제가 해결될 때까지 제외하고, `candidate-4`는 latency가 개선되거나 별도 장시간 평가가 필요할 때 재검토한다.

이 결정은 최종 모델 추천이 아니라, 2차 비교 평가를 실행하기 위한 shortlist 결정이다. 최종 추천은 2차 공개 benchmark 평가 결과의 score, invalid/failure rate, latency와 별도 MileDay product-specific 평가 결과를 종합해 별도 report에서 판단한다.

## 3차 테스트 계획

3차 테스트는 2차 공개 benchmark 결과를 바탕으로 최종 후보를 `candidate-3`, `candidate-5`로 좁혀 진행한다. 2차 평가에서 `candidate-3`는 weighted score, parser 안정성, latency가 가장 좋았고, `candidate-5`는 CLIcK와 KoBALT-700 일부 항목에서 강점을 보였으며 모든 응답이 parser를 통과했다. 반면 `candidate-1`은 한국계 1.2B baseline으로는 의미가 있지만, 객관식 benchmark 3종에서 `PARSER_ERROR`가 반복되어 3차 정밀 비교에서는 제외한다.

3차 테스트의 목적은 일반 지식 benchmark 전체를 넓게 비교하는 것이 아니라, MileDay 제품 요구사항과 직접 연결되는 두 역량을 더 엄격하게 확인하는 것이다.

| 핵심 역량 | Dataset | 사용 이유 |
|---|---|---|
| 형식 제약 및 지시 준수 | IFEval-Ko | MileDay 일정 생성은 설명문, JSON, 날짜, 필드 형식 등 출력 제약을 안정적으로 따라야 한다. |
| 한국어 추론 안정성 | KoBALT-700 | 일정 조정, 마일스톤 순서 판단, 의존성 해석에는 한국어 문장 이해와 추론 안정성이 필요하다. |

CLIcK와 KMMLU-Pro는 3차 테스트에서 평가 및 weighted score 계산에서 제외한다. CLIcK는 한국어 문맥 이해를 확인하는 데 유용하지만, MileDay의 핵심 리스크인 형식 제약과 일정 추론 안정성보다 우선순위가 낮다. KMMLU-Pro는 전문지식/시험형 문제 해결 능력을 측정하지만, 일정 관리 제품의 실제 사용 시나리오와 직접 연결되는 정도가 낮다.

## 3차 테스트 대상

| 항목 | 결정 |
|---|---|
| 테스트 명칭 | 3차 형식 제약·추론 안정성 테스트 |
| 대상 모델 | `candidate-3`, `candidate-5` |
| 사용 dataset | IFEval-Ko, KoBALT-700 |
| dataset 기준 | `datasets/*/processed/data.jsonl` 기준 전체 dataset |
| sampling | 사용하지 않음 |
| scoring 방식 | deterministic scoring |
| LLM-as-Judge | 사용하지 않음 |
| batch 구성 | 두 모델을 같은 batch로 묶고 같은 dataset 순서를 공유 |

`processed/data.jsonl`을 기준으로 사용하는 이유는 harness가 변환한 local snapshot을 통해 실행 재현성을 확보하기 위해서다. 원본 dataset을 매번 직접 읽으면 원본 포맷, dependency, 외부 dataset 변경에 영향을 받을 수 있으므로, 3차 테스트에서는 현재 repository가 관리하는 processed artifact를 평가 기준으로 삼는다.

## 3차 System Prompt 정책

3차 테스트에서는 `candidate-3`, `candidate-5`에 동일한 system prompt를 적용한다. 동일 prompt를 적용해야 모델별 조건이 일치하고, 결과 차이를 prompt tuning 차이가 아니라 모델의 형식 준수 및 추론 안정성 차이로 해석할 수 있다.

System prompt는 다음 원칙을 따른다.

- 사용자의 문제와 지시를 최우선으로 따른다.
- 숨은 사고 과정, 풀이 과정, 자체 검토 과정, 메타 설명을 출력하지 않는다.
- 최종 답변만 출력한다.
- 객관식 문제에서는 허용된 선택지 중 하나만 출력한다.
- 정답을 모를 때도 설명을 덧붙이지 않고 가장 가능성 높은 선택지 하나만 출력한다.
- IFEval-Ko에서는 문제에 포함된 형식, 길이, 키워드, 금지어, 반복, 종료 조건을 그대로 따른다.
- KoBALT-700에서는 `A`부터 `J`까지의 선택지 중 하나만 출력한다.

초안 prompt:

```text
당신은 한국어 평가 데이터셋에 응답하는 로컬 LLM입니다.

반드시 사용자의 지시를 최우선으로 따르세요.
숨은 사고 과정, 풀이 과정, 자체 검토 과정, 메타 설명을 출력하지 마세요.
최종 답변만 출력하세요.

IFEval-Ko 문제에서는 사용자가 요구한 형식, 길이, 키워드, 금지어, 반복, 종료 조건을 정확히 따르세요.
KoBALT-700 객관식 문제에서는 A, B, C, D, E, F, G, H, I, J 중 정답 하나만 출력하세요.
정답을 모르는 경우에도 설명하지 말고 가장 가능성 높은 선택지 하나만 출력하세요.
```

이 prompt는 평가 공정성을 위해 두 모델에 동일하게 적용한다. 모델별 별도 prompt는 특정 모델의 약점을 보정할 수 있지만, 3차 테스트의 목적은 prompt 최적화가 아니라 후보 모델의 동일 조건 비교이므로 사용하지 않는다.

## 3차 평가 가중치

3차 테스트의 weighted score는 다음 두 dataset만 사용한다.

| 평가 항목 | 가중치 |
|---|---:|
| IFEval-Ko | 60% |
| KoBALT-700 | 40% |

형식 제약 및 지시 준수를 더 크게 반영하기 위해 IFEval-Ko에 60%를 부여한다. MileDay는 일정 추천 결과를 사용자가 검토한 뒤 DB 반영 후보로 사용할 예정이므로, 모델이 요구 형식과 제약을 어기는 경우 실제 기능 안정성이 크게 떨어진다. KoBALT-700은 한국어 추론 안정성을 보기 위해 40%를 부여하되, 형식 안정성보다 낮은 가중치로 둔다.

3차 weighted score 계산식:

```text
weighted_score = IFEval-Ko score * 0.60 + KoBALT-700 score * 0.40
```

CLIcK와 KMMLU-Pro는 3차 테스트의 실행 대상과 점수 계산에서 모두 제외한다.

## 3차 판단 기준

3차 테스트의 최종 판단은 다음 순서로 진행한다.

| 우선순위 | 기준 | 판단 방식 |
|---:|---|---|
| 1 | 실행 안정성 | `failed=0`이어야 한다. runtime failure가 발생하면 해당 모델은 운영 후보에서 제외한다. |
| 2 | 출력 형식 안정성 | `invalid rate`가 낮은 모델을 우선한다. 두 모델 중 하나라도 `invalid rate >= 5%`이면 제품 적용 전 prompt 또는 parser 정책을 재검토한다. |
| 3 | weighted score | IFEval-Ko 60%, KoBALT-700 40% 가중 점수로 1순위 모델을 결정한다. |
| 4 | IFEval-Ko score | weighted score 차이가 0.03 미만이면 IFEval-Ko 점수가 높은 모델을 우선한다. |
| 5 | latency | 품질 지표가 유사하면 평균 latency와 p95 latency가 낮은 모델을 우선한다. |

최종 추천 모델은 `failed=0`, `invalid rate < 5%`, weighted score 1위 조건을 모두 만족하는 모델로 결정한다. 두 모델 모두 조건을 만족하지 못하면, 모델 교체보다 먼저 system prompt와 출력 parser 정책을 재검토한다.

## 3차 리포트에 포함할 지표

3차 테스트 결과 리포트는 다음 항목을 포함해야 한다.

| 지표 | 설명 |
|---|---|
| dataset별 score | IFEval-Ko, KoBALT-700 각각의 deterministic score |
| weighted score | 60/40 가중치 반영 최종 비교 점수 |
| passed / invalid / failed | 실행 안정성과 출력 형식 안정성 |
| parser error reason | invalid 발생 시 dataset별 주요 원인 |
| latency avg / p50 / p95 | 로컬 데스크톱 앱 적용 가능성 |
| TTFT avg / p50 / p95 | 사용자 체감 첫 응답 시간 |
| tokens/sec | 로컬 실행 효율 |
| raw artifact path | 재검토 가능한 원문 응답 위치 |

3차 테스트 결과는 2차 공개 benchmark 결과보다 최종 모델 선정 근거에 더 큰 비중을 둔다. 2차 평가는 후보 축소용이고, 3차 평가는 MileDay의 핵심 요구사항인 형식 제약 준수와 한국어 추론 안정성을 확인하는 최종 비교 단계다.
