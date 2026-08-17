# ADR 0006: 2차·3차 모델 평가 후보 선정

- 날짜: 2026-07-29
- 상태: Accepted
- 관련 문서:
  - `configs/models.yaml`
  - `harness/README.md`
  - `datasets/README.md`
  - `artifacts/runs/benchmark-batch-1-50cases-summary.md`
  - `artifacts/runs/third-benchmark-batch-2-summary.md`

## 배경

MileDay는 한국어 일정 계획, 마일스톤 생성, 자연어 기반 일정 수정 기능에 사용할 로컬 LLM 후보를 비교하고 있다. 평가 리포트는 단순 실행 기록이 아니라, 후보를 좁히는 기준과 평가 설계가 재현 가능하게 설명되어야 한다.

초기 후보는 다음 5개 모델이었다.

| candidate | model_tag | 주요 역할 가정 |
|---|---|---|
| candidate-1 | `ingu627/exaone4.0:1.2b` | 한국계 소형 모델 baseline |
| candidate-2 | `hf.co/pathcosmos/frankenstallm:Q4_K_M` | 한국어 특화 3B 후보 |
| candidate-3 | `granite4.1:3b` | 안정적인 다국어 구조화 출력 후보 |
| candidate-4 | `qwen3.5:4b` | 최신 멀티링구얼 고성능 후보 |
| candidate-5 | `ministral-3:3b` | 경량 다국어 구조화 출력 후보 |

## 1차 Smoke 판단

1차는 MileDay 자체 synthetic fixture를 사용해 로컬 실행 가능성, 응답 형식, parser 안정성, latency를 빠르게 확인했다. 이 단계는 최종 benchmark가 아니라 2차 평가로 보낼 후보를 줄이기 위한 사전 점검이다.

| candidate | 기록 case 수 | passed | invalid | failed | 주요 오류 | 평균 latency | 평균 TTFT | 평균 tok/s |
|---|---:|---:|---:|---:|---|---:|---:|---:|
| candidate-1 | 10 | 0 | 10 | 0 | `PARSER_ERROR=10` | 8.40초 | 4.24초 | 199.18 |
| candidate-2 | 10 | 0 | 0 | 10 | `MODEL_NOT_INSTALLED=5`, `EXTERNAL_DEPENDENCY=5` | 3.82초 | 없음 | 없음 |
| candidate-3 | 45 | 16 | 29 | 0 | `PARSER_ERROR=29` | 9.34초 | 3.85초 | 84.97 |
| candidate-4 | 15 | 4 | 11 | 0 | `PARSER_ERROR=11` | 58.80초 | 54.28초 | 64.77 |
| candidate-5 | 40 | 13 | 27 | 0 | `PARSER_ERROR=27` | 7.73초 | 3.72초 | 86.24 |

## 2차 후보 결정

2차 benchmark 비교 대상은 `candidate-1`, `candidate-3`, `candidate-5`로 제한했다.

`candidate-2`는 Ollama 실행 호환 안정성이 낮아 2차 dataset 비교에서 제외했다. 초기 실행에서 모든 case가 `failed`였고, 로컬에서 `ollama run hf.co/pathcosmos/frankenstallm:Q4_K_M` 실행 시 `400 Bad Request`가 발생한 이력이 있다. 모델 품질 평가 전에 runtime compatibility 문제를 먼저 해결해야 한다.

`candidate-4`는 응답 품질 가능성은 있으나 현재 로컬 환경에서 평균 latency가 58.80초로 다른 후보보다 매우 높았다. 반복 dataset 평가에서는 시간 비용이 과도하므로 2차 비교에서 제외했다.

`candidate-1`은 요구 형식을 자주 깨지만 한국어 소형 모델 baseline으로 비교 가치가 있다고 판단했다. 최종 후보가 되지 않더라도, 작은 한국어 모델이 실제 평가에서 어떤 한계를 보이는지 설명하는 기준선 역할을 할 수 있다.

## 2차 평가 계획

2차 평가는 MileDay 자체 테스트셋을 제외하고 공개 benchmark 4개 dataset을 사용했다.

