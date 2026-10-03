from __future__ import annotations

from dataclasses import dataclass
import json
import math
import re
from typing import Literal

from .identity import VisioIdentityError, validate_cell_id
from .snapshot import VisioGlueSnapshot, VisioPageSnapshot, VisioShapeSnapshot


_MM_PER_INCH = 25.4
_CONNECTION_ROW = re.compile(r"^Connections\.(\d+)\.X$", re.IGNORECASE)


class VisioQolError(ValueError):
    """Deterministic planning failure for Visio editor QoL operations."""

    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(f"{code}: {message}")


@dataclass(frozen=True, slots=True)
class VisioCellAnchor:
    shape_id: int
    x_mm: float
    y_mm: float
    bus_shape_id: int
    bus_terminal_shape_id: int
    bus_terminal_nt: int
    bus_slot_index: int
    source_endpoint: Literal["begin", "end"]
    target_connection_row: int


@dataclass(frozen=True, slots=True)
class VisioCell:
    page_name: str
    seed_shape_id: int
    anchor: VisioCellAnchor
    member_shape_ids: tuple[int, ...]
    electrical_core_shape_ids: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class VisioDuplicateExecutionRequest:
    """Bounded arguments for the qualified bridge duplicate primitive."""

    tool_name: str
    shape_ids_json: str
    dx_mm: float
    dy_mm: float
    select_result: bool
    glue_items_json: str
    new_cell_id: str
    identity_reset_required: bool

    def arguments(self) -> dict[str, object]:
        return {
            "shape_ids_json": self.shape_ids_json,
            "dx_mm": self.dx_mm,
            "dy_mm": self.dy_mm,
            "select_result": self.select_result,
            "glue_items_json": self.glue_items_json,
            "new_cell_id": self.new_cell_id,
        }


@dataclass(frozen=True, slots=True)
class VisioConnectionPoint:
    target_shape_id: int
    target_connection_row: int
    x_mm: float
    y_mm: float


@dataclass(frozen=True, slots=True)
class VisioGlueCandidate:
    target_shape_id: int
    target_connection_row: int
    x_mm: float
    y_mm: float
    distance_mm: float


@dataclass(frozen=True, slots=True)
class VisioGlueRepairPlan:
    source_shape_id: int
    source_endpoint: Literal["begin", "end"]
    source_x_mm: float
    source_y_mm: float
    candidate: VisioGlueCandidate
    tolerance_mm: float


@dataclass(frozen=True, slots=True)
class VisioGlueExecutionRequest:
    tool_name: str
    items_json: str

    def arguments(self) -> dict[str, object]:
        return {"items_json": self.items_json}


@dataclass(frozen=True, slots=True)
class VisioMoveExecutionRequest:
    """Bounded arguments for the qualified bridge exact-move primitive."""

    tool_name: str
    shape_ids_json: str
    dx_mm: float
    dy_mm: float
    select_result: bool
    detach_items_json: str
    glue_items_json: str

    def arguments(self) -> dict[str, object]:
        return {
            "shape_ids_json": self.shape_ids_json,
            "dx_mm": self.dx_mm,
            "dy_mm": self.dy_mm,
            "select_result": self.select_result,
            "detach_items_json": self.detach_items_json,
            "glue_items_json": self.glue_items_json,
        }


@dataclass(frozen=True, slots=True)
class DuplicateCellPlan:
    page_name: str
    source_cell: VisioCell
    direction: Literal["left", "right"]
    pitch_mm: float
    dx_mm: float
    dy_mm: float
    target_bus_terminal_shape_id: int
    target_bus_terminal_nt: int
    source_bus_slot_index: int
    target_bus_slot_index: int
    target_connection_row: int
    source_endpoint: Literal["begin", "end"]
    new_cell_id: str
    reset_identity: bool = True

    @property
    def shape_ids(self) -> tuple[int, ...]:
        return self.source_cell.member_shape_ids


