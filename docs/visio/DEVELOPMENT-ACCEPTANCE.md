# Visio development and live-acceptance guide

## 1. Before changing Visio code

Read:

1. `docs/PROJECT-STATUS.md`;
2. `docs/roadmap.md`;
3. `docs/visio/README.md`;
4. `docs/visio/TOPOLOGY-UNDO.md`;
5. `docs/work-items/VISIO-EDITOR-QOL-001.md`;
6. relevant pure planner/mapping tests in `src/energologic/frontends/visio/` and `tests/`.

Confirm whether the requested change belongs in EnergoLogic or development-bridge.

## 2. Ownership boundary

### EnergoLogic

Change here when modifying:

- canonical mapping contracts;
- pure planners;
- identity/model rules;
- deterministic Scheme Doctor logic;
- architecture/work-item/evidence docs;
- frontend tests independent of live COM.

### development-bridge

Change here when modifying:

- C# COM add-in runtime;
- Windows/Visio bridge deployment;
- external topology helper;
- live COM tooling;
- portable-kit build/install implementation.

If both are affected, keep commits/references explicit and reconcile evidence/version numbers in EnergoLogic before calling the work complete.

## 3. Destructive test policy

- Never use the user-owned/reference page for destructive experiments when a disposable duplicate can be used.
- Create named disposable acceptance pages/copies.
- Preserve original documents and masters.
- Delete only disposable pages created by the current acceptance run unless the owner explicitly authorizes cleanup of historical pages.

## 4. Mutation acceptance loop

For a topology/geometry mutation:

1. capture baseline geometry/topology;
2. execute the production command path — not a private helper-only shortcut;
3. wait/finalize any explicit helper transaction;
4. inspect ShapeSheet critical cells;
5. inspect `Page.Connects`/Glue;
6. check shape count/identity expectations;
7. render/visually inspect when layout is user-visible;
8. run native Undo/Redo acceptance when transaction semantics changed;
9. record exact evidence and limitations.

## 5. Native Undo rules

Do not use keyboard emulation as primary proof if direct native history inspection is available.

An OS `SendKeys` probe can be blocked by Windows foreground restrictions. A failed focus activation is not evidence that Visio's native Undo stack is wrong.

When qualifying history, compare complete relevant pre/post state and verify exactly one native Undo/Redo unit for the command under test.

## 6. Glue safety

- Do not trust visual coincidence.
- Do not blanket-detach every endpoint.
- Treat double-ended 1-D managed connectors according to the qualified selective-detach rules.
- VTD shapes may use non-standard formulas; verify rather than normalize by assumption.
- On unresolved repair ambiguity: fail closed and report evidence.

## 7. UI wrapper safety

Avoid mutation-like UI side effects in supposedly read-only wrapper code.

In particular:

- do not reassign `ActiveWindow.Page` when the requested page is already active;
- do not refresh COM add-ins on every command hot path;
- keep UI selection updates outside topology transaction scope.

## 8. Packaging gate

A release/package change must verify:

- current version/ProgID/CLSID consistency;
- prebuilt AnyCPU release binary;
- helper binary;
- manifest hashes;
- no forbidden runtime PIA refs;
- no target-side compiler dependency;
- Registry32/Registry64 behavior;
- portable validation mode;
- third-party stencil/VTD inclusion policy.

## 9. Versioning rule

Do not reuse a COM identity for a materially changed DLL that may already be loaded/locked by the running Visio CLR host.

Use a new side-by-side version/ProgID/CLSID when required by live deployment constraints, migrate legacy registration explicitly, and document the change.

## 10. Evidence required before updating project status

At minimum record:

- runtime/editor/API/package versions;
- exact source commit(s);
- exact acceptance document/page;
- commands exercised;
- topology/geometry/Undo findings;
- test counts;
- package hash if packaging changed;
- compatibility boundary;
- any environment limitation.

Do not update `PROJECT-STATUS` from a plan or intention; update it from observed/merged evidence.
