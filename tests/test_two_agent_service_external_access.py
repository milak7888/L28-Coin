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


def test_developer_mcp_lists_and_dispatches_summary_tool():
    def purchase(text):
        assert text == "One useful summary."
        return {"receipt_verified": True}

    message = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
    tool, = ext.handle_mcp_message(message, developer_purchase=purchase)["result"]["tools"]
    assert tool["name"] == "l28_purchase_developer_summary"
    assert tool["inputSchema"]["properties"]["service_id"]["const"] == ext.SUMMARY_SERVICE_ID
    message.update(method="tools/call", params={"name": tool["name"], "arguments": {
        "service_id": ext.SUMMARY_SERVICE_ID, "input": "One useful summary."}})
    result = ext.handle_mcp_message(message, developer_purchase=purchase)["result"]
    assert not result["isError"] and result["structuredContent"]["receipt_verified"]


def test_developer_real_mtls_mcp_purchase(tmp_path):
    import datetime
    import hashlib
    import ipaddress
    import socket
    import sqlite3
    import ssl
    import subprocess
    import sys
    from http.server import BaseHTTPRequestHandler, HTTPServer

    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import NameOID
    from coin import public_testnet_service_demo as demo
    from coin.durable_restart_safe_service_demo import DB_NAME

    now = datetime.datetime.now(datetime.timezone.utc)

    def cert(name, issuer=None):
        key = ec.generate_private_key(ec.SECP256R1())
        subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, name)])
        builder = (x509.CertificateBuilder().subject_name(subject)
                   .issuer_name(subject if issuer is None else issuer[1].subject)
                   .public_key(key.public_key()).serial_number(x509.random_serial_number())
                   .not_valid_before(now - datetime.timedelta(minutes=1))
                   .not_valid_after(now + datetime.timedelta(minutes=5))
                   .add_extension(x509.BasicConstraints(ca=issuer is None, path_length=None), critical=True))
        if name == "edge":
            builder = builder.add_extension(x509.SubjectAlternativeName([
                x509.IPAddress(ipaddress.IPv4Address("127.0.0.1"))]), critical=False)
        certificate = builder.sign(key if issuer is None else issuer[0], hashes.SHA256())
        cert_path, key_path = tmp_path / (name + ".pem"), tmp_path / (name + ".key")
        cert_path.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
        key_path.write_bytes(key.private_bytes(serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
        return key, certificate, cert_path, key_path

    ca = cert("ca")
    edge, client, wrong = [cert(name, ca) for name in ("edge", "client", "wrong")]
    approved = client[1].public_bytes(serialization.Encoding.DER)
    state = tmp_path / "store"
    provider_capture = tmp_path / "provider-signed.json"
    mcp_capture = tmp_path / "mcp-response.json"
    for path in (provider_capture, mcp_capture):
        path.touch(mode=0o600, exist_ok=False)
    provider = subprocess.Popen([sys.executable, "-B", "-m", "coin.public_testnet_service_demo",
                                 "--role", "developer-provider", "--state-dir", str(state)],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    edge_server = thread = None
    forwarded = []
    try:
        ready = ext._read_json_line(provider.stdout, timeout=5)

        class Edge(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def forward(self):
                if self.connection.getpeercert(binary_form=True) != approved:
                    self.send_error(403)
                    return
                if (self.command, self.path) not in {("GET", demo.DISCOVERY_PATH),
                        ("GET", demo.HELLO_PATH), ("POST", demo.SESSION_PATH)}:
                    self.send_error(404)
                    return
                body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
                assert len(body) <= demo.MAX_BODY_BYTES
                origin = http.client.HTTPConnection("127.0.0.1", ready["port"], timeout=2)
                try:
                    forwarded.append((self.command, self.path, body))
                    origin.request(self.command, self.path, body=body)
                    response = origin.getresponse()
                    data = response.read()
                    if self.command == "POST" and json.loads(body).get("message_type") == "payment_package":
                        provider_capture.write_bytes(data)
                    self.send_response(response.status)
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                finally:
                    origin.close()

            do_GET = do_POST = forward

        edge_server = HTTPServer(("127.0.0.1", 0), Edge)
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(edge[2], edge[3])
        ctx.load_verify_locations(cafile=ca[2])
        ctx.verify_mode = ssl.CERT_REQUIRED
        edge_server.socket = ctx.wrap_socket(edge_server.socket, server_side=True)
        thread = threading.Thread(target=edge_server.serve_forever, daemon=True)
        thread.start()
        url = f"https://127.0.0.1:{edge_server.server_port}"

        for presented in (None, wrong):
            tls = ssl.create_default_context(cafile=ca[2])
            if presented:
                tls.load_cert_chain(presented[2], presented[3])
            with pytest.raises(demo.PublicTestnetError):
                demo.purchase_developer_summary(url, "A useful summary.", expected_provider_key=ready["provider_public_key"],
                                                tls_context=tls, loopback_test=True)
        assert not forwarded

        # A wrong pin is covered by the focused test. Run the real one-shot
        # MCP client only with the approved pin so the hello slot stays unused.
        text = "L28 supports machine payments. This test buys a useful text summary."
        call = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {
            "name": "l28_purchase_developer_summary", "arguments": {
                "service_id": ext.SUMMARY_SERVICE_ID, "input": text}}}
        proc = subprocess.run([sys.executable, "-B", "-m", "coin.two_agent_service_external_access_demo",
            "--runtime", "mcp", "--developer-endpoint", url, "--developer-loopback-test",
            "--developer-ca", str(ca[2]), "--developer-client-cert", str(client[2]),
            "--developer-client-key", str(client[3]), "--expected-provider-key", ready["provider_public_key"]],
            input=json.dumps(call) + "\n", capture_output=True, text=True, timeout=10, check=True)
        mcp_capture.write_text(proc.stdout)
        result = json.loads(proc.stdout)["result"]
        assert not result["isError"], result
        text_carrier = json.loads(result["content"][0]["text"])
        result = result["structuredContent"]
        artifacts = result["public_artifacts"]
        original = json.loads(provider_capture.read_bytes())["payload"]
        for carrier in (result, text_carrier):
            delivered = carrier["public_artifacts"]
            for key in ("service_result", "receipt"):
                assert demo._pilot_bytes(original[key]) == demo._pilot_bytes(delivered[key])
            demo.verify_purchase_artifacts(delivered, input_text=text, service_id=ext.SUMMARY_SERVICE_ID)
        out, err = provider.communicate(timeout=5)
        assert provider.returncode == 0, err
        evidence = json.loads(out)
        assert evidence["listener_closed"]
        tx_id = result["payment_tx_id"]
        assert evidence["evidence"]["payment_tx_id"] == tx_id
        assert [evidence["evidence"][key] for key in (
            "requester_balance_before", "provider_balance_before",
            "requester_balance_after", "provider_balance_after")] == [100, 0, 72, 28]
        assert sum(json.loads(body).get("message_type") == "payment_package"
                   for method, _, body in forwarded if method == "POST") == 1
        db_path = state / DB_NAME
        digest = hashlib.sha256(db_path.read_bytes()).hexdigest()
        with socket.socket() as probe:
            probe.settimeout(1)
            assert probe.connect_ex(("127.0.0.1", ready["port"])) != 0
        assert digest == hashlib.sha256(db_path.read_bytes()).hexdigest()
        with sqlite3.connect((state / DB_NAME).as_uri() + "?mode=ro", uri=True) as db:
            assert db.execute("SELECT event,payment_tx_id FROM audit ORDER BY id").fetchall() == [
                ("payment_committed", tx_id), ("receipt_linked", tx_id)]
            receipt_id = artifacts["receipt"]["receipt_id"]
            assert db.execute("SELECT receipt_id,amount FROM accepted_payments").fetchall() == [(receipt_id, 28)]
        record = {"provider": evidence, "requester": result, "receipt_id": receipt_id,
                  "database_sha256": hashlib.sha256((state / DB_NAME).read_bytes()).hexdigest()}
        (tmp_path / "acceptance.json").write_text(json.dumps(record))
    finally:
        if edge_server is not None:
            if thread is not None:
                edge_server.shutdown()
                thread.join(timeout=2)
            edge_server.server_close()
        if provider.poll() is None:
            provider.kill()
            provider.communicate(timeout=5)
    assert not thread.is_alive()
    with socket.socket() as probe:
        probe.settimeout(1)
        assert probe.connect_ex(("127.0.0.1", edge_server.server_port)) != 0
    record["cleanup_verified"] = True
    record["provider_pid"] = provider.pid
    (tmp_path / "acceptance.json").write_text(json.dumps(record))
