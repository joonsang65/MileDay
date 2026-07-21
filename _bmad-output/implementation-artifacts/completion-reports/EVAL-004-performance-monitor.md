# 스토리 완료 보고서

## 스토리

- ID: EVAL-004
- 제목: Performance Monitor
- 최종 상태: done

## 기준 문서

- `AGENTS.md`
- `docs/codex_rules.md`
- 스토리: `_bmad-output/implementation-artifacts/stories/EVAL-004-performance-monitor.md`
- 지원 문서:
  - `_bmad-output/planning-artifacts/prd.md`
  - `_bmad-output/planning-artifacts/architecture.md`

## 요약

harness run을 위한 configurable performance monitor를 추가했다. CPU/RAM sampling, Ollama RSS sampling, optional NVML VRAM sampling, 명확한 NVML degradation metadata, peak metric aggregation, mock 기반 단위 테스트를 포함한다.

## 변경 파일

- `harness/performance/__init__.py`: performance package marker를 추가했다.
- `harness/performance/monitor.py`: monitor config, sample/peak model, psutil 기반 system/RSS sampling, optional NVML VRAM sampling, peak summary 계산을 추가했다.
- `tests/harness/performance/test_monitor.py`: interval validation, RAM sampling, Ollama RSS, VRAM, NVML degradation, peak metric 테스트를 추가했다.
- `requirements.txt`: `psutil` 의존성을 명시적으로 추가했다.
- `_bmad-output/implementation-artifacts/stories/EVAL-004-performance-monitor.md`: AC 완료와 Story done 상태를 반영했다.
- `_bmad-output/implementation-artifacts/sprint-status.yaml`: EVAL-004를 done으로 표시했다.

## 실행한 명령

```text
pytest tests/harness/performance/test_monitor.py
pytest tests/harness/performance/test_monitor.py --no-cov
pytest
```

## 검증 결과

| 검증 | 결과 | 근거 |
|---|---|---|
| Backend tests | PASS | `pytest`: 102 passed, 1 deselected, coverage 94.83%. |
| Frontend audit | NOT_EXECUTED | 이 Story는 frontend 파일을 변경하지 않았다. |
| Frontend tests | NOT_EXECUTED | 이 Story는 frontend 파일을 변경하지 않았다. |
| Frontend lint | NOT_EXECUTED | 이 Story는 frontend 파일을 변경하지 않았다. |
| Frontend build | NOT_EXECUTED | 이 Story는 frontend 파일을 변경하지 않았다. |
| Story performance test | FAIL | `pytest tests/harness/performance/test_monitor.py`는 6개 테스트가 통과한 뒤, 당시 전역 `pytest.ini`의 backend coverage gate 때문에 실패했다. |
| Story performance test without backend coverage | PASS | `pytest tests/harness/performance/test_monitor.py --no-cov`: 6 passed. |

## 인수 조건

- [x] System RAM usage가 sampling된다: `sample_system_usage`가 `psutil.virtual_memory`를 통해 RAM used bytes와 RAM percent를 반환한다.
- [x] Ollama process RSS가 가능한 경우 sampling된다: `sample_process_rss`가 matching Ollama process RSS를 합산하고 없으면 `None`을 반환한다.
- [x] VRAM이 가능한 경우 NVML을 통해 sampling된다: `sample_nvml_vram`이 `pynvml`로 device별 VRAM usage를 합산한다.
- [x] NVML 누락은 unit test 실패 없이 명확히 degrade된다: NVML import/init/device 실패가 `vram_status="unavailable"`와 `vram_error`를 반환한다.
- [x] Peak metrics가 계산된다: `PerformanceMonitor.summarize`가 peak CPU, RAM, Ollama RSS, VRAM을 계산한다.
- [x] Sample interval은 100ms~250ms로 설정 가능하다: `PerformanceMonitorConfig.sample_interval_ms`가 `ge=100`, `le=250`을 검증한다.

## 산출물

- `_bmad-output/implementation-artifacts/completion-reports/EVAL-004-performance-monitor.md`

## 실패/미실행 항목

- 분류: CONFIG_ERROR
- 설명: 당시 정확한 Story 명령 `pytest tests/harness/performance/test_monitor.py`가 repository-level backend coverage 설정과 충돌했다.
- 재현: 기존 coverage gate 설정 상태에서 `pytest tests/harness/performance/test_monitor.py`를 실행한다.
- 권장 조치: harness 전용 test profile을 사용하거나 harness-only targeted test에는 coverage gate를 분리한다.

## 알려진 위험

- NVML 지원은 optional이며 local NVIDIA driver/NVML availability에 의존한다.
- 새 환경에서는 `requirements.txt`의 `psutil` 설치가 필요하다.
- monitor는 sample과 peak만 기록한다. EVAL-004는 full benchmark run orchestration에 sampling을 연결하지 않는다.

## 후속 작업

- 추가 harness-only targeted Story 명령을 안정적으로 실행할 수 있도록 pytest coverage profile을 분리하거나, targeted test에는 별도 profile을 사용한다.
