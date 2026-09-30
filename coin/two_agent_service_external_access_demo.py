# SPDX-License-Identifier: Apache-2.0
"""Bounded local HTTP/JSON + MCP stdio exposure for the L28 two-agent purchase.

This module exposes exactly one already-working disposable purchase service:
`l28.service.structured_text_analysis/v0.1`.

HTTP is hard-bound to 127.0.0.1 only. MCP uses stdio only. Both delegate to
`execute_two_agent_service_transaction` and create no alternate validator,
payment engine, production signer, broadcast path, or production settlement.
"""

from __future__ import annotations

import argparse
import http.client
import json
import selectors
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, TextIO

from coin.two_agent_service_transaction_demo import (
    MAX_INPUT_CHARS,
    PRICE_L28,
    SERVICE_ID,
    DemoError,
    execute_two_agent_service_transaction,
)

LOOPBACK_HOST = "127.0.0.1"
PURCHASE_PATH = "/v1/l28/services/structured_text_analysis/purchase"
MCP_TOOL_NAME = "l28_purchase_structured_text_analysis"
MCP_PROTOCOL_VERSION = "2025-06-18"
MAX_HTTP_BODY_BYTES = 8192
RUNTIME_PROFILE = "l28-two-agent-external-access/v0.1"


class ExternalAccessError(Exception):
    """Fail-closed transport/runtime error."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _validate_purchase_payload(payload: Any) -> str:
    if not isinstance(payload, dict):
        raise ExternalAccessError("request_body_invalid")
    if set(payload) != {"service_id", "input"}:
        raise ExternalAccessError("request_fields_invalid")
    if payload.get("service_id") != SERVICE_ID:
        raise ExternalAccessError("service_id_invalid")
    input_text = payload.get("input")
    if not isinstance(input_text, str) or not input_text or len(input_text) > MAX_INPUT_CHARS:
        raise ExternalAccessError("input_invalid")
    return input_text


def purchase_service(payload: Any) -> dict[str, Any]:
    """Validate the transport request and delegate to the existing core purchase."""
    input_text = _validate_purchase_payload(payload)
    try:
        purchase = execute_two_agent_service_transaction(input_text)
    except DemoError as exc:
        raise ExternalAccessError(exc.code) from exc
    return {
        "ok": True,
        "runtime_profile": RUNTIME_PROFILE,
        "service_id": SERVICE_ID,
        "purchase": purchase,
    }


class _PurchaseHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, _format: str, *_args: Any) -> None:
        return

    def _write(self, status: int, payload: dict[str, Any]) -> None:
        body = _json_bytes(payload)
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == PURCHASE_PATH:
            self._write(405, {"ok": False, "error": "method_not_allowed"})
        else:
            self._write(404, {"ok": False, "error": "path_not_found"})

    def do_POST(self) -> None:
        if self.path != PURCHASE_PATH:
            self._write(404, {"ok": False, "error": "path_not_found"})
            return

        content_type = self.headers.get("Content-Type", "")
        if content_type.split(";", 1)[0].strip().lower() != "application/json":
            self._write(415, {"ok": False, "error": "content_type_invalid"})
            return

        raw_length = self.headers.get("Content-Length")
        try:
            length = int(raw_length) if raw_length is not None else -1
        except ValueError:
            length = -1

        if length < 0:
            self._write(411, {"ok": False, "error": "content_length_required"})
            return
        if length > MAX_HTTP_BODY_BYTES:
            self._write(413, {"ok": False, "error": "request_too_large"})
            return

        raw = self.rfile.read(length)
        if len(raw) != length:
            self._write(400, {"ok": False, "error": "request_body_incomplete"})
            return

        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._write(400, {"ok": False, "error": "malformed_json"})
            return

        try:
            result = purchase_service(payload)
        except ExternalAccessError as exc:
            self._write(400, {"ok": False, "error": exc.code})
            return

        self._write(200, result)


def make_http_server(port: int = 0) -> HTTPServer:
    """Create a server hard-bound to the IPv4 loopback interface."""
    if not isinstance(port, int) or not (0 <= port <= 65535):
        raise ExternalAccessError("port_invalid")
    return HTTPServer((LOOPBACK_HOST, port), _PurchaseHandler)


def run_http_runtime(port: int = 0) -> int:
    server = make_http_server(port)
    actual_host, actual_port = server.server_address[:2]
    startup = {
        "event": "http_runtime_started",
        "host": actual_host,
        "port": actual_port,
        "path": PURCHASE_PATH,
        "service_id": SERVICE_ID,
    }
    sys.stdout.write(_json_bytes(startup).decode("utf-8") + "\n")
    sys.stdout.flush()
    try:
        server.serve_forever(poll_interval=0.05)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


def _mcp_tool_definition() -> dict[str, Any]:
    return {
        "name": MCP_TOOL_NAME,
        "description": "Purchase deterministic structured-text analysis for 28 disposable L28.",
        "inputSchema": {
            "type": "object",
            "required": ["service_id", "input"],
            "additionalProperties": False,
            "properties": {
                "service_id": {"type": "string", "const": SERVICE_ID},
                "input": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": MAX_INPUT_CHARS,
                },
            },
        },
    }


def _mcp_result(request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _mcp_error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": code, "message": message},
    }


def handle_mcp_message(message: Any) -> dict[str, Any] | None:
    if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
        return _mcp_error(message.get("id") if isinstance(message, dict) else None, -32600, "invalid_request")

    method = message.get("method")
    request_id = message.get("id")

    if method == "notifications/initialized":
        return None

    if method == "initialize":
        if "id" not in message:
            return _mcp_error(None, -32600, "initialize_requires_id")
        return _mcp_result(
            request_id,
            {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {
                    "name": "l28-two-agent-service",
                    "version": "0.1",
                },
            },
        )

    if method == "ping":
        if "id" not in message:
            return None
        return _mcp_result(request_id, {})

    if method == "tools/list":
        if "id" not in message:
            return _mcp_error(None, -32600, "tools_list_requires_id")
        return _mcp_result(request_id, {"tools": [_mcp_tool_definition()]})

    if method == "tools/call":
        if "id" not in message:
            return _mcp_error(None, -32600, "tools_call_requires_id")
        params = message.get("params")
        if not isinstance(params, dict):
            return _mcp_error(request_id, -32602, "params_invalid")
        if params.get("name") != MCP_TOOL_NAME:
            return _mcp_error(request_id, -32602, "tool_unsupported")
        arguments = params.get("arguments")
        try:
            result = purchase_service(arguments)
        except ExternalAccessError as exc:
            error_payload = {"ok": False, "error": exc.code}
            return _mcp_result(
                request_id,
                {
                    "content": [
                        {
                            "type": "text",
                            "text": _json_bytes(error_payload).decode("utf-8"),
                        }
                    ],
                    "structuredContent": error_payload,
                    "isError": True,
                },
            )
        return _mcp_result(
            request_id,
            {
                "content": [
                    {
                        "type": "text",
                        "text": _json_bytes(result).decode("utf-8"),
                    }
                ],
                "structuredContent": result,
                "isError": False,
            },
        )

    if "id" not in message:
        return None
    return _mcp_error(request_id, -32601, "method_not_found")


def run_mcp_stdio_runtime() -> int:
    for raw_line in sys.stdin:
        line = raw_line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            response = _mcp_error(None, -32700, "parse_error")
        else:
            response = handle_mcp_message(message)
        if response is not None:
            sys.stdout.write(_json_bytes(response).decode("utf-8") + "\n")
            sys.stdout.flush()
    return 0


def _read_json_line(stream: TextIO, *, timeout: float = 5.0) -> dict[str, Any]:
    selector = selectors.DefaultSelector()
    try:
        selector.register(stream, selectors.EVENT_READ)
        if not selector.select(timeout):
            raise ExternalAccessError("runtime_response_timeout")
        line = stream.readline()
    finally:
        selector.close()
    if not line:
        raise ExternalAccessError("runtime_closed")
    try:
        value = json.loads(line)
    except json.JSONDecodeError as exc:
        raise ExternalAccessError("runtime_response_invalid_json") from exc
    if not isinstance(value, dict):
        raise ExternalAccessError("runtime_response_invalid")
    return value


def _stop_process(proc: subprocess.Popen[str]) -> None:
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=3)


def _repo_root() -> str:
    return str(Path(__file__).resolve().parents[1])


def _run_http_external_purchase(input_text: str) -> tuple[int, dict[str, Any], dict[str, Any]]:
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "coin.two_agent_service_external_access_demo",
            "--runtime",
            "http",
            "--port",
            "0",
        ],
        cwd=_repo_root(),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    if proc.stdout is None:
        _stop_process(proc)
        raise ExternalAccessError("http_stdout_missing")

    try:
        startup = _read_json_line(proc.stdout)
        if startup.get("event") != "http_runtime_started":
            raise ExternalAccessError("http_startup_invalid")
        if startup.get("host") != LOOPBACK_HOST:
            raise ExternalAccessError("http_not_loopback")
        port = startup.get("port")
        if not isinstance(port, int) or not (1 <= port <= 65535):
            raise ExternalAccessError("http_port_invalid")

        body = _json_bytes({"service_id": SERVICE_ID, "input": input_text})
        conn = http.client.HTTPConnection(LOOPBACK_HOST, port, timeout=5)
        try:
            conn.request(
                "POST",
                PURCHASE_PATH,
                body=body,
                headers={
                    "Content-Type": "application/json",
                    "Content-Length": str(len(body)),
                },
            )
            response = conn.getresponse()
            status = response.status
            raw = response.read()
        finally:
            conn.close()

        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ExternalAccessError("http_response_invalid_json") from exc
        if not isinstance(payload, dict):
            raise ExternalAccessError("http_response_invalid")
        return status, payload, startup
    finally:
        _stop_process(proc)


def _send_mcp(
    proc: subprocess.Popen[str],
    message: dict[str, Any],
    *,
    expect_response: bool,
) -> dict[str, Any] | None:
    if proc.stdin is None or proc.stdout is None:
        raise ExternalAccessError("mcp_pipe_missing")
    proc.stdin.write(_json_bytes(message).decode("utf-8") + "\n")
    proc.stdin.flush()
    if not expect_response:
        return None
    return _read_json_line(proc.stdout)


def _run_mcp_external_purchase(input_text: str) -> tuple[dict[str, Any], dict[str, Any]]:
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "coin.two_agent_service_external_access_demo",
            "--runtime",
            "mcp",
        ],
        cwd=_repo_root(),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    try:
        initialize = _send_mcp(
            proc,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": MCP_PROTOCOL_VERSION,
                    "capabilities": {},
                    "clientInfo": {"name": "l28-external-access-demo", "version": "0.1"},
                },
            },
            expect_response=True,
        )
        if not isinstance(initialize, dict) or "result" not in initialize:
            raise ExternalAccessError("mcp_initialize_failed")

        _send_mcp(
            proc,
            {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
            expect_response=False,
        )

        tools = _send_mcp(
            proc,
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
            expect_response=True,
        )
        tool_list = tools.get("result", {}).get("tools") if isinstance(tools, dict) else None
        if not isinstance(tool_list, list) or [t.get("name") for t in tool_list] != [MCP_TOOL_NAME]:
            raise ExternalAccessError("mcp_tool_list_invalid")

        response = _send_mcp(
            proc,
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": MCP_TOOL_NAME,
                    "arguments": {
                        "service_id": SERVICE_ID,
                        "input": input_text,
                    },
                },
            },
            expect_response=True,
        )
        if not isinstance(response, dict) or "result" not in response:
            raise ExternalAccessError("mcp_call_failed")
        result = response["result"]
        if not isinstance(result, dict) or result.get("isError") is not False:
            raise ExternalAccessError("mcp_tool_failed")
        payload = result.get("structuredContent")
        if not isinstance(payload, dict):
            raise ExternalAccessError("mcp_structured_content_missing")
        return payload, initialize
    finally:
        if proc.stdin is not None:
            try:
                proc.stdin.close()
            except OSError:
                pass
        _stop_process(proc)


def _verified_purchase(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("ok") is not True or payload.get("service_id") != SERVICE_ID:
        raise ExternalAccessError("purchase_envelope_invalid")
    purchase = payload.get("purchase")
    if not isinstance(purchase, dict):
        raise ExternalAccessError("purchase_missing")

    expected = {
        "quoted_amount": PRICE_L28,
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
        "canonical_history_touched": False,
        "public_network_used": False,
        "production_keys_used": False,
    }
    for key, value in expected.items():
        if purchase.get(key) != value:
            raise ExternalAccessError("purchase_field_invalid:" + key)

    if purchase.get("service_id") != SERVICE_ID or purchase.get("asset_id") != "L28":
        raise ExternalAccessError("purchase_identity_invalid")

    for key in ("payment_tx_id", "service_result_id", "receipt_id"):
        value = purchase.get(key)
        if not isinstance(value, str) or len(value) != 64:
            raise ExternalAccessError("purchase_id_invalid:" + key)

    if not isinstance(purchase.get("service_output"), dict):
        raise ExternalAccessError("service_output_missing")
    return purchase


def _stable_semantics(http_purchase: dict[str, Any], mcp_purchase: dict[str, Any]) -> bool:
    stable_keys = (
        "service_id",
        "asset_id",
        "quoted_amount",
        "canonical_validation",
        "payment_applied",
        "payment_verified",
        "agent_a_balance_before",
        "agent_b_balance_before",
        "agent_a_balance_after",
        "agent_b_balance_after",
        "service_executed",
        "service_result_verified",
        "receipt_created",
        "receipt_verified",
        "canonical_history_touched",
        "public_network_used",
        "production_keys_used",
        "service_output",
    )
    return all(http_purchase.get(key) == mcp_purchase.get(key) for key in stable_keys)


def execute_external_access_demo(input_text: str) -> dict[str, Any]:
    if not isinstance(input_text, str) or not input_text or len(input_text) > MAX_INPUT_CHARS:
        raise ExternalAccessError("input_invalid")

    http_status, http_payload, http_startup = _run_http_external_purchase(input_text)
    if http_status != 200:
        raise ExternalAccessError("http_purchase_failed")
    http_purchase = _verified_purchase(http_payload)

    mcp_payload, mcp_initialize = _run_mcp_external_purchase(input_text)
    mcp_purchase = _verified_purchase(mcp_payload)

    equivalent = _stable_semantics(http_purchase, mcp_purchase)
    if not equivalent:
        raise ExternalAccessError("transport_semantics_mismatch")

    return {
        "demo_profile": RUNTIME_PROFILE,
        "http_runtime_started": True,
        "http_bound_host": http_startup["host"],
        "http_external_call": True,
        "http_status": http_status,
        "http_purchase_verified": True,
        "http_quoted_amount": http_purchase["quoted_amount"],
        "http_payment_tx_id": http_purchase["payment_tx_id"],
        "http_payment_verified": http_purchase["payment_verified"],
        "http_service_executed": http_purchase["service_executed"],
        "http_service_result_id": http_purchase["service_result_id"],
        "http_receipt_id": http_purchase["receipt_id"],
        "http_receipt_verified": http_purchase["receipt_verified"],
        "mcp_runtime_started": True,
        "mcp_transport": "stdio",
        "mcp_protocol_version": mcp_initialize["result"]["protocolVersion"],
        "mcp_external_call": True,
        "mcp_tool": MCP_TOOL_NAME,
        "mcp_purchase_verified": True,
        "mcp_quoted_amount": mcp_purchase["quoted_amount"],
        "mcp_payment_tx_id": mcp_purchase["payment_tx_id"],
        "mcp_payment_verified": mcp_purchase["payment_verified"],
        "mcp_service_executed": mcp_purchase["service_executed"],
        "mcp_service_result_id": mcp_purchase["service_result_id"],
        "mcp_receipt_id": mcp_purchase["receipt_id"],
        "mcp_receipt_verified": mcp_purchase["receipt_verified"],
        "service_id": SERVICE_ID,
        "service_output": http_purchase["service_output"],
        "same_core_transaction": True,
        "stable_semantics_equivalent": equivalent,
        "canonical_history_touched": (
            http_purchase["canonical_history_touched"]
            or mcp_purchase["canonical_history_touched"]
        ),
        "public_network_used": (
            http_purchase["public_network_used"]
            or mcp_purchase["public_network_used"]
        ),
        "production_keys_used": (
            http_purchase["production_keys_used"]
            or mcp_purchase["production_keys_used"]
        ),
        "production_settlement": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m coin.two_agent_service_external_access_demo",
        description="Run bounded local HTTP/JSON + MCP stdio L28 service access.",
    )
    parser.add_argument(
        "--runtime",
        choices=("demo", "http", "mcp"),
        default="demo",
    )
    parser.add_argument(
        "--input",
        default="L28 enables machine payments between autonomous systems.",
    )
    parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    if args.runtime == "http":
        return run_http_runtime(args.port)
    if args.runtime == "mcp":
        return run_mcp_stdio_runtime()

    try:
        result = execute_external_access_demo(args.input)
    except ExternalAccessError as exc:
        sys.stderr.write(exc.code + "\n")
        return 1

    sys.stdout.write(_json_bytes(result).decode("utf-8") + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
