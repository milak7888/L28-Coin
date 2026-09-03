# SPDX-License-Identifier: Apache-2.0

import ast
import hashlib
from pathlib import Path

import pytest

from coin.uaii_json import canon_uaii
from coin.uaii_python_sdk import (
    PythonSdkError,
    UaiiPythonClient,
    network_activated,
    package_published,
    runtime_activated,
    sdk_implemented,
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
    params = (
        {"include_adapter_declarations": False}
        if operation == "discover_capabilities"
        else {}
    )
    return {
        "interface_profile": INTERFACE_PROFILE,
        "operation": operation,
        "request_id": _hex64("python-sdk-" + operation),
        "created_at": 1_699_999_000,
        "expires_at": 1_700_000_100,
        "nonce": "foundation130",
        "execution_authorized": False,
        "params": params,
    }


def test_sdk_declares_exact_canonical_profile_and_operations():
    client = UaiiPythonClient(_context())
    assert client.interface_profile == INTERFACE_PROFILE
    assert client.operations == OPERATIONS
    assert len(client.operations) == 8


def test_generic_invoke_is_direct_uaii_equivalent():
    env = _envelope()
    direct = process_uaii_request(canon_uaii(env), _context())
    client = UaiiPythonClient(_context())
    via_sdk = client.invoke(env)

    assert via_sdk == direct
    assert canon_uaii(via_sdk) == canon_uaii(direct)


def test_named_method_is_direct_uaii_equivalent():
    env = _envelope()
    client = UaiiPythonClient(_context())

    generic = client.invoke(env)
    named = client.discover_capabilities(env)

    assert named == generic


def test_all_canonical_operations_have_named_methods():
    client = UaiiPythonClient(_context())

    for operation in OPERATIONS:
        method = getattr(client, operation, None)
        assert callable(method), operation


def test_operation_mismatch_fails_closed():
    env = _envelope("discover_capabilities")
    client = UaiiPythonClient(_context())

    with pytest.raises(PythonSdkError) as exc:
        client.invoke_operation("get_protocol_status", env)

    assert exc.value.code == "python_sdk_operation_mismatch"


def test_unknown_sdk_operation_fails_closed():
    env = _envelope()
    client = UaiiPythonClient(_context())

    with pytest.raises(PythonSdkError) as exc:
        client.invoke_operation("not_real", env)

    assert exc.value.code == "python_sdk_operation_unsupported"


def test_noncanonical_field_order_fails_closed():
    env = _envelope()
    reordered = {"operation": env["operation"]}
    reordered.update({k: v for k, v in env.items() if k != "operation"})

    client = UaiiPythonClient(_context())

    with pytest.raises(PythonSdkError) as exc:
        client.invoke(reordered)

    assert exc.value.code == "python_sdk_request_not_canonical"


def test_canonical_uaii_error_is_preserved():
    env = _envelope()
    env["params"] = {"password": "forbidden"}

    result = UaiiPythonClient(_context()).invoke(env)

    assert result["ok"] is False
    assert result["code"] == "secret_material_forbidden"


def test_sdk_has_zero_runtime_or_economic_authority():
    assert sdk_implemented is True
    assert package_published is False
    assert runtime_activated is False
    assert network_activated is False
    assert signing_authorized is False
    assert spend_authorized is False
    assert settlement_authorized is False
    assert transaction_submission_authorized is False


def test_sdk_import_boundary_is_offline_only():
    path = Path(__file__).resolve().parents[1] / "coin/uaii_python_sdk.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))

    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])

    forbidden = {
        "socket",
        "ssl",
        "http",
        "urllib",
        "requests",
        "subprocess",
        "asyncio",
        "websockets",
        "fastapi",
        "flask",
        "uvicorn",
    }

    assert not (imported & forbidden)
