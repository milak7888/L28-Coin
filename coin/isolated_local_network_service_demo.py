# SPDX-License-Identifier: Apache-2.0
"""Isolated two-process L28 paid-service transaction over IPv4 loopback TCP.

Agent A and Agent B are separate child processes. Request, quote, payment,
result, and receipt cross one 127.0.0.1 TCP session. Payment validation and
ledger application stay on the existing canonical path.

This slice does not authorize LAN, public networking, testnet, production
keys, broadcast, mining, or production settlement. Private keys are generated
inside the owning process and are never serialized or sent.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import select
import socket
import struct
import subprocess
import sys
import tempfile
import time
from collections.abc import Mapping
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from coin.disposable_offline_transfer_demo import (
    ALICE_INITIAL_BALANCE,
    BOB_INITIAL_BALANCE,
    DEMO_TIMESTAMP,
    TRANSFER_AMOUNT,
    _open_ledger,
    _require_protected_economics,
    apply_transfer,
    build_signed_transfer,
    classify_transfer,
    public_identity,
)
from coin.two_agent_service_transaction_demo import (
    PRICE_L28,
    DemoError as ServiceDemoError,
    _perform_paid_service,
    _public_key_hex,
    build_payment_authorization,
    build_service_quote,
    build_service_receipt,
    build_service_request,
    build_service_result,
    structured_text_analysis,
    verify_accepted_payment,
    verify_payment_intent_binding,
    verify_service_quote,
    verify_service_receipt,
    verify_service_request,
    verify_service_result,
)


DEMO_PROFILE = "l28-isolated-local-network-service/v0.1"
TRANSPORT_VERSION = 1
LOOPBACK_HOST = "127.0.0.1"
MAX_FRAME_BYTES = 65536
SOCKET_TIMEOUT_SECONDS = 10.0
PARENT_DEADLINE_SECONDS = 25.0
FRAME_FIELDS = ("message_type", "payload", "profile", "sequence", "version")
MESSAGE_SEQUENCE = (
    "provider_hello",
    "service_request",
    "service_quote",
    "payment_package",
    "service_result_package",
)
HELLO_FIELDS = ("provider_identity", "provider_public_key")
PAYMENT_PACKAGE_FIELDS = ("payment_authorization", "payment_tx")
RESULT_PACKAGE_FIELDS = ("receipt", "service_result")


class NetworkDemoError(Exception):
    """Fail-closed public error. The code is not secret material."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise NetworkDemoError("malformed_frame")
        result[key] = value
    return result


