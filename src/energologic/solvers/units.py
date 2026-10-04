from __future__ import annotations


def volts_to_kilovolts(value_v: float) -> float:
    return value_v / 1_000.0


def kilovolts_to_volts(value_kv: float) -> float:
    return value_kv * 1_000.0


def amperes_to_kiloamperes(value_a: float) -> float:
    return value_a / 1_000.0


def kiloamperes_to_amperes(value_ka: float) -> float:
    return value_ka * 1_000.0


def watts_to_megawatts(value_w: float) -> float:
    return value_w / 1_000_000.0


def megawatts_to_watts(value_mw: float) -> float:
    return value_mw * 1_000_000.0


def vars_to_megavars(value_var: float) -> float:
    return value_var / 1_000_000.0


def megavars_to_vars(value_mvar: float) -> float:
    return value_mvar * 1_000_000.0


def watts_to_kilowatts(value_w: float) -> float:
    return value_w / 1_000.0


def metres_to_kilometres(value_m: float) -> float:
    return value_m / 1_000.0


def ohm_per_metre_to_ohm_per_kilometre(value: float) -> float:
    return value * 1_000.0


def farad_per_metre_to_nanofarad_per_kilometre(value: float) -> float:
    return value * 1_000_000_000_000.0

def volt_amperes_to_megavolt_amperes(value_va: float) -> float:
    return value_va / 1_000_000.0


def megavolt_amperes_to_volt_amperes(value_mva: float) -> float:
    return value_mva * 1_000_000.0
