from __future__ import annotations

import ast
import http.client
import json
import threading
from pathlib import Path

import pytest

from coin import two_agent_service_external_access_demo as ext


def _fake_purchase(text: str):
    return {
        "service_id": ext.SERVICE_ID,
        "asset_id": "L28",
        "quoted_amount": 28,
        "canonical_validation": "PASS",
        "payment_applied": True,
        "payment_verified": True,
        "agent_a_balance_before": 100,
        "agent_b_balance_before": 0,
        "agent_a_balance_after": 72,
        "agent_b_balance_after": 28,
        "service_executed": True,
        "service_result_verified": True,
        "receipt_created": True,
        "receipt_verified": True,
        "payment_tx_id": "a" * 64,
        "service_result_id": "b" * 64,
        "receipt_id": "c" * 64,
        "canonical_history_touched": False,
        "public_network_used": False,
        "production_keys_used": False,
        "service_output": {
            "character_count": len(text),
            "word_count": len(text.split()),
            "unique_word_count": len(set(text.lower().split())),
            "sentence_count": 1,
            "top_terms": [],
            "input_digest": "d" * 64,
        },
    }


def _http_request(server, method, path, body=None, content_type="application/json"):
    host, port = server.server_address[:2]
    conn = http.client.HTTPConnection(host, port, timeout=3)
    raw = body
    headers = {}
    if body is not None:
        if isinstance(body, dict):
            raw = json.dumps(body).encode()
        elif isinstance(body, str):
            raw = body.encode()
        headers["Content-Type"] = content_type
        headers["Content-Length"] = str(len(raw))
    try:
        conn.request(method, path, body=raw, headers=headers)
        response = conn.getresponse()
        payload = json.loads(response.read().decode())
        return response.status, payload
    finally:
        conn.close()


@pytest.fixture
def http_server():
    server = ext.make_http_server(0)
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01})
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def test_purchase_boundary_delegates_to_existing_core_once(monkeypatch):
    calls = []

    def fake(text):
        calls.append(text)
        return _fake_purchase(text)

    monkeypatch.setattr(ext, "execute_two_agent_service_transaction", fake)
    result = ext.purchase_service(
        {"service_id": ext.SERVICE_ID, "input": "hello machine"}
    )
    assert calls == ["hello machine"]
    assert result["ok"] is True
    assert result["service_id"] == ext.SERVICE_ID
    assert result["purchase"]["quoted_amount"] == 28


def test_invalid_transport_payload_never_calls_core(monkeypatch):
    called = {"count": 0}

    def fake(_text):
        called["count"] += 1
        return _fake_purchase("x")

    monkeypatch.setattr(ext, "execute_two_agent_service_transaction", fake)

    bad = [
        None,
        {},
        {"service_id": "wrong", "input": "x"},
        {"service_id": ext.SERVICE_ID, "input": ""},
        {"service_id": ext.SERVICE_ID, "input": "x", "extra": True},
        {"service_id": ext.SERVICE_ID, "input": "x" * (ext.MAX_INPUT_CHARS + 1)},
    ]
    for payload in bad:
        with pytest.raises(ext.ExternalAccessError):
            ext.purchase_service(payload)
    assert called["count"] == 0


def test_http_purchase_crosses_loopback_server_boundary(http_server, monkeypatch):
    monkeypatch.setattr(
        ext,
        "execute_two_agent_service_transaction",
        lambda text: _fake_purchase(text),
    )
    assert http_server.server_address[0] == ext.LOOPBACK_HOST == "127.0.0.1"
    status, payload = _http_request(
        http_server,
        "POST",
        ext.PURCHASE_PATH,
        {"service_id": ext.SERVICE_ID, "input": "alpha beta"},
    )
    assert status == 200
    assert payload["ok"] is True
    assert payload["purchase"]["payment_verified"] is True
    assert payload["purchase"]["receipt_verified"] is True


def test_http_boundary_failures_fail_closed(http_server, monkeypatch):
    calls = {"count": 0}

    def fake(text):
        calls["count"] += 1
        return _fake_purchase(text)

    monkeypatch.setattr(ext, "execute_two_agent_service_transaction", fake)

    status, payload = _http_request(http_server, "GET", ext.PURCHASE_PATH)
    assert status == 405 and payload["ok"] is False

    status, payload = _http_request(
        http_server,
        "POST",
        "/not-real",
        {"service_id": ext.SERVICE_ID, "input": "x"},
    )
    assert status == 404 and payload["ok"] is False

    status, payload = _http_request(
        http_server,
        "POST",
        ext.PURCHASE_PATH,
        "{not-json",
    )
    assert status == 400 and payload["error"] == "malformed_json"

    status, payload = _http_request(
        http_server,
        "POST",
        ext.PURCHASE_PATH,
        {"service_id": "wrong", "input": "x"},
    )
    assert status == 400 and payload["error"] == "service_id_invalid"

    status, payload = _http_request(
        http_server,
        "POST",
        ext.PURCHASE_PATH,
        {"service_id": ext.SERVICE_ID, "input": ""},
    )
    assert status == 400 and payload["error"] == "input_invalid"

    assert calls["count"] == 0


