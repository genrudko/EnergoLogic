# ADR-0003 — Deterministic runtime baseline

Status: Proposed  
Work item: PROJECT-FOUNDATION-001

## Decision

Critical foundation behavior is implemented as local deterministic code with no network or AI dependency.

For a valid canonical model:

- canonical JSON uses UTF-8;
- object keys are sorted;
- compact JSON separators are fixed;
- identity-set arrays are sorted by ID;
- undirected connection endpoints are sorted;
- output ends with one LF;
- SHA-256 over canonical bytes is the model fingerprint.

Semantic validation emits stable issue records sorted by `(code, path, message)`.

## Rationale

This provides a reproducible substrate for tests, change detection, persistence, frontend synchronization and later analysis integrations.

An LLM may propose edits, explanations or mappings, but those proposals must become explicit canonical data and pass deterministic validation before critical use.
