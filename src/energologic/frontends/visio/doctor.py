from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable, Literal

from .identity import VisioIdentityError, projection_cell_id
from .qol import VisioConnectionPoint
from .snapshot import VisioPageSnapshot


_MM_PER_INCH = 25.4


@dataclass(frozen=True, slots=True)
class VisioEndpointProbe:
    """Page-coordinate evidence for one electrical endpoint."""

    shape_id: int
    endpoint: Literal["begin", "end"]
    x_mm: float
    y_mm: float
    is_glued: bool


@dataclass(frozen=True, slots=True, order=True)
class VisioDoctorIssue:
    """One deterministic structural issue reported by Scheme Doctor."""

    code: str
    severity: Literal["error", "warning"]
    path: str
    message: str


def _mm(value_in: float) -> float:
    return float(value_in) * _MM_PER_INCH


def _decode_positive_int(raw: object) -> int | None:
    text = str(raw).strip()
    if text.startswith("="):
        text = text[1:].strip()
    try:
        value = int(text)
    except ValueError:
        return None
    return value if value > 0 else None


def _bus_slot(shape) -> int | None:
    raw = shape.user_cells.get("slot")
    if raw is None:
        raw = shape.text
    return _decode_positive_int(raw)


def _bus_nt(shape) -> int | None:
    raw = shape.user_cells.get("nt")
    if raw is None:
        return None
    return _decode_positive_int(raw)


def diagnose_page_structure(
    snapshot: VisioPageSnapshot,
    *,
    expected_pitch_mm: float | None = None,
    pitch_tolerance_mm: float = 0.25,
) -> tuple[VisioDoctorIssue, ...]:
    """Run deterministic QoL structural checks that need only a page snapshot."""

    issues: list[VisioDoctorIssue] = []
    shapes_by_id = {shape.shape_id: shape for shape in snapshot.shapes}

    if len(shapes_by_id) != len(snapshot.shapes):
        issues.append(
            VisioDoctorIssue(
                "duplicate_shape_id",
                "error",
                f"/pages/{snapshot.page_name}/shapes",
                "page snapshot contains duplicate shape IDs",
            )
        )

    pitch = None if expected_pitch_mm is None else float(expected_pitch_mm)
    tolerance = float(pitch_tolerance_mm)
    if pitch is not None and (not math.isfinite(pitch) or pitch <= 0):
        raise ValueError("expected_pitch_mm must be a finite positive number")
    if not math.isfinite(tolerance) or tolerance < 0:
        raise ValueError("pitch_tolerance_mm must be a finite non-negative number")

    terminals_by_bus: dict[int, list[tuple[int, int | None, int, float]]] = {}
    for shape in snapshot.shapes:
        if shape.parent_shape_id is None:
            continue
        slot = _bus_slot(shape)
        nt = _bus_nt(shape)
        if slot is None and nt is None:
            continue
        if slot is None:
            issues.append(
                VisioDoctorIssue(
                    "missing_bus_slot",
                    "error",
                    f"/shapes/{shape.shape_id}",
                    "native bus terminal exposes User.nt but no positive visible slot",
                )
            )
            continue
        terminals_by_bus.setdefault(shape.parent_shape_id, []).append(
            (slot, nt, shape.shape_id, _mm(shape.geometry.pin_x))
        )

    for bus_id, terminals in sorted(terminals_by_bus.items()):
        by_slot: dict[int, list[tuple[int | None, int, float]]] = {}
        by_nt: dict[int, list[int]] = {}
        for slot, nt, shape_id, x_mm in terminals:
            by_slot.setdefault(slot, []).append((nt, shape_id, x_mm))
            if nt is not None:
                by_nt.setdefault(nt, []).append(shape_id)

        for slot, rows in sorted(by_slot.items()):
            if len(rows) > 1:
                shape_ids = ",".join(str(row[1]) for row in sorted(rows))
                issues.append(
                    VisioDoctorIssue(
                        "duplicate_bus_slot",
                        "error",
                        f"/buses/{bus_id}/slots/{slot}",
                        f"visible bus slot {slot} is represented by multiple shapes: {shape_ids}",
                    )
                )

        for nt, shape_ids in sorted(by_nt.items()):
            if len(shape_ids) > 1:
                issues.append(
                    VisioDoctorIssue(
                        "duplicate_bus_terminal_nt",
                        "error",
                        f"/buses/{bus_id}/nt/{nt}",
                        (
                            f"native User.nt={nt} is represented by multiple shapes: "
                            + ",".join(str(value) for value in sorted(shape_ids))
                        ),
                    )
                )

        if pitch is not None:
            unique_slots = [
                (slot, rows[0][1], rows[0][2])
                for slot, rows in sorted(by_slot.items())
                if len(rows) == 1
            ]
            for left, right in zip(unique_slots, unique_slots[1:]):
                left_slot, left_shape, left_x = left
                right_slot, right_shape, right_x = right
                slot_delta = right_slot - left_slot
                if slot_delta <= 0:
                    continue
                expected_delta = pitch * slot_delta
                actual_delta = right_x - left_x
                if abs(actual_delta - expected_delta) > tolerance:
                    issues.append(
                        VisioDoctorIssue(
                            "bus_pitch_mismatch",
                            "error",
                            f"/buses/{bus_id}/slots/{left_slot}-{right_slot}",
                            (
                                f"bus terminal shapes {left_shape}->{right_shape} are "
                                f"{actual_delta:.3f} mm apart; expected "
                                f"{expected_delta:.3f}±{tolerance:.3f} mm"
                            ),
                        )
                    )

    # Explicit cell identity is allowed on every member of one cell. It becomes a
    # conflict only when the same identity appears on multiple independent bus anchors.
    anchors_by_cell_id: dict[str, set[int]] = {}
    for glue in snapshot.connections:
        source = shapes_by_id.get(glue.from_shape_id)
        target = shapes_by_id.get(glue.to_shape_id)
        if source is None or target is None or target.parent_shape_id is None:
            continue
        try:
            cell_id = projection_cell_id(source.user_cells)
        except VisioIdentityError as exc:
            issues.append(
                VisioDoctorIssue(
                    exc.code,
                    "error",
                    f"/shapes/{source.shape_id}/User.EnergoLogicCellId",
                    str(exc).split(": ", 1)[-1],
                )
            )
            continue
        if cell_id is not None:
            anchors_by_cell_id.setdefault(cell_id, set()).add(source.shape_id)

    for cell_id, anchors in sorted(anchors_by_cell_id.items()):
        if len(anchors) > 1:
            issues.append(
                VisioDoctorIssue(
                    "duplicate_cell_identity",
                    "error",
                    f"/cells/{cell_id}",
                    (
                        f"EnergoLogicCellId {cell_id!r} is attached to multiple "
                        f"bus anchors: {','.join(str(value) for value in sorted(anchors))}"
                    ),
                )
            )

    return tuple(sorted(set(issues)))


