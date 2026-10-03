# VISIO-CANONICAL-BRIDGE-001

Status: In progress  
Issue: #3  
Draft PR: #4

## Objective

Prove a deterministic Visio ↔ canonical-model vertical slice while preserving the canonical electrical model as the source of truth.

## Dependency

PROJECT-FOUNDATION-001 was accepted and merged to `main` as
`8de6b8184bc82720e48bc2e71042e0c231c3f985`.

## Supported first slice

The live VTD/GOST reference proved the real path is slightly richer than the initial shorthand:

`bus → circuit breaker → current transformer → current transformer (NP) → external/object link`

The native `Шина10` connection point is a child shape of the bus group and is treated as projection plumbing, not as an electrical element.

## Mapping contract

- Exact native masters are recognized fail-closed.
- Shape text is normalized and combined with canonical kind to derive a deterministic import identity; duplicate normalized identities are rejected.
- `Prop.u = INDEX(n,Prop.u.Format)` is decoded through the explicit VTD voltage table.
- Visio page/shape IDs and geometry remain projection-only.
- `BeginX` / `EndX` and `Connections.N.X` are mapped to canonical terminals for the supported 1-D masters.
- Child connection-point shapes of `Шина10` alias the parent bus terminal.
- Unknown masters, unsupported voltage formulas/classes, ambiguous identities and unresolved group children fail closed.
- The first render plan accepts only one connected bus-to-external path and emits exact native stencil/master selections.

## Live qualification baseline

Document: `KRU-35_normal_scheme_v2_final.vsdx`  
Page: `MCP-v2`

Reference shapes:

- bus: `Шина10 #101`;
- native bus child point: `Sheet.103`;
- breaker: `Выкатная тележка выключателя #66`, text `В-1-35`;
- CT: `ТТ #69`, text `ТТ / В-1-35`;
- CT NP: `ТТ #117`, text `ТТ НП / В-1-35`;
- external link: `Связь с объектом2 #119`, text `В-1`.

All five electrical shapes use `Prop.u = INDEX(10,Prop.u.Format)` = 35 kV.

Observed native glue path:

- `66.BeginX → 103.Connections.2.X`;
- `69.BeginX → 66.Connections.2.X`;
- `117.BeginX → 69.Connections.2.X`;
- `119.BeginX → 117.Connections.2.X`.

Native stencil mapping was verified live:

- `Шина10` → `Шины.vss`;
- `Выкатная тележка выключателя` → `Коммутационные аппараты.vss`;
- `ТТ` → `Трансформаторы.vss`;
- `Связь с объектом2` → `Линии, заземление.vss`.

Baseline page snapshot was visually inspected before mutation.

## Acceptance checks

- [x] Dedicated branch and Draft PR.
- [x] Transport-neutral Visio snapshot contract.
- [x] Pure deterministic snapshot → canonical mapper implemented.
- [x] Canonical → Visio render-plan generation implemented.
- [x] Visio IDs are absent from canonical electrical identity.
- [x] Unknown/ambiguous masters/identities fail closed.
- [x] Bus child connection point aliases parent bus semantics.
- [x] Geometry-only invariance covered by regression test.
- [x] Electrical Shape Data sensitivity covered by regression test.
- [x] Synthetic render-plan round-trip fingerprint invariant covered by regression test.
- [x] Live read-only capture evidence recorded.
- [ ] Branch CI green after implementation.
- [ ] Separate-page live rendered rebuild completed.
- [ ] Live rendered rebuild visually inspected.
- [ ] Live recapture fingerprint matches source capture.
- [ ] Owner acceptance.
- [x] No merge without explicit owner command.
