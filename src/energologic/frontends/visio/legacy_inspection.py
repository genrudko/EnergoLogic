from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import math
import re
import unicodedata
from typing import Any, Iterable, Mapping, Protocol


REPORT_VERSION = "legacy-visio-inspection-0.1"

CONFIDENCE_EXACT_NATIVE = "exact_native"
CONFIDENCE_HIGH = "high_confidence"
CONFIDENCE_REVIEW = "review_recommended"
CONFIDENCE_AMBIGUOUS = "ambiguous"
CONFIDENCE_UNKNOWN = "unknown"

CONFIDENCE_LEVELS = (
    CONFIDENCE_EXACT_NATIVE,
    CONFIDENCE_HIGH,
    CONFIDENCE_REVIEW,
    CONFIDENCE_AMBIGUOUS,
    CONFIDENCE_UNKNOWN,
)


@dataclass(frozen=True, slots=True)
class LegacyGeometry:
    pin_x: float = 0.0
    pin_y: float = 0.0
    width: float = 0.0
    height: float = 0.0
    rotation: float = 0.0


@dataclass(frozen=True, slots=True)
class LegacyShapeSheetCell:
    section: str
    row: str
    cell: str
    formula: str = ""
    value: float | str | bool | None = None
    unit: str | None = None


@dataclass(frozen=True, slots=True)
class LegacyConnectionPoint:
    row: str
    x: float | None = None
    y: float | None = None
    x_formula: str = ""
    y_formula: str = ""
    direction_formula: str = ""


@dataclass(frozen=True, slots=True)
class LegacyShapeSnapshot:
    shape_id: int
    name: str = ""
    name_u: str = ""
    shape_type: str = ""
    master_name: str = ""
    master_name_u: str = ""
    master_shape_id: int | None = None
    parent_shape_id: int | None = None
    geometry: LegacyGeometry = field(default_factory=LegacyGeometry)
    text: str = ""
    layers: tuple[str, ...] = ()
    cells: tuple[LegacyShapeSheetCell, ...] = ()
    connection_points: tuple[LegacyConnectionPoint, ...] = ()
    begin_x_formula: str = ""
    begin_y_formula: str = ""
    end_x_formula: str = ""
    end_y_formula: str = ""


@dataclass(frozen=True, slots=True)
class LegacyGlueSnapshot:
    from_shape_id: int
    from_cell: str
    to_shape_id: int
    to_cell: str


@dataclass(frozen=True, slots=True)
class LegacyPageSnapshot:
    page_id: int
    name: str
    name_u: str = ""
    width: float | None = None
    height: float | None = None
    shapes: tuple[LegacyShapeSnapshot, ...] = ()
    connects: tuple[LegacyGlueSnapshot, ...] = ()


@dataclass(frozen=True, slots=True)
class LegacyDocumentSnapshot:
    name: str
    full_name: str = ""
    visio_version: str = ""
    read_only: bool | None = None
    pages: tuple[LegacyPageSnapshot, ...] = ()
    metadata: Mapping[str, str | int | float | bool | None] = field(default_factory=dict)


class LegacyVisioSnapshotSource(Protocol):
    """Read-only transport boundary for future COM/bridge collectors."""

    def capture_read_only(self) -> LegacyDocumentSnapshot: ...


_NUMBER = re.compile(r"(?<![A-Za-z_])[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][-+]?\d+)?")
_STRING_LITERAL = re.compile(r'"(?:[^"]|"")*"')
_DIGITS = re.compile(r"\d+")
_WS = re.compile(r"\s+")


def _norm_text(value: str) -> str:
    return _WS.sub(" ", unicodedata.normalize("NFKC", value or "").strip())


def _formula_shape(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value or "").strip()
    normalized = _STRING_LITERAL.sub('"<str>"', normalized)
    normalized = _NUMBER.sub("#", normalized)
    return _WS.sub("", normalized).casefold()


def _text_pattern(value: str) -> str:
    normalized = _norm_text(value)
    return _DIGITS.sub("#", normalized).casefold()


def _round(value: float) -> float:
    if not math.isfinite(value):
        return 0.0
    rounded = round(value, 6)
    return 0.0 if rounded == -0.0 else rounded


