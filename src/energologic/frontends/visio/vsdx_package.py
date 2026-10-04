from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path, PurePosixPath
import re
from typing import Iterable
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from .legacy_inspection import (
    LegacyConnectionPoint,
    LegacyDocumentSnapshot,
    LegacyGeometry,
    LegacyGlueSnapshot,
    LegacyPageSnapshot,
    LegacyShapeSheetCell,
    LegacyShapeSnapshot,
)


_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
_R_ID = f"{{{_REL_NS}}}id"
_NUMBER = re.compile(r"^[-+]?(?:\\d+(?:\\.\\d*)?|\\.\\d+)(?:[Ee][-+]?\\d+)?$")
_INTEGER = re.compile(r"^[+-]?\\d+$")


class VsdxInspectionError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class _MasterIdentity:
    master_id: int
    name: str = ""
    name_u: str = ""


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _xml(zip_file: ZipFile, member: str) -> ET.Element:
    try:
        payload = zip_file.read(member)
    except KeyError as exc:
        raise VsdxInspectionError(f"missing VSDX package part: {member}") from exc
    try:
        return ET.fromstring(payload)
    except ET.ParseError as exc:
        raise VsdxInspectionError(f"invalid XML in VSDX package part: {member}") from exc


def _relationship_targets(zip_file: ZipFile, rels_member: str) -> dict[str, str]:
    try:
        root = _xml(zip_file, rels_member)
    except VsdxInspectionError:
        return {}
    result: dict[str, str] = {}
    for rel in root:
        if _local_name(rel.tag) != "Relationship":
            continue
        rel_id = rel.attrib.get("Id")
        target = rel.attrib.get("Target")
        if rel_id and target and rel.attrib.get("TargetMode", "Internal") != "External":
            result[rel_id] = target
    return result


def _resolve_target(source_dir: str, target: str) -> str:
    # OPC relationship targets use POSIX separators and are relative to the
    # source part's directory. Prevent an archive target from escaping root.
    resolved = PurePosixPath(source_dir, target)
    normalized: list[str] = []
    for part in resolved.parts:
        if part in {"", ".", "/"}:
            continue
        if part == "..":
            if normalized:
                normalized.pop()
            continue
        normalized.append(part)
    return "/".join(normalized)


def _cell_value(raw: str | None) -> float | int | bool | str | None:
    if raw is None:
        return None
    stripped = raw.strip()
    if stripped.upper() == "TRUE":
        return True
    if stripped.upper() == "FALSE":
        return False
    if _INTEGER.fullmatch(stripped):
        try:
            return int(stripped)
        except ValueError:
            pass
    if _NUMBER.fullmatch(stripped):
        try:
            return float(stripped)
        except ValueError:
            pass
    return raw


def _cell_formula(cell: ET.Element) -> str:
    return cell.attrib.get("F", "")


def _cell_raw_value(cell: ET.Element) -> str | None:
    return cell.attrib.get("V")


def _direct_cells(element: ET.Element) -> dict[str, ET.Element]:
    return {
        cell.attrib.get("N", ""): cell
        for cell in element
        if _local_name(cell.tag) == "Cell" and cell.attrib.get("N")
    }


