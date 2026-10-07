# Visio topology and native Undo architecture

## Problem

Native VTD/GOST diagrams contain topology encoded through Visio Glue, 1-D endpoint formulas, grouped shapes and master-specific behavior. A visually correct move can still corrupt topology or leave a one-ended/stretched connector.

At the same time an engineering command must behave as one user transaction where the underlying Visio API permits it.

## Accepted production design

For topology-sensitive compound commands:

```text
EnergoLogic add-in
    ↓ builds explicit move/topology plan
EnergoLogic.TopologyRestoreHelper.exe
    ↓ single COM owner
BeginUndoScope
    ↓
pre-detach only qualified endpoints that would otherwise be broken implicitly
    ↓
geometry mutation
    ↓
Glue restoration
    ↓
ShapeSheet / Connects verification and bounded repair
    ↓
EndUndoScope(commit)
    ↓
selection/UI update after the transaction
```

The helper owns the whole compound mutation. The add-in does **not** keep an UndoScope open across separate external callbacks.

## Why selective explicit detach exists

Testing showed that Visio may implicitly break one end of a moved double-ended 1-D connector. When this happens inside a normal `Selection.Move`, the first native Undo can fail to recover the original Glue exactly.

Explicitly detaching the relevant managed begin/end endpoints before movement, inside the same helper-owned native scope, restores symmetric Undo/Redo behavior.

Blanket detach is unsafe: some VTD elements use non-standard formulas/semantics and may not accept generic Glue repair. Therefore production logic auto-detaches only qualified double-ended managed sources represented by the expected topology plan; singly-managed/non-standard endpoints remain untouched unless their specific operation owns them.

## Rejected approaches

The following research paths are **not production architecture**:

### Cross-call held UndoScope

Holding a Visio `Application` UndoScope open across add-in/external helper calls did not provide reliable user-native history and couples transaction lifetime to multiple COM owners.

### Custom `IVBUndoUnit` ShapeSheet mutation

A custom UndoUnit could register/execute, but relevant ShapeSheet writes failed in the callback context. It is not used for production mutation.

### Probe-only Undo/keyboard tools

Bare Undo/Redo, Ctrl+Z send-key probes and helper probe modes were useful during investigation but were removed from production once the native transaction mechanism was proven.

## Same-page activation trap

A subtle extra native Undo unit was traced to the wrapper reassigning `ActiveWindow.Page` even when the target page was already active. That same-page activation can fire Visio/VTD UI events and create a separate native history unit.

Production wrapper logic therefore activates a page only when document/page identity actually differs.

Repeated `COMAddIns.Update()` was also removed from the command hot path; it was unnecessary even though it was not the primary extra-unit cause.

## Accepted native history evidence

### Single real-cell Move

Production Move on a real 11-member cell:

- forward state moved +40 mm and restored expected Glue;
- one native `Application.Undo()` restored the exact baseline geometry/Glue state;
- one native `Application.Redo()` restored the exact forward state.

### Multi-step DistributePitch

A production distribution containing **two MoveSteps inside one helper-owned scope** was accepted:

- forward: two independent cells changed slots;
- one native Undo restored 26 shapes × six critical ShapeSheet cells with `mismatch_count = 0` against baseline;
- one Redo restored the exact forward state and expected Glue.

This proves that one compound helper transaction can map to one native Visio history unit.

## Scope of the claim

The evidence above directly proves the helper-owned transaction path used by production Move/Distribute. Do not extrapolate a one-step native Undo guarantee to a new command until that command uses the same qualified transaction architecture or has its own live evidence.

## Development invariants

1. No active-window selection mutation inside the compound native scope.
2. Prepare off-screen/native selection state before opening the scope when needed.
3. Explicitly state expected topology in the transaction plan.
4. Verify geometry and Glue before commit.
5. Roll back/fail closed on unresolved mismatch.
6. Perform final UI selection/feedback after commit.
7. Never reintroduce a rejected Undo mechanism merely because it appears simpler.