| 평가 family | dataset | 샘플 수 | scoring 방식 | 평가 목적 |
|---|---:|---:|---|---|
| Instruction following | IFEval-Ko | 50 | deterministic instruction evaluator | 한국어 지시 준수 및 형식 제약 |
| Korean reasoning | KoBALT-700 | 50 | deterministic scoring | 한국어 상식/추론 안정성 |
| Korean reading/context | CLIcK | 50 | deterministic MCQ scoring | 한국어 문맥 이해 |
| Knowledge benchmark | KMMLU-Pro | 50 | deterministic MCQ scoring | 한국어 전문지식/시험형 문제 해결 |

총 실행량:

```text
3 models * 4 datasets * 50 samples = 600 generations
```

2차 공개 benchmark 평가 가중치:

| 평가 항목 | 가중치 |
|---|---:|
| IFEval-Ko | 40% |
| KoBALT-700 | 30% |
| CLIcK | 15% |
| KMMLU-Pro | 15% |

IFEval-Ko, KoBALT-700, CLIcK, KMMLU-Pro는 재현성과 비용 관리를 위해 deterministic scoring을 유지한다. Gemini LLM-as-Judge는 공개 benchmark 2차 비교에는 사용하지 않고, MileDay 자체 일정 생성 평가에서만 별도로 사용한다.

## 2차 결과 해석 기준

2차 평가는 모델 성능을 하나의 accuracy로만 판단하지 않는다. MileDay의 실제 요구사항에 맞춰 다음 지표를 함께 본다.

| 지표 | 설명 | 평가 리포트에서 보는 이유 |
|---|---|---|
| dataset별 score | 각 benchmark의 deterministic score | 모델별 강점과 약점 분리 |
| parser error rate | 출력 형식 불일치 비율 | 구조화 출력 안정성 |
| failure rate | runtime/model/API 실패 비율 | 운영 안정성 |
| latency p50/p95/avg | 로컬 inference 시간 | 데스크톱 앱 적용 가능성 |
| tokens/sec | 처리량 | 로컬 실행 효율 |
| weighted score | 공개 benchmark 가중치 반영 | 후보 축소 근거 |

2차 결과를 통해 최종 집중 비교 대상은 `candidate-3`, `candidate-5`로 좁혔다. `candidate-1`은 baseline 역할은 있었지만 객관식 benchmark 3종에서 `PARSER_ERROR`가 반복되어 3차 정밀 비교에서는 제외했다.

## 3차 테스트 계획

3차 테스트의 목적은 일반 지식 benchmark 전체를 넓게 비교하는 것이 아니라, MileDay 제품 요구사항과 직접 연결되는 두 역량을 더 엄격하게 확인하는 것이다.

| 핵심 역량 | Dataset | 사용 이유 |
|---|---|---|
| 형식 제약 및 지시 준수 | IFEval-Ko | MileDay 일정 생성은 설명문, JSON, 날짜, 필드 형식 등 출력 제약을 안정적으로 따라야 한다. |
| 한국어 추론 안정성 | KoBALT-700 | 일정 조정, 마일스톤 순서 판단, 의존성 해석에는 한국어 문장 이해와 추론 안정성이 필요하다. |

CLIcK와 KMMLU-Pro는 3차 테스트의 평가 및 weighted score 계산에서 제외한다. 두 dataset은 보조 지표로 유용하지만, MileDay의 핵심 리스크인 형식 제약과 일정 추론 안정성보다 우선순위가 낮다.

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

System prompt 원칙:

- 사용자의 문제와 지시를 최우선으로 따른다.
- 숨은 사고 과정, 추론 과정, 자체 검토 과정, 메타 설명을 출력하지 않는다.
- 최종 답만 출력한다.
- 객관식 문제에서는 허용된 선택지 중 하나만 출력한다.
- IFEval-Ko에서는 문제에 포함된 형식, 길이, 키워드, 금지어, 반복, 종료 조건을 그대로 따른다.
- KoBALT-700에서는 `A`부터 `J`까지의 선택지 중 하나만 출력한다.

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

## 3차 판단 기준

3차 테스트의 최종 판단은 다음 순서로 진행한다.

| 우선순위 | 기준 | 판단 방식 |
|---:|---|---|
| 1 | 실행 안정성 | `failed=0`이어야 한다. runtime failure가 발생하면 해당 모델은 운영 후보에서 제외한다. |
| 2 | 출력 형식 안정성 | `invalid rate < 5%`를 기본 통과 기준으로 둔다. |
| 3 | weighted score | IFEval-Ko 60%, KoBALT-700 40% 가중 점수로 1순위 모델을 결정한다. |
| 4 | IFEval-Ko score | weighted score 차이가 0.03 미만이면 IFEval-Ko 점수가 높은 모델을 우선한다. |
| 5 | latency | 품질 지표가 유사하면 평균 latency와 p95 latency가 낮은 모델을 우선한다. |

