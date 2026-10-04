from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class OperationalStatus(str, Enum):
    SUCCESS = "success"
    INVALID_MODEL = "invalid_model"
    INVALID_SOURCE = "invalid_source"
    INCOMPATIBLE_MODELS = "incompatible_models"


@dataclass(frozen=True, slots=True, order=True)
class SourceRef:
    element_id: str
    terminal_id: str


@dataclass(frozen=True, slots=True)
class OperationalMessage:
    code: str
    message: str
    element_id: str | None = None
    terminal_id: str | None = None
    path: str | None = None


@dataclass(frozen=True, slots=True)
class TerminalOperationalState:
    element_id: str
    terminal_id: str
    energized: bool
    sources: tuple[SourceRef, ...] = ()


@dataclass(frozen=True, slots=True)
class ElementOperationalState:
    element_id: str
    energized: bool
    fully_energized: bool
    energized_terminal_ids: tuple[str, ...] = ()
    deenergized_terminal_ids: tuple[str, ...] = ()
    sources: tuple[SourceRef, ...] = ()


@dataclass(frozen=True, slots=True)
class OperationalResult:
    status: OperationalStatus
    model_id: str
    model_fingerprint: str | None
    conductive_topology_fingerprint: str | None
    terminal_states: tuple[TerminalOperationalState, ...] = ()
    element_states: tuple[ElementOperationalState, ...] = ()
    messages: tuple[OperationalMessage, ...] = ()


@dataclass(frozen=True, slots=True)
class TerminalOperationalDelta:
    element_id: str
    terminal_id: str
    before_energized: bool
    after_energized: bool
    before_sources: tuple[SourceRef, ...] = ()
    after_sources: tuple[SourceRef, ...] = ()


@dataclass(frozen=True, slots=True)
class OperationalDelta:
    status: OperationalStatus
    before_model_id: str
    after_model_id: str
    topology_changed: bool
    terminal_changes: tuple[TerminalOperationalDelta, ...] = ()
    messages: tuple[OperationalMessage, ...] = ()
