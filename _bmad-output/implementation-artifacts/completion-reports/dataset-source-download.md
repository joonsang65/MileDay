# Dataset Source Download Report

## 요약

공개 벤치마크 4종의 Hugging Face revision을 고정한 상태로 원본 snapshot을 다운로드하고, 각 revision별 `dataset_manifest.json`을 생성했다. 원본 `source/` 디렉터리는 Git에서 제외하고, manifest와 mapping config는 추적 가능하게 유지했다.

## 환경

- Python: 3.11.5
- datasets: 5.0.0
- huggingface_hub: 1.24.0
- fsspec: 2026.4.0
- Hugging Face account: `NJS0125`
- Token exposed: No

## 다운로드 결과

| Benchmark | Dataset ID | Revision | Source Path | Manifest |
|---|---|---|---|---|
| KMMLU-Pro | `LGAI-EXAONE/KMMLU-Pro` | `e1567939724a369e428e66f15472562c55a5d181` | `datasets/kmmlu-pro/e1567939724a369e428e66f15472562c55a5d181/source/` | `datasets/kmmlu-pro/e1567939724a369e428e66f15472562c55a5d181/dataset_manifest.json` |
| KoBALT-700 | `snunlp/KoBALT-700` | `30c30a431066508e6bef77cfa6d6059b85b12f0d` | `datasets/kobalt-700/30c30a431066508e6bef77cfa6d6059b85b12f0d/source/` | `datasets/kobalt-700/30c30a431066508e6bef77cfa6d6059b85b12f0d/dataset_manifest.json` |
| CLIcK | `EunsuKim/CLIcK` | `d61627859645b5e6edc03fd9f835735d8226fa4e` | `datasets/click/d61627859645b5e6edc03fd9f835735d8226fa4e/source/` | `datasets/click/d61627859645b5e6edc03fd9f835735d8226fa4e/dataset_manifest.json` |
| IFEval-Ko | `allganize/IFEval-Ko` | `54199e3801116897697babf341865741dcd06fc8` | `datasets/ifeval-ko/54199e3801116897697babf341865741dcd06fc8/source/` | `datasets/ifeval-ko/54199e3801116897697babf341865741dcd06fc8/dataset_manifest.json` |

## 변경 파일

- `.gitignore`: dataset source, processed, evaluator 디렉터리 제외 규칙 추가.
- `configs/datasets.yaml`: 실제 inspection 결과 기반 dataset ID, revision, config, split, source field mapping 기록.
- `scripts/download_public_benchmarks.py`: pinned revision snapshot 다운로드 및 manifest 생성 스크립트 추가.
- `datasets/*/*/dataset_manifest.json`: dataset별 manifest 생성.
- `_bmad-output/implementation-artifacts/completion-reports/dataset-source-download.md`: 다운로드 완료 증거 기록.

## 실행 명령

```text
python scripts\download_public_benchmarks.py
Get-ChildItem -Recurse -Filter dataset_manifest.json datasets | ForEach-Object { Get-Content $_.FullName | ConvertFrom-Json | Select-Object dataset_key,dataset_id,revision,selected_config,selected_split }
python -m py_compile scripts\inspect_public_benchmarks.py scripts\download_public_benchmarks.py
git diff --check
```

## 검증 결과

| 검증 | 결과 | 근거 |
|---|---|---|
| Snapshot download | PASS | 4개 benchmark 모두 source path와 manifest path가 출력됐다. |
| Manifest JSON parse | PASS | 4개 `dataset_manifest.json` 모두 `ConvertFrom-Json`으로 읽혔다. |
| Script compile | PASS | `py_compile` 성공. |
| Git ignore | PASS | `datasets/*/*/source/`가 ignored로 표시되고 manifest는 추적 가능 상태다. |
| Whitespace check | PASS | `git diff --check`는 CRLF 경고 외 오류 없음. |

## 실패/미실행 항목

- 분류: NOT_EXECUTED
- 설명: `processed/` 생성과 adapter smoke test는 아직 실행하지 않았다.
- 재현: 실제 source schema가 기존 synthetic adapter schema와 다르다.
- 권장 조치: 다음 Story에서 source-to-processed 변환기와 실제 schema 기반 smoke test를 구현한다.

## 알려진 위험

- KMMLU-Pro: gated, `cc-by-nc-nd-4.0`.
- KoBALT-700: `cc-by-nc-4.0`.
- CLIcK: license가 `unknown`으로 남아 commercial use verified가 아니다.
- IFEval-Ko: dataset은 `apache-2.0`이나 official evaluator 연결은 별도 검토가 필요하다.
- Windows Hugging Face cache symlink warning으로 cache 공간 사용량이 증가할 수 있다.

## 후속 작업

- `configs/datasets.yaml`을 읽는 dataset registry/loader 추가.
- 실제 HF source schema를 common processed schema로 변환하는 processor 추가.
- KMMLU-Pro `options` list와 `solution` 숫자 답안을 A-E label로 정규화.
- KoBALT-700 `Question` 내부 선택지를 A-J choices로 파싱.
- CLIcK `choices` list와 answer 문자열을 label answer로 정규화.
- IFEval-Ko deterministic verifier + Gemini judge 보조 방식 설계.
