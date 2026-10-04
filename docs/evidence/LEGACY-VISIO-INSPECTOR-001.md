# LEGACY-VISIO-INSPECTOR-001 — evidence

Issue: #13  
Draft PR: #16

## Isolation

Branch: `migration/legacy-visio-inspector-001`  
Base: `9edc59a0e83f17e94c50ca10f7feac320332b2a1` (`main`).

The branch was created directly from `main`, not from `visio/visio-editor-qol-001`. No EnergoLogic Editor / Cell Pitch / current Glue implementation files are changed.

## Focused tests

Command: `PYTHONPATH=src python3 -m unittest tests.test_legacy_visio_inspector -v`

Focused result after hardening: `Ran 10 tests ... OK`.

Covered invariants: stable family under Shape ID and absolute coordinate changes; text/designation separation; geometry distinction; nested groups; exact native Glue evidence; no inferred topology from visual contact; deterministic read-only behavior; raw ShapeSheet/report statistics exposure; declared report-schema required keys.

## Full regression

Command: `PYTHONPATH=src python3 -m compileall -q src && PYTHONPATH=src python3 -m unittest discover -s tests -v`

Result: **80/80 PASS** (`Ran 80 tests in 0.581s`, `OK`).

## Live Visio acceptance

Bounded read-only exploration was attempted through the existing `visio-bridge` infrastructure.

Observed state on 2026-10-04:

- `mcp_discover` sees `visio-bridge` with live schema and 15 tools, state `idle`;
- `visio_node_status` returns Bridge `INTERNAL_ERROR`;
- `visio_list_open_documents` returns the same Bridge `INTERNAL_ERROR`;
- no online Windows Desktop Commander device is available;
- the accessible VPS filesystem does not contain the Kochubeevskaya source VSD/VSDX.

The project Library contains a PDF export of the Kochubeevskaya normal electrical scheme, but a PDF cannot supply native `Page.Connects`, ShapeSheet or master/group identity and is therefore not substituted for the requested source-Visio inspection.

Result: real Kochubeevskaya Visio statistics remain **not measured**, rather than estimated or inferred from the PDF. No source mutation was performed.