def diagnose_endpoint_glue(
    endpoint: VisioEndpointProbe,
    connection_points: Iterable[VisioConnectionPoint],
    *,
    tolerance_mm: float = 1.0,
) -> tuple[VisioDoctorIssue, ...]:
    """Detect geometry that looks connected but lacks real native Glue."""

    tolerance = float(tolerance_mm)
    if not math.isfinite(tolerance) or tolerance < 0:
        raise ValueError("tolerance_mm must be a finite non-negative number")
    if endpoint.is_glued:
        return ()

    candidates: list[tuple[float, VisioConnectionPoint]] = []
    for point in connection_points:
        distance = math.hypot(
            float(point.x_mm) - float(endpoint.x_mm),
            float(point.y_mm) - float(endpoint.y_mm),
        )
        if distance <= tolerance:
            candidates.append((distance, point))
    candidates.sort(
        key=lambda item: (
            item[0],
            item[1].target_shape_id,
            item[1].target_connection_row,
        )
    )

    if not candidates:
        return ()

    path = f"/shapes/{endpoint.shape_id}/{endpoint.endpoint}"
    if len(candidates) == 1:
        distance, point = candidates[0]
        return (
            VisioDoctorIssue(
                "visual_touch_without_glue",
                "error",
                path,
                (
                    f"endpoint visually matches shape {point.target_shape_id} "
                    f"Connections.{point.target_connection_row} at "
                    f"{distance:.3f} mm but has no native Glue"
                ),
            ),
        )

    preview = ", ".join(
        (
            f"{point.target_shape_id}/Connections.{point.target_connection_row}"
            f"@{distance:.3f}mm"
        )
        for distance, point in candidates
    )
    return (
        VisioDoctorIssue(
            "ambiguous_visual_touch_without_glue",
            "error",
            path,
            (
                "endpoint has no native Glue and multiple geometric candidates "
                f"within {tolerance:.3f} mm: {preview}"
            ),
        ),
    )


def diagnose_scheme(
    snapshot: VisioPageSnapshot,
    *,
    endpoint_probes: Iterable[VisioEndpointProbe] = (),
    connection_points: Iterable[VisioConnectionPoint] = (),
    expected_pitch_mm: float | None = None,
    pitch_tolerance_mm: float = 0.25,
    glue_tolerance_mm: float = 1.0,
) -> tuple[VisioDoctorIssue, ...]:
    """Run the deterministic Scheme Doctor subset qualified by VISIO-EDITOR-QOL-001."""

    points = tuple(connection_points)
    issues = list(
        diagnose_page_structure(
            snapshot,
            expected_pitch_mm=expected_pitch_mm,
            pitch_tolerance_mm=pitch_tolerance_mm,
        )
    )
    for endpoint in endpoint_probes:
        issues.extend(
            diagnose_endpoint_glue(
                endpoint,
                points,
                tolerance_mm=glue_tolerance_mm,
            )
        )
    return tuple(sorted(set(issues)))
