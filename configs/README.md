# Configs

`configs/`는 현재 harness에서 로컬 Ollama 후보 모델 registry만 관리합니다.
flash-lite API 테스트는 모델을 코드 상수로 고정하므로 별도 config 파일을 사용하지 않습니다.

## 파일

```text
configs/
  models.yaml
```

| 파일 | 역할 |
|---|---|
| `models.yaml` | 로컬 Ollama 후보 모델 목록, model tag, context window, quantization, license note |

## 확인 명령

```powershell
python -m harness.cli list-models
python -m harness.cli list-models --check-installed
```

## 수정 기준

- 모델 tag나 license는 추측해서 넣지 않습니다.
- flash-lite API 모델은 `configs/models.yaml`에 등록하지 않습니다.
- `configs/` 변경 후에는 최소 `pytest tests\harness`를 실행합니다.
