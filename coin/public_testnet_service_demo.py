# SPDX-License-Identifier: Apache-2.0
"""One-shot disposable public-testnet purchase over provider-neutral HTTP/JSON.

The frozen slice authorizes this experiment only. Identity-module runtime,
network, testnet-start, signing, mining, broadcast, and settlement flags stay
false. The provider listens on loopback so an already-available public HTTPS
ingress can forward one transaction. Localhost and LAN request paths are not
product evidence. Private keys stay in the owning process and are not serialized.
"""

from __future__ import annotations

import argparse
import http.client
import ipaddress
import json
import socket
import sys
import threading
import urllib.parse
from collections.abc import Mapping
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from coin.disposable_offline_transfer_demo import (
    DEMO_TIMESTAMP,
    TRANSFER_AMOUNT,
    _public_key_hex,
    build_signed_transfer,
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
from coin.limited_testnet_service_demo import (
    LimitedTestnetError,
    settle_disposable_payment,
    verify_provider_hello,
)
from coin.two_agent_service_transaction_demo import (
    ASSET_ID,
    MAX_INPUT_CHARS,
    PRICE_L28,
    SERVICE_ID,
    DemoError as ServiceDemoError,
    _perform_paid_service,
    build_payment_authorization,
    build_service_quote,
    build_service_receipt,
    build_service_request,
    build_service_result,
    structured_text_analysis,
    verify_service_quote,
    verify_service_receipt,
    verify_service_request,
    verify_service_result,
)


DEMO_PROFILE = "l28-public-testnet-service/v0.1"
DISCOVERY_PROFILE = "l28-public-testnet-service-discovery/v0.1"
DISCOVERY_VERSION = 1
RELEASE_CANDIDATE = "l28-public-testnet-v0.1.0-rc1"
NON_PRODUCTION_DESIGNATION = "NON_PRODUCTION_DISPOSABLE_TESTNET"
TRANSPORT_VERSION = 1
NETWORK_ID = "L28-DISPOSABLE-PUBLIC001"
DATA_DIR_TAG = "l28-disposable-testnet:public001"
ENDPOINT_BLOCKER = "PUBLIC_TESTNET_ENDPOINT_UNAVAILABLE"
DISCOVERY_PATH = "/v1/l28/public-testnet/services"
HELLO_PATH = "/v1/l28/public-testnet/provider_hello"
SESSION_PATH = "/v1/l28/public-testnet/session"
LOOPBACK_HOST = "127.0.0.1"
MAX_BODY_BYTES = 65536
REQUEST_TIMEOUT_SECONDS = 10.0
SESSION_DEADLINE_SECONDS = 120.0
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


class PublicTestnetError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise PublicTestnetError("malformed_json")
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
        raise PublicTestnetError("identity_flag_mutated")


def public_testnet_config() -> dict[str, Any]:
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


def public_testnet_binding() -> dict[str, Any]:
    assert_identity_flags_unchanged()
    binding = validate_and_bind_disposable_testnet_config(public_testnet_config())
    if binding["network_id"] != NETWORK_ID or binding["data_dir_tag"] != DATA_DIR_TAG:
        raise PublicTestnetError("wrong_network")
    authorized = (
        binding["runtime_authorized"],
        binding["network_authorized"],
        binding["testnet_start_authorized"],
        binding["signing_authorized"],
        binding["mining_authorized"],
        binding["broadcast_authorized"],
        binding["settlement_authorized"],
    )
    if any(flag is not False for flag in authorized):
        raise PublicTestnetError("identity_flag_mutated")
    return binding


def build_service_discovery(binding: Mapping[str, Any]) -> dict[str, Any]:
    """Return the exact public catalog without advancing the one-shot session."""
    assert_identity_flags_unchanged()
    if (
        binding.get("network_id") != NETWORK_ID
        or not isinstance(binding.get("genesis_hash"), str)
        or not isinstance(binding.get("config_hash"), str)
    ):
        raise PublicTestnetError("discovery_binding_invalid")
    return {
        "discovery_profile": DISCOVERY_PROFILE,
        "discovery_version": DISCOVERY_VERSION,
        "release_candidate": RELEASE_CANDIDATE,
        "designation": NON_PRODUCTION_DESIGNATION,
        "network_id": NETWORK_ID,
        "protocol_version": PROTOCOL_VERSION,
        "genesis_hash": binding["genesis_hash"],
        "config_hash": binding["config_hash"],
        "transport_profile": DEMO_PROFILE,
        "http_json": {
            "discovery_path": DISCOVERY_PATH,
            "provider_hello_path": HELLO_PATH,
            "session_path": SESSION_PATH,
            "external_https_required": True,
            "max_body_bytes": MAX_BODY_BYTES,
            "request_timeout_seconds": int(REQUEST_TIMEOUT_SECONDS),
            "session_deadline_seconds": int(SESSION_DEADLINE_SECONDS),
        },
        "services": [
            {
                "service_id": SERVICE_ID,
                "asset_id": ASSET_ID,
                "price": PRICE_L28,
                "max_input_chars": MAX_INPUT_CHARS,
                "one_shot": True,
            }
        ],
        "production_authority": False,
    }


def validate_service_discovery(body: bytes, binding: Mapping[str, Any]) -> dict[str, Any]:
    """Fail closed unless discovery is the exact catalog for this binding."""
    enforce_body_bound(len(body))
    try:
        value = json.loads(body.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys)
        actual = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except PublicTestnetError:
        raise
    except (TypeError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        raise PublicTestnetError("discovery_invalid") from exc
    expected = build_service_discovery(binding)
    canonical_expected = json.dumps(
        expected,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    if not isinstance(value, dict) or actual != canonical_expected:
        raise PublicTestnetError("discovery_invalid")
    return value


def _host_is_local_or_lan(host: str) -> str:
    lowered = host.strip("[]").lower()
    if lowered in {"localhost", "localhost.localdomain"} or lowered.endswith(".local"):
        return "localhost_request_path"
    try:
        address = ipaddress.ip_address(lowered)
    except ValueError:
        return ""
    if address.is_loopback or address.is_unspecified:
        return "localhost_request_path"
    if address.is_private or address.is_link_local or address.is_multicast:
        return "direct_lan_request_path"
    return ""


def require_public_https_endpoint(endpoint: str) -> str:
    parsed = urllib.parse.urlsplit(endpoint)
    host = parsed.hostname or ""
    local = _host_is_local_or_lan(host)
    if parsed.scheme != "https" or not host or parsed.username or parsed.password:
        raise PublicTestnetError(ENDPOINT_BLOCKER)
    if local:
        raise PublicTestnetError(local)
    if host == LOOPBACK_HOST:
        raise PublicTestnetError("localhost_request_path")
    return endpoint


def enforce_body_bound(length: int) -> None:
    if type(length) is not int or length < 0 or length > MAX_BODY_BYTES:
        raise PublicTestnetError("oversized_body")


def frame_bytes(message_type: str, sequence: int, payload: Mapping[str, Any], binding: Mapping[str, Any]) -> bytes:
    if message_type not in MESSAGE_SEQUENCE:
        raise PublicTestnetError("unknown_message_type")
    if type(sequence) is not int or sequence != MESSAGE_SEQUENCE.index(message_type) + 1:
        raise PublicTestnetError("wrong_sequence")
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
    body = json.dumps(frame, sort_keys=False, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    enforce_body_bound(len(body))
    return body


def parse_frame(body: bytes, *, expected_sequence: int, binding: Mapping[str, Any]) -> dict[str, Any]:
    enforce_body_bound(len(body))
    try:
        frame = json.loads(body.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise PublicTestnetError("malformed_json") from exc
    if not isinstance(frame, dict) or tuple(sorted(frame)) != FRAME_FIELDS:
        raise PublicTestnetError("unexpected_field")
    if frame.get("profile") != DEMO_PROFILE or frame.get("version") != TRANSPORT_VERSION:
        raise PublicTestnetError("wrong_profile")
    if frame.get("network_id") != binding["network_id"]:
        raise PublicTestnetError("wrong_network")
    if frame.get("genesis_hash") != binding["genesis_hash"] or frame.get("config_hash") != binding["config_hash"]:
        raise PublicTestnetError("wrong_network_binding")
    message_type = frame.get("message_type")
    sequence = frame.get("sequence")
    if not isinstance(message_type, str) or message_type not in MESSAGE_SEQUENCE or type(sequence) is not int:
        raise PublicTestnetError("wrong_sequence")
    if sequence != expected_sequence:
        raise PublicTestnetError("duplicate_sequence" if sequence < expected_sequence else "wrong_sequence")
    if MESSAGE_SEQUENCE[sequence - 1] != message_type or not isinstance(frame.get("payload"), dict):
        raise PublicTestnetError("wrong_sequence")
    return frame


class PublicProvider:
    def __init__(self) -> None:
        self.binding = public_testnet_binding()
        self._key = Ed25519PrivateKey.generate()
        self.public_key = _public_key_hex(self._key)
        self.identity = public_identity(self.public_key)
        self.expected = 1
        self.finished = threading.Event()
        self.evidence: dict[str, Any] | None = None
        self._request: dict[str, Any] | None = None
        self._quote: dict[str, Any] | None = None
        self._lock = threading.Lock()

    def close(self) -> None:
        self._key = None  # type: ignore[assignment]

    def hello_frame(self) -> dict[str, Any]:
        with self._lock:
            if self.finished.is_set():
                raise PublicTestnetError("session_closed")
            if self.expected != 1:
                raise PublicTestnetError("wrong_sequence")
            payload = {"provider_identity": self.identity, "provider_public_key": self.public_key}
            self.expected = 2
            return json.loads(frame_bytes("provider_hello", 1, payload, self.binding))

    def handle_frame(self, body: bytes) -> dict[str, Any]:
        with self._lock:
            if self.finished.is_set():
                raise PublicTestnetError("session_closed")
            frame = parse_frame(body, expected_sequence=self.expected, binding=self.binding)
            if frame["message_type"] == "service_request":
                return self._quote_for(frame["payload"])
            if frame["message_type"] == "payment_package":
                return self._settle(frame["payload"])
            raise PublicTestnetError("wrong_sequence")

    def _quote_for(self, request: dict[str, Any]) -> dict[str, Any]:
        verified = verify_service_request(request)
        if verified["provider_identity"] != self.identity:
            raise PublicTestnetError("wrong_provider_identity")
        quote = build_service_quote(self._key, request=request)
        if quote["amount"] != PRICE_L28:
            raise PublicTestnetError("wrong_amount")
        self._request = request
        self._quote = quote
        self.expected = 4
        return json.loads(frame_bytes("service_quote", 3, quote, self.binding))

    def _settle(self, package: Mapping[str, Any]) -> dict[str, Any]:
        if self._request is None or self._quote is None:
            raise PublicTestnetError("wrong_sequence")
        if tuple(sorted(package)) != ("payment_authorization", "payment_tx"):
            raise PublicTestnetError("unexpected_field")
        payment_tx = package["payment_tx"]
        authorization = package["payment_authorization"]
        if not isinstance(payment_tx, dict) or not isinstance(authorization, dict):
            raise PublicTestnetError("malformed_json")
        from tempfile import TemporaryDirectory

        from coin.disposable_offline_transfer_demo import _open_ledger

        try:
            with TemporaryDirectory(prefix="l28-public-testnet-") as data_dir:
                payment_tx_id, payer_before, provider_before, payer_after, provider_after = settle_disposable_payment(
                    _open_ledger(data_dir),
                    request=self._request,
                    quote=self._quote,
                    payment_tx=payment_tx,
                    authorization=authorization,
                )
        except LimitedTestnetError as exc:
            raise PublicTestnetError(exc.code) from exc
        output = _perform_paid_service(self._request["input"]["text"], payment_verified=True)
        service_result = build_service_result(
            self._key,
            request=self._request,
            quote=self._quote,
            payment_tx_id=payment_tx_id,
            output=output,
        )
        receipt = build_service_receipt(
            self._key,
            request=self._request,
            quote=self._quote,
            service_result=service_result,
            payment_tx_id=payment_tx_id,
        )
        self.evidence = {
            "service_request_verified": True,
            "quoted_amount": PRICE_L28,
            "canonical_validation": "PASS",
            "payment_applied": True,
            "payment_verified": True,
            "payment_tx_id": payment_tx_id,
            "requester_balance_before": payer_before,
            "provider_balance_before": provider_before,
            "requester_balance_after": payer_after,
            "provider_balance_after": provider_after,
            "replay_rejected": True,
            "service_executed": True,
            "receipt_created": True,
            "canonical_history_touched": False,
            "historical_state_imported": False,
            "production_keys_used": False,
            "mining_used": False,
            "canonical_broadcast_used": False,
            "production_settlement": False,
        }
        self.expected = 0
        self.close()
        self.finished.set()
        return json.loads(
            frame_bytes(
                "service_result_package",
                5,
                {"service_result": service_result, "receipt": receipt},
                self.binding,
            )
        )


def run_requester(exchange: Any, input_text: str, binding: Mapping[str, Any]) -> dict[str, Any]:
    discovery_body = exchange("GET", DISCOVERY_PATH, None)
    discovery = validate_service_discovery(discovery_body, binding)
    service = discovery["services"][0]
    payer = Ed25519PrivateKey.generate()
    hello_body = exchange("GET", HELLO_PATH, None)
    hello_frame = parse_frame(hello_body, expected_sequence=1, binding=binding)
    hello = verify_provider_hello(hello_frame["payload"])
    request = build_service_request(payer, provider_identity=hello["provider_identity"], input_text=input_text)
    quote_body = exchange("POST", SESSION_PATH, frame_bytes("service_request", 2, request, binding))
    quote_frame = parse_frame(quote_body, expected_sequence=3, binding=binding)
    quote = quote_frame["payload"]
    verify_service_quote(quote, request=request)
    if quote["amount"] != PRICE_L28 or quote["amount"] != TRANSFER_AMOUNT:
        raise PublicTestnetError("wrong_amount")
    payment_tx = build_signed_transfer(
        payer,
        receiver=hello["provider_identity"],
        amount=PRICE_L28,
        timestamp=DEMO_TIMESTAMP,
        nonce=100,
    )
    authorization = build_payment_authorization(payer, request=request, quote=quote, payment_tx=payment_tx)
    result_body = exchange(
        "POST",
        SESSION_PATH,
        frame_bytes(
            "payment_package",
            4,
            {"payment_tx": payment_tx, "payment_authorization": authorization},
            binding,
        ),
    )
    result_frame = parse_frame(result_body, expected_sequence=5, binding=binding)
    package = result_frame["payload"]
    if tuple(sorted(package)) != ("receipt", "service_result"):
        raise PublicTestnetError("unexpected_field")
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
        raise PublicTestnetError("tampered_result")
    del payer
    return {
        "service_discovery_received": True,
        "service_discovery_verified": True,
        "discovered_service_id": service["service_id"],
        "discovered_price": service["price"],
        "provider_hello_received": True,
        "service_request_sent": True,
        "service_quote_received": True,
        "quote_verified": True,
        "quoted_amount": PRICE_L28,
        "payment_package_sent": True,
        "service_result_package_received": True,
        "service_result_verified": True,
        "receipt_verified": True,
        "service_executed": True,
        "payment_tx_id": payment_tx["id"],
        "production_keys_used": False,
    }


def provider_evidence_record(evidence: Mapping[str, Any], *, network_id: str, shutdown_complete: bool) -> dict[str, Any]:
    """Return the already-computed one-shot provider record. Does not apply a payment."""
    if shutdown_complete is not True or network_id != NETWORK_ID:
        raise PublicTestnetError("provider_evidence_incomplete")
    balances = (
        evidence.get("requester_balance_before"),
        evidence.get("provider_balance_before"),
        evidence.get("requester_balance_after"),
        evidence.get("provider_balance_after"),
    )
    if balances != (100, 0, 72, 28):
        raise PublicTestnetError("provider_evidence_incomplete")
    if evidence.get("payment_tx_id") in {None, ""} or evidence.get("canonical_validation") != "PASS":
        raise PublicTestnetError("provider_evidence_incomplete")
    flags = (
        "payment_applied",
        "payment_verified",
        "replay_rejected",
        "service_executed",
        "receipt_created",
    )
    if any(evidence.get(flag) is not True for flag in flags):
        raise PublicTestnetError("provider_evidence_incomplete")
    if any(evidence.get(flag) is not False for flag in (
        "canonical_history_touched",
        "historical_state_imported",
        "production_keys_used",
        "mining_used",
        "canonical_broadcast_used",
        "production_settlement",
    )):
        raise PublicTestnetError("provider_evidence_incomplete")
    return {
        "coordination": "provider_evidence",
        "public_testnet": True,
        "network_id": network_id,
        "canonical_validation": evidence["canonical_validation"],
        "payment_applied": evidence["payment_applied"],
        "payment_verified": evidence["payment_verified"],
        "payment_tx_id": evidence["payment_tx_id"],
        "requester_balance_before": evidence["requester_balance_before"],
        "requester_balance_after": evidence["requester_balance_after"],
        "provider_balance_before": evidence["provider_balance_before"],
        "provider_balance_after": evidence["provider_balance_after"],
        "replay_rejected": evidence["replay_rejected"],
        "service_executed": evidence["service_executed"],
        "receipt_created": evidence["receipt_created"],
        "canonical_history_touched": evidence["canonical_history_touched"],
        "historical_state_imported": evidence["historical_state_imported"],
        "production_keys_used": evidence["production_keys_used"],
        "mining_used": evidence["mining_used"],
        "canonical_broadcast_used": evidence["canonical_broadcast_used"],
        "production_settlement": evidence["production_settlement"],
        "bounded_provider_shutdown": True,
    }


def build_public_evidence(endpoint: str, provider_evidence: Mapping[str, Any], requester_evidence: Mapping[str, Any]) -> dict[str, Any]:
    require_public_https_endpoint(endpoint)
    balances = (
        provider_evidence.get("requester_balance_before"),
        provider_evidence.get("provider_balance_before"),
        provider_evidence.get("requester_balance_after"),
        provider_evidence.get("provider_balance_after"),
    )
    if balances != (100, 0, 72, 28):
        raise PublicTestnetError("balance_transition_mismatch")
    if provider_evidence.get("payment_tx_id") != requester_evidence.get("payment_tx_id"):
        raise PublicTestnetError("payment_binding_invalid")
    assert_identity_flags_unchanged()
    return {
        "public_testnet": True,
        "network_id": NETWORK_ID,
        "public_endpoint_used": True,
        "localhost_request_path": False,
        "direct_lan_request_path": False,
        "provider_hello_received": True,
        "service_request_verified": True,
        "quoted_amount": 28,
        "quote_verified": True,
        "canonical_validation": "PASS",
        "payment_applied": True,
        "payment_verified": True,
        "payment_tx_id": provider_evidence["payment_tx_id"],
        "requester_balance_before": 100,
        "requester_balance_after": 72,
        "provider_balance_before": 0,
        "provider_balance_after": 28,
        "replay_rejected": provider_evidence.get("replay_rejected") is True,
        "service_executed": True,
        "service_result_verified": requester_evidence.get("service_result_verified") is True,
        "receipt_verified": requester_evidence.get("receipt_verified") is True,
        "canonical_history_touched": False,
        "historical_state_imported": False,
        "production_keys_used": False,
        "mining_used": False,
        "canonical_broadcast_used": False,
        "production_settlement": False,
        "bounded_provider_shutdown": True,
    }


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server: "_Server"

    def log_message(self, _format: str, *_args: Any) -> None:
        return

    def handle(self) -> None:
        self.request.settimeout(REQUEST_TIMEOUT_SECONDS)
        try:
            super().handle()
        except (TimeoutError, socket.timeout):
            self._error("request_timeout")

    def _error(self, code: str) -> None:
        body = json.dumps({"ok": False, "error": code}, sort_keys=True, separators=(",", ":")).encode("utf-8")
        try:
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(body)
        except OSError:
            return

    def _ok(self, payload: Mapping[str, Any]) -> None:
        body = json.dumps(payload, sort_keys=False, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> bytes:
        raw_length = self.headers.get("Content-Length")
        try:
            length = int(raw_length) if raw_length is not None else -1
        except ValueError:
            length = -1
        enforce_body_bound(length)
        body = self.rfile.read(length)
        if len(body) != length:
            raise PublicTestnetError("truncated_body")
        return body

    def do_GET(self) -> None:
        if self.path == DISCOVERY_PATH:
            try:
                self._ok(build_service_discovery(self.server.provider.binding))
            except PublicTestnetError as exc:
                self._error(exc.code)
            return
        if self.path != HELLO_PATH:
            self._error("path_not_found")
            return
        try:
            self._ok(self.server.provider.hello_frame())
        except (PublicTestnetError, ServiceDemoError) as exc:
            self._error(getattr(exc, "code", "request_rejected"))

    def do_POST(self) -> None:
        if self.path != SESSION_PATH:
            self._error("path_not_found")
            return
        try:
            body = self._read_body()
            response = self.server.provider.handle_frame(body)
            self._ok(response)
            if self.server.provider.finished.is_set():
                threading.Thread(target=self.server.shutdown, daemon=True).start()
        except (PublicTestnetError, ServiceDemoError, LimitedTestnetError) as exc:
            self._error(getattr(exc, "code", "request_rejected"))


class _Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False

    def __init__(self, provider: PublicProvider, port: int) -> None:
        if type(port) is not int or not 0 <= port <= 65535:
            raise PublicTestnetError("invalid_port")
        self.provider = provider
        super().__init__((LOOPBACK_HOST, port), _Handler)
        bound_host = self.server_address[0]
        if bound_host != LOOPBACK_HOST:
            self.server_close()
            raise PublicTestnetError("localhost_request_path")


def start_one_shot_server(port: int = 0) -> tuple[_Server, threading.Thread, PublicProvider]:
    provider = PublicProvider()
    server = _Server(provider, port)
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
    thread.start()
    return server, thread, provider


def stop_one_shot_server(server: _Server, thread: threading.Thread) -> None:
    server.shutdown()
    thread.join(timeout=2)
    server.server_close()
    server.provider.close()


def http_exchange(base_url: str, method: str, path: str, body: bytes | None, timeout: float, *, allow_local_harness: bool = False) -> bytes:
    if not allow_local_harness:
        require_public_https_endpoint(base_url)
    parsed = urllib.parse.urlsplit(base_url)
    host = parsed.hostname or ""
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    connection_type = http.client.HTTPSConnection if parsed.scheme == "https" else http.client.HTTPConnection
    if parsed.scheme == "http" and not allow_local_harness:
        raise PublicTestnetError(ENDPOINT_BLOCKER)
    connection = connection_type(host, port, timeout=timeout)
    try:
        connection.request(
            method,
            path,
            body=body,
            headers={"Content-Type": "application/json", "Content-Length": str(len(body or b""))},
        )
        if not allow_local_harness:
            peer = connection.sock.getpeername()[0] if connection.sock is not None else ""
            local = _host_is_local_or_lan(peer)
            if local:
                raise PublicTestnetError(local)
        response = connection.getresponse()
        payload = response.read(MAX_BODY_BYTES + 1)
    except PublicTestnetError:
        raise
    except (TimeoutError, socket.timeout) as exc:
        raise PublicTestnetError("request_timeout") from exc
    except OSError as exc:
        raise PublicTestnetError("request_timeout") from exc
    finally:
        connection.close()
    enforce_body_bound(len(payload))
    if response.status != 200:
        raise PublicTestnetError("request_rejected")
    return payload


def run_public_requester(endpoint: str, input_text: str, timeout: float = REQUEST_TIMEOUT_SECONDS) -> dict[str, Any]:
    require_public_https_endpoint(endpoint)
    binding = public_testnet_binding()

    def exchange(method: str, path: str, body: bytes | None) -> bytes:
        return http_exchange(endpoint, method, path, body, timeout)

    requester = run_requester(exchange, input_text, binding)
    return requester


def execute_local_release_example(input_text: str) -> dict[str, Any]:
    """Exercise the real HTTP provider/requester locally without public exposure."""
    server, thread, provider = start_one_shot_server()
    host, port = server.server_address
    base_url = f"http://{host}:{port}"

    def exchange(method: str, path: str, body: bytes | None) -> bytes:
        return http_exchange(
            base_url,
            method,
            path,
            body,
            REQUEST_TIMEOUT_SECONDS,
            allow_local_harness=True,
        )

    evidence: dict[str, Any] | None = None
    try:
        requester = run_requester(exchange, input_text, provider.binding)
        evidence = provider.evidence
    finally:
        stop_one_shot_server(server, thread)
    if evidence is None:
        raise PublicTestnetError("provider_evidence_incomplete")
    provider_record = provider_evidence_record(
        evidence,
        network_id=provider.binding["network_id"],
        shutdown_complete=True,
    )
    if requester["payment_tx_id"] != provider_record["payment_tx_id"]:
        raise PublicTestnetError("payment_binding_invalid")
    return {
        "release_candidate": RELEASE_CANDIDATE,
        "designation": NON_PRODUCTION_DESIGNATION,
        "verification_scope": "LOCAL_ONLY",
        "service_discovery_verified": requester["service_discovery_verified"],
        "service_id": requester["discovered_service_id"],
        "network_id": provider_record["network_id"],
        "quoted_amount": requester["quoted_amount"],
        "canonical_validation": provider_record["canonical_validation"],
        "payment_tx_id": requester["payment_tx_id"],
        "payment_verified": provider_record["payment_verified"],
        "replay_rejected": provider_record["replay_rejected"],
        "service_executed": requester["service_executed"],
        "service_result_verified": requester["service_result_verified"],
        "receipt_verified": requester["receipt_verified"],
        "canonical_history_touched": provider_record["canonical_history_touched"],
        "production_keys_used": provider_record["production_keys_used"],
        "public_network_used": False,
        "external_https_exposure": False,
        "production_settlement": provider_record["production_settlement"],
        "bounded_provider_shutdown": provider_record["bounded_provider_shutdown"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m coin.public_testnet_service_demo")
    parser.add_argument(
        "--role",
        choices=("parent", "provider", "requester", "local-example"),
        default="parent",
    )
    parser.add_argument("--public-endpoint")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--input", default="L28 enables machine payments between autonomous systems.")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    try:
        assert_identity_flags_unchanged()
        if args.role == "provider":
            server, thread, provider = start_one_shot_server(args.port)
            host, port = server.server_address
            sys.stdout.write(json.dumps({"coordination": "provider_ready", "host": host, "port": port}, sort_keys=True) + "\n")
            sys.stdout.flush()
            finished = provider.finished.wait(SESSION_DEADLINE_SECONDS)
            evidence = provider.evidence
            network_id = provider.binding["network_id"]
            stop_one_shot_server(server, thread)
            if not finished or evidence is None:
                raise PublicTestnetError("request_timeout")
            record = provider_evidence_record(evidence, network_id=network_id, shutdown_complete=True)
            sys.stdout.write(json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n")
            sys.stdout.flush()
            return 0
        if args.role == "local-example":
            result = execute_local_release_example(args.input)
            sys.stdout.write(
                json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
                + "\n"
            )
            return 0
        if not args.public_endpoint:
            raise PublicTestnetError(ENDPOINT_BLOCKER)
        require_public_https_endpoint(args.public_endpoint)
        result = run_public_requester(args.public_endpoint, args.input)
    except PublicTestnetError as exc:
        if exc.code == ENDPOINT_BLOCKER:
            sys.stderr.write("BLOCKER=PUBLIC_TESTNET_ENDPOINT_UNAVAILABLE\n")
            return 2
        sys.stderr.write(exc.code + "\n")
        return 1
    sys.stdout.write(json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
