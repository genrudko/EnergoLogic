"""Adapter for the authorized Visio MCP call surface.

The caller is injected by the application host; this module does not access
secrets, establish independent desktop sessions, or bypass the journal gate.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence


class VisioToolCallError(RuntimeError):
    """MCP transport or returned tool error; mutation outcome may be unknown."""


VisioCall = Callable[[str, dict[str, Any], dict[str, Any] | None], Any]


@dataclass(slots=True)
class McpVtdVisioGateway:
    """Typed gateway to a trusted invocation of `visio_call`.

    Only approved tool names are called. A mutation always passes an explicit
    mutation journal to the host. The host must enforce its own access policy
    and must never retry an uncertain `trigger_shape_action`.
    """

    call: VisioCall

    @staticmethod
    def _decode(value: Any) -> Any:
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except (ValueError, TypeError) as error:
                raise VisioToolCallError("invalid MCP response JSON") from error
        if not isinstance(value, Mapping):
            raise VisioToolCallError("invalid MCP response shape")
        if value.get("ok") is False or value.get("isError") is True or value.get("error"):
            raise VisioToolCallError("Visio MCP returned failure")
        # The normal production Master MCP exposes an outer bridge envelope;
        # an injected client can also return the decoded inner tool response.
        if "data" in value and isinstance(value["data"], Mapping):
            data = value["data"]
            if data.get("isError") is True or data.get("error"):
                raise VisioToolCallError("Visio MCP nested tool failure")
            result = data.get("structuredContent", {}).get("result") if isinstance(data.get("structuredContent"), Mapping) else None
            if result is None:
                raise VisioToolCallError("missing Visio structured result")
            if isinstance(result, str):
                try:
                    result = json.loads(result)
                except (TypeError, ValueError) as error:
                    raise VisioToolCallError("invalid nested Visio JSON") from error
            if isinstance(result, Mapping) and (
                result.get("error") or result.get("isError") is True or result.get("ok") is False
            ):
                raise VisioToolCallError("Visio nested operation returned an error")
            return result
        return value

    def _invoke(
        self, tool_name: str, arguments: Mapping[str, Any], *,
        mutation: bool = False,
    ) -> Any:
        journal = (
            {
                "mutation": True,
                "summary": "EnergoLogic gated test projection: native VTD breaker action",
            }
            if mutation
            else None
        )
        try:
            return self._decode(self.call(tool_name, dict(arguments), journal))
        except VisioToolCallError:
            raise
        except Exception as error:
            raise VisioToolCallError("Visio MCP invocation failed") from error

    def list_open_documents(self) -> Sequence[Mapping[str, Any]]:
        result = self._invoke("list_open_documents", {})
        if not isinstance(result, list):
            raise VisioToolCallError("documents result is not a list")
        return result

    def list_pages(self, document_name: str) -> Sequence[Mapping[str, Any]]:
        result = self._invoke("list_pages", {"doc_name": document_name})
        if not isinstance(result, list):
            raise VisioToolCallError("pages result is not a list")
        return result

    def inspect_shape_state_model(
        self, document_name: str, page_name: str, shape_id: int,
    ) -> Mapping[str, Any]:
        result = self._invoke("inspect_shape_state_model", {
            "doc_name": document_name, "page": page_name, "shape_id": shape_id,
        })
        if not isinstance(result, Mapping):
            raise VisioToolCallError("shape model result is not an object")
        return result

    def get_vtd_state(
        self, document_name: str, page_name: str, shape_id: int,
    ) -> Mapping[str, Any]:
        result = self._invoke("get_vtd_state", {
            "doc_name": document_name, "page": page_name, "shape_id": shape_id,
        })
        if not isinstance(result, Mapping):
            raise VisioToolCallError("VTD state result is not an object")
        return result

    def trigger_shape_action(
        self, document_name: str, page_name: str, shape_id: int,
        action_name: str,
    ) -> Any:
        if action_name != "Row_1":
            raise VisioToolCallError("unsupported native VTD action")
        return self._invoke("trigger_shape_action", {
            "doc_name": document_name,
            "page": page_name,
            "shape_id": shape_id,
            "action_name": action_name,
        }, mutation=True)
