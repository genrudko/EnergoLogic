# ADR-0001 — System boundaries

Status: Accepted foundation baseline in `main` via PROJECT-FOUNDATION-001 / `8de6b81`
Work item: PROJECT-FOUNDATION-001

## Context

EnergoLogic needs an engineering-grade core while initially using Microsoft Visio as the operator-facing editor. The main architectural risk is accidentally making Visio documents, COM automation, future solver objects, or probabilistic/LLM behavior the place where electrical semantics live.

## Decision

The system is split into three conceptual zones:

1. **Canonical core** — versioned electrical model, validation and deterministic transformations.
2. **Frontends/adapters** — Visio first; other frontends may be added later.
3. **Optional integrations/analysis** — future isolated adapters and services.

Dependency direction is inward:

```text
Visio frontend ───────┐
other frontends ──────┼──> canonical core
future integrations ──┘
```

The canonical core must not import a frontend or optional integration.

Visio-specific identifiers such as document/page/shape IDs are projection metadata. They do not become canonical electrical identity.

LLM/agent behavior may assist users and development, but critical model validity and execution cannot depend on a model response.

## Consequences

- A VSDX document can be imported or rendered, but is not the authoritative storage format for semantics.
- The same canonical model can be tested headlessly on non-Windows systems.
- Future solver and standards integrations can be replaced without rewriting the model core.
