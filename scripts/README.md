# Scripts

`scripts/`는 개발 실행, 성능 측정, 공개 benchmark dataset 준비를 위한 보조 스크립트를 모아 둔 디렉터리입니다.

제품 코드의 핵심 로직은 이곳에 두지 않습니다. 반복 실행이 필요한 개발/평가 작업을 자동화하는 용도로 사용합니다.

## 파일

| 파일 | 역할 |
|---|---|
| `dev.ps1` | backend health check 후 frontend/Electron 개발 환경 실행 |
| `perf.ps1` | frontend 성능 측정 script 실행 보조 |
| `download_public_benchmarks.py` | Hugging Face 공개 benchmark dataset snapshot 다운로드 |
| `inspect_public_benchmarks.py` | 공개 dataset 구조, row 수, field 확인 |
| `smoke_processed_benchmarks.py` | processed benchmark artifact가 scorer에서 읽히는지 빠르게 확인 |

## 개발 실행

루트에서 실행합니다.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\dev.ps1
```

이 스크립트는 backend `/health`, `/health/db` 상태를 확인하고 frontend 개발 서버 실행을 돕습니다. Supabase 설정이 잘못되어 있으면 DB health check 단계에서 실패할 수 있습니다.

## 성능 측정

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\perf.ps1
```

Frontend package script에 등록된 성능 측정 명령을 실행하는 보조 script입니다. 테스트 데이터 cleanup이 필요한 경우 `frontend`의 `perf:cleanup` 명령도 함께 확인합니다.

## 공개 Benchmark Dataset 작업

일반적으로는 harness CLI를 우선 사용합니다.

```powershell
python -m harness.cli prepare-datasets
```

`scripts/download_public_benchmarks.py`와 `scripts/inspect_public_benchmarks.py`는 dataset setup을 조사하거나 수동 점검할 때 사용합니다.

예:

```powershell
python scripts\inspect_public_benchmarks.py
python scripts\download_public_benchmarks.py
```

네트워크가 필요한 작업은 로컬 환경에서 직접 실행해야 합니다. Codex sandbox에서는 network가 제한될 수 있습니다.

## Smoke 확인

processed benchmark 데이터가 adapter/scorer에서 읽히는지 빠르게 확인할 때:

```powershell
python scripts\smoke_processed_benchmarks.py
```

이 검사는 실제 Ollama 모델 추론이 아니라 데이터셋 처리 결과의 기본 구조 확인에 가깝습니다.

## 수정 기준

- 반복 실행이 필요한 개발 작업만 script로 분리합니다.
- 제품 runtime 경로에 들어가야 할 로직을 scripts에 숨기지 않습니다.
- PowerShell script는 Windows 개발 환경을 기준으로 작성합니다.
- dataset 처리 흐름을 바꿀 때는 `harness/` 구현과 `tests/harness`를 함께 확인합니다.
- 외부 API key나 DB secret을 script에 직접 쓰지 않습니다.