## 3차 결과

3차 테스트는 `third-benchmark-batch-2`로 완료되었다.

| model | passed | invalid | failed | weighted score | IFEval-Ko | KoBALT-700 | avg latency ms | avg TTFT ms | avg tok/s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| candidate-3 | 1042 | 0 | 0 | 0.389 | 0.564 | 0.126 | 4032.054 | 3038.885 | 101.340 |
| candidate-5 | 1042 | 0 | 0 | 0.354 | 0.482 | 0.161 | 4935.422 | 3296.360 | 123.665 |

두 모델 모두 `failed=0`, `invalid=0`으로 실행 안정성 기준은 통과했다. `candidate-5`는 KoBALT-700과 throughput에서 더 나은 결과를 보였지만, 3차 핵심 가중치 기준에서는 `candidate-3`가 우세했다.

3차 weighted score 차이는 0.035로 near-tie 기준 0.03보다 크다. 따라서 tie-break 없이 `candidate-3`를 우선 후보로 판단한다.

## 3차 컴퓨팅 자원 사용량

아래 값은 `performance.jsonl`에 저장된 case별 resource sample을 집계한 결과다. 각 row의 `peak_*` 값은 해당 case 실행 중 관측된 peak이므로, `avg`는 “case별 peak의 평균”, `max`는 “전체 3차 실행 중 관측된 최대값”으로 해석한다.

| model | samples | avg CPU peak | max CPU peak | avg RAM peak | max RAM peak | avg VRAM peak | max VRAM peak | avg Ollama RSS | max Ollama RSS | VRAM status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| candidate-3 | 1042 | 24.834% | 64.700% | 14.302 GiB | 15.145 GiB | 2.725 GiB | 6.064 GiB | 0.034 GiB | 0.044 GiB | ok=1042 |
| candidate-5 | 1042 | 23.303% | 54.200% | 14.554 GiB | 15.261 GiB | 3.672 GiB | 6.062 GiB | 0.054 GiB | 0.056 GiB | ok=1042 |

자원 사용량만 보면 CPU peak 평균과 최대값은 `candidate-5`가 더 낮다. 하지만 RAM peak 평균, RAM peak 최대값, VRAM peak 평균, Ollama RSS 평균은 `candidate-3`가 더 낮다. 특히 VRAM peak 평균은 `candidate-3`가 2.725 GiB, `candidate-5`가 3.672 GiB로 약 0.947 GiB 차이가 난다.

두 모델 모두 VRAM 상태는 모든 sample에서 `ok`였으므로 resource exhaustion은 발생하지 않았다. 다만 로컬 데스크톱 앱 적용 관점에서는 평균 latency, TTFT, RAM/VRAM 평균 사용량이 더 낮은 `candidate-3`가 더 안정적인 운영 후보로 해석된다.

## 최종 판단

3차 형식 제약·추론 안정성 테스트 기준의 최종 선택 모델은 `candidate-3`로 등록된 `granite4.1:3b`이다. 이 모델은 `configs/models.yaml` 기준 `IBM Granite 4.1 3B instruct` 후보이며, 로컬 실행 runtime은 Ollama를 사용한다.

근거:

- `failed=0`, `invalid=0`으로 실행 안정성 기준을 통과했다.
- `granite4.1:3b`의 weighted score가 0.389로 `candidate-5`의 0.354보다 높다.
- `granite4.1:3b`의 IFEval-Ko 점수가 0.564로 `candidate-5`의 0.482보다 높다.
- 평균 latency와 TTFT가 `candidate-5`보다 낮다.
- RAM/VRAM 평균 peak와 Ollama RSS 평균이 `candidate-5`보다 낮다.
- MileDay는 형식 제약과 지시 준수를 더 높은 우선순위로 두므로 `granite4.1:3b`의 강점이 제품 요구사항과 더 잘 맞는다.

단, `candidate-5`는 KoBALT-700과 throughput에서 장점이 있으므로 product-specific 일정 생성 평가에서는 보조 비교군으로 유지한다.