@dataclass(frozen=True, slots=True)
class MoveCellPlan:
    page_name: str
    source_cell: VisioCell
    direction: Literal["left", "right"]
    pitch_mm: float
    dx_mm: float
    dy_mm: float
    source_bus_terminal_shape_id: int
    source_bus_terminal_nt: int
    target_bus_terminal_shape_id: int
    target_bus_terminal_nt: int
    source_bus_slot_index: int
    target_bus_slot_index: int
    target_connection_row: int
    source_endpoint: Literal["begin", "end"]

    @property
    def shape_ids(self) -> tuple[int, ...]:
        return self.source_cell.member_shape_ids


def _mm(value_in: float) -> float:
    return float(value_in) * _MM_PER_INCH


def _shape_index(snapshot: VisioPageSnapshot) -> dict[int, VisioShapeSnapshot]:
    result: dict[int, VisioShapeSnapshot] = {}
    for shape in snapshot.shapes:
        if shape.shape_id in result:
            raise VisioQolError(
                "duplicate_shape_id",
                f"page {snapshot.page_name!r} contains duplicate shape id {shape.shape_id}",
            )
        result[shape.shape_id] = shape
    return result


def _user_int(shape: VisioShapeSnapshot, name: str) -> int:
    raw = shape.user_cells.get(name)
    if raw is None:
        raise VisioQolError(
            "missing_user_cell",
            f"shape {shape.shape_id} has no User.{name} snapshot",
        )
    value = str(raw).strip()
    if value.startswith("="):
        value = value[1:].strip()
    try:
        parsed = int(value)
    except ValueError as exc:
        raise VisioQolError(
            "invalid_user_cell",
            f"shape {shape.shape_id} User.{name} must be an integer, got {raw!r}",
        ) from exc
    return parsed



def _bus_slot_index(shape: VisioShapeSnapshot) -> int:
    raw = shape.user_cells.get("slot")
    if raw is None:
        raw = shape.text
    value = str(raw).strip()
    if value.startswith("="):
        value = value[1:].strip()
    try:
        parsed = int(value)
    except ValueError as exc:
        raise VisioQolError(
            "missing_bus_slot_index",
            (
                f"bus terminal shape {shape.shape_id} must expose an integer slot "
                f"through User.slot or its text; got {raw!r}"
            ),
        ) from exc
    if parsed <= 0:
        raise VisioQolError(
            "invalid_bus_slot_index",
            f"bus terminal shape {shape.shape_id} has non-positive slot {parsed}",
        )
    return parsed

def _endpoint_name(cell_name: str) -> Literal["begin", "end"]:
    normalized = cell_name.strip().casefold()
    if normalized == "beginx":
        return "begin"
    if normalized == "endx":
        return "end"
    raise VisioQolError(
        "unsupported_bus_endpoint",
        f"bus attachment must use BeginX or EndX, got {cell_name!r}",
    )


def _connection_row(cell_name: str) -> int:
    match = _CONNECTION_ROW.fullmatch(cell_name.strip())
    if match is None:
        raise VisioQolError(
            "unsupported_bus_connection_cell",
            f"expected Connections.N.X, got {cell_name!r}",
        )
    return int(match.group(1))


def discover_cell_anchor(
    snapshot: VisioPageSnapshot,
    *,
    seed_shape_id: int,
) -> VisioCellAnchor:
    """Resolve the seed's real native Glue to a child terminal of a bus shape."""

    shapes = _shape_index(snapshot)
    try:
        seed = shapes[seed_shape_id]
    except KeyError as exc:
        raise VisioQolError(
            "unknown_seed_shape",
            f"shape {seed_shape_id} is not present on page {snapshot.page_name!r}",
        ) from exc
    if seed.parent_shape_id is not None:
        raise VisioQolError(
            "invalid_seed_shape",
            f"shape {seed_shape_id} is a group child and cannot anchor a cell",
        )

    candidates: list[tuple[VisioGlueSnapshot, VisioShapeSnapshot, VisioShapeSnapshot]] = []
    for glue in snapshot.connections:
        if glue.from_shape_id != seed_shape_id:
            continue
        target = shapes.get(glue.to_shape_id)
        if target is None or target.parent_shape_id is None:
            continue
        parent = shapes.get(target.parent_shape_id)
        if parent is None:
            raise VisioQolError(
                "orphan_bus_terminal",
                f"bus terminal shape {target.shape_id} has missing parent {target.parent_shape_id}",
            )
        candidates.append((glue, target, parent))

    if len(candidates) != 1:
        raise VisioQolError(
            "ambiguous_bus_attachment",
            (
                f"seed shape {seed_shape_id} must have exactly one Glue to a child bus "
                f"terminal, found {len(candidates)}"
            ),
        )

    glue, terminal, bus = candidates[0]
    return VisioCellAnchor(
        shape_id=seed_shape_id,
        x_mm=_mm(seed.geometry.pin_x),
        y_mm=_mm(seed.geometry.pin_y),
        bus_shape_id=bus.shape_id,
        bus_terminal_shape_id=terminal.shape_id,
        bus_terminal_nt=_user_int(terminal, "nt"),
        bus_slot_index=_bus_slot_index(terminal),
        source_endpoint=_endpoint_name(glue.from_cell),
        target_connection_row=_connection_row(glue.to_cell),
    )


