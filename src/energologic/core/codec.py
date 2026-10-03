from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from .errors import ModelDecodeError
from .model import CanonicalModel, Connection, Element, Endpoint, Terminal


def _mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise ModelDecodeError(path, "expected object")
    return value


def _list(value: Any, path: str) -> list[Any]:
    if not isinstance(value, list):
        raise ModelDecodeError(path, "expected array")
    return value


def _string(value: Any, path: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise ModelDecodeError(path, "expected string")
    if not allow_empty and not value:
        raise ModelDecodeError(path, "must not be empty")
    return value


def _keys(obj: Mapping[str, Any], path: str, allowed: set[str], required: set[str]) -> None:
    missing = sorted(required - obj.keys())
    if missing:
        raise ModelDecodeError(path, f"missing required field(s): {', '.join(missing)}")
    extra = sorted(obj.keys() - allowed)
    if extra:
        raise ModelDecodeError(path, f"unknown field(s): {', '.join(extra)}")


def _json_value(value: Any, path: str) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            raise ModelDecodeError(path, "non-finite numbers are not allowed")
        return value
    if isinstance(value, list):
        return [_json_value(item, f"{path}/{index}") for index, item in enumerate(value)]
    if isinstance(value, dict):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ModelDecodeError(path, "object keys must be strings")
            normalized[key] = _json_value(item, f"{path}/{key}")
        return normalized
    raise ModelDecodeError(path, f"unsupported JSON value type: {type(value).__name__}")


def _attributes(obj: Mapping[str, Any], path: str) -> dict[str, Any]:
    value = obj.get("attributes", {})
    return dict(_mapping(_json_value(value, path), path))


def _terminal(data: Any, path: str) -> Terminal:
    obj = _mapping(data, path)
    _keys(obj, path, {"id", "name", "attributes"}, {"id"})
    return Terminal(
        id=_string(obj["id"], f"{path}/id"),
        name=_string(obj.get("name", ""), f"{path}/name", allow_empty=True),
        attributes=_attributes(obj, f"{path}/attributes"),
    )


def _element(data: Any, path: str) -> Element:
    obj = _mapping(data, path)
    _keys(obj, path, {"id", "kind", "name", "terminals", "attributes"}, {"id", "kind"})
    terminals = tuple(
        _terminal(item, f"{path}/terminals/{index}")
        for index, item in enumerate(_list(obj.get("terminals", []), f"{path}/terminals"))
    )
    return Element(
        id=_string(obj["id"], f"{path}/id"),
        kind=_string(obj["kind"], f"{path}/kind"),
        name=_string(obj.get("name", ""), f"{path}/name", allow_empty=True),
        terminals=terminals,
        attributes=_attributes(obj, f"{path}/attributes"),
    )


def _endpoint(data: Any, path: str) -> Endpoint:
    obj = _mapping(data, path)
    _keys(obj, path, {"element_id", "terminal_id"}, {"element_id", "terminal_id"})
    return Endpoint(
        element_id=_string(obj["element_id"], f"{path}/element_id"),
        terminal_id=_string(obj["terminal_id"], f"{path}/terminal_id"),
    )


def _connection(data: Any, path: str) -> Connection:
    obj = _mapping(data, path)
    _keys(obj, path, {"id", "endpoints", "attributes"}, {"id", "endpoints"})
    endpoints = _list(obj["endpoints"], f"{path}/endpoints")
    if len(endpoints) != 2:
        raise ModelDecodeError(f"{path}/endpoints", "must contain exactly two endpoints")
    return Connection(
        id=_string(obj["id"], f"{path}/id"),
        endpoints=(
            _endpoint(endpoints[0], f"{path}/endpoints/0"),
            _endpoint(endpoints[1], f"{path}/endpoints/1"),
        ),
        attributes=_attributes(obj, f"{path}/attributes"),
    )


def decode_model(data: Any) -> CanonicalModel:
    obj = _mapping(data, "/")
    _keys(
        obj,
        "/",
        {"schema_version", "model_id", "elements", "connections", "metadata"},
        {"schema_version", "model_id"},
    )
    schema_version = _string(obj["schema_version"], "/schema_version")
    if schema_version != "0.1":
        raise ModelDecodeError("/schema_version", f"unsupported schema version: {schema_version}")

    elements = tuple(
        _element(item, f"/elements/{index}")
        for index, item in enumerate(_list(obj.get("elements", []), "/elements"))
    )
    connections = tuple(
        _connection(item, f"/connections/{index}")
        for index, item in enumerate(_list(obj.get("connections", []), "/connections"))
    )
    metadata = dict(_mapping(_json_value(obj.get("metadata", {}), "/metadata"), "/metadata"))

    return CanonicalModel(
        schema_version=schema_version,
        model_id=_string(obj["model_id"], "/model_id"),
        elements=elements,
        connections=connections,
        metadata=metadata,
    )


def load_model(path: str | Path) -> CanonicalModel:
    source = Path(path)
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ModelDecodeError(
            "/",
            f"invalid JSON at line {exc.lineno}, column {exc.colno}",
        ) from exc
    return decode_model(data)


def _terminal_data(terminal: Terminal) -> dict[str, Any]:
    return {
        "id": terminal.id,
        "name": terminal.name,
        "attributes": dict(terminal.attributes),
    }


def _element_data(element: Element) -> dict[str, Any]:
    return {
        "id": element.id,
        "kind": element.kind,
        "name": element.name,
        "terminals": [
            _terminal_data(terminal)
            for terminal in sorted(element.terminals, key=lambda item: item.id)
        ],
        "attributes": dict(element.attributes),
    }


def _endpoint_data(endpoint: Endpoint) -> dict[str, str]:
    return {"element_id": endpoint.element_id, "terminal_id": endpoint.terminal_id}


def _connection_data(connection: Connection) -> dict[str, Any]:
    endpoints = sorted(connection.endpoints)
    return {
        "id": connection.id,
        "endpoints": [_endpoint_data(endpoint) for endpoint in endpoints],
        "attributes": dict(connection.attributes),
    }


def model_to_data(model: CanonicalModel) -> dict[str, Any]:
    return {
        "schema_version": model.schema_version,
        "model_id": model.model_id,
        "elements": [
            _element_data(element)
            for element in sorted(model.elements, key=lambda item: item.id)
        ],
        "connections": [
            _connection_data(connection)
            for connection in sorted(model.connections, key=lambda item: item.id)
        ],
        "metadata": dict(model.metadata),
    }


def canonical_json(model: CanonicalModel) -> str:
    return (
        json.dumps(
            model_to_data(model),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    )


def canonical_bytes(model: CanonicalModel) -> bytes:
    return canonical_json(model).encode("utf-8")


def fingerprint(model: CanonicalModel) -> str:
    return hashlib.sha256(canonical_bytes(model)).hexdigest()
