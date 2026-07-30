# Configs

`configs/`는 harness가 사용할 모델과 데이터셋 registry를 관리하는 디렉터리입니다. CLI 명령은 이 YAML 파일을 읽어 어떤 모델을 실행할지, 어떤 데이터셋을 준비하고 평가할지 결정합니다.

제품 backend/frontend 설정은 이곳이 아니라 `.env`, `backend/app/core/config.py`, `frontend/.env` 계층에서 관리합니다.

## 파일

```text
configs/
  models.yaml
  datasets.yaml
```

| 파일 | 역할 |
|---|---|
| `models.yaml` | Ollama 후보 모델 목록, model tag, context window, quantization, license note |
| `datasets.yaml` | 공개 benchmark dataset의 Hugging Face id, revision, split, field mapping, license |

## `models.yaml`

후보 모델은 `models` 배열에 등록합니다.

```yaml
models:
  - id: candidate-3
    provider: ollama
    runtime: ollama
    model_tag: granite4.1:3b
    context_window: 131072
    quantization: Q4_K_M
    license_note: IBM Granite 4.1 3B instruct; Apache-2.0.
```

| 필드 | 설명 |
|---|---|
| `id` | CLI에서 사용하는 내부 모델 id. 예: `candidate-3` |
| `provider` | 모델 제공 방식. 현재는 `ollama` |
| `runtime` | 실행 adapter. 현재는 `ollama` |
| `model_tag` | `ollama run` 또는 Ollama API에서 사용하는 실제 모델명 |
| `context_window` | 모델 context window 참고값 |
| `quantization` | 로컬 모델 quantization 정보 |
| `license_note` | 평가/서비스 사용 전 확인해야 할 license 메모 |

모델을 추가한 뒤에는 다음 명령으로 registry와 로컬 설치 상태를 확인합니다.

```powershell
python -m harness.cli list-models --check-installed
```

## `datasets.yaml`

공개 benchmark dataset은 `datasets` mapping에 등록합니다.

```yaml
datasets:
  ifeval_ko:
    dataset_id: allganize/IFEval-Ko
    revision: 54199e3801116897697babf341865741dcd06fc8
    split: train
    fields:
      id: key
      prompt: prompt
```

| 필드 | 설명 |
|---|---|
| `dataset_id` | Hugging Face dataset id |
| `source_url` | 데이터셋 원본 페이지 |
| `official_repository` | 공식 repository 또는 evaluator 기준 |
| `revision` | 재현성을 위한 고정 revision |
| `config` | Hugging Face dataset config |
| `split` | 사용할 split |
| `license` | 데이터셋 license |
| `commercial_use_verified` | 상업 사용 가능 여부 확인 상태 |
| `fields` | 원본 column을 harness schema로 매핑하는 규칙 |

데이터셋을 수정한 뒤에는 processed artifact를 다시 생성합니다.

```powershell
python -m harness.cli prepare-datasets
```

샘플만 빠르게 확인하려면:

```powershell
python -m harness.cli prepare-datasets --sample-limit 5
```

## 수정 기준

- 모델 tag나 dataset revision은 추측해서 넣지 않습니다.
- 모델 license는 평가 목적과 서비스 목적을 분리해서 기록합니다.
- dataset revision을 바꾸면 기존 평가 결과와 직접 비교하기 어렵습니다.
- field mapping을 바꾸면 adapter와 scorer가 기대하는 schema도 함께 확인합니다.
- `configs/` 변경 후에는 최소 `pytest tests\harness`를 실행해 registry loader와 adapter 테스트가 깨지지 않는지 확인합니다.
