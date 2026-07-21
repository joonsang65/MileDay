# Product Brief: Local LLM Evaluation Harness

## Background

MileDay may use local LLMs for Korean schedule planning, milestone generation, and natural-language schedule edits. Before choosing a model, the project needs a repeatable way to compare local Korean and multilingual LLM candidates under the same prompts, datasets, hardware conditions, and validation rules.

## Problem

Manual model testing is difficult to reproduce. It often mixes benchmark quality, runtime performance, prompt compliance, and domain-specific behavior without preserving enough raw evidence to explain why a model won or failed.

## Target Users

- MileDay developers selecting a local LLM for product features
- Evaluators comparing Korean and multilingual model behavior
- Maintainers reviewing model upgrade decisions

## Evaluation Scope

The harness will evaluate five local LLM candidates against:

- KMMLU-Pro
- KoBALT-700
- CLIcK
- IFEval-Ko
- MileDay-specific schedule generation and constraint-following test sets

## Success Criteria

- Five model candidates can be configured without hardcoding model tags.
- Four public benchmark adapters can run from versioned inputs.
- MileDay-specific test sets can validate structured output, schedule constraints, and semantic fit.
- Raw responses, parsed outputs, metrics, and reports are preserved.
- A hard-gate summary can recommend a final candidate with traceable evidence.
- CI can run offline unit/config/fixture checks without requiring Ollama or GPU.

## Out of Scope

- Automatic model download or license acceptance
- Production serving infrastructure
- Multi-GPU optimization
- Real user A/B testing
- Cloud-hosted model inference
