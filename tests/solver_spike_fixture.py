from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from energologic.core import CanonicalModel, load_model
from energologic.solvers.contracts import (
    ExternalGridParameters,
    LineParameters,
    LoadParameters,
    SolverStudyInput,
    Transformer2WParameters,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "examples" / "ws8-synthetic-network.json"


def state_a_model() -> CanonicalModel:
    return load_model(FIXTURE)


def state_b_model() -> CanonicalModel:
    model = state_a_model()
    changed = []
    for element in model.elements:
        if element.id != "breaker:bus-coupler":
            changed.append(element)
            continue
        attributes = dict(element.attributes)
        attributes["switch_state"] = "closed"
        changed.append(replace(element, attributes=attributes))
    return replace(
        model,
        elements=tuple(changed),
        metadata={**model.metadata, "state": "B"},
    )


def study(model: CanonicalModel | None = None) -> SolverStudyInput:
    return SolverStudyInput(
        model=model or state_a_model(),
        external_grids=(
            ExternalGridParameters(
                canonical_id="source:grid",
                voltage_pu=1.0,
                angle_deg=0.0,
                short_circuit_power_max_va=500_000_000.0,
                rx_max=0.1,
                zero_sequence_r_over_x_max=0.1,
                zero_sequence_x_over_x_max=1.0,
            ),
        ),
        lines=(
            LineParameters(
                canonical_id="line:feed-a",
                length_m=2_000.0,
                resistance_ohm_per_m=0.00012,
                reactance_ohm_per_m=0.00008,
                capacitance_f_per_m=1.0e-11,
                max_current_a=400.0,
                line_type="cable",
                zero_sequence_resistance_ohm_per_m=0.00036,
                zero_sequence_reactance_ohm_per_m=0.00024,
                zero_sequence_capacitance_f_per_m=6.0e-12,
                end_temperature_c=70.0,
            ),
            LineParameters(
                canonical_id="line:feed-b",
                length_m=3_000.0,
                resistance_ohm_per_m=0.00018,
                reactance_ohm_per_m=0.00010,
                capacitance_f_per_m=1.0e-11,
                max_current_a=400.0,
                line_type="cable",
                zero_sequence_resistance_ohm_per_m=0.00054,
                zero_sequence_reactance_ohm_per_m=0.00030,
                zero_sequence_capacitance_f_per_m=6.0e-12,
                end_temperature_c=70.0,
            ),
        ),
        transformers_2w=(
            Transformer2WParameters(
                canonical_id="transformer:t1",
                rated_power_va=5_000_000.0,
                hv_voltage_v=35_000.0,
                lv_voltage_v=400.0,
                short_circuit_voltage_percent=6.0,
                short_circuit_resistance_percent=1.0,
                iron_loss_w=5_000.0,
                no_load_current_percent=0.5,
                phase_shift_deg=30.0,
                vector_group="Dyn",
                zero_sequence_short_circuit_voltage_percent=6.0,
                zero_sequence_short_circuit_resistance_percent=1.0,
                zero_sequence_magnetizing_percent=100.0,
                zero_sequence_magnetizing_r_over_x=0.0,
                zero_sequence_hv_partition=0.9,
            ),
        ),
        loads=(
            LoadParameters(
                canonical_id="load:section-a",
                active_power_w=4_000_000.0,
                reactive_power_var=1_000_000.0,
            ),
            LoadParameters(
                canonical_id="load:lv",
                active_power_w=1_000_000.0,
                reactive_power_var=300_000.0,
            ),
        ),
    )
