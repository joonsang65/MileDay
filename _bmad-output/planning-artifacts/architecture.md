# Architecture: Local LLM Evaluation Harness

## Module Overview

```text
CLI
  -> Evaluation Orchestrator
      -> Runtime Adapter
          -> Ollama Runtime
      -> Benchmark Adapter
          -> KMMLU-Pro
          -> KoBALT-700
          -> CLIcK
          -> IFEval-Ko
      -> MileDay Evaluator
          -> Schema Validator
          -> Constraint Validator
          -> Semantic Judge
      -> Performance Monitor
          -> CPU/RAM Monitor
          -> GPU Monitor
      -> Reporter
          -> Raw Results
          -> Summary Tables
          -> Markdown Report
```

## Responsibilities

- CLI: parses commands and loads configuration.
- Evaluation Orchestrator: schedules model/dataset/case execution and resume.
- Runtime Adapter: normalizes inference request and response data.
- Ollama Runtime: calls local Ollama and records streaming metadata.
- Benchmark Adapter: loads dataset cases, builds prompts, parses responses, and scores.
- MileDay Evaluator: validates domain-specific structured output and schedule constraints.
- Performance Monitor: samples system resource usage during runs.
- Reporter: writes raw artifacts and summary reports.

## Data Flow

1. CLI loads configuration and model registry.
2. Orchestrator builds a run plan from selected models and datasets.
3. Runtime executes prompts and returns raw output plus timing metadata.
4. Adapter parses raw output and marks valid, invalid, or failed.
5. Evaluators compute deterministic and semantic scores.
6. Reporter persists artifacts and produces summaries.

## Request Result Schema

Canonical schemas for benchmark cases, runtime responses, persisted results, performance samples, artifact layout, and MileDay generation fixtures are defined in `_bmad-output/planning-artifacts/schemas.md`. This section keeps the core persisted request result shape for quick reference.

```json
{
  "run_id": "string",
  "model_id": "string",
  "dataset_id": "string",
  "case_id": "string",
  "status": "passed | failed | invalid | skipped",
  "raw_output_path": "string",
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

## Artifact Layout

```text
artifacts/
  runs/
    {run_id}/
      config.snapshot.yaml
      raw/
      parsed/
      metrics/
      summary.csv
      report.md
```

## Resume Key

Resume is keyed by:

- run_id
- model_id
- dataset_id
- case_id

## Error Categories

Use the shared categories from `AGENTS.md`.

## Runtime Boundary

Ollama is the default local runtime for initial stories. Future llama.cpp or vLLM support must implement the same runtime interface and preserve the same result schema.
