from __future__ import annotations

from dataclasses import replace
import importlib.util
import json
from pathlib import Path
import unittest

from energologic.core import load_model, CanonicalModel, Element
from energologic.domain.calculation import (
    CalculationDecodeError, CalculationValidationError,
    decode_calculation_profile, load_calculation_profile,
    calculation_profile_to_data, validate_calculation,
)
from energologic.solvers.materialization import materialize_study
from energologic.solvers.contracts import SolverStatus
from energologic.solvers.pandapower_adapter import PandapowerAdapter


ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "examples/electrical-calculation-v1.synthetic-network.json"
PROFILE_PATH = ROOT / "examples/electrical-calculation-v1.synthetic-profile.json"
GOLDEN_PATH = ROOT / "tests/fixtures/electrical-calculation-v1.golden.json"


def fixture():
    return load_model(MODEL_PATH), load_calculation_profile(PROFILE_PATH)


def mutated(profile, canonical_id, key, fact):
    data = calculation_profile_to_data(profile)
    for item in data["equipment"]:
        if item["canonical_id"] == canonical_id:
            if fact is None:
                del item["parameters"][key]
            else:
                item["parameters"][key] = fact
            break
    return decode_calculation_profile(data)


def codes(model, profile, study_type="power_flow"):
    return {issue.code for issue in validate_calculation(model, profile, study_type=study_type)}