def _float_cell(cells: dict[str, ET.Element], name: str) -> float | None:
    cell = cells.get(name)
    if cell is None:
        return None
    raw = _cell_raw_value(cell)
    if raw is None:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _all_shape_cells(shape: ET.Element) -> tuple[LegacyShapeSheetCell, ...]:
    result: list[LegacyShapeSheetCell] = []

    for cell in shape:
        if _local_name(cell.tag) != "Cell":
            continue
        name = cell.attrib.get("N", "")
        if not name:
            continue
        result.append(
            LegacyShapeSheetCell(
                section="Shape",
                row="",
                cell=name,
                formula=_cell_formula(cell),
                value=_cell_value(_cell_raw_value(cell)),
                unit=cell.attrib.get("U"),
            )
        )

    for section in shape:
        if _local_name(section.tag) != "Section":
            continue
        section_name = section.attrib.get("N") or (
            "Geometry" + section.attrib.get("IX", "")
            if section.attrib.get("N", "").casefold().startswith("geometry")
            or "Geometry" in section.attrib.get("N", "")
            else f"Section:{section.attrib.get('IX', '')}"
        )
        # Geometry sections usually have N="Geometry" and IX=n. Preserve IX
        # so multiple geometry sections remain distinct.
        if section.attrib.get("N", "").casefold().startswith("geometry"):
            section_name = f"Geometry{section.attrib.get('IX', '0')}"

        for cell in section:
            if _local_name(cell.tag) == "Cell":
                name = cell.attrib.get("N", "")
                if name:
                    result.append(
                        LegacyShapeSheetCell(
                            section=section_name,
                            row="",
                            cell=name,
                            formula=_cell_formula(cell),
                            value=_cell_value(_cell_raw_value(cell)),
                            unit=cell.attrib.get("U"),
                        )
                    )
                continue
            if _local_name(cell.tag) != "Row":
                continue
            row_name = (
                cell.attrib.get("N")
                or cell.attrib.get("T")
                or f"IX:{cell.attrib.get('IX', '')}"
            )
            if cell.attrib.get("IX") is not None and cell.attrib.get("T"):
                row_name = f"{cell.attrib.get('T')}:{cell.attrib.get('IX')}"
            for row_cell in cell:
                if _local_name(row_cell.tag) != "Cell":
                    continue
                name = row_cell.attrib.get("N", "")
                if not name:
                    continue
                result.append(
                    LegacyShapeSheetCell(
                        section=section_name,
                        row=row_name,
                        cell=name,
                        formula=_cell_formula(row_cell),
                        value=_cell_value(_cell_raw_value(row_cell)),
                        unit=row_cell.attrib.get("U"),
                    )
                )

    return tuple(result)


def _connection_points(shape: ET.Element) -> tuple[LegacyConnectionPoint, ...]:
    points: list[LegacyConnectionPoint] = []
    for section in shape:
        if _local_name(section.tag) != "Section":
            continue
        section_name = section.attrib.get("N", "").casefold()
        if not section_name.startswith("connection"):
            continue
        for row in section:
            if _local_name(row.tag) != "Row":
                continue
            row_cells = _direct_cells(row)
            row_name = row.attrib.get("N") or row.attrib.get("IX") or ""
            x = _float_cell(row_cells, "X")
            y = _float_cell(row_cells, "Y")
            dir_parts = []
            for name in ("DirX", "DirY", "Type"):
                cell = row_cells.get(name)
                if cell is not None:
                    dir_parts.append(f"{name}={_cell_formula(cell) or _cell_raw_value(cell) or ''}")
            points.append(
                LegacyConnectionPoint(
                    row=str(row_name),
                    x=x,
                    y=y,
                    x_formula=_cell_formula(row_cells["X"]) if "X" in row_cells else "",
                    y_formula=_cell_formula(row_cells["Y"]) if "Y" in row_cells else "",
                    direction_formula=";".join(dir_parts),
                )
            )
    return tuple(points)


def _shape_text(shape: ET.Element) -> str:
    for child in shape:
        if _local_name(child.tag) == "Text":
            return "".join(child.itertext()).strip()
    return ""


def _layer_names(page_root: ET.Element) -> dict[str, str]:
    page_sheet = next(
        (child for child in page_root if _local_name(child.tag) == "PageSheet"),
        None,
    )
    if page_sheet is None:
        return {}
    result: dict[str, str] = {}
    for section in page_sheet:
        if _local_name(section.tag) != "Section" or section.attrib.get("N", "").casefold() != "layer":
            continue
        for row in section:
            if _local_name(row.tag) != "Row":
                continue
            index = row.attrib.get("IX")
            if index is None:
                continue
            cells = _direct_cells(row)
            name_cell = cells.get("Name")
            raw = _cell_raw_value(name_cell) if name_cell is not None else None
            result[index] = raw or f"layer-index:{index}"
    return result


def _shape_layers(shape: ET.Element, layers: dict[str, str]) -> tuple[str, ...]:
    cells = _direct_cells(shape)
    member = cells.get("LayerMember")
    if member is None:
        return ()
    raw = _cell_raw_value(member) or _cell_formula(member)
    if not raw:
        return ()
    indices = [part.strip() for part in re.split(r"[;,]", raw) if part.strip()]
    return tuple(layers.get(index, f"layer-index:{index}") for index in indices)


