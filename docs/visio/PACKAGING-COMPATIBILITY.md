# Visio packaging and compatibility — V364

## Canonical package

`EnergoLogic-Visio-Editor-Kit-0.3.64.zip`

Final validated build on 2026-10-07:

- size: **689,913 bytes**;
- SHA-256: `3a584ee4bc1178809b1fe47bca42904446a2901d53c7eeb611bb2d4dcc820aff`;
- manifest entries: 23;
- bundled personal ГОСТ stencils: 10;
- third-party VTD files: not included.

## Target-machine model

The target PC receives prebuilt release artifacts:

- `EnergoLogic.VisioEditorAddinV364.dll` — AnyCPU;
- `EnergoLogic.TopologyRestoreHelper.exe` — AnyCPU.

Installation validates/copies the artifacts and registers the COM add-in per user. The target PC does **not** compile the editor.

Current V364 relies on the Windows/.NET Framework 4.x runtime available on the supported Windows platform. The user is not expected to install a developer SDK/toolchain. Product-wide standalone packaging remains responsible for keeping runtime prerequisites automatic/self-contained.

Normal target installation therefore does not require the user to install/configure:

- Internet access;
- ChatGPT/MCP;
- Python/pip;
- Visual Studio;
- C# compiler;
- Office/Visio PIA deployment;
- Visual Studio Interop assembly;
- Office `.NET Programmability Support`.

The package retains source payload for audit/reproducibility, not target-side compilation.

## Interop design

Office COM type metadata required by the add-in is embedded at build time.

`IDTExtensibility2` is represented by the exact local COM contract needed by the add-in, including GUID/DispId/marshaling semantics. Release validation rejects a built DLL that retains runtime assembly references to:

- `Office`;
- `Extensibility`;
- `Microsoft.VisualStudio.Interop`.

## Registry / bitness

The release artifacts are AnyCPU.

On 64-bit Windows the installer manages both per-user registry views:

- Registry64;
- Registry32.

This allows the packaging architecture to support either 32-bit or 64-bit Visio without binding the add-in binary to a single host bitness.

## Qualification levels

- **LIVE PASS** — exact Visio SKU/bitness was exercised with the running add-in.
- **ARCH/PACKAGE PASS** — package/registration/API design supports the target but that exact SKU is not installed on the qualification workstation.
- **PENDING LIVE** — physical qualification remains required.

## Current matrix

| Visio | 32-bit target | 64-bit target | Status |
|---|---:|---:|---|
| 2010 | yes | yes | ARCH/PACKAGE PASS; PENDING LIVE |
| 2013 | yes | yes | ARCH/PACKAGE PASS; PENDING LIVE |
| 2016 | yes | yes | ARCH/PACKAGE PASS; PENDING LIVE |
| 2019 | yes | yes | ARCH/PACKAGE PASS; PENDING LIVE |
| 2021 | yes | yes | ARCH/PACKAGE PASS; PENDING LIVE |
| Visio 16.x / current M365 host | target | current host | **LIVE PASS on installed host** |

Do not convert `target` into `LIVE PASS` without the actual SKU/bitness.

## Historical-SKU qualification gate

For each pending environment:

1. clean user profile / no previous EnergoLogic registration;
2. package integrity validation;
3. per-user install;
4. launch Visio through EnergoLogic launcher;
5. verify exactly one connected current ProgID and native UI;
6. run geometry commands;
7. run real-cell Move/Distribute + Glue verification;
8. verify one native Undo and one Redo on the accepted compound path;
9. restart Visio and repeat minimal smoke;
10. uninstall and verify both registry views/files are cleaned.

## Third-party assets

Personal project-owned ГОСТ stencils may be bundled by the controlled builder.

Third-party VTD files are **not** silently copied or redistributed. Their licensing/provenance must be resolved explicitly before any packaging decision changes.
