# SPDX-License-Identifier: Apache-2.0

import ast
import hashlib
from pathlib import Path

import pytest

from coin.uaii_json import canon_uaii
from coin.uaii_mcp_adapter import (
    MCP_TOOL_NAMES,
    McpAdapterError,
    adapter_implemented,
    invoke_mcp_tool,
    list_mcp_tools,
    network_activated,
    runtime_activated,
    server_started,
    settlement_authorized,
    signing_authorized,
    spend_authorized,
    transaction_submission_authorized,
)
from coin.uaii_reference_core import (
    ENVELOPE_FIELDS,
    INTERFACE_PROFILE,
    OPERATIONS,
    process_uaii_request,
)


class _Replay:
    def lookup(self, _key: str) -> str:
        return "absent"


def _context():
    return {
        "t_eval": 1_700_000_000,
        "replay_state": _Replay(),
    }


def _hex64(seed: str) -> str:
    return hashlib.sha256(seed.encode()).hexdigest()


def _envelope(operation="discover_capabilities"):
    return {
        "interface_profile": INTERFACE_PROFILE,
        "operation": operation,
        "request_id": _hex64(operation),
        "created_at": 1_699_999_000,
        "expires_at": 1_700_000_100,
        "nonce": "foundation128",
        "execution_authorized": False,
        "params": {"include_adapter_declarations": False},
    }


def test_registry_maps_exactly_to_canonical_operations():
    tools = list_mcp_tools()
    assert len(tools) == len(OPERATIONS) == 8
    assert [t["operation"] for t in tools] == list(OPERATIONS)
    assert [t["name"] for t in tools] == list(MCP_TOOL_NAMES)
    assert all(t["interface_profile"] == INTERFACE_PROFILE for t in tools)
    assert all(t["input_fields"] == list(ENVELOPE_FIELDS) for t in tools)


def test_offline_adapter_is_direct_uaii_equivalent():
    env = _envelope()
    direct = process_uaii_request(canon_uaii(env), _context())
    mapped = invoke_mcp_tool(MCP_TOOL_NAMES[0], env, _context())
    assert mapped == direct
    assert canon_uaii(mapped) == canon_uaii(direct)


def test_unknown_tool_fails_at_transport_boundary():
    with pytest.raises(McpAdapterError) as exc:
        invoke_mcp_tool("l28_uaii_not_real", _envelope(), _context())
    assert exc.value.code == "mcp_tool_unsupported"


def test_tool_operation_mismatch_fails_closed():
    env = _envelope()
    with pytest.raises(McpAdapterError) as exc:
        invoke_mcp_tool(MCP_TOOL_NAMES[1], env, _context())
    assert exc.value.code == "mcp_operation_mismatch"


def test_noncanonical_envelope_order_fails_closed():
    env = _envelope()
    reordered = {"operation": env["operation"]}
    reordered.update({k: v for k, v in env.items() if k != "operation"})
    with pytest.raises(McpAdapterError) as exc:
        invoke_mcp_tool(MCP_TOOL_NAMES[0], reordered, _context())
    assert exc.value.code == "mcp_arguments_not_canonical"


def test_core_security_failure_is_preserved_not_rewritten():
    env = _envelope()
    env["params"] = {"password": "forbidden"}
    result = invoke_mcp_tool(MCP_TOOL_NAMES[0], env, _context())
    assert result["ok"] is False
    assert result["code"] == "secret_material_forbidden"


def test_adapter_has_zero_runtime_or_economic_authority():
    assert adapter_implemented is True
    assert runtime_activated is False
    assert network_activated is False
    assert server_started is False
    assert signing_authorized is False
    assert spend_authorized is False
    assert settlement_authorized is False
    assert transaction_submission_authorized is False


def test_adapter_import_boundary_is_offline_only():
    path = Path(__file__).resolve().parents[1] / "coin/uaii_mcp_adapter.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))

    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)

    assert imported <= {
        "__future__",
        "typing",
        "uaii_json",
        "uaii_reference_core",
    }
