# 스토리 완료 보고서

## 스토리

- ID: EVAL-002
- 제목: 모델 레지스트리
- 최종 상태: done

## 기준 문서

- `AGENTS.md`
- `docs/codex_rules.md`
- 스토리: `_bmad-output/implementation-artifacts/stories/EVAL-002-model-registry.md`
- 지원 문서:
  - `_bmad-output/planning-artifacts/product-brief.md`
  - `_bmad-output/planning-artifacts/prd.md`
  - `_bmad-output/planning-artifacts/architecture.md`
  - `docs/decisions/0001-use-ollama-as-default-runtime.md`

## 요약

5개 로컬 모델 후보를 관리하는 YAML 기반 모델 레지스트리를 추가했다. 필수 필드와 중복 검증, Ollama model tag 기반 설치 여부 확인, `list-models` CLI 명령도 함께 추가했다.

## 변경 파일

- `configs/models.yaml`: 평가 전에 교체해야 하는 placeholder tag를 가진 5개 모델 후보를 추가했다.
- `harness/model_registry.py`: registry schema, YAML loading, validation, Ollama list parsing, availability check를 추가했다.
- `harness/cli.py`: 선택적으로 `--check-installed`를 받을 수 있는 `list-models` 명령을 추가했다.
- `tests/harness/test_model_registry.py`: registry validation, parsing, missing model behavior 테스트를 추가했다.
- `tests/harness/test_cli.py`: `list-models` CLI smoke test를 추가했다.
- `requirements.txt`: `PyYAML` 의존성을 명시적으로 추가했다.
- `_bmad-output/implementation-artifacts/stories/EVAL-002-model-registry.md`: AC 완료와 Story done 상태를 반영했다.
- `_bmad-output/implementation-artifacts/sprint-status.yaml`: EVAL-002를 done으로 표시했다.

## 실행한 명령

```text
pytest tests/harness/test_model_registry.py
python -m harness.cli list-models
pytest
pytest tests/harness/test_model_registry.py --no-cov
```

## 검증 결과

| 검증 | 결과 | 근거 |
|---|---|---|
| Backend tests | PASS | `pytest`: 89 passed, 1 deselected, coverage 94.83%. |
| Frontend audit | NOT_EXECUTED | 이 Story는 frontend 파일을 변경하지 않았다. |
| Frontend tests | NOT_EXECUTED | 이 Story는 frontend 파일을 변경하지 않았다. |
| Frontend lint | NOT_EXECUTED | 이 Story는 frontend 파일을 변경하지 않았다. |
| Frontend build | NOT_EXECUTED | 이 Story는 frontend 파일을 변경하지 않았다. |
| Story model registry test | FAIL | `pytest tests/harness/test_model_registry.py`는 6개 테스트가 통과한 뒤, 당시 전역 `pytest.ini`의 backend coverage gate 때문에 실패했다. |
| Story model registry test without backend coverage | PASS | `pytest tests/harness/test_model_registry.py --no-cov`: 6 passed. |
| Story CLI smoke test | PASS | `python -m harness.cli list-models`가 5개 후보를 `installed=not_checked`로 출력했다. |

## 인수 조건

- [x] 5개 모델이 YAML로 관리된다: `configs/models.yaml`에 정확히 5개 후보가 있다.
- [x] 모델 tag가 코드에 하드코딩되지 않는다: `load_model_registry`가 YAML에서 model tag를 로드한다.
- [x] 필수 필드 누락 시 명확한 validation error가 발생한다: Pydantic validation이 필드 단위 오류를 발생시키며 테스트로 검증했다.
- [x] 설치된 모델 여부를 확인할 수 있다: `check_model_availability`와 `list-models --check-installed`가 설정된 tag와 Ollama tag를 비교한다.
- [x] 누락 모델은 자동 대체되지 않는다: availability는 각 `model_tag`를 유지하면서 `installed=false`를 반환한다.

## 산출물

- `_bmad-output/implementation-artifacts/completion-reports/EVAL-002-model-registry.md`

## 실패/미실행 항목

- 분류: CONFIG_ERROR
- 설명: 당시 정확한 Story 명령 `pytest tests/harness/test_model_registry.py`가 repository-level backend coverage 설정과 충돌했다.
- 재현: 기존 coverage gate 설정 상태에서 `pytest tests/harness/test_model_registry.py`를 실행한다.
- 권장 조치: harness 전용 test profile을 사용하거나 harness-only targeted test에는 coverage gate를 분리한다.

## 알려진 위험

- `configs/models.yaml`은 명시적 placeholder model tag를 사용한다. benchmark 또는 runtime Story 실행 전 실제 local Ollama tag로 교체해야 한다.
- `--check-installed`는 local `ollama` 실행 파일과 사용 가능한 Ollama 설치가 필요하다. 기본 `list-models` 명령은 오프라인으로 동작한다.

## 후속 작업

- 다음으로 EVAL-003 Ollama Streaming Runtime을 구현한다.
