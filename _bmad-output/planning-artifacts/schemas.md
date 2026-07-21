# Schemas: Local LLM Evaluation Harness

## Purpose

This document defines canonical harness schemas for Stories after EVAL-005. It does not define or assume public benchmark provider dataset fields. Benchmark adapters must map versioned input files into these internal schemas.

## Principles

- Do not invent external dataset fields.
- Preserve raw model output before parsing or scoring.
- Keep official benchmark evaluation separate from MileDay generation evaluation.
- Use deterministic validation before semantic evaluation.
- Use the shared failure categories from `AGENTS.md`.
- Use `run_id`, `model_id`, `dataset_id`, and `case_id` as the resume key.

## Internal Benchmark Case

Benchmark adapters normalize public benchmark rows into this shape before prompt building.

```json
{
  "benchmark_id": "string",
  "dataset_id": "string",
  "case_id": "string",
  "category": "string | null",
  "question": "string",
  "choices": [
    {
      "label": "A",
      "text": "string"
    }
  ],
  "answer": "A",
  "metadata": {}
}
```

Rules:

- `choices` supports labels `A` through `J`.
- `answer` must match one of the choice labels.
- `metadata` may preserve source split, subject, subcategory, source row id, or license/version data when available.
- Adapter-specific field mapping must be explicit in code or config; do not infer fields silently.

## MCQ Parse Result

```json
{
  "status": "parsed | invalid",
  "raw_output": "string",
  "parsed_answer": "A | null",
  "invalid_reason": "string | null"
}
```

Rules:

- Ambiguous, multiple, missing, or out-of-range answers are `invalid`.
- `raw_output` is preserved even when parsing fails.
- Parser output must not silently correct invalid model output.

## MCQ Case Result

```json
{
  "benchmark_id": "string",
  "case_id": "string",
  "category": "string | null",
  "correct_answer": "A",
  "raw_output": "string",
  "parsed_answer": "A | null",
  "is_correct": true,
  "is_invalid": false,
  "invalid_reason": "string | null"
}
```

Rules:

- Invalid output is never counted as correct.
- Category can be `null`; aggregators should treat it as `uncategorized`.

## Runtime Request

```json
{
  "model_tag": "string",
  "prompt": "string",
  "system": "string | null",
  "options": {},
  "timeout_seconds": 120
}
```

Rules:

- `model_tag` comes from `configs/models.yaml`.
- Runtime adapters must not substitute missing models.

## Runtime Response

```json
{
  "model_tag": "string",
  "text": "string",
  "metrics": {
    "ttft_ms": 0,
    "latency_ms": 0,
    "tokens_per_second": 0
  },
  "metadata": {},
  "error": {
    "category": "TIMEOUT",
    "message": "string"
  }
}
```

Rules:

- `metadata` preserves runtime-provided fields such as Ollama token and duration metadata.
- `error` is `null` for successful runtime responses.

## Request Result

This is the canonical persisted unit for result storage.

```json
{
  "run_id": "string",
  "model_id": "string",
  "dataset_id": "string",
  "case_id": "string",
  "status": "passed | failed | invalid | skipped",
  "raw_output_path": "string | null",
  "parsed_output": {},
  "metrics": {
    "ttft_ms": 0,
    "latency_ms": 0,
    "tokens_per_second": 0
  },
  "error": {
    "category": "CODE_ERROR",
    "message": "string"
  }
}
```

Rules:

- `raw_output_path` points to a file under `artifacts/runs/{run_id}/raw/`.
- `parsed_output` stores benchmark-specific parsed fields, not raw text.
- `status=invalid` is used for parse or validation failures with preserved raw output.
- `status=failed` is used for runtime, dataset, timeout, resource, or code failures.

## Performance Sample

```json
{
  "timestamp_s": 0,
  "cpu_percent": 0,
  "ram_used_bytes": 0,
  "ram_percent": 0,
  "ollama_rss_bytes": 0,
  "vram_used_bytes": 0,
  "vram_total_bytes": 0,
  "vram_status": "ok | unavailable | disabled | not_sampled",
  "vram_error": "string | null"
}
```

Rules:

- Missing Ollama process RSS is `null`.
- Missing NVML is not a test failure; record `vram_status=unavailable`.
- Sampling interval is 100ms to 250ms.

## Artifact Layout

```text
artifacts/
  runs/
    {run_id}/
      config.snapshot.yaml
      raw/
        {model_id}__{dataset_id}__{case_id}.txt
      parsed/
        results.jsonl
      metrics/
        performance.jsonl
      summary.csv
      report.md
```

Rules:

- The run directory is append/resume friendly.
- File names must be deterministic from the resume key.
- Raw output is written before parsed or scored output.

## MileDay Generation Case

MileDay-specific generation Stories should use this internal fixture shape.

```json
{
  "dataset_id": "mileday-schedule",
  "case_id": "string",
  "locale": "ko-KR",
  "timezone": "Asia/Seoul",
  "input": {
    "goal_title": "string",
    "deadline": "YYYY-MM-DD",
    "constraints": {}
  },
  "expected": {
    "min_milestones": 1,
    "max_milestones": 10,
    "latest_allowed_date": "YYYY-MM-DD",
    "required_fields": []
  },
  "metadata": {}
}
```

Rules:

- Dates use `YYYY-MM-DD`.
- Deterministic constraints validate before semantic rubrics.
- Do not depend on MileDay production user data.

