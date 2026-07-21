# ADR-0001: Use Ollama as Default Runtime

## Status

accepted

## Context

The initial harness must run local LLM candidates on a developer workstation without production serving infrastructure.

## Decision

Use Ollama as the default runtime adapter for initial model execution.

## Consequences

### Positive

- Simple local setup for smoke tests.
- Clear model installation check through Ollama model tags.
- Streaming and timing metadata can be captured from one runtime boundary.

### Negative

- Results depend on local Ollama version and installed model tags.
- GPU and quantization behavior may differ from other runtimes.

## Alternatives Considered

- llama.cpp directly
- vLLM
- Cloud-hosted inference APIs
