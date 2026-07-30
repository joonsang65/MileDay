# MileDay Harness

MileDay harness는 로컬 LLM 후보 모델을 동일한 조건에서 평가하기 위한 CLI 기반 평가 도구입니다. 기존 MileDay 앱의 FastAPI backend와 분리되어 있으며, 모델 선정과 평가 리포트 생성을 위한 offline benchmark 파이프라인을 담당합니다.

## 역할

Harness의 책임은 다음과 같습니다.

- `configs/models.yaml`에 등록된 Ollama 후보 모델 조회 및 실행
- `configs/datasets.yaml`에 등록된 공개 benchmark dataset 준비
- MileDay 일정 생성 smoke test 실행
- IFEval-Ko, KoBALT-700, CLIcK, KMMLU-Pro 기반 public benchmark 실행
- 모델 응답 원문, 파싱 결과, 성능 metric, Markdown report 저장
- batch 단위 실행 결과와 모델별 요약 report 생성
- Gemini API를 사용한 MileDay 설명문 judge 및 batch 품질 요약

Harness는 제품 runtime이 아니라 평가 runtime입니다. 실제 사용자 데이터 처리, Supabase 접근, 앱 API 제공은 `backend/`의 책임입니다.

## 아키텍처

Harness는 다음 흐름을 기준으로 동작합니다.

```text
CLI
  -> Model Registry / Dataset Registry
  -> Dataset Loader / Benchmark Adapter
  -> Orchestrator
  -> Runtime Adapter
  -> Scorer / Judge
  -> ResultStore
  -> Markdown Report / Batch Summary
```

| 계층 | 위치 | 책임 |
|---|---|---|
| CLI | `harness/cli.py` | Typer command 정의, 실행 옵션 검증, batch 실행 조립 |
| Registry | `model_registry.py`, `dataset_registry.py` | 모델 및 dataset 설정 로드/검증 |
| Dataset Processing | `dataset_processor.py` | 원본 dataset을 processed JSONL로 변환 |
| Benchmark Adapter | `benchmarks/` | dataset별 prompt 구성, 응답 파싱, deterministic scoring |
| Runtime | `runtime/` | Ollama 호출 추상화 및 오류 분류 |
| Orchestrator | `orchestrator.py` | case 실행, cold/warm mode, resume, progress callback |
| MileDay Evaluation | `mileday/` | 자체 일정 생성 fixture, JSON 검증, rubric, Gemini judge |
| Performance | `performance/` | CPU/RAM/Ollama process resource sampling |
| Result/Report | `results.py`, `reporting.py`, `recommendation.py` | artifact 저장, report 생성, 모델 추천 요약 |
| Schema | `schemas.py` | 공통 result, metric, failure category 모델 |

## 디렉터리 구조

```text
harness/
  cli.py
  config.py
  dataset_processor.py
  dataset_registry.py
  model_registry.py
  orchestrator.py
  recommendation.py
  reporting.py
  results.py
  schemas.py
  benchmarks/
  mileday/
  performance/
  runtime/
```

주요 파일:

| 파일 | 설명 |
|---|---|
| `cli.py` | `preflight`, `list-models`, `prepare-datasets`, `run-mileday-smoke`, `run-benchmark` command 제공 |
| `config.py` | `.env`와 기본값 기반 harness 설정 로드 |
| `model_registry.py` | `configs/models.yaml` 후보 모델 로드 및 Ollama 설치 여부 확인 |
| `dataset_registry.py` | `configs/datasets.yaml` dataset registry 로드 |
| `dataset_processor.py` | pinned source snapshot을 `datasets/*/processed/data.jsonl`로 변환 |
| `orchestrator.py` | 모델 실행 loop, runtime 호출, resume 처리, tqdm 진행률 callback 연결 |
| `results.py` | raw output, parsed result, pretty JSON, performance metric 저장 |
| `reporting.py` | run artifact를 기반으로 한글 Markdown report 생성 |
| `recommendation.py` | hard-gate 기반 모델 추천 요약 생성 |
| `schemas.py` | `RequestResult`, `ResultStatus`, `FailureCategory`, metric schema 정의 |

## Benchmark Adapter

`harness/benchmarks/`는 공개 benchmark dataset별 평가 규칙을 담습니다.

| 파일 | Dataset | 평가 방식 |
|---|---|---|
| `mcq.py` | 공통 객관식 helper | 선택지 prompt 구성, 정답 option 파싱, 점수 계산 |
| `kmmlu_pro.py` | KMMLU-Pro | 객관식 deterministic scoring |
| `kobalt_700.py` | KoBALT-700 | 객관식 deterministic scoring |
| `click_adapter.py` | CLIcK | 객관식 deterministic scoring |
| `ifeval_ko.py` | IFEval-Ko | instruction following 제약 조건 기반 deterministic scoring |

