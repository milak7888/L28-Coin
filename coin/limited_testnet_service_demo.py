# SPDX-License-Identifier: Apache-2.0
"""Limited testnet paid-service transaction across two explicit RFC1918 nodes.

The frozen slice authorizes this experiment only. Identity-module runtime,
network, testnet-start, signing, mining, broadcast, and settlement flags stay
false. Private keys are generated in the owning process and are never serialized.
"""

from __future__ import annotations

import argparse
import asyncio

try:
    import fcntl
except ImportError:
    fcntl = None
import ipaddress
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
from coin.disposable_testnet_identity import (
    BROADCAST_AUTHORIZED,
    GENESIS_PROFILE,
    MINING_AUTHORIZED,
    NETWORK_AUTHORIZED,
    NETWORK_SCOPE,
    PROFILE as IDENTITY_PROFILE,
    PROTECTED_ECONOMIC_FACTS,
    PROTOCOL_VERSION,
    RUNTIME_AUTHORIZED,
    SETTLEMENT_AUTHORIZED,
    SIGNING_AUTHORIZED,
    TESTNET_START_AUTHORIZED,
    validate_and_bind_disposable_testnet_config,
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


DEMO_PROFILE = "l28-limited-testnet-service/v0.1"
TRANSPORT_VERSION = 1
NETWORK_ID = "L28-DISPOSABLE-LIMITED001"
DATA_DIR_TAG = "l28-disposable-testnet:limited001"
ENDPOINT_BLOCKER = "DISTINCT_PRIVATE_TESTNET_ENDPOINT_UNAVAILABLE"
MAX_FRAME_BYTES = 65536
SOCKET_TIMEOUT_SECONDS = 10.0
MANUAL_ACCEPT_TIMEOUT_SECONDS = 120.0
PARENT_DEADLINE_SECONDS = 25.0
FRAME_FIELDS = (
    "config_hash",
    "genesis_hash",
    "message_type",
    "network_id",
    "payload",
    "profile",
    "sequence",
    "version",
)
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
_DARWIN_SIOCGIFADDR = 0xC0206921


class LimitedTestnetError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise LimitedTestnetError("malformed_frame")
        result[key] = value
    return result


def assert_identity_flags_unchanged() -> None:
    if any(
        (
            RUNTIME_AUTHORIZED,
            NETWORK_AUTHORIZED,
            TESTNET_START_AUTHORIZED,
            SIGNING_AUTHORIZED,
            MINING_AUTHORIZED,
            BROADCAST_AUTHORIZED,
            SETTLEMENT_AUTHORIZED,
        )
    ):
        raise LimitedTestnetError("identity_flag_mutated")


def limited_testnet_config() -> dict[str, Any]:
    return {
        "profile": IDENTITY_PROFILE,
        "protocol_version": PROTOCOL_VERSION,
        "network_scope": NETWORK_SCOPE,
        "network_id": NETWORK_ID,
        "data_dir_tag": DATA_DIR_TAG,
        "genesis": {
            "profile": GENESIS_PROFILE,
            "network_id": NETWORK_ID,
            "initial_height": 0,
            "initial_issued_supply": 0,
            "historical_checkpoint_imported": False,
            "historical_balances_loaded": False,
            "protected_economic_facts": dict(PROTECTED_ECONOMIC_FACTS),
        },
        "key_policy": {
            "allow_production_keys": False,
            "allow_creator_private_material": False,
            "allow_external_wallet_paths": False,
        },
        "acknowledge_disposable_test_only": True,
    }


def limited_testnet_binding() -> dict[str, Any]:
    assert_identity_flags_unchanged()
    binding = validate_and_bind_disposable_testnet_config(limited_testnet_config())
    if binding["network_id"] != NETWORK_ID or binding["data_dir_tag"] != DATA_DIR_TAG:
        raise LimitedTestnetError("wrong_network")
    if binding["runtime_authorized"] is not False or binding["network_authorized"] is not False:
        raise LimitedTestnetError("identity_flag_mutated")
    if binding["testnet_start_authorized"] is not False or binding["signing_authorized"] is not False:
        raise LimitedTestnetError("identity_flag_mutated")
    if binding["mining_authorized"] is not False or binding["broadcast_authorized"] is not False:
        raise LimitedTestnetError("identity_flag_mutated")
    if binding["settlement_authorized"] is not False:
        raise LimitedTestnetError("identity_flag_mutated")
    return binding


def classify_private_ipv4(host: str) -> str:
    try:
        address = ipaddress.IPv4Address(host)
    except (ipaddress.AddressValueError, ValueError) as exc:
        raise LimitedTestnetError("public_ip_rejected") from exc
    if address.is_loopback:
        raise LimitedTestnetError("loopback_rejected")
    if address.is_unspecified:
        raise LimitedTestnetError("unspecified_address_rejected")
    if address.is_multicast or address.is_link_local or int(address) == 0xFFFFFFFF:
        raise LimitedTestnetError("public_ip_rejected")
    octets = [int(part) for part in str(address).split(".")]
    if octets[0] == 10:
        return str(address)
    if octets[0] == 172 and 16 <= octets[1] <= 31:
        return str(address)
    if octets[0] == 192 and octets[1] == 168:
        return str(address)
    raise LimitedTestnetError("public_ip_rejected")


def require_distinct_endpoints(requester_host: str, provider_host: str) -> tuple[str, str]:
    requester = classify_private_ipv4(requester_host)
    provider = classify_private_ipv4(provider_host)
    if requester == provider:
        raise LimitedTestnetError(ENDPOINT_BLOCKER)
    return requester, provider


def enforce_allowlisted_peer(actual_host: str, allowed_host: str) -> str:
    actual = classify_private_ipv4(actual_host)
    allowed = classify_private_ipv4(allowed_host)
    if actual != allowed:
        raise LimitedTestnetError("peer_not_allowlisted")
    return actual


def discover_local_ipv4() -> list[str]:
    if fcntl is None:
        raise LimitedTestnetError(ENDPOINT_BLOCKER)
    found: list[str] = []
    for _index, name in socket.if_nameindex():
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            request = struct.pack("16s16s", name.encode("utf-8")[:15], b"\x00" * 16)
            result = fcntl.ioctl(probe.fileno(), _DARWIN_SIOCGIFADDR, request)
            address = socket.inet_ntoa(result[20:24])
        except OSError:
            continue
        finally:
            probe.close()
        if address not in found:
            found.append(address)
    return found


def select_distinct_endpoints(addresses: list[str]) -> tuple[str, str]:
    private: list[str] = []
    for address in addresses:
        try:
            private.append(classify_private_ipv4(address))
        except LimitedTestnetError:
            continue
    unique = list(dict.fromkeys(private))
    if len(unique) < 2:
        raise LimitedTestnetError(ENDPOINT_BLOCKER)
    return unique[0], unique[1]


def discover_distinct_rfc1918_endpoints() -> tuple[str, str]:
    return select_distinct_endpoints(discover_local_ipv4())


def _canonical_frame(
    message_type: str,
    sequence: int,
    payload: Mapping[str, Any],
    binding: Mapping[str, Any],
) -> bytes:
    if message_type not in MESSAGE_SEQUENCE:
        raise LimitedTestnetError("unknown_message_type")
    if type(sequence) is not int or sequence != MESSAGE_SEQUENCE.index(message_type) + 1:
        raise LimitedTestnetError("wrong_sequence")
    frame = {
        "profile": DEMO_PROFILE,
        "version": TRANSPORT_VERSION,
        "network_id": binding["network_id"],
        "genesis_hash": binding["genesis_hash"],
        "config_hash": binding["config_hash"],
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
        raise LimitedTestnetError("oversized_frame")
    return body


def encode_frame(
    message_type: str,
    sequence: int,
    payload: Mapping[str, Any],
    binding: Mapping[str, Any],
) -> bytes:
    body = _canonical_frame(message_type, sequence, payload, binding)
    return struct.pack(">I", len(body)) + body


def decode_frame(body: bytes, *, expected_sequence: int, binding: Mapping[str, Any]) -> dict[str, Any]:
    if len(body) > MAX_FRAME_BYTES:
        raise LimitedTestnetError("oversized_frame")
    try:
        frame = json.loads(body.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise LimitedTestnetError("malformed_frame") from exc
    if not isinstance(frame, dict) or tuple(sorted(frame)) != FRAME_FIELDS:
        raise LimitedTestnetError("unexpected_field")
    if frame.get("profile") != DEMO_PROFILE or type(frame.get("version")) is not int:
        raise LimitedTestnetError("wrong_profile")
    if frame.get("version") != TRANSPORT_VERSION:
        raise LimitedTestnetError("wrong_profile")
    if frame.get("network_id") != binding["network_id"]:
        raise LimitedTestnetError("wrong_network")
    if frame.get("genesis_hash") != binding["genesis_hash"] or frame.get("config_hash") != binding["config_hash"]:
        raise LimitedTestnetError("wrong_network_binding")
    message_type = frame.get("message_type")
    sequence = frame.get("sequence")
    if not isinstance(message_type, str) or message_type not in MESSAGE_SEQUENCE:
        raise LimitedTestnetError("unknown_message_type")
    if type(sequence) is not int:
        raise LimitedTestnetError("wrong_sequence")
    if sequence != expected_sequence:
        raise LimitedTestnetError("duplicate_sequence" if sequence < expected_sequence else "wrong_sequence")
    if MESSAGE_SEQUENCE[sequence - 1] != message_type:
        raise LimitedTestnetError("wrong_sequence")
    if not isinstance(frame.get("payload"), dict):
        raise LimitedTestnetError("malformed_frame")
    return frame


def _read_exact(sock: socket.socket, size: int) -> bytes:
    chunks = bytearray()
    while len(chunks) < size:
        try:
            part = sock.recv(size - len(chunks))
        except socket.timeout as exc:
            raise LimitedTestnetError("truncated_frame") from exc
        if not part:
            raise LimitedTestnetError("truncated_frame" if chunks else "premature_eof")
        chunks.extend(part)
    return bytes(chunks)


def read_frame(sock: socket.socket, *, expected_sequence: int, binding: Mapping[str, Any]) -> dict[str, Any]:
    try:
        header = _read_exact(sock, 4)
    except LimitedTestnetError as exc:
        if exc.code in {"premature_eof", "truncated_frame"}:
            raise LimitedTestnetError("premature_eof") from exc
        raise
    length = struct.unpack(">I", header)[0]
    if length <= 0 or length > MAX_FRAME_BYTES:
        raise LimitedTestnetError("oversized_frame")
    return decode_frame(_read_exact(sock, length), expected_sequence=expected_sequence, binding=binding)


def write_frame(
    sock: socket.socket,
    message_type: str,
    sequence: int,
    payload: Mapping[str, Any],
    binding: Mapping[str, Any],
) -> None:
    try:
        sock.sendall(encode_frame(message_type, sequence, payload, binding))
    except OSError as exc:
        raise LimitedTestnetError("truncated_frame") from exc


def open_provider_listener(
    provider_host: str,
    port: int = 0,
    *,
    accept_timeout: float = SOCKET_TIMEOUT_SECONDS,
) -> socket.socket:
    host = classify_private_ipv4(provider_host)
    if type(port) is not int or not 0 <= port <= 65535:
        raise LimitedTestnetError("invalid_port")
    if type(accept_timeout) not in {int, float} or accept_timeout <= 0:
        raise LimitedTestnetError("invalid_port")
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        listener.bind((host, port))
        bound_host, bound_port = listener.getsockname()
        if bound_host != host or (port != 0 and bound_port != port):
            raise LimitedTestnetError("peer_not_allowlisted")
        listener.listen(1)
        listener.settimeout(accept_timeout)
    except LimitedTestnetError:
        listener.close()
        raise
    except OSError as exc:
        listener.close()
        raise LimitedTestnetError("listener_failed") from exc
    return listener


def connect_requester(requester_host: str, provider_host: str, port: int) -> socket.socket:
    local_host, remote_host = require_distinct_endpoints(requester_host, provider_host)
    if type(port) is not int or not 0 < port < 65536:
        raise LimitedTestnetError("peer_not_allowlisted")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(SOCKET_TIMEOUT_SECONDS)
    try:
        sock.bind((local_host, 0))
        sock.connect((remote_host, port))
    except OSError as exc:
        sock.close()
        raise LimitedTestnetError("connect_failed") from exc
    if sock.getsockname()[0] != local_host or sock.getpeername()[0] != remote_host:
        sock.close()
        raise LimitedTestnetError("peer_not_allowlisted")
    return sock


def _exact_payload(payload: Mapping[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    if not isinstance(payload, dict) or tuple(sorted(payload)) != tuple(sorted(fields)):
        raise LimitedTestnetError("unexpected_field")
    return dict(payload)


def verify_provider_hello(payload: Mapping[str, Any]) -> dict[str, str]:
    hello = _exact_payload(payload, HELLO_FIELDS)
    identity = hello["provider_identity"]
    public_key = hello["provider_public_key"]
    if not isinstance(identity, str) or not isinstance(public_key, str):
        raise LimitedTestnetError("wrong_provider_identity")
    if identity != public_identity(public_key):
        raise LimitedTestnetError("wrong_provider_identity")
    return {"provider_identity": identity, "provider_public_key": public_key}


async def _apply_payment_once(ledger: Any, payment_tx: dict[str, Any]) -> None:
    if not await apply_transfer(ledger, payment_tx):
        raise LimitedTestnetError("payment_apply_failed")
    replay_ok, _tx_id, replay_reason = classify_transfer(ledger, payment_tx)
    if replay_ok or replay_reason != "replay" or await apply_transfer(ledger, payment_tx):
        raise LimitedTestnetError("replay_not_rejected")


def settle_disposable_payment(
    ledger: Any,
    *,
    request: Mapping[str, Any],
    quote: Mapping[str, Any],
    payment_tx: dict[str, Any],
    authorization: Mapping[str, Any],
) -> tuple[str, int, int, int, int]:
    verify_payment_intent_binding(
        request=request,
        quote=quote,
        payment_tx=payment_tx,
        payment_authorization=authorization,
    )
    payer_identity = str(payment_tx["sender"])
    provider_identity = str(payment_tx["receiver"])
    if ledger.issued_supply != 0 or ledger.mint_height != 0:
        raise LimitedTestnetError("canonical_issuance_mutated")
    ledger.balances[payer_identity] = ALICE_INITIAL_BALANCE
    ledger.balances[provider_identity] = BOB_INITIAL_BALANCE
    payer_before = ledger.get_balance(payer_identity)
    provider_before = ledger.get_balance(provider_identity)
    canonical_ok, payment_tx_id, canonical_reason = classify_transfer(ledger, payment_tx)
    if not canonical_ok or canonical_reason != "ok" or payment_tx_id != payment_tx.get("id"):
        raise LimitedTestnetError("canonical_validation_failed")
    asyncio.run(_apply_payment_once(ledger, payment_tx))
    verify_accepted_payment(
        ledger,
        request=request,
        quote=quote,
        payment_tx=payment_tx,
        payment_authorization=authorization,
    )
    if (ledger.get_balance(payer_identity), ledger.get_balance(provider_identity)) != (72, 28):
        raise LimitedTestnetError("balance_transition_mismatch")
    if int(ledger.total_transactions) != 1 or ledger.issued_supply != 0 or ledger.mint_height != 0:
        raise LimitedTestnetError("replay_not_rejected")
    return payment_tx_id, payer_before, provider_before, 72, 28


def run_provider_session(
    conn: socket.socket,
    *,
    binding: Mapping[str, Any],
    requester_host: str,
) -> dict[str, Any]:
    enforce_allowlisted_peer(conn.getpeername()[0], requester_host)
    provider_key = Ed25519PrivateKey.generate()
    public_key = _public_key_hex(provider_key)
    hello = {
        "provider_identity": public_identity(public_key),
        "provider_public_key": public_key,
    }
    write_frame(conn, "provider_hello", 1, hello, binding)
    request = read_frame(conn, expected_sequence=2, binding=binding)["payload"]
    verified_request = verify_service_request(request)
    if verified_request["provider_identity"] != hello["provider_identity"]:
        raise LimitedTestnetError("wrong_provider_identity")
    quote = build_service_quote(provider_key, request=request)
    write_frame(conn, "service_quote", 3, quote, binding)
    package = _exact_payload(read_frame(conn, expected_sequence=4, binding=binding)["payload"], PAYMENT_PACKAGE_FIELDS)
    payment_tx = package["payment_tx"]
    authorization = package["payment_authorization"]
    if not isinstance(payment_tx, dict) or not isinstance(authorization, dict):
        raise LimitedTestnetError("malformed_frame")
    with tempfile.TemporaryDirectory(prefix="l28-limited-testnet-") as data_dir:
        ledger = _open_ledger(data_dir)
        payment_tx_id, payer_before, provider_before, payer_after, provider_after = settle_disposable_payment(
            ledger,
            request=request,
            quote=quote,
            payment_tx=payment_tx,
            authorization=authorization,
        )
        output = _perform_paid_service(verified_request["input"]["text"], payment_verified=True)
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
    write_frame(
        conn,
        "service_result_package",
        5,
        {"service_result": service_result, "receipt": receipt},
        binding,
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
        "network_binding_verified": True,
        "peer_allowlist_enforced": True,
        "historical_state_imported": False,
        "canonical_history_touched": False,
        "production_keys_used": False,
        "mining_used": False,
        "broadcast_used": False,
        "production_settlement": False,
        "loopback_used": False,
        "public_network_used": False,
    }


def run_requester_session(
    sock: socket.socket,
    input_text: str,
    *,
    binding: Mapping[str, Any],
    provider_host: str,
) -> dict[str, Any]:
    enforce_allowlisted_peer(sock.getpeername()[0], provider_host)
    payer_key = Ed25519PrivateKey.generate()
    hello = verify_provider_hello(read_frame(sock, expected_sequence=1, binding=binding)["payload"])
    request = build_service_request(
        payer_key,
        provider_identity=hello["provider_identity"],
        input_text=input_text,
    )
    write_frame(sock, "service_request", 2, request, binding)
    quote = read_frame(sock, expected_sequence=3, binding=binding)["payload"]
    verified_quote = verify_service_quote(quote, request=request)
    if verified_quote["amount"] != PRICE_L28 or verified_quote["amount"] != TRANSFER_AMOUNT:
        raise LimitedTestnetError("wrong_amount")
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
        binding,
    )
    package = _exact_payload(read_frame(sock, expected_sequence=5, binding=binding)["payload"], RESULT_PACKAGE_FIELDS)
    service_result = package["service_result"]
    receipt = package["receipt"]
    verify_service_result(service_result, request=request, quote=quote, payment_tx_id=payment_tx["id"])
    verify_service_receipt(
        receipt,
        request=request,
        quote=quote,
        service_result=service_result,
        payment_tx_id=payment_tx["id"],
    )
    if service_result["output"] != structured_text_analysis(input_text):
        raise LimitedTestnetError("output_mismatch")
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
        "payment_tx_id": payment_tx["id"],
        "service_output": service_result["output"],
        "service_executed": True,
        "network_binding_verified": True,
        "peer_allowlist_enforced": True,
        "production_keys_used": False,
        "loopback_used": False,
        "public_network_used": False,
    }


def _emit(payload: Mapping[str, Any]) -> None:
    sys.stdout.write(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False))
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


def provider_main(provider_host: str, requester_host: str, port: int | None = None) -> int:
    require_distinct_endpoints(requester_host, provider_host)
    binding = limited_testnet_binding()
    listener = None
    conn = None
    evidence = None
    code = 1
    try:
        if port is None:
            bind_port = 0
            accept_timeout = SOCKET_TIMEOUT_SECONDS
        elif type(port) is not int or not 1 <= port <= 65535:
            raise LimitedTestnetError("invalid_port")
        else:
            bind_port = port
            accept_timeout = MANUAL_ACCEPT_TIMEOUT_SECONDS
        listener = open_provider_listener(provider_host, bind_port, accept_timeout=accept_timeout)
        host, bound_port = listener.getsockname()
        _emit({"coordination": "provider_ready", "host": host, "port": bound_port})
        try:
            conn, address = listener.accept()
        except TimeoutError as exc:
            raise LimitedTestnetError("accept_timeout") from exc
        conn.settimeout(SOCKET_TIMEOUT_SECONDS)
        enforce_allowlisted_peer(address[0], requester_host)
        evidence = run_provider_session(conn, binding=binding, requester_host=requester_host)
        code = 0
    except (LimitedTestnetError, ServiceDemoError) as exc:
        sys.stderr.write(getattr(exc, "code", "provider_failed") + "\n")
    finally:
        _close_socket(conn)
        _close_socket(listener)
    if code == 0 and evidence is not None:
        evidence["sockets_closed"] = True
        _emit({"coordination": "provider_evidence", **evidence})
    return code


def requester_main(requester_host: str, provider_host: str, port: int, input_text: str) -> int:
    binding = limited_testnet_binding()
    sock = None
    evidence = None
    code = 1
    try:
        sock = connect_requester(requester_host, provider_host, port)
        evidence = run_requester_session(sock, input_text, binding=binding, provider_host=provider_host)
        code = 0
    except (LimitedTestnetError, ServiceDemoError) as exc:
        sys.stderr.write(getattr(exc, "code", "requester_failed") + "\n")
    finally:
        _close_socket(sock)
    if code == 0 and evidence is not None:
        evidence["sockets_closed"] = True
        _emit({"coordination": "requester_evidence", **evidence})
    return code


def _argv(role: str, requester_host: str, provider_host: str, port: int | None = None, input_text: str | None = None) -> list[str]:
    command = [
        sys.executable,
        "-m",
        "coin.limited_testnet_service_demo",
        "--role",
        role,
        "--requester-host",
        requester_host,
        "--provider-host",
        provider_host,
    ]
    if port is not None:
        command.extend(["--port", str(port)])
    if input_text is not None:
        command.extend(["--input", input_text])
    return command


def _read_json_line(stream: Any, deadline: float) -> dict[str, Any]:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise LimitedTestnetError("parent_deadline")
    ready, _unused, _errors = select.select([stream], [], [], remaining)
    if not ready:
        raise LimitedTestnetError("parent_deadline")
    line = stream.readline()
    if not line:
        raise LimitedTestnetError("premature_eof")
    payload = json.loads(line, object_pairs_hook=_reject_duplicate_keys)
    if not isinstance(payload, dict):
        raise LimitedTestnetError("malformed_frame")
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


def execute_limited_testnet_service(input_text: str, requester_host: str, provider_host: str) -> dict[str, Any]:
    _require_protected_economics()
    requester_host, provider_host = require_distinct_endpoints(requester_host, provider_host)
    binding = limited_testnet_binding()
    deadline = time.monotonic() + PARENT_DEADLINE_SECONDS
    provider = subprocess.Popen(
        _argv("provider", requester_host, provider_host),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    requester = None
    try:
        if provider.stdout is None:
            raise LimitedTestnetError("parent_coordination_failed")
        ready = _read_json_line(provider.stdout, deadline)
        if ready.get("coordination") != "provider_ready" or ready.get("host") != provider_host:
            raise LimitedTestnetError("parent_coordination_failed")
        port = ready.get("port")
        if type(port) is not int:
            raise LimitedTestnetError("parent_coordination_failed")
        requester = subprocess.Popen(
            _argv("requester", requester_host, provider_host, port, input_text),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        requester_stdout, _requester_err = requester.communicate(timeout=max(0.1, deadline - time.monotonic()))
        provider_stdout, _provider_err = provider.communicate(timeout=max(0.1, deadline - time.monotonic()))
        if provider.returncode != 0 or requester.returncode != 0:
            raise LimitedTestnetError("child_failed")
        if provider.pid in {os.getpid(), requester.pid}:
            raise LimitedTestnetError("process_boundary_invalid")
        provider_evidence = json.loads(provider_stdout, object_pairs_hook=_reject_duplicate_keys)
        requester_evidence = json.loads(requester_stdout, object_pairs_hook=_reject_duplicate_keys)
    except subprocess.TimeoutExpired as exc:
        raise LimitedTestnetError("parent_deadline") from exc
    finally:
        _terminate(requester)
        _terminate(provider)
    if provider_evidence.get("payment_tx_id") != requester_evidence.get("payment_tx_id"):
        raise LimitedTestnetError("payment_binding_invalid")
    _require_protected_economics()
    assert_identity_flags_unchanged()
    return {
        "demo_profile": DEMO_PROFILE,
        "network_id": binding["network_id"],
        "genesis_hash": binding["genesis_hash"],
        "config_hash": binding["config_hash"],
        "requester_private_ipv4": requester_host,
        "provider_private_ipv4": provider_host,
        "distinct_network_endpoints": requester_host != provider_host,
        "loopback_used": False,
        "public_network_used": False,
        "peer_allowlist_enforced": True,
        "network_binding_verified": True,
        "quoted_amount": 28,
        "payment_tx_id": provider_evidence["payment_tx_id"],
        "canonical_validation": "PASS",
        "payment_applied": True,
        "payment_verified": True,
        "agent_a_balance_before": 100,
        "agent_b_balance_before": 0,
        "agent_a_balance_after": 72,
        "agent_b_balance_after": 28,
        "service_executed": True,
        "service_output": requester_evidence.get("service_output"),
        "service_result_verified": requester_evidence.get("service_result_verified") is True,
        "receipt_verified": requester_evidence.get("receipt_verified") is True,
        "canonical_history_touched": False,
        "historical_state_imported": False,
        "production_keys_used": False,
        "mining_used": False,
        "broadcast_used": False,
        "production_settlement": False,
        "sockets_closed": provider_evidence.get("sockets_closed") is True and requester_evidence.get("sockets_closed") is True,
        "both_processes_terminal": True,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m coin.limited_testnet_service_demo")
    parser.add_argument("--role", choices=("parent", "provider", "requester"), default="parent")
    parser.add_argument("--requester-host")
    parser.add_argument("--provider-host")
    parser.add_argument("--port", type=int)
    parser.add_argument("--input", default="L28 enables machine payments between autonomous systems.")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    try:
        assert_identity_flags_unchanged()
        if args.role == "provider":
            if not args.requester_host or not args.provider_host:
                raise LimitedTestnetError(ENDPOINT_BLOCKER)
            return provider_main(args.provider_host, args.requester_host, args.port)
        if args.role == "requester":
            if args.port is None or not args.requester_host or not args.provider_host:
                raise LimitedTestnetError(ENDPOINT_BLOCKER)
            return requester_main(args.requester_host, args.provider_host, args.port, args.input)
        if args.requester_host and args.provider_host:
            requester_host, provider_host = require_distinct_endpoints(args.requester_host, args.provider_host)
        else:
            requester_host, provider_host = discover_distinct_rfc1918_endpoints()
        result = execute_limited_testnet_service(args.input, requester_host, provider_host)
    except (LimitedTestnetError, ServiceDemoError) as exc:
        if exc.code == ENDPOINT_BLOCKER:
            sys.stderr.write("BLOCKER=DISTINCT_PRIVATE_TESTNET_ENDPOINT_UNAVAILABLE\n")
            return 2
        sys.stderr.write(exc.code + "\n")
        return 1
    _emit(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
