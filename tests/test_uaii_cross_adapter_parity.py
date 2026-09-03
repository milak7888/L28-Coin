# SPDX-License-Identifier: Apache-2.0

import json
import shutil
import subprocess
from pathlib import Path

from coin import uaii_mcp_adapter as mcp
from coin import uaii_python_sdk as python_sdk
from coin import uaii_rest_adapter as rest
from coin.uaii_json import canon_uaii
from coin.uaii_reference_core import (
    INTERFACE_PROFILE,
    OPERATIONS,
    process_uaii_request,
)


ROOT = Path(__file__).resolve().parents[1]
TS_RUNNER = ROOT / "tests" / "typescript" / "uaii_cross_adapter_parity.mts"


class _Replay:
    def lookup(self, _key: str) -> str:
        return "absent"


def _context():
    return {
        "t_eval": 1_700_000_000,
        "replay_state": _Replay(),
    }


def _envelope():
    return {
        "interface_profile": INTERFACE_PROFILE,
        "operation": "discover_capabilities",
        "request_id": "b" * 64,
        "created_at": 1_699_999_000,
        "expires_at": 1_700_000_100,
        "nonce": "foundation132",
        "execution_authorized": False,
        "params": {
            "include_adapter_declarations": False,
        },
    }


def _typescript_snapshot():
    node = shutil.which("node")
    assert node is not None, "node required for TypeScript parity test"

    completed = subprocess.run(
        [node, str(TS_RUNNER)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    return json.loads(completed.stdout.strip())


def test_operation_inventory_parity():
    assert tuple(item["operation"] for item in mcp.list_mcp_tools()) == OPERATIONS
    assert tuple(rest.REST_PATHS.values()) == OPERATIONS

    client = python_sdk.UaiiPythonClient(_context())
    assert client.interface_profile == INTERFACE_PROFILE
    assert client.operations == OPERATIONS

    snapshot = _typescript_snapshot()
    assert snapshot["interface_profile"] == INTERFACE_PROFILE
    assert tuple(snapshot["operations"]) == OPERATIONS


def test_python_adapter_response_parity_with_canonical_core():
    request = _envelope()

    canonical = process_uaii_request(
        canon_uaii(request),
        _context(),
    )

    via_mcp = mcp.invoke_mcp_tool(
        mcp.MCP_TOOL_NAMES[0],
        request,
        _context(),
    )

    via_rest = rest.invoke_rest_request(
        "POST",
        "/v1/uaii/discover_capabilities",
        request,
        _context(),
    )

    via_python = python_sdk.UaiiPythonClient(
        _context()
    ).discover_capabilities(request)

    assert via_mcp == canonical
    assert via_rest == canonical
    assert via_python == canonical

    assert canon_uaii(via_mcp) == canon_uaii(canonical)
    assert canon_uaii(via_rest) == canon_uaii(canonical)
    assert canon_uaii(via_python) == canon_uaii(canonical)


def test_typescript_request_serialization_parity():
    request = _envelope()
    canonical = canon_uaii(request)

    if isinstance(canonical, bytes):
        canonical_text = canonical.decode("utf-8")
    else:
        canonical_text = canonical

    snapshot = _typescript_snapshot()

    assert snapshot["encoded"] == canonical_text


def test_all_adapter_authority_boundaries_remain_closed():
    assert mcp.runtime_activated is False
    assert mcp.network_activated is False
    assert mcp.signing_authorized is False
    assert mcp.spend_authorized is False
    assert mcp.settlement_authorized is False
    assert mcp.transaction_submission_authorized is False

    assert rest.runtime_activated is False
    assert rest.network_activated is False
    assert rest.signing_authorized is False
    assert rest.spend_authorized is False
    assert rest.settlement_authorized is False
    assert rest.transaction_submission_authorized is False

    assert python_sdk.package_published is False
    assert python_sdk.runtime_activated is False
    assert python_sdk.network_activated is False
    assert python_sdk.signing_authorized is False
    assert python_sdk.spend_authorized is False
    assert python_sdk.settlement_authorized is False
    assert python_sdk.transaction_submission_authorized is False

    authority = _typescript_snapshot()["authority"]

    assert authority == {
        "package_published": False,
        "runtime_activated": False,
        "network_activated": False,
        "signing_authorized": False,
        "spend_authorized": False,
        "settlement_authorized": False,
        "transaction_submission_authorized": False,
    }
