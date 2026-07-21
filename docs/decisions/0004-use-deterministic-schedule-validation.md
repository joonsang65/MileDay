# ADR-0004: Use Deterministic Schedule Validation

## Status

accepted

## Context

MileDay schedule generation must satisfy hard constraints such as date format, deadlines, recurrence, and milestone count.

## Decision

Use deterministic validators for hard schedule constraints before optional semantic judging.

## Consequences

### Positive

- Hard failures are explainable and reproducible.
- Semantic scores cannot hide invalid schedules.

### Negative

- Validators must be updated when MileDay scheduling rules change.

## Alternatives Considered

- Semantic-only judging
- Manual review only