def _electrical_core(
    snapshot: VisioPageSnapshot,
    *,
    seed_shape_id: int,
    bus_shape_id: int,
) -> tuple[int, ...]:
    """Return the Glue-connected top-level component without the external bus."""

    shapes = _shape_index(snapshot)
    adjacency: dict[int, set[int]] = {
        sid: set()
        for sid, shape in shapes.items()
        if shape.parent_shape_id is None and sid != bus_shape_id
    }
    for glue in snapshot.connections:
        left = shapes.get(glue.from_shape_id)
        right = shapes.get(glue.to_shape_id)
        if left is None or right is None:
            raise VisioQolError(
                "unknown_shape_reference",
                f"Glue {glue.from_shape_id}->{glue.to_shape_id} references an unknown shape",
            )
        if left.parent_shape_id is not None or right.parent_shape_id is not None:
            continue
        if left.shape_id == bus_shape_id or right.shape_id == bus_shape_id:
            continue
        if left.shape_id in adjacency and right.shape_id in adjacency:
            adjacency[left.shape_id].add(right.shape_id)
            adjacency[right.shape_id].add(left.shape_id)

    if seed_shape_id not in adjacency:
        raise VisioQolError(
            "invalid_seed_shape",
            f"shape {seed_shape_id} is not a top-level non-bus shape",
        )

    seen: set[int] = set()
    stack = [seed_shape_id]
    while stack:
        current = stack.pop()
        if current in seen:
            continue
        seen.add(current)
        stack.extend(sorted(adjacency[current] - seen, reverse=True))
    return tuple(sorted(seen))


def discover_cell(
    snapshot: VisioPageSnapshot,
    *,
    seed_shape_id: int,
    pitch_mm: float,
    vertical_margin_mm: float = 10.0,
) -> VisioCell:
    """Discover one visual cell while keeping electrical topology Glue-only.

    The electrical core is discovered only from native Glue. Additional projection
    members (labels, side equipment, helper shapes) may be included by the cell's
    geometric column, but that inclusion never creates an electrical connection.
    """

    pitch = float(pitch_mm)
    margin = float(vertical_margin_mm)
    if not math.isfinite(pitch) or pitch <= 0.0:
        raise VisioQolError("invalid_pitch", "pitch_mm must be a finite positive number")
    if not math.isfinite(margin) or margin < 0.0:
        raise VisioQolError(
            "invalid_vertical_margin",
            "vertical_margin_mm must be a finite non-negative number",
        )

    shapes = _shape_index(snapshot)
    anchor = discover_cell_anchor(snapshot, seed_shape_id=seed_shape_id)
    core_ids = _electrical_core(
        snapshot,
        seed_shape_id=seed_shape_id,
        bus_shape_id=anchor.bus_shape_id,
    )
    core_shapes = [shapes[sid] for sid in core_ids]
    core_y = [_mm(shape.geometry.pin_y) for shape in core_shapes]
    y_min = min(core_y) - margin
    y_max = max(core_y) + margin
    half_pitch = pitch / 2.0
    boundary_tolerance = 0.01

    members: set[int] = set(core_ids)
    for shape in snapshot.shapes:
        if shape.parent_shape_id is not None or shape.shape_id == anchor.bus_shape_id:
            continue
        x_mm = _mm(shape.geometry.pin_x)
        y_mm = _mm(shape.geometry.pin_y)
        distance = abs(x_mm - anchor.x_mm)
        if abs(distance - half_pitch) <= boundary_tolerance and y_min <= y_mm <= y_max:
            raise VisioQolError(
                "ambiguous_cell_boundary",
                (
                    f"shape {shape.shape_id} lies on the cell boundary at "
                    f"{distance:.3f} mm from anchor {seed_shape_id}"
                ),
            )
        if distance < half_pitch - boundary_tolerance and y_min <= y_mm <= y_max:
            members.add(shape.shape_id)

    return VisioCell(
        page_name=snapshot.page_name,
        seed_shape_id=seed_shape_id,
        anchor=anchor,
        member_shape_ids=tuple(sorted(members)),
        electrical_core_shape_ids=core_ids,
    )


