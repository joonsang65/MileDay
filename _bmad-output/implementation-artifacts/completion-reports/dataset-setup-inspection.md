# Dataset Setup Report

## Environment

- Python: 3.11.5
- datasets: 5.0.0
- huggingface_hub: 1.24.0
- fsspec: 2026.4.0
- Hugging Face account: logged in as `NJS0125`
- Token exposed: No
- Inspection time: 2026-07-21 KST

## KMMLU-Pro

- Access: OK, gated dataset with accepted access
- Dataset ID: `LGAI-EXAONE/KMMLU-Pro`
- Revision: `e1567939724a369e428e66f15472562c55a5d181`
- Config: `kmmlu_pro`
- Split: `test`
- Rows: 2822
- Columns: `question`, `options`, `solution`, `score`, `license_name`, `subject`, `year`, `round`, `session`
- Features:
  - `question`: string
  - `options`: list[string]
  - `solution`: string
  - `score`: float64
  - `license_name`: string
  - `subject`: string
  - `year`: int64
  - `round`: int64
  - `session`: int64
- License: `cc-by-nc-nd-4.0`
- Source path: NOT_EXECUTED, full snapshot download intentionally deferred
- Manifest path: NOT_EXECUTED, manifest will be generated after pinned source download
- Smoke test: NOT_EXECUTED, adapter source connection should be done after source download

## KoBALT-700

- Access: OK, public
- Dataset ID: `snunlp/KoBALT-700`
- Revision: `30c30a431066508e6bef77cfa6d6059b85b12f0d`
- Config: `kobalt_v1`
- Split: `raw`
- Rows: 700
- Columns: `ID`, `Class`, `Subclass`, `Question`, `Answer`, `Level`, `Sampling_YN`
- Features:
  - `ID`: string
  - `Class`: string
  - `Subclass`: string
  - `Question`: string
  - `Answer`: string
  - `Level`: int64
  - `Sampling_YN`: int64
- License: `cc-by-nc-4.0`
- Source path: NOT_EXECUTED, full snapshot download intentionally deferred
- Manifest path: NOT_EXECUTED, manifest will be generated after pinned source download
- Smoke test: NOT_EXECUTED, adapter source connection should be done after source download

## CLIcK

- Access: OK, public
- Dataset ID: `EunsuKim/CLIcK`
- Revision: `d61627859645b5e6edc03fd9f835735d8226fa4e`
- Config: `default`
- Split: `train`
- Rows: 1995
- Columns: `id`, `paragraph`, `question`, `choices`, `answer`
- Features:
  - `id`: string
  - `paragraph`: string
  - `question`: string
  - `choices`: list[string]
  - `answer`: string
- License: `unknown`
- Source path: NOT_EXECUTED, full snapshot download intentionally deferred
- Manifest path: NOT_EXECUTED, manifest will be generated after pinned source download
- Smoke test: NOT_EXECUTED, adapter source connection should be done after source download

## IFEval-Ko

- Access: OK, public
- Dataset ID: `allganize/IFEval-Ko`
- Revision: `54199e3801116897697babf341865741dcd06fc8`
- Config: `default`
- Split: `train`
- Rows: 342
- Columns: `key`, `prompt`, `instruction_id_list`, `kwargs`
- Features:
  - `key`: int64
  - `prompt`: string
  - `instruction_id_list`: list[string]
  - `kwargs`: list[object]
- License: `apache-2.0`
- Evaluator path: NOT_EXECUTED, official evaluator source review deferred to IFEval-Ko implementation story
- Source path: NOT_EXECUTED, full snapshot download intentionally deferred
- Manifest path: NOT_EXECUTED, manifest will be generated after pinned source download
- Smoke test: NOT_EXECUTED, adapter source connection should be done after source download

## Field Mapping Candidates

These mappings are based on actual inspected schemas. They should be moved into a dataset mapping config only when the source snapshots and manifests are generated.

```yaml
datasets:
  kmmlu_pro:
    dataset_id: LGAI-EXAONE/KMMLU-Pro
    revision: e1567939724a369e428e66f15472562c55a5d181
    config: kmmlu_pro
    split: test
    fields:
      question: question
      choices: options
      answer: solution
      score: score
      license_name: license_name
      subject: subject
      year: year
      round: round
      session: session

  kobalt:
    dataset_id: snunlp/KoBALT-700
    revision: 30c30a431066508e6bef77cfa6d6059b85b12f0d
    config: kobalt_v1
    split: raw
    fields:
      id: ID
      category: Class
      subcategory: Subclass
      question: Question
      answer: Answer
      difficulty: Level
      sampling_flag: Sampling_YN

  click:
    dataset_id: EunsuKim/CLIcK
    revision: d61627859645b5e6edc03fd9f835735d8226fa4e
    config: default
    split: train
    fields:
      id: id
      context: paragraph
      question: question
      choices: choices
      answer: answer

  ifeval_ko:
    dataset_id: allganize/IFEval-Ko
    revision: 54199e3801116897697babf341865741dcd06fc8
    config: default
    split: train
    fields:
      id: key
      prompt: prompt
      instruction_ids: instruction_id_list
      kwargs: kwargs
```

## Files Changed

- `.gitignore`: exclude dataset source, processed, and evaluator directories while keeping manifest/config files trackable.
- `scripts/inspect_public_benchmarks.py`: add a token-safe metadata inspection script for the four public benchmark datasets.
- `_bmad-output/implementation-artifacts/completion-reports/dataset-setup-inspection.md`: record inspection evidence and deferred work.

## Commands Run

```text
python --version
python -m pip show datasets huggingface_hub fsspec
hf auth whoami
python scripts\inspect_public_benchmarks.py
```

## Failures

- Initial `hf auth whoami` inside the Codex sandbox failed with a Windows socket access error. It succeeded when rerun with approved external network access.

## Not Executed

- Full dataset snapshot downloads were not executed.
- `dataset_manifest.json` files were not generated.
- Dataset adapter smoke tests were not executed.
- IFEval-Ko official evaluator import/path review was not executed.

## Risks

- KMMLU-Pro is gated and non-commercial/no-derivatives licensed; access and permitted usage must remain explicit.
- KoBALT-700 is non-commercial licensed.
- CLIcK license is still `unknown` from the Hugging Face dataset card inspection and must be treated as not commercially verified.
- Hugging Face cache symlink warnings appeared on Windows; cache still works but may use more disk space unless Developer Mode or administrator symlink support is enabled.
- `load_dataset` inspection cached dataset files under the local Hugging Face cache, but no repository `datasets/` source snapshot was created.
