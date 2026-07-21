# ADR-0003: Preserve Raw Model Output

## Status

accepted

## Context

Model outputs may be invalid, ambiguous, unsafe, or difficult to parse. Losing raw output makes later debugging and audit impossible.

## Decision

Every harness run must preserve raw model output before parsing, validation, or scoring.

## Consequences

### Positive

- Failures can be reproduced and inspected.
- Parser changes can be evaluated against previous outputs.

### Negative

- Artifact storage grows with benchmark size.
- Raw outputs may contain sensitive prompt content and need careful handling.

## Alternatives Considered

- Store only parsed JSON
- Store only aggregate scores
