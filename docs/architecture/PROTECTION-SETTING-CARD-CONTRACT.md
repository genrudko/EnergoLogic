# Protection Setting Card Contract v1

Status: **Proposed in PROTECTION-SETTING-IMPORT-001 / Draft PR #22**  
Workstream: **WS-9A — Protection setting-card importer / data model**

## 1. Purpose

This contract defines the source-neutral representation used to import protection/RZA
settings into EnergoLogic.

It is deliberately **not** a protection engine.

```text
authoritative source
        ↓
source adapter
        ↓
ProtectionSettingCard v1
        ↓
future WS-9B protection execution
```

The contract records what is configured, where the value came from, what unit/basis
the source used, and what equipment/function associations the source states.

It does not determine whether a protection function picks up, resets, times out or
trips under a measured electrical condition.

## 2. Normative design basis

### Russian setting documentation is not one document type

The Rules approved by Ministry of Energy Order No. 100 dated 13.02.2019 are used in
the current verified revision of 15.01.2024 (including the amendment introduced by
Ministry of Energy Order No. 7 dated 15.01.2024). They distinguish several artifacts
with different completeness and purposes:

- dispatcher-centre setting assignments;
- owner setting assignments;
- manufacturer setting blanks / methods;
- setting cards;
- parameter files and device documentation.

The Rules define a **setting card** as operationally readable technical data about
main operating parameters and algorithms needed by dispatching/operational personnel.

They separately define the owner's setting assignment as a document containing the
full list of settings and operating algorithms in accordance with manufacturer
documentation.

Therefore EnergoLogic must never infer "full device configuration" merely because the
source is called a setting card.

### Primary/secondary/relative quantities are identity-bearing metadata

Order No. 100 requires settings in dispatcher-centre assignments to be specified in
primary quantities, with relative units or secondary quantities used only when the
specific device cannot accept primary quantities.

Consequently, the setting basis is stored explicitly:

- `primary`;
- `secondary`;
- `relative`;
- `device_native`;
- `not_applicable`.

Unit normalization does not change this basis.

For example:

```text
source: 5 A secondary
normalized unit: 5 A
basis: secondary
```

is **not** converted to a primary ampere value unless a future explicit transformation
has authoritative CT/VT data and provenance. WS-9A implements no such transformation.

### Microprocessor-device identity includes software/configuration context

For a `full_configuration` of a microprocessor device, the v1 validator requires an
explicit software version.

Parameter files are modeled as source documents and may be associated with the device.
Their bytes/content are not interpreted generically by this work item.

### IEC 60255 is functional evidence, not an execution implementation

ГОСТ IEC 60255-151-2014 remains applicable to over/under-current protection and
specifies functional/measuring/time characteristics.

WS-9A uses this only to justify representing settings such as pickup and delay as
typed data. Algorithms, timers, return/reset behavior and trip execution belong to
WS-9B.

## 3. Completeness scope

Every setting card declares exactly one:

- `operational_summary` — operationally useful subset; must not be treated as a
  complete IED configuration;
- `partial_configuration` — engineering subset larger than an operational summary,
  but explicitly incomplete;
- `full_configuration` — source claims the complete configuration required by this
  imported model scope.

The importer does not promote one scope to another.

## 4. Provenance

Each source document records:

- stable source ID;
- document type;
- title;
- revision;
- SHA-256;
- issue date when known;
- source URI/reference when available;
- notes.

Every imported device, protection function, stage, setting parameter and action
association carries one or more source references.

A source reference contains:

- `source_id`;
- locator type;
- locator text.

Supported locators include JSON pointer, CSV row/cell, spreadsheet cell/range, page,
vendor path and document-level evidence.

This is designed so a future operator/reviewer can trace a normalized setting back to
the exact source location.

## 5. Setting values

The model supports:

- `quantity`;
- `boolean`;
- `enum`;
- `text`.

For a quantity, both source and normalized representation are stored:

```text
raw_text
source_value
source_unit
quantity_kind
basis
normalized_value
normalized_unit
```

Example:

```text
raw_text = "1,250 кА"
source_value = "1.25"
source_unit = "кА"
quantity_kind = "current"
basis = "primary"
normalized_value = "1250"
normalized_unit = "A"
```

