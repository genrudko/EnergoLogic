from __future__ import annotations

import ast
from dataclasses import replace
from pathlib import Path
import unittest

from energologic.core import CanonicalModel, Element, Terminal, validate_model
from energologic.solvers.contracts import (
    SolverStatus,
    SolverStudyInput,
)
from energologic.solvers.pandapower_adapter import PandapowerAdapter
from energologic.solvers.units import (
    amperes_to_kiloamperes,
    farad_per_metre_to_nanofarad_per_kilometre,
    kiloamperes_to_amperes,
    kilovolts_to_volts,
    megavars_to_vars,
    megawatts_to_watts,
    metres_to_kilometres,
    ohm_per_metre_to_ohm_per_kilometre,
    vars_to_megavars,
    volts_to_kilovolts,
    watts_to_megawatts,
)

from solver_spike_fixture import state_a_model, state_b_model, study


ROOT = Path(__file__).resolve().parents[1]


class SolverContractTests(unittest.TestCase):
    def test_synthetic_network_is_structurally_canonical_and_solver_independent(self):
        model = state_a_model()
        self.assertEqual(validate_model(model), ())
        kinds = {element.kind for element in model.elements}
        self.assertTrue(
            {
                "external_grid",
                "bus",
                "circuit_breaker",
                "disconnector",
                "transformer_2w",
                "line",
                "load",
            }.issubset(kinds)
        )
        self.assertGreaterEqual(
            sum(
                element.kind in {"circuit_breaker", "disconnector"}
                for element in model.elements
            ),
            3,
        )
        fixture_text = (
            ROOT / "examples" / "ws8-synthetic-network.json"
        ).read_text(encoding="utf-8")
        self.assertNotIn("pandapower", fixture_text.lower())

    def test_state_b_changes_only_canonical_coupler_state_and_metadata(self):
        state_a = state_a_model()
        state_b = state_b_model()
        a_elements = {item.id: item for item in state_a.elements}
        b_elements = {item.id: item for item in state_b.elements}

        self.assertEqual(
            a_elements["breaker:bus-coupler"].attributes["switch_state"],
            "open",
        )
        self.assertEqual(
            b_elements["breaker:bus-coupler"].attributes["switch_state"],
            "closed",
        )
        for element_id in sorted(set(a_elements) - {"breaker:bus-coupler"}):
            self.assertEqual(a_elements[element_id], b_elements[element_id])

    def test_solver_contract_uses_si_units_with_explicit_conversions(self):
        self.assertEqual(volts_to_kilovolts(35_000.0), 35.0)
        self.assertEqual(kilovolts_to_volts(35.0), 35_000.0)
        self.assertEqual(amperes_to_kiloamperes(750.0), 0.75)
        self.assertEqual(kiloamperes_to_amperes(0.75), 750.0)
        self.assertEqual(watts_to_megawatts(7_500_000.0), 7.5)
        self.assertEqual(megawatts_to_watts(7.5), 7_500_000.0)
        self.assertEqual(vars_to_megavars(2_500_000.0), 2.5)
        self.assertEqual(megavars_to_vars(2.5), 2_500_000.0)
        self.assertEqual(metres_to_kilometres(1_500.0), 1.5)
        self.assertAlmostEqual(
            ohm_per_metre_to_ohm_per_kilometre(0.00012),
            0.12,
            places=12,
        )
        self.assertEqual(
            farad_per_metre_to_nanofarad_per_kilometre(1.0e-11),
            10.0,
        )

    def test_core_and_domain_never_import_pandapower(self):
        for directory in (
            ROOT / "src" / "energologic" / "core",
            ROOT / "src" / "energologic" / "domain",
        ):
            for path in sorted(directory.rglob("*.py")):
                tree = ast.parse(path.read_text(encoding="utf-8"))
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        imported = {alias.name for alias in node.names}
                        self.assertNotIn("pandapower", imported, path)
                    if isinstance(node, ast.ImportFrom):
                        self.assertFalse(
                            (node.module or "").startswith("pandapower"),
                            path,
                        )

    def test_invalid_structural_model_is_normalized_without_raw_exception(self):
        bad = CanonicalModel(
            schema_version="0.1",
            model_id="bad",
            elements=(
                Element(
                    id="bus",
                    kind="bus",
                    terminals=(Terminal("node"),),
                    attributes={"nominal_voltage_v": 35_000},
                ),
                Element(
                    id="bus",
                    kind="bus",
                    terminals=(Terminal("node"),),
                    attributes={"nominal_voltage_v": 35_000},
                ),
            ),
            connections=(),
        )
        result = PandapowerAdapter().power_flow(SolverStudyInput(model=bad))
        self.assertEqual(result.status, SolverStatus.INVALID_MODEL)
        self.assertTrue(result.errors)
        self.assertNotIn("Traceback", result.errors[0].message)

    def test_missing_parameters_are_normalized_before_backend_import(self):
        base = study()
        missing = replace(base, lines=base.lines[:-1])
        result = PandapowerAdapter().power_flow(missing)
        self.assertEqual(result.status, SolverStatus.MISSING_PARAMETERS)
        self.assertEqual(result.errors[0].code, "missing_solver_parameters")


if __name__ == "__main__":
    unittest.main()