def test_http_rejects_non_json_and_oversized_body(http_server):
    status, payload = _http_request(
        http_server,
        "POST",
        ext.PURCHASE_PATH,
        "hello",
        content_type="text/plain",
    )
    assert status == 415
    assert payload["error"] == "content_type_invalid"

    host, port = http_server.server_address[:2]
    conn = http.client.HTTPConnection(host, port, timeout=3)
    try:
        conn.request(
            "POST",
            ext.PURCHASE_PATH,
            body=b"x",
            headers={
                "Content-Type": "application/json",
                "Content-Length": str(ext.MAX_HTTP_BODY_BYTES + 1),
            },
        )
        response = conn.getresponse()
        payload = json.loads(response.read().decode())
        assert response.status == 413
        assert payload["error"] == "request_too_large"
    finally:
        conn.close()


def test_mcp_initialize_and_tool_registry_are_bounded():
    init = ext.handle_mcp_message(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {},
        }
    )
    assert init["result"]["protocolVersion"] == ext.MCP_PROTOCOL_VERSION

    listed = ext.handle_mcp_message(
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
    )
    tools = listed["result"]["tools"]
    assert [tool["name"] for tool in tools] == [ext.MCP_TOOL_NAME]
    assert tools[0]["inputSchema"]["properties"]["service_id"]["const"] == ext.SERVICE_ID


def test_mcp_purchase_delegates_to_same_core(monkeypatch):
    calls = []

    def fake(text):
        calls.append(text)
        return _fake_purchase(text)

    monkeypatch.setattr(ext, "execute_two_agent_service_transaction", fake)
    response = ext.handle_mcp_message(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": ext.MCP_TOOL_NAME,
                "arguments": {
                    "service_id": ext.SERVICE_ID,
                    "input": "alpha beta",
                },
            },
        }
    )
    assert calls == ["alpha beta"]
    assert response["result"]["isError"] is False
    payload = response["result"]["structuredContent"]
    assert payload["purchase"]["payment_verified"] is True
    assert payload["purchase"]["receipt_verified"] is True


def test_mcp_boundary_failures_fail_closed(monkeypatch):
    calls = {"count": 0}

    def fake(text):
        calls["count"] += 1
        return _fake_purchase(text)

    monkeypatch.setattr(ext, "execute_two_agent_service_transaction", fake)

    bad_request = ext.handle_mcp_message([])
    assert bad_request["error"]["code"] == -32600

    unknown_method = ext.handle_mcp_message(
        {"jsonrpc": "2.0", "id": 1, "method": "not-real", "params": {}}
    )
    assert unknown_method["error"]["code"] == -32601

    unknown_tool = ext.handle_mcp_message(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "not-real", "arguments": {}},
        }
    )
    assert unknown_tool["error"]["code"] == -32602

    wrong_service = ext.handle_mcp_message(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": ext.MCP_TOOL_NAME,
                "arguments": {"service_id": "wrong", "input": "x"},
            },
        }
    )
    assert wrong_service["result"]["isError"] is True
    assert wrong_service["result"]["structuredContent"]["error"] == "service_id_invalid"

    empty_input = ext.handle_mcp_message(
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": ext.MCP_TOOL_NAME,
                "arguments": {"service_id": ext.SERVICE_ID, "input": ""},
            },
        }
    )
    assert empty_input["result"]["isError"] is True
    assert empty_input["result"]["structuredContent"]["error"] == "input_invalid"
    assert calls["count"] == 0


def test_stable_semantics_ignore_ephemeral_ids():
    a = _fake_purchase("same input")
    b = _fake_purchase("same input")
    b["payment_tx_id"] = "1" * 64
    b["service_result_id"] = "2" * 64
    b["receipt_id"] = "3" * 64
    assert ext._stable_semantics(a, b) is True

    b["quoted_amount"] = 27
    assert ext._stable_semantics(a, b) is False


def test_runtime_source_has_bounded_authority_and_no_duplicate_validator():
    path = Path(ext.__file__)
    src = path.read_text(encoding="utf-8")
    tree = ast.parse(src)

    imports = set()
    function_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            function_names.add(node.name)

    assert ext.LOOPBACK_HOST == "127.0.0.1"
    assert "--host" not in src
    assert "validate_transaction" not in function_names
    assert "private_bytes" not in src
    assert "from_private_bytes" not in src
    assert "os.environ" not in src
    assert "getenv(" not in src
    assert "keyring" not in imports
    assert "requests" not in imports
    assert "urllib" not in imports
    assert "execute_two_agent_service_transaction" in src


def test_verified_purchase_requires_core_success_semantics():
    payload = {
        "ok": True,
        "service_id": ext.SERVICE_ID,
        "purchase": _fake_purchase("x"),
    }
    verified = ext._verified_purchase(payload)
    assert verified["quoted_amount"] == 28

    bad = json.loads(json.dumps(payload))
    bad["purchase"]["payment_verified"] = False
    with pytest.raises(ext.ExternalAccessError):
        ext._verified_purchase(bad)
