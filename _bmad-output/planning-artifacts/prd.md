# PRD: Local LLM Evaluation Harness

## Functional Requirements

### Model Registry

- Store five model candidates in configuration.
- Validate required fields: id, provider, runtime, model tag, context window, quantization, license note.
- Never substitute missing models automatically.

### Ollama Runtime

- Provide a runtime interface for prompt execution.
- Support streaming responses.
- Record time to first token, total latency, response text, and runtime metadata.
- Distinguish timeout, HTTP error, unavailable runtime, and missing model.

### Public Benchmark Adapters

- Provide adapters for KMMLU-Pro, KoBALT-700, CLIcK, and IFEval-Ko.
- Use deterministic parsing for multiple-choice answers where applicable.
- Preserve invalid outputs instead of silently correcting them.
- Aggregate benchmark, category, and model-level scores.

### MileDay Dataset Evaluation

- Load MileDay schedule-planning fixtures from versioned files.
- Validate structured output schema.
- Validate schedule constraints such as date format, milestone count, deadline compliance, and recurrence rules.
- Support a semantic evaluator with a documented rubric.

### Performance Monitoring

- Sample CPU and RAM usage.
- Sample Ollama process RSS when available.
- Sample GPU VRAM through NVML when available.
- Degrade clearly when GPU metrics are unavailable.
- Record cold and warm latency metrics.

### Results and Reports

- Store raw outputs, parsed outputs, validation results, errors, and metrics.
- Support resume by run id, model id, benchmark id, and case id.
- Generate CSV or Parquet summaries when dependencies are available.
- Generate a Markdown report with model ranking and failure analysis.

### CLI

- Provide commands for preflight, list-models, run, resume, summarize, and report.
- Separate offline validation from local Ollama smoke tests and full benchmark runs.

## Non-Functional Requirements

- Reproducible configuration and artifacts
- Windows-compatible paths and commands
- Unit-testable adapters and validators
- Clear failure categories
- No fabricated scores or inferred dataset fields
- Raw output preservation
- Extensible runtime adapter boundary for future llama.cpp or vLLM support

## Out of Scope

- Model fine-tuning
- Production deployment
- Automatic benchmark dataset redistribution
- Automatic model download
- Multi-GPU scheduling
