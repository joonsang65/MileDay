# Epics

## Epic 1: Project Foundation and Common Harness

Goal: establish package structure, config loading, common schemas, CLI foundation, and preflight validation.

Stories:

- EVAL-001: Project foundation
- EVAL-002: Model registry

## Epic 2: Local Inference Runtime

Goal: execute local model prompts through Ollama with streaming and timing metrics.

Stories:

- EVAL-003: Ollama streaming runtime

## Epic 3: Public Benchmarks

Goal: implement benchmark adapters and deterministic scoring for public Korean benchmark data.

Stories:

- EVAL-005: Common MCQ adapter
- EVAL-006: KMMLU-Pro adapter
- EVAL-007: KoBALT-700 adapter
- EVAL-008: CLIcK adapter
- EVAL-009: IFEval-Ko adapter

## Epic 4: MileDay Test Set Evaluation

Goal: evaluate schedule-planning outputs with schema validation, deterministic constraints, and semantic rubrics.

Stories:

- EVAL-010: MileDay dataset schema
- EVAL-011: Schedule constraint validator
- EVAL-012: Semantic rubric evaluator

## Epic 5: System Performance

Goal: collect reliable CPU, RAM, VRAM, latency, TTFT, and throughput metrics.

Stories:

- EVAL-004: Performance monitor
- EVAL-013: Cold/warm benchmark mode

## Epic 6: Result Aggregation and Reporting

Goal: persist raw outputs and generate reproducible reports for model selection.

Stories:

- EVAL-014: Result store
- EVAL-015: Markdown report
- EVAL-016: Final model recommendation summary