def measure_cell_pitch(
    snapshot: VisioPageSnapshot,
    *,
    first_seed_shape_id: int,
    second_seed_shape_id: int,
) -> float:
    """Measure horizontal anchor-to-anchor pitch in millimetres."""

    first = discover_cell_anchor(snapshot, seed_shape_id=first_seed_shape_id)
    second = discover_cell_anchor(snapshot, seed_shape_id=second_seed_shape_id)
    if first.bus_shape_id != second.bus_shape_id:
        raise VisioQolError(
            "different_buses",
            "cell pitch can only be measured between anchors attached to the same bus",
        )
    delta = abs(second.x_mm - first.x_mm)
    if delta <= 0.01:
        raise VisioQolError(
            "invalid_pitch",
            f"cell anchors are only {delta:.6f} mm apart",
        )
    return delta


def _bus_terminal_by_nt(
    snapshot: VisioPageSnapshot,
    *,
    bus_shape_id: int,
    terminal_nt: int,
) -> VisioShapeSnapshot:
    matches = [
        shape
        for shape in snapshot.shapes
        if shape.parent_shape_id == bus_shape_id
        and shape.user_cells.get("nt") is not None
        and _user_int(shape, "nt") == terminal_nt
    ]
    if len(matches) != 1:
        raise VisioQolError(
            "ambiguous_bus_terminal",
            (
                f"bus {bus_shape_id} must expose exactly one child with User.nt="
                f"{terminal_nt}, found {len(matches)}"
            ),
        )
    return matches[0]



def _bus_terminal_by_slot(
    snapshot: VisioPageSnapshot,
    *,
    bus_shape_id: int,
    slot_index: int,
) -> VisioShapeSnapshot:
    matches: list[VisioShapeSnapshot] = []
    for shape in snapshot.shapes:
        if shape.parent_shape_id != bus_shape_id:
            continue
        try:
            candidate_slot = _bus_slot_index(shape)
        except VisioQolError as exc:
            if exc.code == "missing_bus_slot_index":
                continue
            raise
        if candidate_slot == slot_index:
            matches.append(shape)
    if len(matches) != 1:
        raise VisioQolError(
            "ambiguous_bus_slot",
            (
                f"bus {bus_shape_id} must expose exactly one child for slot "
                f"{slot_index}, found {len(matches)}"
            ),
        )
    return matches[0]

def _terminal_is_occupied(
    snapshot: VisioPageSnapshot,
    *,
    terminal_shape_id: int,
) -> tuple[int, ...]:
    occupants: set[int] = set()
    for glue in snapshot.connections:
        if glue.to_shape_id == terminal_shape_id:
            occupants.add(glue.from_shape_id)
        if glue.from_shape_id == terminal_shape_id:
            occupants.add(glue.to_shape_id)
    return tuple(sorted(occupants))


