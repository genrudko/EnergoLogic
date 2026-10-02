from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

JsonObject = Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class Terminal:
    id: str
    name: str = ""
    attributes: JsonObject = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Element:
    id: str
    kind: str
    name: str = ""
    terminals: tuple[Terminal, ...] = ()
    attributes: JsonObject = field(default_factory=dict)


@dataclass(frozen=True, slots=True, order=True)
class Endpoint:
    element_id: str
    terminal_id: str


@dataclass(frozen=True, slots=True)
class Connection:
    id: str
    endpoints: tuple[Endpoint, Endpoint]
    attributes: JsonObject = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CanonicalModel:
    schema_version: str
    model_id: str
    elements: tuple[Element, ...] = ()
    connections: tuple[Connection, ...] = ()
    metadata: JsonObject = field(default_factory=dict)
