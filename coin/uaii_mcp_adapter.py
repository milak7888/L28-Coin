# SPDX-License-Identifier: Apache-2.0
"""Pure in-process MCP-to-UAII mapping.

No MCP server, listener, network transport, signing, broadcast, settlement,
wallet, or persistent state is created here.
"""

from __future__ import annotations

from typing import Any

from .uaii_json import UaiiJsonError, canon_uaii
from .uaii_reference_core import (
    ENVELOPE_FIELDS,
    INTERFACE_PROFILE,
    OPERATIONS,
    process_uaii_request,
)

adapter_implemented = True
runtime_activated = False
network_activated = False
server_started = False
signing_authorized = False
spend_authorized = False
settlement_authorized = False
transaction_submission_authorized = False

MCP_TOOL_PREFIX = "l28_uaii_"
MCP_TOOL_NAMES = tuple(f"{MCP_TOOL_PREFIX}{op}" for op in OPERATIONS)
_OPERATION_BY_TOOL = dict(zip(MCP_TOOL_NAMES, OPERATIONS, strict=True))


class McpAdapterError(Exception):
    """Transport-boundary error; never a Protocol success."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def list_mcp_tools() -> tuple[dict[str, Any], ...]:
    """Return deterministic offline MCP tool declarations."""
    return tuple(
        {
            "name": tool_name,
            "operation": operation,
            "interface_profile": INTERFACE_PROFILE,
            "input_fields": list(ENVELOPE_FIELDS),
            "transport_only": True,
            "execution_authorized": False,
            "signing_authorized": False,
            "spend_authorized": False,
            "settlement_authorized": False,
        }
        for tool_name, operation in zip(MCP_TOOL_NAMES, OPERATIONS, strict=True)
    )


def invoke_mcp_tool(
    tool_name: str,
    arguments: dict[str, Any],
    context: Any = None,
) -> dict[str, Any]:
    """Map one offline MCP invocation 1:1 into canonical UAII evaluation."""
    if not isinstance(tool_name, str) or tool_name not in _OPERATION_BY_TOOL:
        raise McpAdapterError("mcp_tool_unsupported")

    if not isinstance(arguments, dict):
        raise McpAdapterError("mcp_arguments_invalid")

    if tuple(arguments.keys()) != ENVELOPE_FIELDS:
        raise McpAdapterError("mcp_arguments_not_canonical")

    if arguments["operation"] != _OPERATION_BY_TOOL[tool_name]:
        raise McpAdapterError("mcp_operation_mismatch")

    try:
        request_bytes = canon_uaii(arguments)
    except UaiiJsonError as exc:
        raise McpAdapterError("mcp_arguments_not_canonical") from exc

    return process_uaii_request(request_bytes, context)
