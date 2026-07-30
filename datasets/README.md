# Datasets

`datasets/`는 harness가 공개 benchmark dataset을 내려받고, 평가에 사용할 processed JSONL로 변환해 저장하는 디렉터리입니다.

이 디렉터리는 모델 평가용 데이터 저장소이며 MileDay 제품 DB가 아닙니다.

## 구조

```text
datasets/
  click/
    <revision>/
      dataset_manifest.json
      processed/
        data.jsonl
  ifeval-ko/
    <revision>/
      dataset_manifest.json
      processed/
        data.jsonl
  kmmlu-pro/
    <revision>/
      dataset_manifest.json
      processed/
        data.jsonl
  kobalt-700/
    <revision>/
      dataset_manifest.json
      processed/
        data.jsonl
```

현재 관리 대상:

| 디렉터리 | Registry key | 목적 |
|---|---|---|
| `ifeval-ko/` | `ifeval_ko` | 한국어 지시 준수, 형식 제약, instruction following 평가 |
| `kobalt-700/` | `kobalt` | 한국어 상식/추론 안정성 평가 |
| `click/` | `click` | 한국어 독해/문맥 이해 기반 객관식 평가 |
| `kmmlu-pro/` | `kmmlu_pro` | 한국어 전문 지식/객관식 평가 |

## Manifest와 Processed

### `dataset_manifest.json`

데이터셋 출처, revision, split, 생성 시점, row 수 같은 메타데이터를 저장합니다. 평가 결과를 재현할 때 어떤 원본 snapshot을 썼는지 확인하는 기준입니다.

### `processed/data.jsonl`

harness adapter가 바로 읽을 수 있도록 정규화한 JSONL입니다. 각 줄은 하나의 평가 case입니다.

원본 row 수와 processed row 수가 다를 수 있습니다.

주요 이유:

- 원본 row 중 필수 필드가 비어 있는 항목 제외
- adapter가 지원하지 않는 형식 제외
- dataset별 split/config 차이
- `--sample-limit`으로 일부만 처리한 smoke artifact
- 중복 id 또는 schema validation 실패 row 제외

정확한 기준은 `harness/dataset_processor.py`와 `harness/benchmarks/*` adapter를 함께 확인합니다.

## 데이터셋 준비

전체 데이터셋 준비:

```powershell
python -m harness.cli prepare-datasets
```

특정 데이터셋만 준비:

```powershell
python -m harness.cli prepare-datasets --dataset ifeval_ko
```

빠른 구조 확인용 샘플 준비:

```powershell
python -m harness.cli prepare-datasets --sample-limit 5
```

주의: `--sample-limit`으로 만든 processed artifact는 전체 평가용이 아닙니다. 전체 데이터셋 평가 전에는 sample limit 없이 다시 생성해야 합니다.

## Benchmark 단계별 데이터셋 기준

현재 모델 평가는 1차 smoke, 2차 public benchmark, 3차 집중 benchmark로 나누어 진행했습니다. 각 단계는 목적이 다르므로 사용하는 데이터셋과 샘플링 기준도 다릅니다.

| 단계 | 목적 | 명령 | 데이터셋 | 샘플링 |
|---|---|---|---|---|
| 1차 | 후보 모델의 로컬 실행 가능성, 응답 형식, latency를 빠르게 확인 | `run-mileday-smoke` | `tests/fixtures/mileday/synthetic_schedule.jsonl` | `--limit`만큼 random sample |
| 2차 | 후보 모델을 공개 benchmark 4종으로 비교해 shortlist 검증 | `run-benchmark` | IFEval-Ko, KoBALT-700, CLIcK, KMMLU-Pro | dataset별 `--limit`만큼 random sample |
| 3차 | 최종 후보 2개를 핵심 지표 2종 전체 데이터셋으로 집중 비교 | `run-third-benchmark` | IFEval-Ko, KoBALT-700 | sampling 없음, 전체 processed dataset |

### 1차 Smoke 기준

1차는 공개 benchmark가 아니라 MileDay 자체 synthetic fixture를 사용합니다. 목적은 모델 성능 순위를 확정하는 것이 아니라, 모델이 로컬 Ollama에서 안정적으로 실행되는지와 MileDay가 요구하는 출력 구조를 대략 따르는지 확인하는 것입니다.

| 항목 | 기준 |
|---|---|
| 명령 | `run-mileday-smoke` |
| 데이터셋 | `tests/fixtures/mileday/synthetic_schedule.jsonl` |
| 모델 | 초기 후보 `candidate-1` ~ `candidate-5` |
| 샘플링 | `--limit` 개수만큼 random sample |
| seed | `--seed`로 고정 가능. 기본값 42 |
| 평가 대상 | 설명문, fenced JSON, JSON load 가능 여부, 일정 constraint, Gemini explanation judge |
| 산출물 | 개별 `report.md`, batch summary, raw/parsed/metrics artifact |

대표 실행:

