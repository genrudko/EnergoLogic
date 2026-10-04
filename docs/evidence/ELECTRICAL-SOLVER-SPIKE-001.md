# ELECTRICAL-SOLVER-SPIKE-001 — Qualification Evidence

Status: **implementation complete; awaiting owner acceptance**  
Issue: #14  
Branch: `solver/electrical-solver-spike-001`  
Draft PR: #15  
Solver qualified: **pandapower 3.5.5**

## 1. Scope result

The spike demonstrates the headless path:

```text
EnergoLogic CanonicalModel
        ↓
solver-neutral SolverStudyInput
        ↓
PandapowerAdapter
        ↓
pandapower 3.5.5
        ↓
normalized EnergoLogic results keyed by canonical IDs
```

No Visio Editor files are changed.

## 2. Synthetic canonical fixture

Fixture:

`examples/ws8-synthetic-network.json`

It contains:

- external grid source;
- 35 kV grid bus;
- feeder A and feeder B buses;
- two 35 kV bus sections;
- two independent feeder cables;
- two incomer circuit breakers;
- a bus-coupler circuit breaker;
- transformer HV disconnector;
- 35/0.4 kV two-winding transformer;
- 35 kV load;
- 0.4 kV load.

State A:

- both incomers closed;
- transformer disconnector closed;
- bus coupler open.

State B changes only the canonical bus-coupler state:

```text
breaker:bus-coupler.switch_state
open → closed
```

No pandapower representation is stored in the fixture.

## 3. Power-flow result

Qualified on the same canonical model with only the bus-coupler state changed.

| Result | State A — coupler open | State B — coupler closed |
|---|---:|---:|
| Section A voltage | 34,967.986 V | 34,972.180 V |
| Section B voltage | 34,981.607 V | 34,972.180 V |
| Section voltage difference | 13.620 V | 0 V |
| Feeder A current | 68.076 A | 58.358 A |
| Feeder B current | 17.532 A | 27.261 A |
| T1 loading | 21.2562 % | 21.2619 % |

The topology signature changes between the two states.

This is the key acceptance fact: changing the **canonical switching state**
changes both effective solver topology and numerical results.

Transformer current is normalized by side:

- T1 HV current: 17.532 A in State A;
- T1 LV current: 1,516.519 A in State A;
- no physically misleading aggregate transformer current is returned.

## 4. Short-circuit result

Fault location:

`bus:section-a-35kv`

Maximum short-circuit case.

### Three-phase fault

| Quantity | Result |
|---|---:|
| `Ik''` | 7,700.125 A |
| `ip` | 17,348.305 A |
| `Ith` | 7,773.477 A |
| short-circuit apparent power | 466.795 MVA |
| feeder A initial branch contribution | 7,700.125 A |

### Two-phase fault

| Quantity | Result |
|---|---:|
| initial current | 6,668.504 A |
| short-circuit apparent power | 134.752 MVA |
| feeder A initial branch contribution | 6,668.504 A |

### Single-phase-to-earth fault

With explicit zero-sequence source, line and transformer data:

| Quantity | Result |
|---|---:|
| initial current | 7,352.760 A |
| feeder A initial branch contribution | 7,352.760 A |

For the 1-phase spike, peak and thermal current were deliberately not claimed
because they were not required to prove API viability, and the backend did not
provide a short-circuit-power value in the observed result. Missing values stay
`None`.

## 5. Independent hand check

A three-phase fault was also applied directly at the 35 kV external-grid bus.

Given:

- `S_sc = 500 MVA`;
- `U_n = 35 kV`.

Independent calculation:

```text
Ik = S_sc / (sqrt(3) × U)
   = 500,000,000 / (sqrt(3) × 35,000)
   = 8,247.860988 A
```

Adapter/pandapower result:

```text
8,247.860988 A
```

Difference is below numerical floating-point noise and well inside the committed
0.5 % analytical acceptance tolerance.

## 6. Golden numerical fixture

Committed golden:

`tests/fixtures/ws8-pandapower-3.5.5-golden.json`

It pins expected values for:

- power flow State A;
- power flow State B;
- 3-phase fault;
- 2-phase fault;
- 1-phase-to-earth fault;
- independent source-bus hand reference.

Tolerances are explicit and are intentionally small enough to detect meaningful
solver/mapping regressions while allowing harmless floating-point variation.

## 7. Unit boundary

Public solver-study parameters use SI-facing EnergoLogic units:

- V;
- A;
- W;
- var;
- VA;
- m;
- ohm / ohm per metre;
- F per metre;
- percent / p.u. where dimensionless representation is appropriate.

The adapter explicitly converts to pandapower's required kV, kA, MW, Mvar,
MVA, km, ohm/km and nF/km representation.

Apparent power has a separate VA/MVA conversion path; it is not mislabeled as
active power.

## 8. Error normalization

Qualified public states exist for:

- success;
- non-converged;
- invalid model;
- unsupported configuration;
- missing parameters;
- solver failure.

Tests explicitly verify that malformed canonical input and missing calculation
parameters return normalized results rather than leaking a Python traceback.

## 9. Dependency and standalone findings

### Upstream runtime dependencies

Pandapower 3.5.5 declares pandas, NetworkX, SciPy, NumPy, packaging, tqdm,
colorama, deepdiff, geojson, typing_extensions and pandera as base dependencies.

The repository keeps them behind the optional
`energologic[solver-pandapower]` extra; the base EnergoLogic package still has
no third-party runtime dependencies.

### Measured Linux installation

Measured on the project VPS, Linux amd64, Python 3.14.4:

- pandapower dependency closure: **25 installed distributions**;
- measured installed dependency files: **356,616,544 bytes (~340 MiB)**;
- full venv/site-packages observed: **~383 MiB**;
- native shared/binary files in the dependency closure: **173**.

Largest installed components in that environment were approximately:

- SciPy: 139.5 MB by distribution file accounting;
- pandas: 72.7 MB;
- NumPy: 68.5 MB;
- pandapower: 38.0 MB;
- NetworkX: 16.4 MB.

### Measured Windows wheel set

A reproducible `pip download` for CPython 3.11 / `win_amd64`,
pandapower 3.5.5 and its resolved base dependency closure produced:

- compressed wheel bundle: **~70 MiB**;
- SciPy wheel: ~35 MiB;
- NumPy wheel: ~13 MiB;
- pandas wheel: ~11 MiB;
- pandapower wheel: ~5.5 MiB.

This excludes:

- the Python runtime itself;
- EnergoLogic application files;
- installer/bootstrapper overhead;
- future OpenDSS/other solver runtime;
- debug symbols/caches.

### Packaging implications

1. A self-contained offline bundle is practical, but the solver stack is not
   small.
2. Native NumPy/SciPy and other binary wheels mean packaging must be qualified
   per Windows architecture/Python ABI.
3. The qualified Windows dependency set is `win_amd64`. Solver process
   bitness therefore must not be implicitly coupled to Visio bitness.
4. For x86 Visio on x64 Windows, the preferred future architecture is an
   out-of-process solver/runtime boundary so the solver can remain x64.
5. A deterministic offline wheelhouse/runtime image is preferable to invoking
   pip on the target machine.
6. `numba` is not required by the baseline adapter. The spike explicitly runs
   balanced power flow with `numba=False`; optional acceleration can be
   evaluated later against footprint and compatibility.
7. Production installer construction is intentionally out of scope here.

A reproducible dependency-size probe is committed as:

`tools/solver_dependency_probe.py`

## 10. pandapower limitations relevant to EnergoLogic

### 10.1 Short-circuit branch results are not equally mature

Pandapower emits an upstream warning that branch short-circuit results are in
beta mode and may be unreliable, especially for transformers.

Consequences:

- line contribution was qualified in this spike;
- transformer branch current must remain side-specific;
- production protection decisions must not rely on unvalidated transformer
  branch-SC values solely because a DataFrame column exists;
- real-site acceptance requires independent reference cases.

### 10.2 Zero-sequence data is a real domain requirement

Single-phase-to-earth short circuit requires zero-sequence source/line data and
transformer vector-group/zero-sequence data.

EnergoLogic cannot infer those values from positive-sequence data. They must
eventually become explicit, validated engineering data with provenance.

### 10.3 Switching-device current is not yet a normalized first-class result

The spike proves that canonical switching state changes topology, but it does
not yet expose current through every circuit breaker/disconnector as a public
result.

If HMI/RZA consumers require breaker current directly, a later bounded item
must qualify pandapower switch-flow calculation or derive current through an
explicit branch representation without losing canonical identity.

### 10.4 Balanced power flow is the qualified production baseline

The spike qualifies `runpp` balanced AC power flow.