def plan_duplicate_cell(
    snapshot: VisioPageSnapshot,
    *,
    source_seed_shape_id: int,
    direction: Literal["left", "right"],
    pitch_mm: float,
    target_bus_terminal_nt: int | None = None,
    new_cell_id: str,
    vertical_margin_mm: float = 10.0,
) -> DuplicateCellPlan:
    """Build a fail-closed, transport-neutral duplicate operation plan."""

    if direction not in {"left", "right"}:
        raise VisioQolError(
            "invalid_direction",
            f"direction must be 'left' or 'right', got {direction!r}",
        )
    try:
        validated_cell_id = validate_cell_id(new_cell_id)
    except VisioIdentityError as exc:
        raise VisioQolError(exc.code, str(exc).split(": ", 1)[-1]) from exc
    cell = discover_cell(
        snapshot,
        seed_shape_id=source_seed_shape_id,
        pitch_mm=pitch_mm,
        vertical_margin_mm=vertical_margin_mm,
    )
    slot_delta = 1 if direction == "right" else -1
    target_slot_index = cell.anchor.bus_slot_index + slot_delta
    target_by_slot = _bus_terminal_by_slot(
        snapshot,
        bus_shape_id=cell.anchor.bus_shape_id,
        slot_index=target_slot_index,
    )
    if target_bus_terminal_nt is None:
        target = target_by_slot
        target_nt = _user_int(target, "nt")
    else:
        target_nt = int(target_bus_terminal_nt)
        target = _bus_terminal_by_nt(
            snapshot,
            bus_shape_id=cell.anchor.bus_shape_id,
            terminal_nt=target_nt,
        )
        if target.shape_id != target_by_slot.shape_id:
            raise VisioQolError(
                "bus_terminal_direction_mismatch",
                (
                    f"direction {direction!r} from slot {cell.anchor.bus_slot_index} "
                    f"requires slot {target_slot_index} (shape {target_by_slot.shape_id}), "
                    f"but User.nt={target_nt} resolves to shape {target.shape_id}"
                ),
            )
    if target.shape_id == cell.anchor.bus_terminal_shape_id:
        raise VisioQolError(
            "same_bus_terminal",
            "duplicate target must not reuse the source bus terminal",
        )
    occupants = _terminal_is_occupied(snapshot, terminal_shape_id=target.shape_id)
    if occupants:
        raise VisioQolError(
            "target_bus_terminal_occupied",
            (
                f"bus terminal shape {target.shape_id} (User.nt={target_nt}) "
                f"is already connected to shape(s) {occupants}"
            ),
        )

    pitch = float(pitch_mm)
    dx = pitch if direction == "right" else -pitch
    return DuplicateCellPlan(
        page_name=snapshot.page_name,
        source_cell=cell,
        direction=direction,
        pitch_mm=pitch,
        dx_mm=dx,
        dy_mm=0.0,
        target_bus_terminal_shape_id=target.shape_id,
        target_bus_terminal_nt=target_nt,
        source_bus_slot_index=cell.anchor.bus_slot_index,
        target_bus_slot_index=target_slot_index,
        target_connection_row=cell.anchor.target_connection_row,
        source_endpoint=cell.anchor.source_endpoint,
        new_cell_id=validated_cell_id,
        reset_identity=True,
    )