def _hash(label: str, payload: object) -> str:
    material = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"{label}:" + hashlib.sha256(material).hexdigest()


def _shape_ref(page: LegacyPageSnapshot, shape_id: int) -> str:
    return f"page:{page.page_id}/shape:{shape_id}"


def _normalized_point(value: float | None, extent: float) -> float | None:
    if value is None:
        return None
    if abs(extent) < 1e-12:
        return _round(value)
    return _round(value / extent)


def _master_signal(shape: LegacyShapeSnapshot) -> dict[str, object]:
    # Numeric Master/Shape IDs are retained in raw instance data but excluded
    # from the stable family key because they are document-local identities.
    # NameU is the stable Visio identity when available; localized/display Name
    # is only a fallback and must not split one family after a display rename.
    name_u = _norm_text(shape.master_name_u).casefold()
    name = _norm_text(shape.master_name).casefold()
    return {"stable_name": name_u or name}


def _geometry_cells(shape: LegacyShapeSnapshot) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    width = abs(shape.geometry.width)
    height = abs(shape.geometry.height)
    for cell in shape.cells:
        if not cell.section.casefold().startswith("geometry"):
            continue
        value: object
        if isinstance(cell.value, bool) or cell.value is None:
            value = cell.value
        elif isinstance(cell.value, (int, float)):
            name = cell.cell.casefold()
            if name in {"x", "a", "c"} or name.endswith("x"):
                value = _normalized_point(float(cell.value), width)
            elif name in {"y", "b", "d"} or name.endswith("y"):
                value = _normalized_point(float(cell.value), height)
            else:
                scale = max(width, height, 1.0)
                value = _round(float(cell.value) / scale)
        else:
            value = "<text>"
        rows.append(
            {
                "section": cell.section.casefold(),
                "row": cell.row.casefold(),
                "cell": cell.cell.casefold(),
                "formula_shape": _formula_shape(cell.formula),
                "value": value,
            }
        )
    rows.sort(key=lambda item: (str(item["section"]), str(item["row"]), str(item["cell"])))
    return rows


def _shape_sheet_signal(shape: LegacyShapeSnapshot) -> list[dict[str, object]]:
    # Keep structural/formula shape, not per-instance literal text/numbers.
    # Placement cells are explicitly excluded; geometry has its own normalized signal.
    excluded_sections = {"xform", "text transform", "texttransform"}
    result: list[dict[str, object]] = []
    for cell in shape.cells:
        section = cell.section.casefold()
        if section in excluded_sections or section.startswith("geometry"):
            continue
        result.append(
            {
                "section": section,
                "row": cell.row.casefold(),
                "cell": cell.cell.casefold(),
                "formula_shape": _formula_shape(cell.formula),
                "value_kind": (
                    "bool"
                    if isinstance(cell.value, bool)
                    else "number"
                    if isinstance(cell.value, (int, float))
                    else "text"
                    if isinstance(cell.value, str)
                    else "none"
                ),
            }
        )
    result.sort(key=lambda item: (str(item["section"]), str(item["row"]), str(item["cell"])))
    return result


def _connection_point_signal(shape: LegacyShapeSnapshot) -> list[dict[str, object]]:
    width = abs(shape.geometry.width)
    height = abs(shape.geometry.height)
    result = [
        {
            "row": point.row.casefold(),
            "x": _normalized_point(point.x, width),
            "y": _normalized_point(point.y, height),
            "x_formula_shape": _formula_shape(point.x_formula),
            "y_formula_shape": _formula_shape(point.y_formula),
            "direction_formula_shape": _formula_shape(point.direction_formula),
        }
        for point in shape.connection_points
    ]
    result.sort(key=lambda item: str(item["row"]))
    return result


def _basic_geometry_signal(shape: LegacyShapeSnapshot) -> dict[str, object]:
    width = abs(shape.geometry.width)
    height = abs(shape.geometry.height)
    scale = max(width, height, 1e-12)
    return {
        "aspect_width": _round(width / scale),
        "aspect_height": _round(height / scale),
        "rotation_mod_pi": _round(shape.geometry.rotation % math.pi),
        "geometry_rows": _geometry_cells(shape),
    }


