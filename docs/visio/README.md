# EnergoLogic Visio subsystem

**Current accepted runtime baseline:** V364 / API 0.3.64
**Date:** 2026-10-07

Microsoft Visio is the first engineering frontend of EnergoLogic. It provides editing, rendering, mnemonic interaction and user commands. It is **not** the canonical electrical model.

## Repository split

The Visio subsystem currently spans two repositories for explicit reasons:

### `genrudko/EnergoLogic`

Owns:

- canonical/domain/frontend contracts;
- pure Visio planners/mapping/doctor logic;
- product architecture and roadmap;
- work-item/evidence state;
- tests that do not require the live COM host.

### `genrudko/development-bridge`

Owns the live Windows/Visio execution and packaging implementation used for qualification:

- managed COM add-in source;
- topology restore helper;
- bridge tools used for deployment/acceptance;
- portable kit builder/templates;
- Windows/Visio live diagnostics.

Accepted V364 implementation:

- branch: `feature/energologic-visio-qol-001`;
- commit: `5695108cf9602ab93ac8223fe0f90c4e7d658209`.

A runtime change in development-bridge is not considered fully reconciled until EnergoLogic version/evidence/docs are updated.

## Current V364 identity

- editor: **V364**;
- API: `0.3.64`;
- ProgID: `EnergoLogic.VisioEditorAddinV364`;
- managed extension/package transport: `2026.10.06.213`;
- Windows target: Windows 10/11;
- Visio target: Visio 2010 through current supported desktop/Microsoft 365 Visio;
- physical live acceptance currently available: installed Visio 16.x.

## Documentation map

- [`EDITOR-V364.md`](EDITOR-V364.md) — features and runtime architecture;
- [`TOPOLOGY-UNDO.md`](TOPOLOGY-UNDO.md) — final Glue/topology/native Undo design;
- [`PACKAGING-COMPATIBILITY.md`](PACKAGING-COMPATIBILITY.md) — standalone package and version matrix;
- [`DEVELOPMENT-ACCEPTANCE.md`](DEVELOPMENT-ACCEPTANCE.md) — how to modify/test the Visio subsystem safely;
- [`../work-items/VISIO-EDITOR-QOL-001.md`](../work-items/VISIO-EDITOR-QOL-001.md) — bounded work-item status;
- [`../evidence/VISIO-EDITOR-QOL-001.md`](../evidence/VISIO-EDITOR-QOL-001.md) — final acceptance evidence.

## Frozen product decisions

1. Do not restart a standalone custom diagram editor effort: Visio remains the primary graphics/interaction host.
2. Canonical electrical meaning remains outside Visio.
3. Visual contact is never electrical connectivity by itself.
4. Native VTD/GOST master internals are treated as third-party/legacy behavior and are not mass-normalized inside QoL work.
5. Compound topology-sensitive edits use the accepted helper-owned transaction architecture.
6. Target deployment remains self-contained/offline and must not require developer tooling.
7. Cross-version compatibility claims are evidence-based; target support and physical LIVE PASS are distinct states.