Public benchmark에서 오답은 일반적으로 `failed`가 아니라 평가 점수 `0.0`인 정상 실행 결과입니다. `failed`는 Ollama 오류, timeout, dataset 누락처럼 실행 자체가 깨진 경우에 사용합니다.

## MileDay Evaluation

`harness/mileday/`는 MileDay 일정 생성 품질을 평가합니다.

| 파일 | 설명 |
|---|---|
| `dataset.py` | 자체 일정 생성 fixture schema 및 loader |
| `constraints.py` | 생성 JSON의 날짜, milestone, dependency, duration 등 deterministic 검증 |
| `rubric.py` | 설명문과 일정 결과에 대한 local semantic rubric |
| `explanation_judge.py` | Gemini API 기반 설명문 alignment judge 및 batch 품질 요약 |

MileDay 생성 응답은 설명문과 fenced JSON을 함께 사용하는 것을 기준으로 합니다.

````text
[EXPLANATION]
사용자에게 보여줄 일정 조정 설명

[JSON]
```json
{ "...": "DB 업데이트 후보 데이터" }
```
````

JSON은 `json.loads()` 가능한 형식이어야 하며, 설명문은 milestone 변경 이유와 일정 판단 근거를 포함해야 합니다.

## 명령어

프로젝트 루트에서 실행합니다.

### 사전 점검

```powershell
python -m harness.cli preflight --check-ollama
```

확인 항목:

- artifact, run, dataset directory
- 기본 timeout
- Ollama base URL
- Ollama API 접근 가능 여부

### 모델 목록 확인

```powershell
python -m harness.cli list-models --check-installed
```

`configs/models.yaml`에 등록된 후보 모델과 로컬 Ollama 설치 여부를 확인합니다.

### Dataset 준비

```powershell
python -m harness.cli prepare-datasets
```

특정 dataset만 준비하려면 다음처럼 실행합니다.

```powershell
python -m harness.cli prepare-datasets --dataset ifeval_ko
```

샘플만 빠르게 처리하려면 `--sample-limit`을 사용할 수 있습니다.

```powershell
python -m harness.cli prepare-datasets --sample-limit 5
```

### MileDay Smoke Test

```powershell
python -m harness.cli run-mileday-smoke --fixture tests\fixtures\mileday\synthetic_schedule.jsonl --model-id candidate-1,candidate-3,candidate-5 --limit 5 --seed 42
```

특징:

- `--model-id`는 쉼표로 여러 모델을 받을 수 있습니다.
- `--limit` 개수만큼 fixture에서 random sample을 추출합니다.
- `--seed`가 같으면 같은 sample sequence를 사용합니다.
- batch 실행 시 모든 모델이 같은 case sequence를 공유합니다.
- 개별 run report와 batch summary를 함께 생성합니다.
- 한 모델이 실패해도 다음 모델 실행을 계속합니다.

### Public Benchmark

```powershell
python -m harness.cli run-benchmark --model-id candidate-1,candidate-3,candidate-5 --limit 50 --seed 42
```

특징:

- IFEval-Ko, KoBALT-700, CLIcK, KMMLU-Pro를 대상으로 실행합니다.
- 각 dataset에서 `--limit` 개수만큼 random sample을 추출합니다.
- batch 안의 모든 모델은 같은 sample snapshot을 공유합니다.
- dataset sample snapshot은 `artifacts/runs/<batch-id>-datasets/`에 저장됩니다.
- 실행 자체가 실패하면 전체 benchmark를 중단합니다.

### 3차 형식 제약·추론 안정성 테스트

```powershell
python -m harness.cli run-third-benchmark
```

특징:

- `candidate-3`, `candidate-5`만 실행합니다.
- IFEval-Ko, KoBALT-700만 사용합니다.
- 두 dataset을 full processed artifact로 재생성한 뒤 `processed/data.jsonl` 전체를 사용합니다.
- random sampling을 하지 않습니다.
- 두 모델에 동일한 system prompt를 적용합니다.
- 진행률은 모델별 dataset 단위로 표시되어 총 4개의 progress bar가 순차 표시됩니다.
- weighted score는 IFEval-Ko 60%, KoBALT-700 40%로 계산합니다.
- CLIcK, KMMLU-Pro는 실행과 점수 계산에서 제외합니다.
- 개별 run report와 `third-benchmark-batch-<n>-summary.md`를 생성합니다.

## 설정

Harness 설정은 프로젝트 루트의 `.env`를 기준으로 로드합니다. 다른 env 파일을 사용하려면 `HARNESS_ENV_FILE`을 지정합니다.

주요 환경 변수:

