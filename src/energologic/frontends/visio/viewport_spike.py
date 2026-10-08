"""P0-B experimental *read-only* page-to-client viewport coordinates.

This module is NOT a Visio renderer. It accepts a host-qualified view
rectangle and matched page coordinates and creates ephemeral screen-local
coordinates without touching document/ShapeSheet/COM.

Current units/coordinate orientation are candidates for desktop Visio COM:
the actual viewport/pixel alignment MUST be qualified on each host before
any graphical overlay can be marked supported.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite


class VisioViewportError(ValueError):
    """Invalid, stale or ambiguously bound viewport sample."""


def _number(value: object, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise VisioViewportError("viewport values must be numeric")
    val = float(value)
    if not isfinite(val) or (positive and val <= 0):
        raise VisioViewportError("viewport values must be finite and valid")
    return val


def _identity(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise VisioViewportError("missing stable document/page/window identity")
    return value


@dataclass(frozen=True, slots=True)
class VisioDrawingViewport:
    """One view token; dimensions in same page units as anchors, client px.

    Pixel coordinates are relative to the *drawing viewport*, NOT monitor
    coordinates; owner-window positioning/DPI transforms belong to the host.
    """

    document_ref: str
    page_ref: str
    window_ref: str
    generation: int
    left_page: float
    top_page: float
    width_page: float
    height_page: float
    client_width_px: float
    client_height_px: float
    page_unit: str = "visio_internal"

    def __post_init__(self) -> None:
        for val in (self.document_ref, self.page_ref, self.window_ref):
            _identity(val)
        if not isinstance(self.generation, int) or isinstance(self.generation, bool) or self.generation < 1:
            raise VisioViewportError("invalid viewport generation")
        if self.page_unit != "visio_internal":
            raise VisioViewportError("unknown Visio page unit")
        for val in (self.left_page, self.top_page):
            _number(val)
        for val in (
            self.width_page, self.height_page, self.client_width_px,
            self.client_height_px,
        ):
            _number(val, positive=True)


@dataclass(frozen=True, slots=True)
class VisioPageAnchor:
    document_ref: str
    page_ref: str
    window_ref: str
    generation: int
    x_page: float
    y_page: float
    page_unit: str = "visio_internal"


@dataclass(frozen=True, slots=True)
class ClientPoint:
    x_px: float
    y_px: float


@dataclass(frozen=True, slots=True)
class ClientSegment:
    start: ClientPoint
    end: ClientPoint


def _bind_and_project(
    viewport: VisioDrawingViewport,
    anchor: VisioPageAnchor,
) -> ClientPoint:
    if (
        not isinstance(viewport, VisioDrawingViewport)
        or not isinstance(anchor, VisioPageAnchor)
        or anchor.document_ref != viewport.document_ref
        or anchor.page_ref != viewport.page_ref
        or anchor.window_ref != viewport.window_ref
        or anchor.generation != viewport.generation
        or anchor.page_unit != viewport.page_unit
    ):
        raise VisioViewportError("stale or incompatible viewport and anchor")
    x = _number(anchor.x_page)
    y = _number(anchor.y_page)
    return ClientPoint(
        (x - viewport.left_page) * viewport.client_width_px / viewport.width_page,
        (viewport.top_page - y) * viewport.client_height_px / viewport.height_page,
    )


def project_point(
    viewport: VisioDrawingViewport, anchor: VisioPageAnchor
) -> ClientPoint | None:
    """Screen-local point or None outside the visible client rectangle."""

    p = _bind_and_project(viewport, anchor)
    if 0 <= p.x_px <= viewport.client_width_px and 0 <= p.y_px <= viewport.client_height_px:
        return p
    return None


def project_segment(
    viewport: VisioDrawingViewport, start: VisioPageAnchor, end: VisioPageAnchor
) -> ClientSegment | None:
    """Clipped line segment for an explicit, qualified canonical conductor.

    Neither line topology nor Visio Glue is inferred here. The caller must
    pass already-qualified segment endpoints and their canonical bindings.
    """

    a, b = _bind_and_project(viewport, start), _bind_and_project(viewport, end)
    dx, dy = b.x_px - a.x_px, b.y_px - a.y_px
    lo, hi = 0.0, 1.0
    for p, q in (
        (-dx, a.x_px), (dx, viewport.client_width_px - a.x_px),
        (-dy, a.y_px), (dy, viewport.client_height_px - a.y_px),
    ):
        if p == 0:
            if q < 0:
                return None
        else:
            factor = q / p
            if p < 0:
                lo = max(lo, factor)
            else:
                hi = min(hi, factor)
            if lo > hi:
                return None
    return ClientSegment(
        ClientPoint(a.x_px + lo * dx, a.y_px + lo * dy),
        ClientPoint(a.x_px + hi * dx, a.y_px + hi * dy),
    )
