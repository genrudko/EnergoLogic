# PROTECTION-SETTING-IMPORT-001 — evidence

Status: **Draft implementation evidence**  
Issue: **#21**  
Draft PR: **#22**  
Branch: `protection/protection-setting-import-001`  
Base: `main@9edc59a0e83f17e94c50ca10f7feac320332b2a1`

## Boundary

WS-9A is built directly from `main`.

It does not modify or depend on:

- WS-6 implementation;
- Visio Editor;
- WS-8 solver adapter;
- pandapower/OpenDSS;
- WS-9B protection execution;
- unmerged WS-2 runtime.

The branch introduces a separate headless `energologic.protection` settings package.

## Normative evidence

### Ministry of Energy Order No. 100

Current searched edition: Order of the Ministry of Energy of Russia dated
13.02.2019 No. 100, amended 15.01.2024.

Relevant requirements captured in the v1 architecture:

- a setting card is an operationally readable representation of main RZA operating
  parameters and algorithm information;
- an owner setting assignment is a different artifact and may contain the complete
  list of settings/algorithms according to manufacturer documentation;
- microprocessor RZA settings are version-sensitive; software version and
  parameterization-file context can be relevant;
- dispatcher-centre settings are specified in primary quantities; secondary/relative
  settings are used only where the concrete device cannot accept primary quantities;
- manufacturer documentation may include a setting blank listing all available
  settings/algorithms.

WS-9A consequences:

- `settings_scope` is mandatory;
- `basis` is mandatory for numeric settings;
- source/normalized representations coexist;
- microprocessor `full_configuration` requires `software_version`;
- parameter files are provenance-bearing source documents.

### ГОСТ IEC 60255-151-2014

Rosstandart lists ГОСТ IEC 60255-151-2014 as **Действует**.

The standard establishes functional requirements for over/under-current protection,
including protection functions, measurement characteristics and time/reset behavior.

WS-9A records typed pickup/delay/etc. settings but intentionally does not implement
the behavior. Execution is WS-9B.

### ГОСТ Р 57114-2022

Rosstandart lists ГОСТ Р 57114-2022 as **Действует** for power-system operational and
dispatch terminology. It remains a terminology/provenance reference; WS-9A does not
encode operational rules from it.

## Implemented model

Version:

`protection-settings-v1`

Key types:

- `ProtectionSettingCard`;
- `SourceDocument` / `SourceReference`;
- `ProtectionDevice`;
- `ProtectionFunctionSettings`;
- `ProtectionStage`;
- `SettingParameter`;
- `SettingValue`;
- `SettingAction`.

Explicit card completeness:

- `operational_summary`;
- `partial_configuration`;
- `full_configuration`.

Explicit numeric basis:

- `primary`;
- `secondary`;
- `relative`;
- `device_native`;
- `not_applicable`.

## Exact quantity handling

Normalization uses Python `decimal.Decimal`, not binary floating point.

Regression evidence includes:

- `1,250 кА` → exact normalized `1250 A`, raw text retained;
- `5,00 А втор.` → `5 A`, **basis remains secondary**;
- `80 %` → `0.8 pu`;
- time supplied as current → rejected;
- normalized-value tampering → rejected;
- negative delay → rejected.

WS-9A never performs CT/VT primary↔secondary transformation.

## Import evidence

### JSON

- duplicate object keys rejected;
- unknown fields rejected;
- missing/invalid model data rejected.

### CSV

- explicit header map required;
- delimiter explicit;
- decimal separator explicit;
- boolean token vocabulary explicit;
- exact source-text SHA-256;
- repeated function/stage identity must be consistent;
- cell/row provenance preserved.

No heuristic header detection exists.

## Synthetic fixture

`examples/protection-settings.synthetic.json`

Covers data representation for:

- `protection.overcurrent` / МТЗ;
- `protection.instantaneous_overcurrent` / ТО;
- `protection.earth_fault`;
- `protection.breaker_failure` / УРОВ.

It includes setting/action associations to stable synthetic equipment IDs.

**The values are synthetic test data and are not Kochubeevskaya WPP settings.**

## Adversarial repair

Initial green implementation exposed a schema/runtime mismatch:
JSON Schema used `additionalProperties=false`, while the Python decoder could ignore
unknown fields.

Repair commit `e6c9dfe3fc563a5e1cbfd8fe9b3dd48399c71e76` makes decode fail closed at every
nested shape and adds duplicate protected-object validation.

CI run **37208241974 — SUCCESS**:

- Ubuntu / Python 3.11 — success;
- Ubuntu / Python 3.12 — success;
- Windows / Python 3.11 — success;
- Windows / Python 3.12 — success;
- representative matrix job: **93 tests — OK**.

## Known limitations

- no production XLSX adapter yet: no real approved source layout has been supplied;
- no arbitrary PDF/image/OCR importer;
- no vendor parameter-file parser;
- no canonical site-profile existence check for external equipment target IDs yet;
- no protection execution/event logic;
- no solver or measured-value integration;
- function concept IDs are WS-2-compatible strings, but WS-2 is not a runtime
  dependency while its PR remains unmerged.

These are deliberate boundaries, not silently inferred capabilities.
