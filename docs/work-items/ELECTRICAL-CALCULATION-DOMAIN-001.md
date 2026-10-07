# ELECTRICAL-CALCULATION-DOMAIN-001

Status: **IN PROGRESS — Draft candidate, not accepted**
Workstreams: WS-1 / WS-8
Issue: [#31](https://github.com/genrudko/EnergoLogic/issues/31)
Branch: `domain/electrical-calculation-domain-001`

## Objective

Qualify the separate `electrical-calculation-v1` engineering-facts profile and materialize it to the **existing** Gate-D `SolverStudyInput`. Canonical model owns identity, topology and switching state; profile owns explicit SI calculation values, state and provenance; solver-neutral DTO is ephemeral.

## Bounded scope

- Production semantics for external grid/source, bus, line/cable, load, two-winding transformer and switch/breaker conduction.
- Exact voltages, rated values, positive- and explicitly known zero-sequence quantities.
- Parameter states known/unknown/not_applicable; absent means missing.
- Deterministic, validation-gated materialization with canonical-ID linkage and golden fixture.
- Provenance-preserving normalized export, tests and evidence.

## Exclusions

No `electrical-v1` silent mutation, pandapower schema leakage, phase-neutral topology, generator/motor/3W transformer/tap changer, runtime host, site data, Visio, or protection integration.

## Acceptance gates

- [ ] Determinism across canonical/profile ordering and normalized fingerprint
- [ ] Independent domain and solver-neutral Gate-D materializer
- [ ] Fail-closed electrical and sequence validation
- [ ] Source locator / provenance round trip
- [ ] End-to-end synthetic topology and golden
- [ ] Existing regression test suite green
- [ ] CI status recorded in evidence
- [ ] Owner review/acceptance
- [ ] Ready for Review — owner command only
- [ ] Merge — owner command only

**Historical/current note:** this file is an active Draft record, not an accepted/merged baseline.
