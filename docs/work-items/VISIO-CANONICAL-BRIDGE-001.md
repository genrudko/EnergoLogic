# VISIO-CANONICAL-BRIDGE-001

Status: Awaiting owner acceptance  
Issue: #3  
Draft PR: #4

## Objective

Prove a deterministic Visio ↔ canonical-model vertical slice while preserving the canonical electrical model as the source of truth.

## Dependency

PROJECT-FOUNDATION-001 was accepted and merged to `main` as
`8de6b8184bc82720e48bc2e71042e0c231c3f985`.

## Qualified vertical slice

The live VTD/GOST topology is:

`bus → circuit breaker → current transformer → current transformer (NP) → external/object link`

The native `Шина10` connection point is a child shape of the bus group and is projection plumbing, not a canonical electrical element.

## Mapping contract

- Exact native masters are recognized fail-closed.
- Shape text is NFKC-normalized with whitespace collapsed and combined with canonical kind to derive deterministic import identity.
- Duplicate normalized identities are rejected.
- `Prop.u = INDEX(n,Prop.u.Format)` is decoded through an explicit VTD voltage table.
- Visio document/page/shape IDs and geometry remain projection-only.
- `BeginX` / `EndX` and `Connections.N.X` map to canonical terminals for the supported native 1-D masters.
- Native child connection-point shapes of `Шина10` alias the parent bus terminal.
- Unknown masters, unsupported voltage formulas/classes, ambiguous identities and unresolved group children fail closed.
- The first render plan accepts only one connected bus-to-external path containing every element.
- The executable native glue plan maps the lower element's `BeginX` to row 2 of the upper element. For `Шина10`, the target child is selected semantically by `User.nt=1`; no Visio shape ID is baked into the plan.

## Live source baseline

Document: `KRU-35_normal_scheme_v2_final.vsdx`  
Page: `MCP-v2`

Reference shapes:

- bus: `Шина10 #101`, text `1 С 35 кВ`;
- native bus child point: `Sheet.103`;
- breaker: `Выкатная тележка выключателя #66`, text `В-1-35`;
- CT: `ТТ #69`, normalized text `ТТ В-1-35`;
- CT NP: `ТТ #117`, normalized text `ТТ НП В-1-35`;
- external link: `Связь с объектом2 #119`, text `В-1`.

All five electrical shapes use `Prop.u = INDEX(10,Prop.u.Format)` = 35 kV.

Observed native source glue path:

- `66.BeginX → 103.Connections.2.X`;
- `69.BeginX → 66.Connections.2.X`;
- `117.BeginX → 69.Connections.2.X`;
- `119.BeginX → 117.Connections.2.X`.

Native stencil mapping was verified live:

- `Шина10` → `Шины.vss`;
- `Выкатная тележка выключателя` → `Коммутационные аппараты.vss`;
- `ТТ` → `Трансформаторы.vss`;
- `Связь с объектом2` → `Линии, заземление.vss`.

Baseline source-page PNG SHA-256:

`71eaa6244aef0dfe478ed052cf25b6ec8da58bd6d6cb32de7f83713e32f91648`

## Live render qualification

A separate page `EnergoLogic-V1` was created. The source pages were not mutated.

Rendered native shapes:

- bus `#1`;
- bus child selected by `User.nt=1`: `Sheet.3`;
- breaker `#13`;
- CT `#16`;
- CT NP `#18`;
- external link `#20`.

All rendered electrical shapes were explicitly set to 35 kV through native Shape Data.

Observed native rendered glue path:

- `13.BeginX → 3.Connections.2.X`;
- `16.BeginX → 13.Connections.2.X`;
- `18.BeginX → 16.Connections.2.X`;
- `20.BeginX → 18.Connections.2.X`.

Visual gates were performed after the representative bus/breaker connection and after the complete slice. Final rendered PNG SHA-256:

`e10283b3582fc9f20c65fd0df36b39423e7231ad397aff4e178d344bf32a0800`

After the rebuild, `MCP-v2` was rendered again and retained the exact original PNG SHA-256:

`71eaa6244aef0dfe478ed052cf25b6ec8da58bd6d6cb32de7f83713e32f91648`

The qualified result was saved as a separate copy:

`C:\Users\Gennadiy\AppData\Local\OpenAI\VisioMCP\workspace\KRU-35_normal_scheme_v2_energologic_v1.vsdx`

## Round-trip evidence

Using model id `kru35:v1-cell`, both the live source capture and the live rendered recapture canonicalize to:

`3f055b816fc016ec6c6ff555c9de771f783e19756a1a87420130511e299a670b`

The Visio instance IDs differ completely between source and rebuild while the canonical fingerprint is identical.

Regression tests additionally prove:

- geometry-only changes do not affect the fingerprint;
- changing supported electrical Shape Data does affect the fingerprint;
- unknown masters fail closed;
- ambiguous semantic identities fail closed;
- arbitrary Visio shape-ID remapping does not affect canonical identity;
- synthetic render-plan round-trip preserves the fingerprint;
- native glue instructions are deterministic, including `Шина10 User.nt=1`.

## CI evidence

Code candidate head:

`5ee4cfbd584321e79f1e7be4c57fa9dae8f6af09`

CI run:

https://github.com/genrudko/EnergoLogic/actions/runs/37110372368

Result: **4/4 PASS**

- Ubuntu / Python 3.11 — PASS;
- Ubuntu / Python 3.12 — PASS;
- Windows / Python 3.11 — PASS;
- Windows / Python 3.12 — PASS.

The subsequent evidence-only documentation commit does not change runtime behavior; the final PR-head CI state is recorded in PR/Issue metadata.

## Acceptance checks

- [x] Dedicated branch and Draft PR.
- [x] Transport-neutral Visio snapshot contract.
- [x] Pure deterministic snapshot → canonical mapper.
- [x] Canonical → Visio render-plan generation.
- [x] Executable deterministic native glue plan.
- [x] Visio IDs absent from canonical electrical identity.
- [x] Unknown/ambiguous masters/identities fail closed.
- [x] Bus child connection point aliases parent bus semantics.
- [x] Geometry-only invariance regression.
- [x] Electrical Shape Data sensitivity regression.
- [x] Synthetic render-plan round-trip fingerprint invariant.
- [x] Live read-only source capture evidence.
- [x] Separate-page live native rebuild.
- [x] Final rendered rebuild visually inspected.
- [x] Reference page proven unchanged by PNG hash.
- [x] Live source/rebuild canonical fingerprints identical.
- [x] Code candidate CI green on Linux/Windows × Python 3.11/3.12.
- [ ] Owner acceptance.
- [x] No merge without explicit owner command.
