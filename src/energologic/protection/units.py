from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation


class UnitNormalizationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class UnitSpec:
    quantity_kind: str
    canonical_unit: str
    factor: Decimal


_UNIT_SPECS: dict[str, UnitSpec] = {}


def _register(
    quantity_kind: str,
    canonical_unit: str,
    factor: str,
    *aliases: str,
) -> None:
    spec = UnitSpec(quantity_kind, canonical_unit, Decimal(factor))
    for alias in aliases:
        _UNIT_SPECS[alias] = spec


_register("current", "A", "1", "A", "А")
_register("current", "A", "1000", "kA", "кА")
_register("current", "A", "0.001", "mA", "мА")
_register("voltage", "V", "1", "V", "В")
_register("voltage", "V", "1000", "kV", "кВ")
_register("voltage", "V", "0.001", "mV", "мВ")
_register("time", "s", "1", "s", "с")
_register("time", "s", "0.001", "ms", "мс")
_register("frequency", "Hz", "1", "Hz", "Гц")
_register("frequency", "Hz", "1000", "kHz", "кГц")
_register("frequency", "Hz", "0.001", "mHz", "мГц")
_register("impedance", "ohm", "1", "ohm", "Ω", "Ом")
_register("impedance", "ohm", "1000", "kohm", "kΩ", "кОм")
_register("power_active", "W", "1", "W", "Вт")
_register("power_active", "W", "1000", "kW", "кВт")
_register("power_active", "W", "1000000", "MW", "МВт")
_register("power_reactive", "var", "1", "var", "вар")
_register("power_reactive", "var", "1000", "kvar", "квар")
_register("power_reactive", "var", "1000000", "Mvar", "Мвар")
_register("angle", "deg", "1", "deg", "°")
_register("ratio", "pu", "1", "pu", "p.u.", "о.е.")
_register("ratio", "pu", "0.01", "%")
_register("scalar", "1", "1", "1")


QUANTITY_KINDS = frozenset(spec.quantity_kind for spec in _UNIT_SPECS.values())
CONTROLLED_UNITS = frozenset(_UNIT_SPECS)


def canonical_decimal(value: Decimal) -> str:
    if not value.is_finite():
        raise UnitNormalizationError("quantity value must be finite")
    if value == 0:
        return "0"
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    if text == "-0":
        return "0"
    return text


def parse_decimal_source(
    value: str,
    *,
    decimal_separator: str = ".",
) -> Decimal:
    if decimal_separator not in {".", ","}:
        raise UnitNormalizationError(
            "decimal_separator must be '.' or ','"
        )
    if not isinstance(value, str) or not value.strip():
        raise UnitNormalizationError("quantity source value must be non-empty text")

    text = value.strip()
    if decimal_separator == ",":
        if "." in text and "," in text:
            raise UnitNormalizationError(
                "mixed decimal separators are not accepted"
            )
        text = text.replace(",", ".")
    elif "," in text:
        raise UnitNormalizationError(
            "comma decimal value requires decimal_separator=','"
        )

    try:
        result = Decimal(text)
    except InvalidOperation as exc:
        raise UnitNormalizationError(
            f"invalid decimal quantity value: {value!r}"
        ) from exc

    if not result.is_finite():
        raise UnitNormalizationError("quantity value must be finite")
    return result


def normalize_quantity(
    source_value: str,
    source_unit: str,
    quantity_kind: str,
    *,
    decimal_separator: str = ".",
) -> tuple[str, str, str]:
    if not isinstance(source_unit, str) or not source_unit:
        raise UnitNormalizationError("source unit is required")
    spec = _UNIT_SPECS.get(source_unit)
    if spec is None:
        raise UnitNormalizationError(
            f"unsupported controlled unit: {source_unit!r}"
        )
    if spec.quantity_kind != quantity_kind:
        raise UnitNormalizationError(
            f"unit {source_unit!r} belongs to {spec.quantity_kind!r}, "
            f"not {quantity_kind!r}"
        )

    source_decimal = parse_decimal_source(
        source_value,
        decimal_separator=decimal_separator,
    )
    normalized = source_decimal * spec.factor
    canonical_source = canonical_decimal(source_decimal)
    canonical_normalized = canonical_decimal(normalized)
    return canonical_source, canonical_normalized, spec.canonical_unit