Pandapower also exposes asymmetric/three-phase power flow, but it was not
qualified here and must not be treated as production-ready merely because the
API exists.

### 10.5 Unbalanced distribution, neutral, harmonics and long QSTS

These are better candidates for an OpenDSS adapter when EnergoLogic reaches
phase-domain distribution studies. OpenDSS is specifically designed around a
general n-phase nodal model and supports harmonics and long quasi-static
time-series modes.

### 10.6 Dynamics / EMT

Neither this pandapower adapter nor the present EnergoLogic architecture should
be interpreted as an EMT/transient-stability solver.

If future RZA studies require waveform-level transients or detailed dynamic
machine/inverter behavior, use a dedicated solver rather than stretching the
steady-state adapter.

### 10.7 Protection remains separate

Pandapower contains some protection functionality, but EnergoLogic's canonical
architecture requires RZA/protection logic to remain a separate
`Protection Engine`.

Pandapower is a source of electrical quantities, not the source of protection
semantics.

### 10.8 Version pinning matters

The golden is specific to pandapower 3.5.5. Solver upgrades require:

1. dependency review;
2. golden rerun;
3. analytical/reference rerun;
4. Windows/Linux packaging qualification;
5. explicit acceptance before changing the production pin.

## 11. Production recommendation

### Recommendation: YES — pandapower is suitable as the first production solver adapter

Use pandapower first for:

- balanced AC load flow;
- bus voltages and angles;
- line/transformer currents and loadings;
- active/reactive power flows and losses;
- topology changes driven by canonical switching state;
- IEC 60909 short-circuit calculations;
- early equipment/loading checks.

Reasons:

- the adapter boundary is practical;
- stable canonical IDs survive translation and result normalization;
- the solver can run fully headless;
- 3ph, 2ph and 1ph fault calculations were demonstrated;
- packaging is substantial but tractable;
- Python integration is straightforward without contaminating core/domain.

### Add OpenDSS as a second adapter for

- detailed phase-domain/unbalanced distribution studies;
- explicit neutral behavior and neutral-to-earth studies;
- harmonics/interharmonics;
- long QSTS / daily/yearly distribution simulations;
- distribution DER/control cases where OpenDSS's native model is materially
  stronger.

### Use another specialized solver when required for

- EMT/waveform transients;
- high-fidelity transient stability;
- detailed machine/inverter dynamics beyond the accepted study class.

## 12. Verification

VPS qualification, Linux amd64, Python 3.14.4, pandapower 3.5.5:

```text
python -m compileall -q src tests tools
python -m unittest discover -s tests -v
```

Result after functional implementation:

```text
Ran 83 tests
OK
```

Dedicated GitHub CI also installs the optional solver extra on Linux and Windows
and runs the full suite.

Final GitHub Actions result is recorded separately on the Draft PR after the
evidence/documentation commit.

## 13. Primary references used for the spike

- pandapower 3.5.5 project metadata:
  https://raw.githubusercontent.com/e2nIEE/pandapower/v3.5.5/pyproject.toml
- pandapower power-flow documentation:
  https://pandapower.readthedocs.io/en/stable/powerflow/run.html
- pandapower short-circuit documentation:
  https://pandapower.readthedocs.io/en/stable/shortcircuit.html
- pandapower line / short-circuit result documentation:
  https://pandapower.readthedocs.io/en/stable/elements/line.html
- pandapower transformer documentation:
  https://pandapower.readthedocs.io/en/stable/elements/trafo.html
- OpenDSS introduction/capabilities:
  https://opendss.epri.com/IntroductiontoOpenDSS.html
  https://opendss.epri.com/OpenDSSDistributionSystem.html

## 14. Remaining architectural questions

1. What are the production canonical semantics for `line`, `cable`,
   `load`, `external_grid`, generators and shunts?
2. Which positive-, negative- and zero-sequence parameters become canonical
   first-class fields, and what provenance is required?
3. Should solver study parameters live directly on equipment, in a versioned
   electrical-parameter profile, or in Site Profile overlays?
4. How should breaker/disconnector current be normalized and associated with
   terminals without imposing solver topology on canonical topology?
5. What is the production solver process boundary: embedded Python runtime,
   dedicated local service/process, or another IPC host?
6. What versioning policy governs solver adapter contract and numerical goldens?
7. Which study classes mandate OpenDSS versus pandapower?
8. What independent trusted reference set will be used for Kochubeevskaya site
   acceptance?