```powershell
python -m harness.cli run-mileday-smoke --fixture tests\fixtures\mileday\synthetic_schedule.jsonl --model-id candidate-1,candidate-3,candidate-5 --limit 5 --seed 42
```

1차 결과는 다음 판단에 사용했습니다.

- `candidate-2`: Ollama 호환 안정성 문제로 2차 dataset 비교에서 제외
- `candidate-4`: 평균 latency가 다른 후보 대비 크게 높아 2차 dataset 비교에서 제외
- `candidate-1`: 요구 형식을 자주 깨지만 한국어 소형 baseline으로 비교 가치가 있어 2차 유지
- `candidate-3`, `candidate-5`: 출력 구조와 latency가 상대적으로 안정적이어서 2차 유지

### 2차 Public Benchmark 기준

2차는 MileDay 자체 fixture를 제외하고 공개 benchmark 4종만 사용합니다. 목적은 후보 모델을 같은 sample snapshot에서 비교하고, 한국어 지시 준수, 추론 안정성, 문맥 이해, 지식형 문제 해결 능력을 균형 있게 확인하는 것입니다.

| 항목 | 기준 |
|---|---|
| 명령 | `run-benchmark` |
| 모델 | `candidate-1`, `candidate-3`, `candidate-5` |
| 데이터셋 | IFEval-Ko, KoBALT-700, CLIcK, KMMLU-Pro |
| 샘플링 | 각 dataset에서 random 50개 |
| seed | 42 |
| batch 조건 | 모든 모델이 같은 sample sequence 공유 |
| scoring | dataset별 deterministic scoring |
| LLM-as-Judge | 사용하지 않음 |
| 실패 정책 | 전체 지표 비교 목적이므로 실행 실패 시 중단 |

대표 실행:

```powershell
python -m harness.cli run-benchmark --model-id candidate-1,candidate-3,candidate-5 --limit 50 --seed 42
```

2차 가중치:

| 평가 항목 | 가중치 | 이유 |
|---|---:|---|
| IFEval-Ko | 40% | 한국어 지시 준수와 형식 제약은 MileDay 일정 생성 결과의 안정성과 직접 연결됨 |
| KoBALT-700 | 30% | 한국어 상식/추론 안정성은 일정 조정과 마일스톤 판단에 중요함 |
| CLIcK | 15% | 한국어 문맥 이해 능력을 보조 지표로 확인 |
| KMMLU-Pro | 15% | 전문 지식형 문제 해결 능력을 보조 지표로 확인 |

총 generation 수:

```text
3 models * 4 datasets * 50 samples = 600 generations
```

2차 결과는 최종 후보를 `candidate-3`, `candidate-5`로 좁히는 근거로 사용했습니다. `candidate-1`은 baseline 역할은 있었지만 parser error와 형식 안정성 측면에서 3차 집중 비교 대상에서는 제외했습니다.

### 3차 Benchmark 기준

3차는 2차 결과를 기반으로 최종 후보 2개를 핵심 지표만으로 다시 비교하는 집중 평가입니다. MileDay에서 중요한 것은 출력 형식 제약과 한국어 추론 안정성이므로 IFEval-Ko와 KoBALT-700만 사용합니다.

| 항목 | 기준 |
|---|---|
| 명령 | `run-third-benchmark` |
| 모델 | `candidate-3`, `candidate-5` |
| 데이터셋 | IFEval-Ko, KoBALT-700 |
| 샘플링 | 없음 |
| 데이터 범위 | 각 processed dataset 전체 |
| system prompt | 두 모델에 동일하게 적용 |
| scoring | deterministic scoring |
| LLM-as-Judge | 사용하지 않음 |
| batch 조건 | 두 모델이 같은 dataset 순서 공유 |
| 제외 | CLIcK, KMMLU-Pro는 실행 및 점수 계산에서 제외 |

대표 실행:

```powershell
python -m harness.cli run-third-benchmark
```

3차 가중치:

| 평가 항목 | 가중치 | 이유 |
|---|---:|---|
| IFEval-Ko | 60% | 형식 제약과 지시 준수 실패는 DB 반영 후보 데이터의 안정성을 직접 훼손함 |
| KoBALT-700 | 40% | 한국어 추론 안정성은 일정 조정, 우선순위 판단, 마일스톤 설명 품질과 연결됨 |

3차 weighted score:

```text
weighted_score = IFEval-Ko score * 0.60 + KoBALT-700 score * 0.40
```

3차 benchmark는 명령 실행 시 IFEval-Ko와 KoBALT-700 processed artifact를 full dataset 기준으로 재생성한 뒤 실행합니다.

## 관리 기준

- `configs/datasets.yaml`의 revision을 기준으로 데이터셋 snapshot을 관리합니다.
- 데이터셋 license와 commercial use 가능 여부는 평가 리포트에 명확히 남깁니다.
- 공개 데이터셋 원본을 임의로 수정하지 않습니다.
- processed schema 변경 시 adapter, scorer, tests를 함께 수정합니다.
- 평가 결론에는 dataset key, revision, row 수, sample 수, seed, 실행 명령을 반드시 기록합니다.
