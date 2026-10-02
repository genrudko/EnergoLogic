# ADR-0002 — Canonical model 0.1

Status: Proposed  
Work item: PROJECT-FOUNDATION-001

## Decision

The first canonical contract is intentionally small. It defines:

- `schema_version`;
- `model_id`;
- typed-but-open `elements`;
- element-local `terminals`;
- binary undirected `connections`;
- explicit extension `attributes` / `metadata`.

Element `kind` is an open string in 0.1. Foundation does not prematurely freeze a complete electrical equipment taxonomy.

A connection endpoint is qualified by both `element_id` and `terminal_id`. Terminal IDs therefore only need to be unique inside their owning element.

Connection endpoints are electrically topological, not directional. Canonical serialization sorts the two endpoints so swapping their input order does not change the canonical representation.

Arrays that represent identity sets (`elements`, `terminals`, `connections`) are canonicalized by ID. Arbitrary arrays inside `attributes` remain ordered data and are not reordered.

## Validation baseline

0.1 rejects:

- duplicate element IDs;
- duplicate terminal IDs inside an element;
- duplicate connection IDs;
- missing referenced elements;
- missing referenced terminals;
- degenerate connections to the same endpoint.

Domain-specific electrical rules belong to later explicitly scoped work items.