| 변수 | 기본값 | 설명 |
|---|---|---|
| `HARNESS_ARTIFACTS_DIR` | `artifacts` | artifact root |
| `HARNESS_RUNS_DIR` | `artifacts/runs` | run output 저장 위치 |
| `HARNESS_DATASETS_DIR` | `datasets` | processed dataset 저장 위치 |
| `HARNESS_DEFAULT_TIMEOUT_SECONDS` | `120` | 모델 응답 timeout |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API base URL |
| `GEMINI_API_KEY` | 없음 | MileDay explanation judge용 Gemini API key |
| `GEMINI_API_BASE_URL` | `https://generativelanguage.googleapis.com/v1beta` | Gemini API base URL |
| `GEMINI_JUDGE_MODEL` | `gemini-3.5-flash` | judge에 사용할 Gemini model |
| `MILEDAY_REQUIRE_EXPLANATION_JUDGE` | `false` | Gemini judge 실패를 invalid 처리할지 여부 |

`.env`에는 API key가 들어갈 수 있으므로 commit하지 않습니다. 예시는 `.env.example`을 기준으로 관리합니다.

## Artifact 구조

Run 결과는 기본적으로 `artifacts/runs/` 아래에 저장됩니다.

```text
artifacts/runs/
  <run-id>/
    config.snapshot.yaml
    raw/
      <model>__<dataset>__<case>.txt
    parsed/
      results.jsonl
      results.pretty.json
    metrics/
      performance.jsonl
    report.md
  <batch-id>-summary.md
  <batch-id>-datasets/
```

| Artifact | 설명 |
|---|---|
| `raw/*.txt` | 모델 원문 응답. 리포트에는 전문을 직접 삽입하지 않고 path만 참조합니다. |
| `parsed/results.jsonl` | 실행 결과 append-only JSONL |
| `parsed/results.pretty.json` | 사람이 읽기 쉬운 pretty JSON 결과 |
| `metrics/performance.jsonl` | latency, TTFT, throughput, resource sample |
| `report.md` | 개별 run 한글 Markdown report |
| `<batch-id>-summary.md` | 여러 모델 batch 실행 요약 |
| `<batch-id>-datasets/` | batch에서 공유한 random sample snapshot |

## Result Status

Harness는 실행 결과를 다음 상태로 분류합니다.

| 상태 | 의미 |
|---|---|
| `passed` | 평가 기준을 통과한 정상 결과 |
| `failed` | runtime, 외부 의존성, 코드 오류 등 실행 실패 |
| `invalid` | 응답은 생성됐지만 parser 또는 schema/constraint 기준을 만족하지 못함 |
| `skipped` | 설정 누락 등으로 평가 일부를 의도적으로 생략 |

주요 실패 category는 `CODE_ERROR`, `CONFIG_ERROR`, `MODEL_NOT_INSTALLED`, `OLLAMA_UNAVAILABLE`, `DATASET_UNAVAILABLE`, `PARSER_ERROR`, `TIMEOUT`, `RESOURCE_EXHAUSTED`, `EXTERNAL_DEPENDENCY`, `NOT_EXECUTED`입니다.

## 테스트

Harness 단위 테스트는 다음 명령으로 실행합니다.

```powershell
pytest tests\harness
```

전체 기본 테스트는 다음 명령을 사용합니다.

```powershell
pytest
```

Ollama 또는 Gemini API를 실제로 호출하는 command는 로컬 모델 설치와 `.env` 설정이 필요합니다.

## 트러블슈팅

### 모델이 실행되지 않는 경우

```powershell
ollama list
python -m harness.cli list-models --check-installed
```

`configs/models.yaml`의 `model_tag`와 `ollama list`의 이름이 일치하는지 확인합니다.

### Dataset 파일을 찾지 못하는 경우

```powershell
python -m harness.cli prepare-datasets
```

processed dataset이 없거나 registry path가 바뀐 경우 먼저 dataset을 준비합니다.

### Gemini judge가 skipped 되는 경우

`.env`에 `GEMINI_API_KEY`가 설정되어 있는지 확인합니다. judge model 이름이 실제 Gemini API에서 지원되지 않으면 `400 Bad Request`가 발생할 수 있습니다.

### Parser error가 발생하는 경우

MileDay smoke test에서는 설명문과 fenced JSON이 모두 필요합니다. JSON block이 없거나, fenced JSON 내부가 `json.loads()` 불가능한 형식이면 `PARSER_ERROR` 또는 `invalid`로 기록됩니다.

### 실행 시간이 긴 경우

`run-benchmark`는 `모델 수 * dataset 수 * limit`만큼 Ollama inference를 수행합니다. 1차 비교는 작은 `--limit`으로 실행한 뒤 후보를 줄이고, 2차 평가에서 `--limit 50` 이상으로 확장하는 방식이 적합합니다.
