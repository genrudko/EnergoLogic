from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from energologic.core.model import CanonicalModel


@dataclass(frozen=True, slots=True)
class VisioShapeBinding:
    """Runtime projection metadata; never part of the canonical electrical model."""

    element_id: str
    page_name: str
    shape_id: int


class VisioFrontend(Protocol):
    """Boundary for the first frontend.

    `capture_model` is an explicit import operation from a Visio document.
    After capture, the returned CanonicalModel is the source of truth.

    `render_model` projects a canonical model into Visio and returns ephemeral
    shape bindings that may be used by the adapter/runtime.
    """

    def capture_model(self) -> CanonicalModel: ...

    def render_model(self, model: CanonicalModel) -> tuple[VisioShapeBinding, ...]: ...
