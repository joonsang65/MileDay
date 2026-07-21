# ADR-0002: Separate Official and Generation Evaluation

## Status

accepted

## Context

Public benchmarks and MileDay-specific generation tasks measure different qualities and require different validation methods.

## Decision

Keep official benchmark adapters separate from MileDay generation evaluation.

## Consequences

### Positive

- Benchmark scores remain traceable to benchmark-specific rules.
- Product-specific schedule validation can evolve independently.

### Negative

- Final model recommendation must combine multiple score families.

## Alternatives Considered

- One shared evaluator for every dataset
- Only product-specific prompts without public benchmarks