def build_duplicate_execution_request(
    plan: DuplicateCellPlan,
    *,
    select_result: bool = True,
) -> VisioDuplicateExecutionRequest:
    """Translate a validated plan into the qualified bridge tool arguments.

    Shape IDs remain projection-only runtime references. The request explicitly
    carries `identity_reset_required` because native Visio Duplicate copies human
    labels and VTD data verbatim; canonical identity must not be inferred from the
    duplicated projection until identity reset/renumber has been completed.
    """

    glue_items = [
        {
            "source_shape_id": plan.source_cell.seed_shape_id,
            "endpoint": plan.source_endpoint,
            "target_shape_id": plan.target_bus_terminal_shape_id,
            "target_connection_row": plan.target_connection_row,
        }
    ]
    return VisioDuplicateExecutionRequest(
        tool_name="duplicate_shapes_exact",
        shape_ids_json=json.dumps(
            list(plan.shape_ids),
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        dx_mm=plan.dx_mm,
        dy_mm=plan.dy_mm,
        select_result=bool(select_result),
        glue_items_json=json.dumps(
            glue_items,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ),
        new_cell_id=plan.new_cell_id,
        identity_reset_required=plan.reset_identity,
    )


def plan_move_cell_to_adjacent_slot(
    snapshot: VisioPageSnapshot,
    *,
    source_seed_shape_id: int,
    direction: Literal["left", "right"],
    pitch_mm: float,
    target_bus_terminal_nt: int | None = None,
    vertical_margin_mm: float = 10.0,
    tolerance_mm: float = 0.01,
) -> MoveCellPlan:
    """Plan moving an existing cell to the adjacent native bus slot.

    The actual move vector comes from source/target bus-terminal geometry.
    pitch_mm is an engineering invariant used to verify that the row itself is
    regular; it is not blindly applied as the movement vector.
    """

    if direction not in {"left", "right"}:
        raise VisioQolError(
            "invalid_direction",
            f"direction must be 'left' or 'right', got {direction!r}",
        )
    pitch = float(pitch_mm)
    tolerance = float(tolerance_mm)
    if not math.isfinite(pitch) or pitch <= 0.0:
        raise VisioQolError("invalid_pitch", "pitch_mm must be a finite positive number")
    if not math.isfinite(tolerance) or tolerance < 0.0:
        raise VisioQolError(
            "invalid_tolerance",
            "tolerance_mm must be a finite non-negative number",
        )

    cell = discover_cell(
        snapshot,
        seed_shape_id=source_seed_shape_id,
        pitch_mm=pitch,
        vertical_margin_mm=vertical_margin_mm,
    )
    shapes = _shape_index(snapshot)
    source_terminal = shapes.get(cell.anchor.bus_terminal_shape_id)
    if source_terminal is None:
        raise VisioQolError(
            "missing_source_bus_terminal",
            f"source bus terminal {cell.anchor.bus_terminal_shape_id} is missing",
        )

    source_occupants = _terminal_is_occupied(
        snapshot,
        terminal_shape_id=source_terminal.shape_id,
    )
    if source_occupants != (cell.seed_shape_id,):
        raise VisioQolError(
            "source_bus_terminal_shared",
            (
                f"source bus terminal {source_terminal.shape_id} must be connected "
                f"only to seed shape {cell.seed_shape_id}; got {source_occupants}"
            ),
        )

    slot_delta = 1 if direction == "right" else -1
    target_slot_index = cell.anchor.bus_slot_index + slot_delta
    target_by_slot = _bus_terminal_by_slot(
        snapshot,
        bus_shape_id=cell.anchor.bus_shape_id,
        slot_index=target_slot_index,
    )
    if target_bus_terminal_nt is None:
        target = target_by_slot
        target_nt = _user_int(target, "nt")
    else:
        target_nt = int(target_bus_terminal_nt)
        target = _bus_terminal_by_nt(
            snapshot,
            bus_shape_id=cell.anchor.bus_shape_id,
            terminal_nt=target_nt,
        )
        if target.shape_id != target_by_slot.shape_id:
            raise VisioQolError(
                "bus_terminal_direction_mismatch",
                (
                    f"direction {direction!r} from slot {cell.anchor.bus_slot_index} "
                    f"requires slot {target_slot_index} (shape {target_by_slot.shape_id}), "
                    f"but User.nt={target_nt} resolves to shape {target.shape_id}"
                ),
            )

    occupants = _terminal_is_occupied(snapshot, terminal_shape_id=target.shape_id)
    if occupants:
        raise VisioQolError(
            "target_bus_terminal_occupied",
            (
                f"bus terminal shape {target.shape_id} (User.nt={target_nt}) "
                f"is already connected to shape(s) {occupants}"
            ),
        )

    dx = _mm(target.geometry.pin_x) - _mm(source_terminal.geometry.pin_x)
    dy = _mm(target.geometry.pin_y) - _mm(source_terminal.geometry.pin_y)
    if abs(abs(dx) - pitch) > tolerance:
        raise VisioQolError(
            "bus_pitch_mismatch",
            (
                f"native bus slots imply {abs(dx):.6f} mm horizontal pitch, "
                f"expected {pitch:.6f} mm"
            ),
        )
    expected_sign = 1.0 if direction == "right" else -1.0
    if dx * expected_sign <= 0.0:
        raise VisioQolError(
            "bus_direction_mismatch",
            (
                f"target slot {target_slot_index} is not geometrically "
                f"{direction} of source slot {cell.anchor.bus_slot_index}"
            ),
        )
    if abs(dy) > tolerance:
        raise VisioQolError(
            "bus_row_misaligned",
            (
                f"source and target bus terminals differ by {dy:.6f} mm vertically; "
                f"tolerance is {tolerance:.6f} mm"
            ),
        )

    return MoveCellPlan(
        page_name=snapshot.page_name,
        source_cell=cell,
        direction=direction,
        pitch_mm=pitch,
        dx_mm=dx,
        dy_mm=dy,
        source_bus_terminal_shape_id=source_terminal.shape_id,
        source_bus_terminal_nt=cell.anchor.bus_terminal_nt,
        target_bus_terminal_shape_id=target.shape_id,
        target_bus_terminal_nt=target_nt,
        source_bus_slot_index=cell.anchor.bus_slot_index,
        target_bus_slot_index=target_slot_index,
        target_connection_row=cell.anchor.target_connection_row,
        source_endpoint=cell.anchor.source_endpoint,
    )


def build_move_execution_request(
    plan: MoveCellPlan,
    *,
    select_result: bool = True,
) -> VisioMoveExecutionRequest:
    """Translate a validated cell move into the bounded bridge primitive."""

    detach_items = [
        {
            "shape_id": plan.source_cell.seed_shape_id,
            "endpoint": plan.source_endpoint,
            "expected_target_shape_id": plan.source_bus_terminal_shape_id,
            "expected_target_connection_row": plan.target_connection_row,
        }
    ]
    glue_items = [
        {
            "shape_id": plan.source_cell.seed_shape_id,
            "endpoint": plan.source_endpoint,
            "target_shape_id": plan.target_bus_terminal_shape_id,
            "target_connection_row": plan.target_connection_row,
        }
    ]
    return VisioMoveExecutionRequest(
        tool_name="move_shapes_exact",
        shape_ids_json=json.dumps(
            list(plan.shape_ids),
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        dx_mm=plan.dx_mm,
        dy_mm=plan.dy_mm,
        select_result=bool(select_result),
        detach_items_json=json.dumps(
            detach_items,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ),
        glue_items_json=json.dumps(
            glue_items,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ),
    )


def find_glue_candidates(
    *,
    source_shape_id: int,
    source_endpoint: Literal["begin", "end"],
    source_x_mm: float,
    source_y_mm: float,
    connection_points: tuple[VisioConnectionPoint, ...],
    tolerance_mm: float = 1.0,
) -> tuple[VisioGlueCandidate, ...]:
    """Return geometry-only repair candidates without creating electrical truth."""

    if source_endpoint not in {"begin", "end"}:
        raise VisioQolError(
            "invalid_endpoint",
            f"source_endpoint must be begin/end, got {source_endpoint!r}",
        )
    x = float(source_x_mm)
    y = float(source_y_mm)
    tolerance = float(tolerance_mm)
    if not math.isfinite(x) or not math.isfinite(y):
        raise VisioQolError(
            "invalid_endpoint_position",
            "source endpoint coordinates must be finite",
        )
    if not math.isfinite(tolerance) or tolerance <= 0.0:
        raise VisioQolError(
            "invalid_glue_tolerance",
            "tolerance_mm must be a finite positive number",
        )

    candidates: list[VisioGlueCandidate] = []
    seen: set[tuple[int, int]] = set()
    for point in connection_points:
        key = (int(point.target_shape_id), int(point.target_connection_row))
        if key in seen:
            raise VisioQolError(
                "duplicate_connection_point",
                f"connection point {key[0]} row {key[1]} is repeated",
            )
        seen.add(key)
        if key[0] == int(source_shape_id):
            continue
        px = float(point.x_mm)
        py = float(point.y_mm)
        if not math.isfinite(px) or not math.isfinite(py):
            raise VisioQolError(
                "invalid_connection_point_position",
                f"connection point {key[0]} row {key[1]} has non-finite coordinates",
            )
        distance = math.hypot(px - x, py - y)
        if distance <= tolerance:
            candidates.append(
                VisioGlueCandidate(
                    target_shape_id=key[0],
                    target_connection_row=key[1],
                    x_mm=px,
                    y_mm=py,
                    distance_mm=distance,
                )
            )

    return tuple(
        sorted(
            candidates,
            key=lambda item: (
                item.distance_mm,
                item.target_shape_id,
                item.target_connection_row,
            ),
        )
    )


def plan_repair_glue(
    *,
    source_shape_id: int,
    source_endpoint: Literal["begin", "end"],
    source_x_mm: float,
    source_y_mm: float,
    connection_points: tuple[VisioConnectionPoint, ...],
    tolerance_mm: float = 1.0,
    selected_target_shape_id: int | None = None,
    selected_target_connection_row: int | None = None,
    source_is_already_glued: bool = False,
) -> VisioGlueRepairPlan:
    """Choose one explicit repair target; never infer electrical truth silently."""

    if source_is_already_glued:
        raise VisioQolError(
            "endpoint_already_glued",
            f"shape {source_shape_id} {source_endpoint} is already glued",
        )
    candidates = find_glue_candidates(
        source_shape_id=source_shape_id,
        source_endpoint=source_endpoint,
        source_x_mm=source_x_mm,
        source_y_mm=source_y_mm,
        connection_points=connection_points,
        tolerance_mm=tolerance_mm,
    )
    if not candidates:
        raise VisioQolError(
            "no_glue_candidate",
            (
                f"shape {source_shape_id} {source_endpoint} has no native connection "
                f"point within {float(tolerance_mm):.3f} mm"
            ),
        )

    explicit = (
        selected_target_shape_id is not None
        or selected_target_connection_row is not None
    )
    if explicit:
        if (
            selected_target_shape_id is None
            or selected_target_connection_row is None
        ):
            raise VisioQolError(
                "incomplete_glue_target",
                "target shape and connection row must be selected together",
            )
        selected = [
            candidate
            for candidate in candidates
            if candidate.target_shape_id == int(selected_target_shape_id)
            and candidate.target_connection_row
            == int(selected_target_connection_row)
        ]
        if len(selected) != 1:
            raise VisioQolError(
                "selected_glue_target_not_candidate",
                (
                    f"selected target {selected_target_shape_id} row "
                    f"{selected_target_connection_row} is not within tolerance"
                ),
            )
        candidate = selected[0]
    else:
        if len(candidates) != 1:
            description = ", ".join(
                (
                    f"{candidate.target_shape_id}:"
                    f"{candidate.target_connection_row}@"
                    f"{candidate.distance_mm:.3f}mm"
                )
                for candidate in candidates
            )
            raise VisioQolError(
                "ambiguous_glue_candidate",
                (
                    "geometry found multiple possible native terminals; "
                    f"explicit preview selection is required: {description}"
                ),
            )
        candidate = candidates[0]

    return VisioGlueRepairPlan(
        source_shape_id=int(source_shape_id),
        source_endpoint=source_endpoint,
        source_x_mm=float(source_x_mm),
        source_y_mm=float(source_y_mm),
        candidate=candidate,
        tolerance_mm=float(tolerance_mm),
    )


def build_glue_repair_execution_request(
    plan: VisioGlueRepairPlan,
) -> VisioGlueExecutionRequest:
    """Build the explicit native Glue mutation after preview/selection."""

    return VisioGlueExecutionRequest(
        tool_name="batch_glue_endpoints",
        items_json=json.dumps(
            [
                {
                    "shape_id": plan.source_shape_id,
                    "endpoint": plan.source_endpoint,
                    "target_shape_id": plan.candidate.target_shape_id,
                    "target_connection_row": plan.candidate.target_connection_row,
                }
            ],
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ),
    )