def _parse_shape(
    shape: ET.Element,
    *,
    parent_shape_id: int | None,
    masters: dict[int, _MasterIdentity],
    layers: dict[str, str],
) -> tuple[LegacyShapeSnapshot, ...]:
    try:
        shape_id = int(shape.attrib["ID"])
    except (KeyError, ValueError) as exc:
        raise VsdxInspectionError("Visio shape without integer ID") from exc

    master_id_raw = shape.attrib.get("Master")
    master_id = int(master_id_raw) if master_id_raw and master_id_raw.isdigit() else None
    master = masters.get(master_id) if master_id is not None else None
    master_shape_raw = shape.attrib.get("MasterShape")
    master_shape_id = (
        int(master_shape_raw)
        if master_shape_raw and master_shape_raw.isdigit()
        else None
    )

    cells = _direct_cells(shape)
    geometry = LegacyGeometry(
        pin_x=_float_cell(cells, "PinX") or 0.0,
        pin_y=_float_cell(cells, "PinY") or 0.0,
        width=_float_cell(cells, "Width") or 0.0,
        height=_float_cell(cells, "Height") or 0.0,
        rotation=_float_cell(cells, "Angle") or 0.0,
    )

    snapshot = LegacyShapeSnapshot(
        shape_id=shape_id,
        name=shape.attrib.get("Name", ""),
        name_u=shape.attrib.get("NameU", ""),
        shape_type=shape.attrib.get("Type", ""),
        master_name=master.name if master else "",
        master_name_u=master.name_u if master else "",
        master_shape_id=master_shape_id,
        parent_shape_id=parent_shape_id,
        geometry=geometry,
        text=_shape_text(shape),
        layers=_shape_layers(shape, layers),
        cells=_all_shape_cells(shape),
        connection_points=_connection_points(shape),
        begin_x_formula=_cell_formula(cells["BeginX"]) if "BeginX" in cells else "",
        begin_y_formula=_cell_formula(cells["BeginY"]) if "BeginY" in cells else "",
        end_x_formula=_cell_formula(cells["EndX"]) if "EndX" in cells else "",
        end_y_formula=_cell_formula(cells["EndY"]) if "EndY" in cells else "",
    )

    result = [snapshot]
    nested_container = next(
        (child for child in shape if _local_name(child.tag) == "Shapes"),
        None,
    )
    if nested_container is not None:
        for child_shape in nested_container:
            if _local_name(child_shape.tag) == "Shape":
                result.extend(
                    _parse_shape(
                        child_shape,
                        parent_shape_id=shape_id,
                        masters=masters,
                        layers=layers,
                    )
                )
    return tuple(result)


def _masters(zip_file: ZipFile) -> dict[int, _MasterIdentity]:
    if "visio/masters/masters.xml" not in zip_file.namelist():
        return {}
    root = _xml(zip_file, "visio/masters/masters.xml")
    result: dict[int, _MasterIdentity] = {}
    for master in root:
        if _local_name(master.tag) != "Master":
            continue
        raw_id = master.attrib.get("ID")
        if raw_id is None:
            continue
        try:
            master_id = int(raw_id)
        except ValueError:
            continue
        result[master_id] = _MasterIdentity(
            master_id=master_id,
            name=master.attrib.get("Name", ""),
            name_u=master.attrib.get("NameU", ""),
        )
    return result


def _core_metadata(zip_file: ZipFile) -> dict[str, str]:
    result: dict[str, str] = {"package_format": "vsdx"}
    for member in ("docProps/core.xml", "docProps/app.xml"):
        if member not in zip_file.namelist():
            continue
        root = _xml(zip_file, member)
        for child in root:
            key = _local_name(child.tag)
            value = (child.text or "").strip()
            if value and key not in result:
                result[key] = value
    return result


def _page_dimensions(page_meta: ET.Element) -> tuple[float | None, float | None]:
    page_sheet = next(
        (child for child in page_meta if _local_name(child.tag) == "PageSheet"),
        None,
    )
    if page_sheet is None:
        return None, None
    cells = _direct_cells(page_sheet)
    return _float_cell(cells, "PageWidth"), _float_cell(cells, "PageHeight")


