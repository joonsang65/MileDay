# 스토리 완료 보고서

## 스토리

- ID: EVAL-003
- 제목: Ollama Streaming Runtime
- 최종 상태: done

## 기준 문서

- `AGENTS.md`
- `docs/codex_rules.md`
- 스토리: `_bmad-output/implementation-artifacts/stories/EVAL-003-ollama-streaming-runtime.md`
- 지원 문서:
  - `_bmad-output/planning-artifacts/prd.md`
  - `_bmad-output/planning-artifacts/architecture.md`
  - `docs/decisions/0001-use-ollama-as-default-runtime.md`

## 요약

공통 runtime interface와 Ollama streaming adapter를 추가했다. normalized chunk, TTFT/총 latency 측정, metadata 보존, runtime error 분류, mock 기반 단위 테스트를 포함한다.

## 변경 파일

- `harness/runtime/__init__.py`: runtime package marker를 추가했다.
- `harness/runtime/base.py`: runtime request, chunk, response, adapter protocol, adapter error type을 추가했다.
- `harness/runtime/ollama.py`: streaming Ollama adapter, health check, NDJSON parsing, timing, metadata preservation, error categorization을 추가했다.
- `harness/cli.py`: `preflight --check-ollama` 지원을 추가했다.
- `tests/harness/runtime/test_ollama.py`: mock 기반 streaming, metrics, metadata, timeout, HTTP, missing model, parser 테스트를 추가했다.
- `tests/harness/test_cli.py`: `preflight --check-ollama`에 대한 mocked CLI coverage를 추가했다.
- `_bmad-output/implementation-artifacts/stories/EVAL-003-ollama-streaming-runtime.md`: AC 완료와 Story done 상태를 반영했다.
- `_bmad-output/implementation-artifacts/sprint-status.yaml`: EVAL-003을 done으로 표시했다.

## 실행한 명령

```text
pytest tests/harness/runtime/test_ollama.py
python -m harness.cli preflight --check-ollama
pytest tests/harness/runtime/test_ollama.py --no-cov
pytest
```

## 검증 결과

| 검증 | 결과 | 근거 |
|---|---|---|
| Backend tests | PASS | `pytest`: 96 passed, 1 deselected, coverage 94.83%. |
| Frontend audit | NOT_EXECUTED | 이 Story는 frontend 파일을 변경하지 않았다. |
| Frontend tests | NOT_EXECUTED | 이 Story는 frontend 파일을 변경하지 않았다. |
| Frontend lint | NOT_EXECUTED | 이 Story는 frontend 파일을 변경하지 않았다. |
| Frontend build | NOT_EXECUTED | 이 Story는 frontend 파일을 변경하지 않았다. |
| Story runtime test | FAIL | `pytest tests/harness/runtime/test_ollama.py`는 6개 테스트가 통과한 뒤, 당시 전역 `pytest.ini`의 backend coverage gate 때문에 실패했다. |
| Story runtime test without backend coverage | PASS | `pytest tests/harness/runtime/test_ollama.py --no-cov`: 6 passed. |
| Story CLI smoke test | PASS | `python -m harness.cli preflight --check-ollama`가 `ollama_status=ok`와 `status=ok`를 출력했다. |

## 인수 조건

- [x] 공통 runtime interface가 존재한다: `harness/runtime/base.py`가 `RuntimeAdapter`, `RuntimeRequest`, `RuntimeChunk`, `RuntimeResponse`를 정의한다.
- [x] Streaming response를 지원한다: `OllamaRuntime.stream`이 Ollama streaming NDJSON을 normalized chunk로 반환한다.
- [x] TTFT가 기록된다: `OllamaRuntime.generate`가 첫 non-empty token 시간을 `RuntimeMetrics.ttft_ms`에 기록한다.
- [x] 총 latency가 기록된다: `OllamaRuntime.generate`가 전체 elapsed time을 `RuntimeMetrics.latency_ms`에 기록한다.
- [x] Ollama token/duration metadata가 보존된다: `total_duration`, `eval_count`, `eval_duration` 같은 최종 stream metadata를 유지한다.
- [x] Timeout과 HTTP error가 분류된다: timeout은 `TIMEOUT`, HTTP 500은 `EXTERNAL_DEPENDENCY`, HTTP 404는 `MODEL_NOT_INSTALLED`로 매핑된다.
- [x] Mock 기반 단위 테스트가 존재한다: `tests/harness/runtime/test_ollama.py`가 `httpx.MockTransport`를 사용한다.

## 산출물

- `_bmad-output/implementation-artifacts/completion-reports/EVAL-003-ollama-streaming-runtime.md`

## 실패/미실행 항목

- 분류: CONFIG_ERROR
- 설명: 당시 정확한 Story 명령 `pytest tests/harness/runtime/test_ollama.py`가 repository-level backend coverage 설정과 충돌했다.
- 재현: 기존 coverage gate 설정 상태에서 `pytest tests/harness/runtime/test_ollama.py`를 실행한다.
- 권장 조치: harness 전용 test profile을 사용하거나 harness-only targeted Story 명령에는 coverage gate를 분리한다.

## 알려진 위험

- `preflight --check-ollama`는 local Ollama availability만 확인하며 model inference를 실행하지 않는다.
- 실제 model 실행은 `configs/models.yaml`의 model tag와 설치된 Ollama model에 의존한다.

## 후속 작업

- 다음으로 EVAL-005 Common MCQ Adapter를 구현하거나, 더 많은 harness-only Story 전에 pytest coverage profile을 분리한다.