class CalculationDomainTests(unittest.TestCase):
    def test_end_to_end_gate_d_and_complete_golden(self):
        model, profile = fixture()
        result = materialize_study(model, profile)
        self.assertEqual(result.normalized_json, GOLDEN_PATH.read_text(encoding="utf-8"))
        self.assertEqual(len(result.fingerprint), 64)
        self.assertEqual(len(result.solver_input.external_grids), 1)
        self.assertEqual(len(result.solver_input.transformers_2w), 1)
        self.assertEqual(len(result.solver_input.lines), 1)
        self.assertEqual(len(result.solver_input.loads), 1)
        self.assertEqual(result.solver_input.lines[0].line_type, "cable")
        self.assertEqual(result.solver_input.transformers_2w[0].hv_voltage_v, 35000.0)
        self.assertEqual(result.solver_input.transformers_2w[0].lv_voltage_v, 400.0)
        self.assertEqual(result.solver_input.transformers_2w[0].vector_group, "Dyn")
        manifest = json.loads(result.normalized_json)
        provenance = manifest["calculation_facts"]["equipment"]
        self.assertIn("synthetic:calc-v1", json.dumps(provenance))
        self.assertEqual(manifest["fingerprint_sha256"], result.fingerprint)
        self.assertNotIn("pandapower", result.normalized_json)

    def test_permutations_do_not_change_manifest_or_fingerprint(self):
        model, profile = fixture()
        base = materialize_study(model, profile)
        reversed_connections = tuple(
            replace(conn, endpoints=tuple(reversed(conn.endpoints)))
            for conn in reversed(model.connections)
        )
        reversed_model = replace(model, elements=tuple(reversed(model.elements)),
                                 connections=reversed_connections)
        reversed_profile = replace(profile, equipment=tuple(
            replace(e, parameters=dict(reversed(list(e.parameters.items()))))
            for e in reversed(profile.equipment)))
        alt = materialize_study(reversed_model, reversed_profile)
        self.assertEqual(alt.normalized_json, base.normalized_json)
        self.assertEqual(alt.fingerprint, base.fingerprint)

    def test_switch_conduction_is_not_inferred(self):
        model, profile = fixture()
        switch = Element("breaker:x", "circuit_breaker",
                         terminals=(), attributes={"nominal_voltage_v":400})
        invalid = replace(model, elements=model.elements + (switch,))
        self.assertIn("invalid_calculation_terminal_contract", codes(invalid, profile))
        self.assertIn("invalid_switch_state", codes(invalid, profile))

    def test_version_and_id_fail_closed(self):
        model, profile = fixture()
        self.assertIn("calculation_model_id_mismatch",
                      codes(model, replace(profile, model_id="other")))
        with self.assertRaises(CalculationDecodeError):
            decode_calculation_profile({**calculation_profile_to_data(profile), "version":"v2"})

    def test_missing_and_explicit_unknown_and_not_applicable_differ(self):
        model, profile = fixture()
        for fact, expected in (
            (None, "missing_required_parameter"),
            ({"state":"unknown"}, "unknown_required_parameter"),
            ({"state":"not_applicable"}, "not_applicable_required_parameter"),
        ):
            changed = mutated(profile, "source:grid", "short_circuit_power_max_va", fact)
            self.assertIn(expected, codes(model, changed))
            with self.assertRaises(CalculationValidationError):
                materialize_study(model, changed)

    def test_invalid_rated_and_impedance_values(self):
        model, profile = fixture()
        raw = calculation_profile_to_data(profile)
        for e in raw["equipment"]:
            if e["canonical_id"] == "transformer:t1":
                e["parameters"]["short_circuit_resistance_percent"]["value"] = 7.0
                e["parameters"]["rated_power_va"]["value"] = -100.0
        bad = decode_calculation_profile(raw)
        self.assertIn("invalid_transformer_impedance", codes(model, bad))
        self.assertIn("invalid_calculation_parameter", codes(model, bad))

    def test_zero_line_impedance_is_rejected(self):
        model, profile = fixture()
        raw = calculation_profile_to_data(profile)
        for e in raw["equipment"]:
            if e["kind"] == "line":
                e["parameters"]["resistance_ohm_per_m"]["value"] = 0
                e["parameters"]["reactance_ohm_per_m"]["value"] = 0
        self.assertIn("invalid_line_impedance", codes(model, decode_calculation_profile(raw)))

    def test_voltage_missing_and_mismatches(self):
        model, profile = fixture()
        changed = tuple(replace(e, attributes={}) if e.id=="bus:lv-400v" else e for e in model.elements)
        self.assertIn("missing_exact_nominal_voltage",
                      codes(replace(model,elements=changed),profile))
        changed = tuple(replace(e, attributes={"nominal_voltage_v": 380}) if e.id=="bus:lv-400v" else e for e in model.elements)
        self.assertIn("incompatible_terminal_node_voltage",
                      codes(replace(model,elements=changed),profile))

    def test_voltage_class_not_promoted_to_exact(self):
        model, profile = fixture()
        changed = tuple(replace(e, attributes={"voltage_class":"below_3000_v"})
                        if e.id=="bus:lv-400v" else e for e in model.elements)
        self.assertIn("missing_exact_nominal_voltage",
                      codes(replace(model,elements=changed),profile))

    def test_missing_sequence_and_explicit_capability_limit(self):
        model, profile = fixture()
        changed = mutated(profile, "source:grid", "zero_sequence_x_over_x_max",
                          {"state":"unknown"})
        issues = codes(model, changed, "short_circuit_1ph")
        self.assertIn("missing_sequence_parameter", issues)
        self.assertIn("unsupported_phase_neutral_topology", issues)
        self.assertIn("unsupported_sequence_study", codes(model, profile, "short_circuit_2ph"))
        self.assertEqual(codes(model, profile, "short_circuit_3ph"), set())

    def test_invalid_boolean_nan_and_unprovenanced_facts(self):
        model, profile = fixture()
        raw = calculation_profile_to_data(profile)
        for e in raw["equipment"]:
            if e["kind"]=="external_grid":
                e["parameters"]["rx_max"]["value"] = True
                del e["parameters"]["angle_deg"]["provenance"]
        with self.assertRaises(CalculationDecodeError):
            decode_calculation_profile(raw)
        raw = calculation_profile_to_data(profile)
        for e in raw["equipment"]:
            if e["kind"]=="external_grid":
                e["parameters"]["rx_max"]["value"] = True
        with self.assertRaises(CalculationDecodeError):
            decode_calculation_profile(raw)

    def test_unknown_zero_sequence_is_never_filled(self):
        model, profile = fixture()
        changed = mutated(profile, "line:feed-a",
                          "zero_sequence_reactance_ohm_per_m", {"state":"unknown"})
        study = materialize_study(model, changed)
        self.assertIsNone(study.solver_input.lines[0].zero_sequence_reactance_ohm_per_m)
        self.assertIn('"state":"unknown"', study.normalized_json)

    def test_foreign_field_and_unsupported_kind_fail(self):
        model, profile = fixture()
        raw = calculation_profile_to_data(profile)
        raw["equipment"][0]["parameters"]["pandapower_bus_index"] = {"state":"unknown"}
        self.assertIn("unknown_calculation_parameter", codes(model, decode_calculation_profile(raw)))


@unittest.skipUnless(importlib.util.find_spec("pandapower"), "pandapower solver extra absent")
class OptionalAdapterIntegrationTests(unittest.TestCase):
    def test_new_domain_drives_existing_pandapower_power_flow(self):
        model, profile = fixture()
        result = PandapowerAdapter().power_flow(materialize_study(model, profile).solver_input)
        self.assertEqual(result.status, SolverStatus.SUCCESS, result.errors)
        self.assertEqual({x.canonical_id for x in result.buses},
                         {e.id for e in model.elements if e.kind == "bus"})
        self.assertEqual({x.canonical_id for x in result.branches},
                         {"line:feed-a", "transformer:t1"})


if __name__=="__main__":
    unittest.main()
