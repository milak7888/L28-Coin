# SPDX-License-Identifier: Apache-2.0

import ast
import hashlib
from pathlib import Path

import pytest

from coin.uaii_json import canon_uaii
from coin.uaii_reference_core import (
    ENVELOPE_FIELDS,
    INTERFACE_PROFILE,
    OPERATIONS,
    process_uaii_request,
)
from coin.uaii_rest_adapter import (
    REST_PATHS,
    RestAdapterError,
    adapter_implemented,
    build_openapi_document,
    invoke_rest_request,
    listener_started,
    network_activated,
    openapi_document_available,
    runtime_activated,
    server_started,
    settlement_authorized,
    signing_authorized,
    spend_authorized,
    transaction_submission_authorized,
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
        "request_id": _hex64("rest-" + operation),
        "created_at": 1_699_999_000,
        "expires_at": 1_700_000_100,
        "nonce": "foundation129",
        "execution_authorized": False,
        "params": {"include_adapter_declarations": False},
    }


def test_paths_map_exactly_to_supported_operations():
    assert list(REST_PATHS.values()) == list(OPERATIONS)
    assert len(REST_PATHS) == len(OPERATIONS) == 8


def test_rest_mapping_is_direct_uaii_equivalent():
    env = _envelope()
    direct = process_uaii_request(canon_uaii(env), _context())
    mapped = invoke_rest_request(
        "POST",
        "/v1/uaii/discover_capabilities",
        env,
        _context(),
    )
    assert mapped == direct
    assert canon_uaii(mapped) == canon_uaii(direct)


def test_method_and_path_fail_at_transport_boundary():
    env = _envelope()

    with pytest.raises(RestAdapterError) as exc:
        invoke_rest_request(
            "GET",
            "/v1/uaii/discover_capabilities",
            env,
            _context(),
        )
    assert exc.value.code == "rest_method_unsupported"

    with pytest.raises(RestAdapterError) as exc:
        invoke_rest_request("POST", "/v1/uaii/not-real", env, _context())
    assert exc.value.code == "rest_path_unsupported"


def test_path_operation_mismatch_fails_closed():
    env = _envelope()
    with pytest.raises(RestAdapterError) as exc:
        invoke_rest_request(
            "POST",
            "/v1/uaii/get_protocol_status",
            env,
            _context(),
        )
    assert exc.value.code == "rest_operation_mismatch"


def test_noncanonical_field_order_fails_closed():
    env = _envelope()
    reordered = {"operation": env["operation"]}
    reordered.update({k: v for k, v in env.items() if k != "operation"})

    with pytest.raises(RestAdapterError) as exc:
        invoke_rest_request(
            "POST",
            "/v1/uaii/discover_capabilities",
            reordered,
            _context(),
        )
    assert exc.value.code == "rest_body_not_canonical"


def test_uaii_security_error_is_preserved():
    env = _envelope()
    env["params"] = {"password": "forbidden"}

    result = invoke_rest_request(
        "POST",
        "/v1/uaii/discover_capabilities",
        env,
        _context(),
    )
    assert result["ok"] is False
    assert result["code"] == "secret_material_forbidden"


def test_openapi_document_is_offline_and_canonical():
    doc = build_openapi_document()

    assert doc["openapi"] == "3.1.0"
    assert doc["servers"] == []
    assert doc["x-l28-interface-profile"] == INTERFACE_PROFILE
    assert doc["x-l28-runtime-activated"] is False
    assert doc["x-l28-network-activated"] is False
    assert doc["x-l28-settlement-authorized"] is False
    assert list(doc["paths"]) == list(REST_PATHS)

    for operation, path in zip(OPERATIONS, REST_PATHS, strict=True):
        post = doc["paths"][path]["post"]
        assert post["operationId"] == operation
        schema = post["requestBody"]["content"]["application/json"]["schema"]
        assert schema["required"] == list(ENVELOPE_FIELDS)
        assert schema["additionalProperties"] is False


def test_adapter_has_zero_runtime_or_economic_authority():
    assert adapter_implemented is True
    assert openapi_document_available is True
    assert runtime_activated is False
    assert network_activated is False
    assert server_started is False
    assert listener_started is False
    assert signing_authorized is False
    assert spend_authorized is False
    assert settlement_authorized is False
    assert transaction_submission_authorized is False


def test_adapter_import_boundary_has_no_network_stack():
    path = Path(__file__).resolve().parents[1] / "coin/uaii_rest_adapter.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))

    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])

    forbidden = {
        "socket", "ssl", "http", "urllib", "requests", "subprocess",
        "asyncio", "websockets", "fastapi", "flask", "uvicorn",
    }
    assert not (imported & forbidden)
