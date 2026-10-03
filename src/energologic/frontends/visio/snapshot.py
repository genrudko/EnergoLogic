from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping


@dataclass(frozen=True, slots=True)
class VisioGeometry:
    """Projection-only geometry. Never contributes to canonical electrical identity."""

    pin_x: float = 0.0
    pin_y: float = 0.0
    width: float = 0.0
    height: float = 0.0


@dataclass(frozen=True, slots=True)
class VisioVtdStateSnapshot:
    """Qualified native VTD state needed for deterministic switch mapping."""

    main_action_active: bool | None = None
    cart_position_value: int | None = None


@dataclass(frozen=True, slots=True)
class VisioShapeSnapshot:
    """Transport-neutral snapshot of one Visio shape relevant to an import slice."""

    shape_id: int
    master_name: str
    text: str = ""
    shape_data: Mapping[str, str] = field(default_factory=dict)
    parent_shape_id: int | None = None
    geometry: VisioGeometry = field(default_factory=VisioGeometry)
    vtd_state: VisioVtdStateSnapshot | None = None


@dataclass(frozen=True, slots=True)
class VisioGlueSnapshot:
    """One Visio glue relation as reported by get_connections."""

    from_shape_id: int
    from_cell: str
    to_shape_id: int
    to_cell: str


@dataclass(frozen=True, slots=True)
class VisioPageSnapshot:
    page_name: str
    shapes: tuple[VisioShapeSnapshot, ...]
    connections: tuple[VisioGlueSnapshot, ...]
