# Protection setting-card import

This document describes how to feed setting data into the WS-9A source-neutral
contract.

## Canonical files

Schema:

```text
schema/protection-setting-card-1.0.schema.json
```

Runtime:

```text
src/energologic/protection/
```

Synthetic example:

```text
examples/protection-settings.synthetic.json
```

The synthetic example is a structural/test fixture. Its numerical settings are **not**
Kochubeevskaya WPP settings and must never be treated as site data.

## Choosing `settings_scope`

Use:

- `operational_summary` for an operator/dispatcher setting card that intentionally
  shows only the principal settings;
- `partial_configuration` for an engineering export containing only part of the
  device configuration;
- `full_configuration` only when the authoritative source is intended to represent
  the complete imported configuration scope.

Do not upgrade an operational card to `full_configuration`.

## Quantity basis

`basis` and `unit` answer different questions.

```text
source value = 5 A
basis = secondary
```

means five secondary amperes. Unit normalization may canonicalize `kA → A`, but it
must not use an unrecorded CT ratio to turn a secondary value into a primary value.

Allowed v1 basis values:

- `primary`;
- `secondary`;
- `relative`;
- `device_native`;
- `not_applicable`.

## JSON import

```python
from energologic.protection import JsonSettingCardAdapter

card = JsonSettingCardAdapter().import_text(source_text)
```

The adapter is strict:

- duplicate JSON keys fail;
- unknown fields fail;
- missing schema fields fail;
- model validation fails on engineering inconsistencies.

## CSV import

CSV is not auto-detected. Define an explicit mapping:

```python
from energologic.protection import (
    CsvColumnMap,
    CsvDeviceSpec,
    CsvImportSpec,
    CsvSettingCardAdapter,
)

columns = CsvColumnMap(
    function_id="function_id",
    function_concept_id="concept",
    function_name="function_name",
    device_id="device_id",
    function_enabled="function_enabled",
    stage_id="stage_id",
    stage_name="stage_name",
    stage_enabled="stage_enabled",
    parameter_id="parameter_id",
    semantic_key="semantic_key",
    role="role",
    value_kind="value_kind",
    value="value",
    unit="unit",
    quantity_kind="quantity_kind",
    basis="basis",
)

spec = CsvImportSpec(
    card_id="setting-card:site:feeder-1",
    card_revision="r1",
    site_id="site:example",
    settings_scope="partial_configuration",
    lifecycle_status="approved",
    protected_object_ids=("line:feeder-1",),
    source_id="source:setting-card:feeder-1",
    source_document_type="setting_card",
    source_title="Example setting export",
    source_revision="r1",
    devices=(
        CsvDeviceSpec(
            id="ied:feeder-1",
            technology="microprocessor",
            software_version="1.0",
        ),
    ),
    columns=columns,
    delimiter=";",
    decimal_separator=",",
    true_tokens=("Вкл",),
    false_tokens=("Откл",),
)

card = CsvSettingCardAdapter(spec).import_text(source_text)
```

If the source uses a different localized boolean vocabulary, change the explicit
token set. Do not expand the generic importer with hidden guesses.

## Adding a real source adapter

Before implementing a vendor/site adapter:

1. identify the authoritative source type and version;
2. determine whether it is an operational summary, partial configuration or full
   configuration;
3. catalogue all fields and units actually present;
4. determine which values are primary, secondary, relative or device-native;
5. define stable protected-object/device/function mappings;
6. record how every output value maps back to a source locator;
7. hash the exact source;
8. fail on ambiguous cells/fields instead of selecting a plausible interpretation;
9. add sanitized golden fixtures and tests;
10. demonstrate that no setting meaning is lost during normalization.

For XLSX, preserve worksheet/cell/range provenance. For vendor parameter files,
preserve exact file hash and software/device compatibility metadata.

Do not parse arbitrary PDF/image content with OCR/LLM in the production critical path.

## Action matrices

WS-9A may store an action association such as:

```text
function/stage -> trip -> breaker:<stable-id>
```

This is configuration data. Importing it must not issue commands, alter switch state
or invoke WS-6.

## Verification

```bash
python -m unittest discover -s tests -v
```