def _children_by_parent(
    shapes: Iterable[LegacyShapeSnapshot],
) -> dict[int, tuple[LegacyShapeSnapshot, ...]]:
    grouped: dict[int, list[LegacyShapeSnapshot]] = {}
    for shape in shapes:
        if shape.parent_shape_id is not None:
            grouped.setdefault(shape.parent_shape_id, []).append(shape)
    return {
        parent: tuple(sorted(children, key=lambda item: item.shape_id))
        for parent, children in grouped.items()
    }


def _relative_geometry(
    child: LegacyShapeSnapshot, parent: LegacyShapeSnapshot
) -> dict[str, float]:
    width = abs(parent.geometry.width)
    height = abs(parent.geometry.height)
    return {
        "x": _round((child.geometry.pin_x - parent.geometry.pin_x) / (width or 1.0)),
        "y": _round((child.geometry.pin_y - parent.geometry.pin_y) / (height or 1.0)),
        "width": _round(abs(child.geometry.width) / (width or 1.0)),
        "height": _round(abs(child.geometry.height) / (height or 1.0)),
        "rotation": _round((child.geometry.rotation - parent.geometry.rotation) % math.pi),
    }


def _shape_signals(
    shape: LegacyShapeSnapshot,
    by_id: Mapping[int, LegacyShapeSnapshot],
    children: Mapping[int, tuple[LegacyShapeSnapshot, ...]],
    cache: dict[int, dict[str, object]],
) -> dict[str, object]:
    if shape.shape_id in cache:
        return cache[shape.shape_id]

    child_signals = []
    for child in children.get(shape.shape_id, ()):
        child_core = _shape_signals(child, by_id, children, cache)
        child_signals.append(
            {
                "shape_type": _norm_text(child.shape_type).casefold(),
                "relative_geometry": _relative_geometry(child, shape),
                "family_core": child_core["family_core"],
            }
        )
    child_signals.sort(
        key=lambda item: json.dumps(item, ensure_ascii=False, sort_keys=True)
    )

    master = _master_signal(shape)
    geometry = _basic_geometry_signal(shape)
    shapesheet = _shape_sheet_signal(shape)
    connection_points = _connection_point_signal(shape)
    group_structure = {
        "child_count": len(child_signals),
        "children": child_signals,
    }

    geometry_signature = _hash("geometry", geometry)
    group_signature = _hash("group", group_structure)
    shapesheet_signature = _hash("shapesheet", shapesheet)
    connection_signature = _hash("connection-points", connection_points)
    master_signature = _hash("master", master)

    family_core = {
        "shape_type": _norm_text(shape.shape_type).casefold(),
        "master": master,
        "geometry_signature": geometry_signature,
        "group_signature": group_signature,
        "shapesheet_signature": shapesheet_signature,
        "connection_point_signature": connection_signature,
    }
    result = {
        "master_signature": master_signature,
        "geometry_signature": geometry_signature,
        "group_signature": group_signature,
        "shapesheet_signature": shapesheet_signature,
        "connection_point_signature": connection_signature,
        "family_core": family_core,
        "candidate_fingerprint": _hash("legacy-symbol", family_core),
        "text_pattern": _text_pattern(shape.text),
    }
    cache[shape.shape_id] = result
    return result


def _family_confidence(shape: LegacyShapeSnapshot, signals: Mapping[str, object]) -> str:
    has_master = bool(shape.master_name or shape.master_name_u)
    has_geometry = bool(_geometry_cells(shape)) or bool(shape.geometry.width or shape.geometry.height)
    has_group = signals["group_signature"] != _hash("group", {"child_count": 0, "children": []})
    has_connections = bool(shape.connection_points)

    if has_master and (has_geometry or has_group or has_connections):
        return CONFIDENCE_HIGH
    if has_geometry and (has_group or has_connections):
        return CONFIDENCE_HIGH
    if has_geometry or has_master:
        return CONFIDENCE_REVIEW
    if shape.text:
        return CONFIDENCE_AMBIGUOUS
    return CONFIDENCE_UNKNOWN