`raw_text` preserves source formatting. Decimal normalization uses
`decimal.Decimal`; floating-point conversion is not used.

The v1 controlled quantities include current, voltage, time, frequency, impedance,
active/reactive power, angle, ratio and scalar.

## 6. Measurement inputs, functions, stages and actions

Measured-quantity references are explicit configuration data rather than free-form
labels. A `MeasurementInput` records:

- stable input ID;
- semantic key;
- quantity kind;
- basis (`primary`, `secondary`, etc.);
- source label;
- optional protected-object / terminal reference;
- provenance.

A protection function references zero or more measurement inputs by stable ID.
Measurement inputs are **function-scoped in v1**. A stage does not carry an independent
measurement-input list; it inherits the function's configured measurement context.
Introducing stage-specific channels later requires an explicit contract change.

A protection function contains:

- stable function ID;
- controlled `protection.*` concept ID;
- original source name;
- device ID;
- explicit enabled state or unknown (`null`);
- measurement-input references;
- function-level settings;
- zero or more stages;
- zero or more action associations;
- provenance.

A stage has its own stable ID, source name, enabled state, parameters/actions and
provenance.

An action is **configuration data only**:

```text
action_type = trip
target_kind = equipment
target_id = breaker:...
```

This does not operate the breaker.

Equipment target IDs are preserved but are not currently validated against a site
canonical model because Gate A/site-profile protection associations are not yet a
merged production contract.

## 7. Import adapters

### JSON

The JSON adapter:

- rejects duplicate object keys;
- rejects fields outside the versioned schema shape;
- requires all schema fields;
- validates the decoded model;
- rejects normalized values that do not recompute exactly.

### Configurable CSV

The generic CSV adapter requires an explicit `CsvImportSpec`:

- delimiter;
- decimal separator;
- column mapping;
- true/false token sets;
- device/source metadata.

It never guesses column names, decimal conventions or localized boolean strings.

The generic CSV adapter currently imports parameter rows. Source-specific action
matrices and richer structures should be implemented as explicit adapters once real
source formats are available.

### Future XLSX / vendor / parameter-file adapters

A vendor-specific adapter must:

1. identify the exact source/version it supports;
2. use explicit mappings;
3. preserve source locators and exact source hash;
4. fail on ambiguous/missing engineering values;
5. output this source-neutral model;
6. add golden fixtures from appropriately sanitized/approved source examples.

No OCR or LLM interpretation is allowed in the critical import path.

## 8. WS-6 / WS-9B boundary

WS-9A is intentionally independent from WS-6.

It may store:

- protected-object IDs;
- configured target IDs;
- setting parameters;
- function/stage enable state.

It does not ask whether a network section is energized and does not consume an event
timeline.

WS-9B may later consume the setting model together with measured quantities and
Gate-E event semantics.

## 9. Terminology boundary

Protection function IDs use the controlled English namespace expected by WS-2, for
example:

- `protection.overcurrent`;
- `protection.instantaneous_overcurrent`;
- `protection.earth_fault`;
- `protection.breaker_failure`.

The v1 WS-9A branch does not import or depend on the unmerged WS-2 runtime. Integration
is by stable identifier contract.

## 10. Failure policy

WS-9A fails closed on information that would change engineering meaning.

Examples:

- unit incompatible with quantity kind;
- unsupported unit;
- non-finite number;
- negative numeric time delay;
- unknown source provenance;
- duplicate stable ID;
- duplicate protected-object ID;
- unknown/extra JSON field;
- normalized-value mismatch;
- missing software version for a claimed full microprocessor configuration;
- inconsistent repeated CSV function/stage identity;
- unconfigured localized boolean token.

Missing information is not guessed.


## 11. Current qualification status

The contract is qualified with a synthetic fixture covering:

- maximum/overcurrent protection;
- instantaneous overcurrent / current cutoff;
- earth-fault protection;
- breaker-failure settings/actions;
- phase-current and residual-current measurement inputs.

The fixture is deliberately synthetic and is not site setting data.

The runtime and JSON schema are both fail-closed. A regression specifically proves
that `measurement_input_ids` serialize on a protection function and do not leak into
the stage shape.