def _exact_fields(payload: Mapping[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    if not isinstance(payload, dict) or tuple(sorted(payload)) != tuple(sorted(fields)):
        raise NetworkDemoError("unexpected_field")
    return dict(payload)


def _canonical_frame(message_type: str, sequence: int, payload: Mapping[str, Any]) -> bytes:
    if message_type not in MESSAGE_SEQUENCE:
        raise NetworkDemoError("unknown_message_type")
    if type(sequence) is not int or sequence != MESSAGE_SEQUENCE.index(message_type) + 1:
        raise NetworkDemoError("wrong_sequence")
    frame = {
        "profile": DEMO_PROFILE,
        "version": TRANSPORT_VERSION,
        "message_type": message_type,
        "sequence": sequence,
        "payload": payload,
    }
    body = json.dumps(
        frame,
        sort_keys=False,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    if len(body) > MAX_FRAME_BYTES:
        raise NetworkDemoError("oversized_frame")
    return body


def encode_frame(message_type: str, sequence: int, payload: Mapping[str, Any]) -> bytes:
    body = _canonical_frame(message_type, sequence, payload)
    return struct.pack(">I", len(body)) + body


def decode_frame(body: bytes, *, expected_sequence: int) -> dict[str, Any]:
    if len(body) > MAX_FRAME_BYTES:
        raise NetworkDemoError("oversized_frame")
    try:
        frame = json.loads(
            body.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=lambda _value: (_ for _ in ()).throw(NetworkDemoError("malformed_frame")),
        )
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise NetworkDemoError("malformed_frame") from exc
    if not isinstance(frame, dict) or tuple(sorted(frame)) != FRAME_FIELDS:
        raise NetworkDemoError("unexpected_field")
    if frame.get("profile") != DEMO_PROFILE or frame.get("version") != TRANSPORT_VERSION:
        raise NetworkDemoError("wrong_profile")
    if type(frame.get("version")) is not int:
        raise NetworkDemoError("wrong_profile")
    message_type = frame.get("message_type")
    sequence = frame.get("sequence")
    if not isinstance(message_type, str) or message_type not in MESSAGE_SEQUENCE:
        raise NetworkDemoError("unknown_message_type")
    if type(sequence) is not int:
        raise NetworkDemoError("wrong_sequence")
    if sequence != expected_sequence:
        raise NetworkDemoError("duplicate_sequence" if sequence < expected_sequence else "wrong_sequence")
    if MESSAGE_SEQUENCE[sequence - 1] != message_type:
        raise NetworkDemoError("wrong_sequence")
    payload = frame.get("payload")
    if not isinstance(payload, dict):
        raise NetworkDemoError("malformed_frame")
    return frame


def _read_exact(sock: socket.socket, size: int) -> bytes:
    chunks = bytearray()
    while len(chunks) < size:
        try:
            part = sock.recv(size - len(chunks))
        except socket.timeout as exc:
            raise NetworkDemoError("truncated_frame") from exc
        if not part:
            raise NetworkDemoError("truncated_frame" if chunks else "premature_eof")
        chunks.extend(part)
    return bytes(chunks)


def read_frame(sock: socket.socket, *, expected_sequence: int) -> dict[str, Any]:
    try:
        header = _read_exact(sock, 4)
    except NetworkDemoError as exc:
        if exc.code == "premature_eof" or exc.code == "truncated_frame":
            raise NetworkDemoError("premature_eof") from exc
        raise
    length = struct.unpack(">I", header)[0]
    if type(length) is not int or length <= 0 or length > MAX_FRAME_BYTES:
        raise NetworkDemoError("oversized_frame")
    body = _read_exact(sock, length)
    if len(body) != length:
        raise NetworkDemoError("truncated_frame")
    return decode_frame(body, expected_sequence=expected_sequence)


def write_frame(
    sock: socket.socket,
    message_type: str,
    sequence: int,
    payload: Mapping[str, Any],
) -> None:
    try:
        sock.sendall(encode_frame(message_type, sequence, payload))
    except OSError as exc:
        raise NetworkDemoError("truncated_frame") from exc


def require_loopback_host(host: str) -> str:
    if host != LOOPBACK_HOST:
        raise NetworkDemoError("non_loopback_host")
    return host


def open_provider_listener(host: str = LOOPBACK_HOST) -> socket.socket:
    require_loopback_host(host)
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        listener.bind((host, 0))
        bound_host, _port = listener.getsockname()
        if bound_host != LOOPBACK_HOST:
            raise NetworkDemoError("non_loopback_host")
        listener.listen(1)
        listener.settimeout(SOCKET_TIMEOUT_SECONDS)
    except NetworkDemoError:
        listener.close()
        raise
    except OSError as exc:
        listener.close()
        raise NetworkDemoError("listener_failed") from exc
    return listener


def connect_requester(host: str, port: int) -> socket.socket:
    require_loopback_host(host)
    if type(port) is not int or not 0 < port < 65536:
        raise NetworkDemoError("non_loopback_host")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(SOCKET_TIMEOUT_SECONDS)
    try:
        sock.connect((host, port))
    except OSError as exc:
        sock.close()
        raise NetworkDemoError("connect_failed") from exc
    peer = sock.getpeername()
    if peer[0] != LOOPBACK_HOST:
        sock.close()
        raise NetworkDemoError("non_loopback_host")
    return sock


def verify_provider_hello(payload: Mapping[str, Any]) -> dict[str, str]:
    hello = _exact_fields(payload, HELLO_FIELDS)
    identity = hello["provider_identity"]
    public_key = hello["provider_public_key"]
    if not isinstance(identity, str) or not isinstance(public_key, str):
        raise NetworkDemoError("wrong_provider_identity")
    if identity != public_identity(public_key):
        raise NetworkDemoError("wrong_provider_identity")
    return {"provider_identity": identity, "provider_public_key": public_key}


def _payment_package(payload: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    package = _exact_fields(payload, PAYMENT_PACKAGE_FIELDS)
    payment_tx = package["payment_tx"]
    authorization = package["payment_authorization"]
    if not isinstance(payment_tx, dict) or not isinstance(authorization, dict):
        raise NetworkDemoError("malformed_frame")
    return payment_tx, authorization


def _result_package(payload: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    package = _exact_fields(payload, RESULT_PACKAGE_FIELDS)
    service_result = package["service_result"]
    receipt = package["receipt"]
    if not isinstance(service_result, dict) or not isinstance(receipt, dict):
        raise NetworkDemoError("malformed_frame")
    return service_result, receipt


async def _apply_payment_once(ledger: Any, payment_tx: dict[str, Any]) -> None:
    if not await apply_transfer(ledger, payment_tx):
        raise NetworkDemoError("payment_apply_failed")
    replay_ok, _tx_id, replay_reason = classify_transfer(ledger, payment_tx)
    if replay_ok or replay_reason != "replay" or await apply_transfer(ledger, payment_tx):
        raise NetworkDemoError("replay_not_rejected")


def _provider_public(provider_key: Ed25519PrivateKey) -> dict[str, str]:
    public_key = _public_key_hex(provider_key)
    return {
        "provider_identity": public_identity(public_key),
        "provider_public_key": public_key,
    }


def run_provider_session(conn: socket.socket) -> dict[str, Any]:
    """Provider/payee session. The provider private key never leaves this process."""

    provider_key = Ed25519PrivateKey.generate()
    hello = _provider_public(provider_key)
    write_frame(conn, "provider_hello", 1, hello)
    request_frame = read_frame(conn, expected_sequence=2)
    if request_frame["message_type"] != "service_request":
        raise NetworkDemoError("wrong_sequence")
    request = request_frame["payload"]
    try:
        verified_request = verify_service_request(request)
    except ServiceDemoError as exc:
        raise NetworkDemoError(exc.code) from exc
    if verified_request["provider_identity"] != hello["provider_identity"]:
        raise NetworkDemoError("wrong_provider_identity")
    quote = build_service_quote(provider_key, request=request)
    write_frame(conn, "service_quote", 3, quote)
    payment_frame = read_frame(conn, expected_sequence=4)
    payment_tx, authorization = _payment_package(payment_frame["payload"])
    try:
        verify_payment_intent_binding(
            request=request,
            quote=quote,
            payment_tx=payment_tx,
            payment_authorization=authorization,
        )
    except ServiceDemoError as exc:
        raise NetworkDemoError(exc.code) from exc

    with tempfile.TemporaryDirectory(prefix="l28-isolated-local-network-") as data_dir:
        ledger = _open_ledger(data_dir)
        if ledger.issued_supply != 0 or ledger.mint_height != 0:
            raise NetworkDemoError("canonical_issuance_mutated")
        payer_identity = verified_request["payer_identity"]
        provider_identity = hello["provider_identity"]
        ledger.balances[payer_identity] = ALICE_INITIAL_BALANCE
        ledger.balances[provider_identity] = BOB_INITIAL_BALANCE
        payer_before = ledger.get_balance(payer_identity)
        provider_before = ledger.get_balance(provider_identity)
        canonical_ok, payment_tx_id, canonical_reason = classify_transfer(ledger, payment_tx)
        if not canonical_ok or canonical_reason != "ok" or payment_tx_id != payment_tx.get("id"):
            raise NetworkDemoError("canonical_validation_failed")
        asyncio.run(_apply_payment_once(ledger, payment_tx))
        verify_accepted_payment(
            ledger,
            request=request,
            quote=quote,
            payment_tx=payment_tx,
            payment_authorization=authorization,
        )
        output = _perform_paid_service(
            verified_request["input"]["text"],
            payment_verified=True,
        )
        service_result = build_service_result(
            provider_key,
            request=request,
            quote=quote,
            payment_tx_id=payment_tx_id,
            output=output,
        )
        receipt = build_service_receipt(
            provider_key,
            request=request,
            quote=quote,
            service_result=service_result,
            payment_tx_id=payment_tx_id,
        )
        payer_after = ledger.get_balance(payer_identity)
        provider_after = ledger.get_balance(provider_identity)
        if (payer_before, provider_before, payer_after, provider_after) != (100, 0, 72, 28):
            raise NetworkDemoError("balance_transition_mismatch")
        if ledger.issued_supply != 0 or ledger.mint_height != 0:
            raise NetworkDemoError("canonical_issuance_mutated")
        if int(ledger.total_transactions) != 1:
            raise NetworkDemoError("replay_not_rejected")

    write_frame(
        conn,
        "service_result_package",
        5,
        {"service_result": service_result, "receipt": receipt},
    )
    del provider_key
    return {
        "provider_hello_sent": True,
        "service_request_received": True,
        "request_verified": True,
        "service_quote_sent": True,
        "quoted_amount": PRICE_L28,
        "payment_package_received": True,
        "canonical_validation": "PASS",
        "payment_applied": True,
        "payment_verified": True,
        "payment_tx_id": payment_tx_id,
        "agent_a_balance_before": payer_before,
        "agent_b_balance_before": provider_before,
        "agent_a_balance_after": payer_after,
        "agent_b_balance_after": provider_after,
        "service_executed": True,
        "service_result_sent": True,
        "receipt_created": True,
        "provider_bound_host": LOOPBACK_HOST,
        "canonical_history_touched": False,
        "external_network_used": False,
        "production_keys_used": False,
        "production_settlement": False,
    }


def run_requester_session(sock: socket.socket, input_text: str) -> dict[str, Any]:
    """Requester/payer session. The payer private key never leaves this process."""

    payer_key = Ed25519PrivateKey.generate()
    hello_frame = read_frame(sock, expected_sequence=1)
    hello = verify_provider_hello(hello_frame["payload"])
    request = build_service_request(
        payer_key,
        provider_identity=hello["provider_identity"],
        input_text=input_text,
    )
    write_frame(sock, "service_request", 2, request)
    quote_frame = read_frame(sock, expected_sequence=3)
    quote = quote_frame["payload"]
    verified_quote = verify_service_quote(quote, request=request)
    if verified_quote["amount"] != PRICE_L28 or verified_quote["amount"] != TRANSFER_AMOUNT:
        raise NetworkDemoError("wrong_amount")
    payment_tx = build_signed_transfer(
        payer_key,
        receiver=hello["provider_identity"],
        amount=PRICE_L28,
        timestamp=DEMO_TIMESTAMP,
        nonce=100,
    )
    authorization = build_payment_authorization(
        payer_key,
        request=request,
        quote=quote,
        payment_tx=payment_tx,
    )
    write_frame(
        sock,
        "payment_package",
        4,
        {"payment_tx": payment_tx, "payment_authorization": authorization},
    )
    result_frame = read_frame(sock, expected_sequence=5)
    service_result, receipt = _result_package(result_frame["payload"])
    payment_tx_id = payment_tx["id"]
    verify_service_result(
        service_result,
        request=request,
        quote=quote,
        payment_tx_id=payment_tx_id,
    )
    verify_service_receipt(
        receipt,
        request=request,
        quote=quote,
        service_result=service_result,
        payment_tx_id=payment_tx_id,
    )
    expected_output = structured_text_analysis(input_text)
    if service_result["output"] != expected_output:
        raise NetworkDemoError("output_mismatch")
    del payer_key
    return {
        "provider_hello_received": True,
        "service_request_sent": True,
        "service_quote_received": True,
        "quote_verified": True,
        "quoted_amount": verified_quote["amount"],
        "payment_package_sent": True,
        "service_result_package_received": True,
        "service_result_verified": True,
        "receipt_verified": True,
        "payment_tx_id": payment_tx_id,
        "service_output": expected_output,
        "service_executed": True,
        "production_keys_used": False,
        "external_network_used": False,
    }


def _emit(payload: Mapping[str, Any]) -> None:
    sys.stdout.write(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    )
    sys.stdout.write("\n")
    sys.stdout.flush()


def _close_socket(sock: socket.socket | None) -> None:
    if sock is None:
        return
    try:
        sock.shutdown(socket.SHUT_RDWR)
    except OSError:
        pass
    sock.close()


def provider_main() -> int:
    listener = None
    conn = None
    evidence = None
    code = 1
    try:
        listener = open_provider_listener(LOOPBACK_HOST)
        host, port = listener.getsockname()
        _emit({"coordination": "provider_ready", "host": host, "port": port})
        conn, address = listener.accept()
        if address[0] != LOOPBACK_HOST:
            raise NetworkDemoError("non_loopback_peer")
        conn.settimeout(SOCKET_TIMEOUT_SECONDS)
        evidence = run_provider_session(conn)
        code = 0
    except (NetworkDemoError, ServiceDemoError) as exc:
        sys.stderr.write(getattr(exc, "code", "provider_failed") + "\n")
        code = 1
    finally:
        _close_socket(conn)
        _close_socket(listener)
    if code == 0 and evidence is not None:
        evidence["sockets_closed"] = True
        _emit({"coordination": "provider_evidence", **evidence})
    return code


def requester_main(host: str, port: int, input_text: str) -> int:
    sock = None
    evidence = None
    code = 1
    try:
        sock = connect_requester(host, port)
        evidence = run_requester_session(sock, input_text)
        code = 0
    except (NetworkDemoError, ServiceDemoError) as exc:
        sys.stderr.write(getattr(exc, "code", "requester_failed") + "\n")
        code = 1
    finally:
        _close_socket(sock)
    if code == 0 and evidence is not None:
        evidence["sockets_closed"] = True
        _emit({"coordination": "requester_evidence", **evidence})
    return code


def _argv_for_role(role: str, *, host: str | None = None, port: int | None = None, input_text: str | None = None) -> list[str]:
    command = [sys.executable, "-m", "coin.isolated_local_network_service_demo", "--role", role]
    if host is not None:
        command.extend(["--host", host])
    if port is not None:
        command.extend(["--port", str(port)])
    if input_text is not None:
        command.extend(["--input", input_text])
    return command


def _read_json_line(stream: Any, deadline: float) -> dict[str, Any]:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise NetworkDemoError("parent_deadline")
    ready, _unused, _errors = select.select([stream], [], [], remaining)
    if not ready:
        raise NetworkDemoError("parent_deadline")
    line = stream.readline()
    if not line:
        raise NetworkDemoError("premature_eof")
    try:
        payload = json.loads(line, object_pairs_hook=_reject_duplicate_keys)
    except (json.JSONDecodeError, UnicodeError, NetworkDemoError) as exc:
        raise NetworkDemoError("malformed_frame") from exc
    if not isinstance(payload, dict):
        raise NetworkDemoError("malformed_frame")
    return payload


def _terminate(process: subprocess.Popen[str] | None) -> None:
    if process is None:
        return
    if process.poll() is None:
        process.kill()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def _contains_secret_key(node: Any) -> bool:
    if isinstance(node, dict):
        for key, value in node.items():
            if isinstance(key, str) and key.lower() in {"private_key", "privkey", "seed", "mnemonic", "xprv"}:
                return True
            if _contains_secret_key(value):
                return True
    elif isinstance(node, list):
        return any(_contains_secret_key(item) for item in node)
    return False


def _merge_evidence(
    *,
    provider: Mapping[str, Any],
    requester: Mapping[str, Any],
    provider_pid: int,
    requester_pid: int,
) -> dict[str, Any]:
    if _contains_secret_key(provider) or _contains_secret_key(requester):
        raise NetworkDemoError("secret_material_forbidden")
    if provider.get("payment_tx_id") != requester.get("payment_tx_id"):
        raise NetworkDemoError("payment_binding_invalid")
    if provider.get("quoted_amount") != PRICE_L28 or requester.get("quoted_amount") != PRICE_L28:
        raise NetworkDemoError("wrong_amount")
    crossed = {
        "provider_hello_crossed_network": bool(provider.get("provider_hello_sent") and requester.get("provider_hello_received")),
        "service_request_crossed_network": bool(provider.get("service_request_received") and requester.get("service_request_sent")),
        "service_quote_crossed_network": bool(provider.get("service_quote_sent") and requester.get("service_quote_received")),
        "payment_package_crossed_network": bool(provider.get("payment_package_received") and requester.get("payment_package_sent")),
        "service_result_package_crossed_network": bool(
            provider.get("service_result_sent") and requester.get("service_result_package_received")
        ),
    }
    if not all(crossed.values()):
        raise NetworkDemoError("network_transfer_incomplete")
    if provider.get("canonical_validation") != "PASS" or provider.get("payment_applied") is not True:
        raise NetworkDemoError("canonical_validation_failed")
    if requester.get("service_result_verified") is not True or requester.get("receipt_verified") is not True:
        raise NetworkDemoError("receipt_not_verified")
    return {
        "demo_profile": DEMO_PROFILE,
        "agent_process_count": 2,
        "distinct_agent_processes": provider_pid != requester_pid,
        "agent_a_pid": requester_pid,
        "agent_b_pid": provider_pid,
        "network_transport": "tcp_ipv4_loopback",
        "provider_bound_host": provider.get("provider_bound_host"),
        "external_network_used": False,
        **crossed,
        "request_verified": provider.get("request_verified") is True,
        "quote_verified": requester.get("quote_verified") is True,
        "quoted_amount": PRICE_L28,
        "payment_tx_id": provider.get("payment_tx_id"),
        "canonical_validation": "PASS",
        "payment_applied": True,
        "payment_verified": provider.get("payment_verified") is True,
        "agent_a_balance_before": provider.get("agent_a_balance_before"),
        "agent_b_balance_before": provider.get("agent_b_balance_before"),
        "agent_a_balance_after": provider.get("agent_a_balance_after"),
        "agent_b_balance_after": provider.get("agent_b_balance_after"),
        "service_executed": provider.get("service_executed") is True and requester.get("service_executed") is True,
        "service_output": requester.get("service_output"),
        "service_result_verified": True,
        "receipt_created": provider.get("receipt_created") is True,
        "receipt_verified": True,
        "both_processes_terminal": True,
        "sockets_closed": provider.get("sockets_closed") is True and requester.get("sockets_closed") is True,
        "canonical_history_touched": False,
        "public_network_used": False,
        "production_keys_used": False,
        "production_settlement": False,
    }


def execute_isolated_local_network_service(input_text: str) -> dict[str, Any]:
    """Parent coordination only. Business artifacts cross TCP between the children."""

    _require_protected_economics()
    deadline = time.monotonic() + PARENT_DEADLINE_SECONDS
    provider = subprocess.Popen(
        _argv_for_role("provider"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    requester = None
    try:
        if provider.stdout is None or provider.stderr is None:
            raise NetworkDemoError("parent_coordination_failed")
        ready = _read_json_line(provider.stdout, deadline)
        if ready.get("coordination") != "provider_ready":
            raise NetworkDemoError("parent_coordination_failed")
        host = require_loopback_host(str(ready.get("host")))
        port = ready.get("port")
        if type(port) is not int:
            raise NetworkDemoError("parent_coordination_failed")
        requester = subprocess.Popen(
            _argv_for_role("requester", host=host, port=port, input_text=input_text),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        remaining = max(0.1, deadline - time.monotonic())
        requester_stdout, requester_stderr = requester.communicate(timeout=remaining)
        remaining = max(0.1, deadline - time.monotonic())
        provider_stdout, provider_stderr = provider.communicate(timeout=remaining)
        if provider.returncode != 0 or requester.returncode != 0:
            raise NetworkDemoError("child_failed")
        if provider.poll() is None or requester.poll() is None:
            raise NetworkDemoError("child_not_terminal")
        provider_evidence = json.loads(provider_stdout, object_pairs_hook=_reject_duplicate_keys)
        requester_evidence = json.loads(requester_stdout, object_pairs_hook=_reject_duplicate_keys)
        if provider_evidence.get("coordination") != "provider_evidence":
            raise NetworkDemoError("parent_coordination_failed")
        if requester_evidence.get("coordination") != "requester_evidence":
            raise NetworkDemoError("parent_coordination_failed")
        del requester_stderr, provider_stderr
        if provider.pid in {os.getpid(), requester.pid} or requester.pid == os.getpid():
            raise NetworkDemoError("process_boundary_invalid")
        result = _merge_evidence(
            provider=provider_evidence,
            requester=requester_evidence,
            provider_pid=provider.pid,
            requester_pid=requester.pid,
        )
    except subprocess.TimeoutExpired as exc:
        raise NetworkDemoError("parent_deadline") from exc
    finally:
        _terminate(requester)
        _terminate(provider)
    if result["distinct_agent_processes"] is not True or result["provider_bound_host"] != LOOPBACK_HOST:
        raise NetworkDemoError("process_boundary_invalid")
    if result["both_processes_terminal"] is not True or result["sockets_closed"] is not True:
        raise NetworkDemoError("cleanup_incomplete")
    _require_protected_economics()
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m coin.isolated_local_network_service_demo",
        description="Run one isolated two-process L28 paid-service transaction on loopback TCP.",
    )
    parser.add_argument("--role", choices=("parent", "provider", "requester"), default="parent")
    parser.add_argument("--host", default=LOOPBACK_HOST)
    parser.add_argument("--port", type=int)
    parser.add_argument(
        "--input",
        default="L28 enables machine payments between autonomous systems.",
    )
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    try:
        if args.role == "provider":
            return provider_main()
        if args.role == "requester":
            if args.port is None:
                raise NetworkDemoError("parent_coordination_failed")
            return requester_main(args.host, args.port, args.input)
        result = execute_isolated_local_network_service(args.input)
    except (NetworkDemoError, ServiceDemoError) as exc:
        sys.stderr.write(exc.code + "\n")
        return 1
    _emit(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
