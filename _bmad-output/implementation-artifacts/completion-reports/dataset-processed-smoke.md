# Dataset Processed Smoke Report

## 요약

Pinned source snapshot을 `configs/datasets.yaml` 기준으로 processed JSONL로 변환하는 경로를 추가했다. 4개 benchmark 모두 `--sample-limit 5` 기준 processed 파일을 생성했고, MCQ 3종은 기존 benchmark adapter가 실제 processed 파일을 로드하는 smoke test까지 통과했다.

## 변경 파일

- `harness/dataset_registry.py`: `configs/datasets.yaml` 로더와 validation schema 추가.
- `harness/dataset_processor.py`: KMMLU-Pro, KoBALT-700, CLIcK, IFEval-Ko source-to-processed 변환기 추가.
- `harness/cli.py`: `prepare-datasets` CLI 명령 추가.
- `tests/harness/test_dataset_registry.py`: dataset registry validation 테스트 추가.
- `tests/harness/test_dataset_processor.py`: answer/choice normalization 단위 테스트 추가.
- `scripts/smoke_processed_benchmarks.py`: processed JSONL adapter smoke test 스크립트 추가.
- `_bmad-output/implementation-artifacts/completion-reports/dataset-processed-smoke.md`: 완료 증거 기록.

## 실행 명령

```text
pytest tests\harness\test_dataset_registry.py tests\harness\test_dataset_processor.py tests\harness\test_cli.py
python -m harness.cli prepare-datasets --dataset ifeval_ko --sample-limit 5
python -m harness.cli prepare-datasets --sample-limit 5
python scripts\smoke_processed_benchmarks.py
pytest tests\harness\test_dataset_registry.py tests\harness\test_dataset_processor.py tests\harness\test_cli.py tests\harness\benchmarks\test_kmmlu_pro.py tests\harness\benchmarks\test_kobalt_700.py tests\harness\benchmarks\test_click_adapter.py
python -m py_compile scripts\smoke_processed_benchmarks.py scripts\download_public_benchmarks.py scripts\inspect_public_benchmarks.py harness\dataset_registry.py harness\dataset_processor.py harness\cli.py
```

## 검증 결과

| 검증 | 결과 | 근거 |
|---|---|---|
| Dataset registry tests | PASS | registry/validation 테스트 포함 10개 테스트 통과. |
| Processed generation smoke | PASS | 4개 dataset 모두 sample 5개 processed JSONL 생성. |
| Adapter load smoke | PASS | `scripts\smoke_processed_benchmarks.py`가 `kmmlu_pro`, `kobalt`, `click`, `ifeval_ko` 각각 5건을 확인. |
| Existing adapter tests | PASS | MCQ adapter 관련 테스트 포함 34개 테스트 통과. |
| Python compile | PASS | 변경 Python 파일 compile 성공. |

## 생성된 processed 샘플

```text
datasets/kmmlu-pro/e1567939724a369e428e66f15472562c55a5d181/processed/data.jsonl
datasets/kobalt-700/30c30a431066508e6bef77cfa6d6059b85b12f0d/processed/data.jsonl
datasets/click/d61627859645b5e6edc03fd9f835735d8226fa4e/processed/data.jsonl
datasets/ifeval-ko/54199e3801116897697babf341865741dcd06fc8/processed/data.jsonl
```

`processed/`는 재생성 가능한 산출물이므로 `.gitignore` 정책에 따라 Git 추적 대상이 아니다.

## 실패/미실행 항목

- 분류: NOT_EXECUTED
- 설명: 전체 row 변환은 아직 실행하지 않았다. 이번 단계는 smoke 범위로 `--sample-limit 5`만 생성했다.
- 권장 조치: 다음 단계에서 전체 변환을 실행하고 row count를 manifest의 selected split row count와 비교한다.

- 분류: NOT_EXECUTED
- 설명: IFEval-Ko deterministic verifier와 Gemini judge 보조 평가는 아직 구현하지 않았다.
- 권장 조치: IFEval-Ko Story에서 official evaluator import/path를 검토한 뒤 deterministic verifier를 우선 연결하고 Gemini judge는 보조 판정 계층으로 분리한다.

## 알려진 위험

- KMMLU-Pro 원본 첫 출력이 콘솔 encoding에서 깨져 보일 수 있으나, 변환은 UTF-8 파일 입출력으로 처리한다.
- KoBALT-700 choices는 `Question` 본문 내 `A:`~`J:` 라벨을 정규식으로 파싱한다. 공식 schema가 문항별로 다른 라벨 형식을 포함하면 `DATASET_SCHEMA_CHANGED`로 실패해야 한다.
- CLIcK answer는 choice text와 정확히 일치해야 label로 정규화된다. 부분 일치나 유사도 기반 보정은 하지 않는다.
- IFEval-Ko는 이번 단계에서 prompt/instruction/kwargs 보존까지만 수행했다.