def inspect_legacy_visio(snapshot: LegacyDocumentSnapshot) -> dict[str, Any]:
    """Create a deterministic, read-only inspection report.

    The function never mutates the snapshot and never converts legacy content
    into canonical electrical semantics. It only reports observable Visio
    structure plus deterministic candidate families and topology evidence.
    """

    pages: list[dict[str, Any]] = []
    instances: list[dict[str, Any]] = []
    text_candidates: list[dict[str, Any]] = []
    connection_points: list[dict[str, Any]] = []
    glue_edges: list[dict[str, Any]] = []
    endpoint_formula_candidates: list[dict[str, Any]] = []
    ambiguous: list[dict[str, Any]] = []
    family_instances: dict[str, list[str]] = {}
    family_signals: dict[str, dict[str, Any]] = {}
    family_confidence: dict[str, str] = {}
    family_text_patterns: dict[str, set[str]] = {}

    for page in sorted(snapshot.pages, key=lambda item: (item.page_id, item.name_u, item.name)):
        by_id = {shape.shape_id: shape for shape in page.shapes}
        children = _children_by_parent(page.shapes)
        cache: dict[int, dict[str, object]] = {}

        page_refs: list[str] = []
        for shape in sorted(page.shapes, key=lambda item: item.shape_id):
            ref = _shape_ref(page, shape.shape_id)
            page_refs.append(ref)
            signals = _shape_signals(shape, by_id, children, cache)
            candidate = str(signals["candidate_fingerprint"])
            family_id = "family:" + candidate.rsplit(":", 1)[-1][:24]
            confidence = _family_confidence(shape, signals)

            family_instances.setdefault(family_id, []).append(ref)
            family_signals.setdefault(
                family_id,
                {
                    "candidate_fingerprint": candidate,
                    "master_signature": signals["master_signature"],
                    "geometry_signature": signals["geometry_signature"],
                    "group_signature": signals["group_signature"],
                    "shapesheet_signature": signals["shapesheet_signature"],
                    "connection_point_signature": signals["connection_point_signature"],
                },
            )
            family_confidence.setdefault(family_id, confidence)
            family_text_patterns.setdefault(family_id, set()).add(str(signals["text_pattern"]))

            child_refs = [
                _shape_ref(page, child.shape_id)
                for child in children.get(shape.shape_id, ())
            ]
            instances.append(
                {
                    "ref": ref,
                    "page_id": page.page_id,
                    "shape_id": shape.shape_id,
                    "name": shape.name,
                    "name_u": shape.name_u,
                    "shape_type": shape.shape_type,
                    "master": {
                        "name": shape.master_name,
                        "name_u": shape.master_name_u,
                        "shape_id": shape.master_shape_id,
                    },
                    "parent_ref": (
                        _shape_ref(page, shape.parent_shape_id)
                        if shape.parent_shape_id is not None
                        else None
                    ),
                    "child_refs": child_refs,
                    "geometry": {
                        "pin_x": shape.geometry.pin_x,
                        "pin_y": shape.geometry.pin_y,
                        "width": shape.geometry.width,
                        "height": shape.geometry.height,
                        "rotation": shape.geometry.rotation,
                    },
                    "layers": list(shape.layers),
                    "shape_sheet_cells": [
                        {
                            "section": cell.section,
                            "row": cell.row,
                            "cell": cell.cell,
                            "formula": cell.formula,
                            "value": cell.value,
                            "unit": cell.unit,
                        }
                        for cell in sorted(
                            shape.cells,
                            key=lambda item: (
                                item.section.casefold(),
                                item.row.casefold(),
                                item.cell.casefold(),
                            ),
                        )
                    ],
                    "normalized_geometry_rows": _geometry_cells(shape),
                    "text": shape.text,
                    "text_pattern": signals["text_pattern"],
                    "endpoint_formulas": {
                        "begin_x": shape.begin_x_formula,
                        "begin_y": shape.begin_y_formula,
                        "end_x": shape.end_x_formula,
                        "end_y": shape.end_y_formula,
                    },
                    "family_id": family_id,
                    "candidate_fingerprint": candidate,
                    "signal_fingerprints": {
                        "master": signals["master_signature"],
                        "geometry": signals["geometry_signature"],
                        "group": signals["group_signature"],
                        "shapesheet": signals["shapesheet_signature"],
                        "connection_points": signals["connection_point_signature"],
                    },
                    "classification_confidence": confidence,
                }
            )

            if shape.text:
                text_candidates.append(
                    {
                        "shape_ref": ref,
                        "text": shape.text,
                        "pattern": signals["text_pattern"],
                        "separate_from_symbol_geometry": True,
                    }
                )

            for point in shape.connection_points:
                connection_points.append(
                    {
                        "shape_ref": ref,
                        "row": point.row,
                        "x": point.x,
                        "y": point.y,
                        "x_formula": point.x_formula,
                        "y_formula": point.y_formula,
                        "direction_formula": point.direction_formula,
                    }
                )

            formulas = {
                "begin_x": shape.begin_x_formula,
                "begin_y": shape.begin_y_formula,
                "end_x": shape.end_x_formula,
                "end_y": shape.end_y_formula,
            }
            nonempty_formulas = {key: value for key, value in formulas.items() if value}
            if nonempty_formulas:
                endpoint_formula_candidates.append(
                    {
                        "shape_ref": ref,
                        "formulas": nonempty_formulas,
                        "evidence_type": "endpoint_formula",
                        "confidence": CONFIDENCE_REVIEW,
                    }
                )

            if shape.parent_shape_id is not None and shape.parent_shape_id not in by_id:
                ambiguous.append(
                    {
                        "shape_ref": ref,
                        "reason": "orphan_parent_shape",
                        "details": {"parent_shape_id": shape.parent_shape_id},
                        "confidence": CONFIDENCE_AMBIGUOUS,
                    }
                )
            elif confidence in {CONFIDENCE_AMBIGUOUS, CONFIDENCE_UNKNOWN}:
                ambiguous.append(
                    {
                        "shape_ref": ref,
                        "reason": (
                            "insufficient_structural_signal"
                            if confidence == CONFIDENCE_UNKNOWN
                            else "text_without_strong_symbol_structure"
                        ),
                        "confidence": confidence,
                    }
                )

        for connect in sorted(
            page.connects,
            key=lambda item: (
                item.from_shape_id,
                item.from_cell.casefold(),
                item.to_shape_id,
                item.to_cell.casefold(),
            ),
        ):
            dangling = (
                connect.from_shape_id not in by_id or connect.to_shape_id not in by_id
            )
            glue_edges.append(
                {
                    "page_id": page.page_id,
                    "from_shape_ref": _shape_ref(page, connect.from_shape_id),
                    "from_cell": connect.from_cell,
                    "to_shape_ref": _shape_ref(page, connect.to_shape_id),
                    "to_cell": connect.to_cell,
                    "evidence": ["page.connects", "native_glue"],
                    "evidence_type": "native_glue",
                    "confidence": CONFIDENCE_EXACT_NATIVE,
                    "inferred": False,
                    "dangling_shape_reference": dangling,
                }
            )
            if dangling:
                ambiguous.append(
                    {
                        "shape_ref": _shape_ref(page, connect.from_shape_id),
                        "reason": "native_glue_references_missing_shape",
                        "details": {
                            "from_shape_id": connect.from_shape_id,
                            "to_shape_id": connect.to_shape_id,
                        },
                        "confidence": CONFIDENCE_REVIEW,
                    }
                )

        pages.append(
            {
                "page_id": page.page_id,
                "name": page.name,
                "name_u": page.name_u,
                "width": page.width,
                "height": page.height,
                "shape_refs": page_refs,
                "shape_count": len(page.shapes),
                "native_glue_count": len(page.connects),
            }
        )

    families = []
    for family_id in sorted(family_instances):
        refs = sorted(family_instances[family_id])
        families.append(
            {
                "family_id": family_id,
                **family_signals[family_id],
                "classification_confidence": family_confidence[family_id],
                "frequency": len(refs),
                "instance_refs": refs,
                "text_patterns": sorted(pattern for pattern in family_text_patterns[family_id] if pattern),
            }
        )

    master_frequency: dict[str, int] = {}
    shape_type_frequency: dict[str, int] = {}
    text_pattern_frequency: dict[str, int] = {}
    for item in instances:
        master = item["master"]["name_u"] or item["master"]["name"] or "<no-master>"
        master_frequency[str(master)] = master_frequency.get(str(master), 0) + 1
        shape_type = str(item["shape_type"] or "<unknown>")
        shape_type_frequency[shape_type] = shape_type_frequency.get(shape_type, 0) + 1
        pattern = str(item["text_pattern"] or "")
        if pattern:
            text_pattern_frequency[pattern] = text_pattern_frequency.get(pattern, 0) + 1

    stats = {
        "page_count": len(pages),
        "shape_count": len(instances),
        "top_level_shape_count": sum(1 for item in instances if item["parent_ref"] is None),
        "nested_shape_count": sum(1 for item in instances if item["parent_ref"] is not None),
        "symbol_family_count": len(families),
        "repeated_symbol_family_count": sum(1 for item in families if item["frequency"] > 1),
        "native_glue_edge_count": len(glue_edges),
        "connection_point_count": len(connection_points),
        "endpoint_formula_shape_count": len(endpoint_formula_candidates),
        "ambiguous_or_unknown_shape_count": len(ambiguous),
        "master_frequency": dict(sorted(master_frequency.items())),
        "shape_type_frequency": dict(sorted(shape_type_frequency.items())),
        "text_pattern_frequency": dict(sorted(text_pattern_frequency.items())),
        "family_frequency": {
            item["family_id"]: item["frequency"]
            for item in sorted(families, key=lambda value: value["family_id"])
        },
    }

    report: dict[str, Any] = {
        "report_version": REPORT_VERSION,
        "source_contract": {
            "read_only": True,
            "mutates_source": False,
            "canonical_import_performed": False,
            "glue_repair_performed": False,
        },
        "document": {
            "name": snapshot.name,
            "full_name": snapshot.full_name,
            "visio_version": snapshot.visio_version,
            "reported_read_only": snapshot.read_only,
            "metadata": dict(sorted(snapshot.metadata.items())),
        },
        "pages": pages,
        "symbol_families": families,
        "instances": sorted(instances, key=lambda item: item["ref"]),
        "text_designation_candidates": sorted(
            text_candidates, key=lambda item: item["shape_ref"]
        ),
        "glue_graph": {
            "edges": glue_edges,
            "inferred_edges": [],
            "policy": {
                "native_glue": CONFIDENCE_EXACT_NATIVE,
                "endpoint_formula": CONFIDENCE_REVIEW,
                "connection_point": CONFIDENCE_REVIEW,
                "spatial_proximity": CONFIDENCE_AMBIGUOUS,
                "topology_context": CONFIDENCE_REVIEW,
                "visual_contact_is_proof": False,
            },
        },
        "endpoint_formula_candidates": endpoint_formula_candidates,
        "connection_point_inventory": connection_points,
        "ambiguous_unclassified": sorted(
            ambiguous, key=lambda item: item["shape_ref"]
        ),
        "statistics": stats,
    }
    report["inspection_fingerprint"] = _hash("inspection", report)
    return report


def report_json(report: Mapping[str, Any]) -> str:
    return json.dumps(
        report,
        ensure_ascii=False,
        sort_keys=True,
        indent=2,
    ) + "\n"


__all__ = [
    "CONFIDENCE_AMBIGUOUS",
    "CONFIDENCE_EXACT_NATIVE",
    "CONFIDENCE_HIGH",
    "CONFIDENCE_LEVELS",
    "CONFIDENCE_REVIEW",
    "CONFIDENCE_UNKNOWN",
    "LegacyConnectionPoint",
    "LegacyDocumentSnapshot",
    "LegacyGeometry",
    "LegacyGlueSnapshot",
    "LegacyPageSnapshot",
    "LegacyShapeSheetCell",
    "LegacyShapeSnapshot",
    "LegacyVisioSnapshotSource",
    "REPORT_VERSION",
    "inspect_legacy_visio",
    "report_json",
]