def _page_part_map(zip_file: ZipFile) -> tuple[ET.Element, dict[str, str]]:
    root = _xml(zip_file, "visio/pages/pages.xml")
    rels = _relationship_targets(zip_file, "visio/pages/_rels/pages.xml.rels")
    return root, rels


def capture_vsdx_package(path: str | Path) -> LegacyDocumentSnapshot:
    """Read a VSDX package without invoking Visio and without writing the file."""

    source = Path(path)
    if not source.is_file():
        raise VsdxInspectionError(f"VSDX file does not exist: {source}")
    before_sha = _sha256(source)

    with ZipFile(source, "r") as zip_file:
        names = set(zip_file.namelist())
        if "visio/pages/pages.xml" not in names:
            raise VsdxInspectionError("not a supported VSDX package: pages.xml missing")

        metadata = _core_metadata(zip_file)
        metadata["source_sha256"] = before_sha
        masters = _masters(zip_file)
        pages_root, page_rels = _page_part_map(zip_file)
        pages: list[LegacyPageSnapshot] = []

        for page_meta in pages_root:
            if _local_name(page_meta.tag) != "Page":
                continue
            raw_page_id = page_meta.attrib.get("ID")
            try:
                page_id = int(raw_page_id) if raw_page_id is not None else len(pages)
            except ValueError:
                page_id = len(pages)
            rel_element = next(
                (child for child in page_meta if _local_name(child.tag) == "Rel"),
                None,
            )
            rel_id = rel_element.attrib.get(_R_ID) if rel_element is not None else None
            if not rel_id or rel_id not in page_rels:
                raise VsdxInspectionError(f"page {page_id} has no resolvable package relationship")
            page_member = _resolve_target("visio/pages", page_rels[rel_id])
            page_root = _xml(zip_file, page_member)
            layers = _layer_names(page_root)

            shape_container = next(
                (child for child in page_root if _local_name(child.tag) == "Shapes"),
                None,
            )
            shapes: list[LegacyShapeSnapshot] = []
            if shape_container is not None:
                for shape in shape_container:
                    if _local_name(shape.tag) != "Shape":
                        continue
                    shapes.extend(
                        _parse_shape(
                            shape,
                            parent_shape_id=None,
                            masters=masters,
                            layers=layers,
                        )
                    )

            connects_container = next(
                (child for child in page_root if _local_name(child.tag) == "Connects"),
                None,
            )
            connects: list[LegacyGlueSnapshot] = []
            if connects_container is not None:
                for connect in connects_container:
                    if _local_name(connect.tag) != "Connect":
                        continue
                    try:
                        from_shape = int(connect.attrib["FromSheet"])
                        to_shape = int(connect.attrib["ToSheet"])
                    except (KeyError, ValueError):
                        continue
                    to_cell = connect.attrib.get("ToCell")
                    if not to_cell:
                        to_part = connect.attrib.get("ToPart", "")
                        to_cell = f"ToPart:{to_part}" if to_part else ""
                    connects.append(
                        LegacyGlueSnapshot(
                            from_shape_id=from_shape,
                            from_cell=connect.attrib.get("FromCell", ""),
                            to_shape_id=to_shape,
                            to_cell=to_cell,
                        )
                    )

            width, height = _page_dimensions(page_meta)
            pages.append(
                LegacyPageSnapshot(
                    page_id=page_id,
                    name=page_meta.attrib.get("Name", ""),
                    name_u=page_meta.attrib.get("NameU", ""),
                    width=width,
                    height=height,
                    shapes=tuple(shapes),
                    connects=tuple(connects),
                )
            )

        visio_version = metadata.get("AppVersion", "")
        snapshot = LegacyDocumentSnapshot(
            name=source.name,
            full_name=str(source.resolve()),
            visio_version=visio_version,
            read_only=True,
            pages=tuple(pages),
            metadata=metadata,
        )

    after_sha = _sha256(source)
    if after_sha != before_sha:
        raise VsdxInspectionError("source VSDX content changed during read-only inspection")
    return snapshot


__all__ = ["VsdxInspectionError", "capture_vsdx_package"]
