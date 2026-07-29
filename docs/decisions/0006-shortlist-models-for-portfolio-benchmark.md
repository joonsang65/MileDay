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
