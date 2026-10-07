# EnergoLogic repository instructions

## Read first

Before substantial work, read:

1. `docs/PROJECT-STATUS.md`;
2. `docs/roadmap.md`;
3. `docs/architecture/CANONICAL-PRODUCT-ARCHITECTURE.md`;
4. `docs/EXECUTOR-GUIDE.md`;
5. the relevant architecture/work-item/evidence documents.

`docs/EXECUTOR-GUIDE.md` is the detailed operating manual. This file records non-negotiable repository rules.

## Mandatory process

Every substantial change follows:

1. Issue
2. dedicated branch
3. Draft PR
4. implementation + tests + evidence
5. owner acceptance

Do **not** merge or mark a PR Ready for Review without explicit owner instruction.
Do not create duplicate issue/branch/PR when an existing bounded work item covers the task.

## Source-of-truth hierarchy

For current project state, prefer:

1. code/tests and accepted merge state in `main`;
2. `docs/PROJECT-STATUS.md`;
3. current architecture contracts;
4. `docs/roadmap.md`;
5. current work-item/evidence documents;
6. PR bodies/comments and historical chats only as supplemental history.

If documents disagree, reconcile them instead of choosing the older statement silently.

## Architecture invariants

- Canonical electrical model is the source of truth.
- Visio is the first engineering frontend, not system of record.
- Structural schema validation and named domain profiles are separate layers.
- Critical runtime behavior is deterministic, explicit and fail-closed.
- LLM/agent behavior does not participate in critical electrical logic.
- Solver implementation schemas never become canonical schemas.
- Protection logic is separate from solver physics and from operational breaker execution.
- Normative/site rules are separate, versioned and provenance-bearing.
- Generic code and Kochubeevskaya/site-specific data remain separable.

## Layer dependency rules

- `src/energologic/core` must not depend on domain/frontend/COM/solver/protection stacks.
- `src/energologic/domain` may depend on core but not on frontends/COM/solver implementation.
- `src/energologic/operational` consumes core/domain semantics; it does not calculate solver physics or protection algorithms.
- `src/energologic/solvers` exposes solver-neutral EnergoLogic contracts and normalized results.
- `src/energologic/protection` consumes explicit settings/measurements/logical time and emits declarative requests; it does not silently mutate switch state.
- frontends may depend downward; frontend geometry does not redefine canonical electrical semantics.

## Electrical-domain rules

- `electrical-v1` remains an explicit accepted profile; do not silently broaden it with solver-spike kinds.
- Canonical voltage/parameter facts use explicit units and provenance where the contract requires it.
- Do not weaken terminal/voltage/topology checks to accommodate a frontend or solver.
- Transformer voltage remains terminal-scoped for `transformer_2w`.
- Preserve source precision: a voltage class is not an exact voltage.
- Grounding/earthing semantics are not ordinary disconnector semantics.
- Phase/neutral/zero-sequence data must not be invented.

## Switching / operational rules

- `switch_state` and `withdrawable_position` remain independent facts.
- A closed withdrawable switch conducts the primary circuit only in `working` position.
- Explicit active sources drive energized traversal; no source is inferred from names/geometry.
- A switching operation and its permission/interlock validation are separate concerns.
- Deterministic event timelines use logical ordering/time; do not introduce wall-clock behavior into critical simulation semantics.

## Protection rules

- Settings import is data/provenance, not execution.
- Production protection execution is fail-closed on incomplete/ambiguous semantics.
- Measured quantity kind/unit/basis must match the qualified protection function contract.
- `ProtectionOutputRequest` is not proof that a breaker opened.
- Breaker-failure behavior requires explicit start/feedback/binding semantics.
- Unsupported functions remain explicit; do not approximate advanced RZA behavior.

## Terminology rules

- UI: canonical Russian power-engineering terminology.
- Code/API/schema: canonical English electrical terminology.
- New domain concepts must be checked against Terminology Registry and authoritative evidence.
- Transliteration/ad-hoc synonyms are not canonical naming.
- Import aliases are allowed but do not replace canonical output terminology.

## Visio rules — V364 baseline

Current accepted runtime baseline: **V364 / API 0.3.64**.
Read `docs/visio/README.md` before touching Visio functionality.

- CELL / EQUIPMENT / TERMINAL / BUS / ANCHOR / CONNECTION are engineering concepts; bounding box alone is not cell identity.
- Electrical attachment requires native Glue/canonical mapping; visual contact is not electrical truth.
- Preserve VTD master internals unless a separate normalization item proves otherwise.
- Topology-sensitive compound mutations use the accepted external helper-owned **single native Visio UndoScope**.
- Do not reintroduce cross-call held UndoScope, `IVBUndoUnit` ShapeSheet mutation or acceptance-only probe paths into production.
- Destructive acceptance uses disposable pages/copies.
- Release binaries remain prebuilt AnyCPU; target install must not require compiler/Office PIA/Visual Studio.
- Do not bundle third-party VTD files without explicit redistribution authority.
- `Visio 2010+ target` is not equivalent to `Visio 2010 live-qualified`; physical claims require the actual SKU/bitness.

## Evidence discipline

Every work item records:

- changed contracts;
- verification commands;
- test/CI results;
- observed live evidence where required;
- known limitations;
- final acceptance/merge state.

When a merged work item still contains a historical pre-merge checklist, keep that history but add a clear final reconciliation status.
