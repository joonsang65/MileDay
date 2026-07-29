# Story Completion Report

## Story

- ID: EVAL-009
- Title: IFEval-Ko Adapter
- Final Status: done

## Source Documents

- `AGENTS.md`
- `docs/codex_rules.md`
- Story: `_bmad-output/implementation-artifacts/stories/EVAL-009-ifeval-ko-adapter.md`
- Supporting documents:
  - `_bmad-output/planning-artifacts/product-brief.md`
  - `_bmad-output/planning-artifacts/prd.md`
  - `_bmad-output/planning-artifacts/architecture.md`
  - `_bmad-output/planning-artifacts/epics.md`
  - `_bmad-output/planning-artifacts/schemas.md`
  - `_bmad-output/implementation-artifacts/sprint-status.yaml`
  - `_bmad-output/implementation-artifacts/completion-reports/dataset-setup-inspection.md`
  - `_bmad-output/implementation-artifacts/completion-reports/dataset-processed-smoke.md`
  - `docs/decisions/0002-separate-official-and-generation-evaluation.md`
  - `docs/decisions/0003-preserve-raw-model-output.md`

## Summary

IFEval-Ko adapter를 공식 evaluator 기반으로 업데이트했다. `lm-eval`, `langdetect`, `immutabledict` 라이브러리를 추가했고, adapter는 IFEval-Ko 공식 `process_results` evaluator를 통해 instruction-following 결과를 산출한다.

## Changed Files

- `requirements.txt`: IFEval-Ko 공식 evaluator 실행에 필요한 라이브러리를 추가했다.
- `harness/benchmarks/ifeval_ko.py`: IFEval-Ko case, mapping, loader, 공식 evaluator 연결, aggregate report를 추가했다.
- `tests/harness/benchmarks/test_ifeval_ko.py`: offline fixture 기반 loader, mapping, error category, raw output preservation, 공식 evaluator scoring 테스트를 추가했다.
- `tests/fixtures/benchmarks/ifeval_ko/synthetic.jsonl`: IFEval-Ko synthetic fixture 2건을 추가했다.
- `_bmad-output/implementation-artifacts/stories/EVAL-009-ifeval-ko-adapter.md`: AC 완료와 Story done 상태를 반영했다.
- `_bmad-output/implementation-artifacts/sprint-status.yaml`: EVAL-009를 done으로 표시했다.
- `_bmad-output/implementation-artifacts/completion-reports/EVAL-009-ifeval-ko-adapter.md`: 완료 증거를 기록했다.

## Commands Run

```text
python -m pip install lm-eval==0.4.12
python -m pip install langdetect==1.0.9
python -m pip install immutabledict==4.2.1
python -c "from pathlib import Path; import lm_eval.tasks; lm_eval.tasks.__path__.append(str(Path('datasets/ifeval-ko/54199e3801116897697babf341865741dcd06fc8/source').resolve())); from lm_eval.tasks.ifeval_ko import utils; print(utils.process_results({'key':1,'instruction_id_list':['punctuation:no_comma'],'prompt':'Avoid commas.','kwargs':[{}]}, ['No comma here']))"
pytest tests/harness/benchmarks/test_ifeval_ko.py
pytest
pytest -c pytest-backend.ini
```

## Verification Results

| Verification | Result | Evidence |
|---|---|---|
| Official evaluator check | PASS | 공식 IFEval-Ko `process_results` evaluator 호출이 성공했다. |
| Story smoke test | PASS | `pytest tests/harness/benchmarks/test_ifeval_ko.py`: 12 passed. |
| Default tests | PASS | `pytest`: 156 passed, 1 deselected. |
| Backend coverage | PASS | `pytest -c pytest-backend.ini`: 156 passed, 1 deselected, coverage 94.83%. |

## Acceptance Criteria

- [x] IFEval-Ko adapter package/module exists under `harness/benchmarks/`: `harness/benchmarks/ifeval_ko.py`를 추가했다.
- [x] Adapter loads versioned local fixture or processed files without network access: JSONL/CSV loader와 synthetic JSONL fixture 테스트를 추가했다.
- [x] Source-to-internal field mapping is explicit and based on inspected local fixture/source shape: processed shape 기본 mapping과 raw source shape용 custom mapping 테스트를 추가했다.
- [x] Adapter does not infer, rename, fabricate, or silently coerce missing IFEval-Ko dataset fields: missing mapped field와 unsupported row를 `DATASET_SCHEMA_CHANGED`로 실패시킨다.
- [x] The Story implementation documents that the official local evaluator is used for IFEval-Ko scoring: 공식 evaluator 연결을 구현했고 해당 evaluator로 평가한다.
- [x] Adapter does not assume IFEval-Ko is MCQ; MCQ primitives are reused only if the inspected source shape actually requires them: MCQ module을 사용하지 않고 prompt를 그대로 반환한다.
- [x] Unsupported source rows fail clearly with `DATASET_SCHEMA_CHANGED`: unsupported row 테스트를 추가했다.
- [x] Missing files or unreadable dataset paths are reported with `DATASET_UNAVAILABLE`: missing file 테스트를 추가했다.
- [x] Raw model outputs remain available to downstream result storage and are not overwritten by parsed or judged outputs: `IFEvalKoCaseResult.raw_output` 보존 테스트를 추가했다.
- [x] Offline fixture tests cover valid rows, explicit mapping, missing required fields, unsupported row shape, invalid JSONL, and official evaluator invocation behavior: `tests/harness/benchmarks/test_ifeval_ko.py`에 해당 case들을 추가했다.

## Generated Artifacts

- `tests/fixtures/benchmarks/ifeval_ko/synthetic.jsonl`
- `_bmad-output/implementation-artifacts/completion-reports/EVAL-009-ifeval-ko-adapter.md`

## Failures / Not Executed Items

- 없음.

## Known Risks

- 공식 evaluator source snapshot은 로컬 dataset source 경로에 있어야 한다.
- IFEval-Ko 전체 run은 EVAL-009 범위 밖이므로 실행하지 않았다.

## Follow-Up Work

- EVAL-010 MileDay dataset schema를 구현한다.
