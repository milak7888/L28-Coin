# SPDX-License-Identifier: Apache-2.0
"""One-shot disposable public-testnet purchase over provider-neutral HTTP/JSON.

The frozen slice authorizes this experiment only. Identity-module runtime,
network, testnet-start, signing, mining, broadcast, and settlement flags stay
false. The provider listens on loopback so an already-available public HTTPS
ingress can forward one transaction. The explicitly selected local-example is
LOCAL_ONLY product evidence, never public reachability. Private keys stay in
the owning process and are not serialized.
"""

from __future__ import annotations

import argparse
import hashlib
import http.client
import ipaddress
import json
import os
import selectors
import socket
import subprocess
import sys
import threading
import time
import urllib.parse
from collections.abc import Mapping
from http.server import BaseHTTPRequestHandler, HTTPServer, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from coin.disposable_offline_transfer_demo import (
    DEMO_TIMESTAMP,
    TRANSFER_AMOUNT,
    _public_key_hex,
    build_signed_transfer,
    public_identity,
    verify_transfer_signature,
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
    SERVICE_IDS,
    SUMMARY_SERVICE_ID,
    DemoError as ServiceDemoError,
    _perform_paid_service,
    _sign_domain,
    _verify_domain,
    build_payment_authorization,
    build_service_quote,
    build_service_receipt,
    build_service_request,
    build_service_result,
    verify_payment_intent_binding,
    verify_service_quote,
    verify_service_receipt,
    verify_service_request,
    verify_service_result,
)
from coin.tx_validation import TxPolicy, validate_transaction


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


def build_service_discovery(binding: Mapping[str, Any], *, service_id: str = SERVICE_ID,
                            private_pilot: bool = False) -> dict[str, Any]:
    """Return the exact public catalog without advancing the one-shot session."""
    assert_identity_flags_unchanged()
    if service_id not in SERVICE_IDS:
        raise PublicTestnetError("service_invalid")
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
            "external_https_required": not private_pilot,
            "max_body_bytes": MAX_BODY_BYTES,
            "request_timeout_seconds": int(REQUEST_TIMEOUT_SECONDS),
            "session_deadline_seconds": int(SESSION_DEADLINE_SECONDS),
        },
        "services": [
            {
                "service_id": service_id,
                "asset_id": ASSET_ID,
                "price": PRICE_L28,
                "max_input_chars": MAX_INPUT_CHARS,
                "one_shot": True,
            }
        ],
        "production_authority": False,
    }


def validate_service_discovery(body: bytes, binding: Mapping[str, Any], *, service_id: str = SERVICE_ID,
                               private_pilot: bool = False) -> dict[str, Any]:
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
    expected = build_service_discovery(binding, service_id=service_id, private_pilot=private_pilot)
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
    def __init__(self, *, service_id: str = SERVICE_ID) -> None:
        if service_id not in SERVICE_IDS:
            raise PublicTestnetError("service_invalid")
        self.service_id = service_id
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
        verified = verify_service_request(request, service_id=self.service_id)
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
        # Validate against the existing read-only disposable opening fixture before
        # opening/persisting a ledger. Rejected payment must create no state/work.
        verify_payment_intent_binding(request=self._request, quote=self._quote,
                                      payment_tx=payment_tx, payment_authorization=authorization)
        accepted, checked_id, reason = validate_transaction(
            payment_tx, policy=TxPolicy(require_signatures=True),
            current_balance_lookup=lambda identity, _network: 100 if identity == self._request["payer_identity"] else 0,
            seen_tx_lookup=lambda _tx_id: False, verify_signature=verify_transfer_signature,
            now_ts=DEMO_TIMESTAMP,
        )
        if not accepted or reason != "ok" or checked_id != payment_tx.get("id"):
            raise PublicTestnetError("canonical_validation_failed")
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
        output = _perform_paid_service(self._request["input"]["text"], payment_verified=True, service_id=self.service_id)
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


def verify_purchase_artifacts(
    artifacts: Mapping[str, Any], *, input_text: str, service_id: str = SERVICE_ID,
) -> dict[str, Any]:
    """Public verification of delivery, not proof of canonical settlement/finality."""
    fields = {"request", "quote", "payment_tx", "payment_authorization", "service_result", "receipt"}
    if not isinstance(artifacts, dict) or set(artifacts) != fields or any(not isinstance(artifacts[key], dict) for key in fields):
        raise PublicTestnetError("purchase_artifacts_invalid")
    request, quote, payment = artifacts["request"], artifacts["quote"], artifacts["payment_tx"]
    verified = verify_service_request(request, service_id=service_id)
    if verified["input"] != {"text": input_text}:
        raise PublicTestnetError("input_binding_invalid")
    verify_service_quote(quote, request=request)
    verify_payment_intent_binding(request=request, quote=quote, payment_tx=payment, payment_authorization=artifacts["payment_authorization"])
    if not verify_transfer_signature(payment):
        raise PublicTestnetError("payment_signature_invalid")
    result, receipt = artifacts["service_result"], artifacts["receipt"]
    verify_service_result(result, request=request, quote=quote, payment_tx_id=payment["id"])
    verify_service_receipt(receipt, request=request, quote=quote, service_result=result, payment_tx_id=payment["id"])
    return dict(result["output"])


def run_requester(exchange: Any, input_text: str, binding: Mapping[str, Any], *, service_id: str = SERVICE_ID,
                  payer_key: Ed25519PrivateKey | None = None, private_pilot: bool = False) -> dict[str, Any]:
    discovery_body = exchange("GET", DISCOVERY_PATH, None)
    discovery = validate_service_discovery(discovery_body, binding, service_id=service_id, private_pilot=private_pilot)
    service = discovery["services"][0]
    payer = payer_key if payer_key is not None else Ed25519PrivateKey.generate()
    hello_body = exchange("GET", HELLO_PATH, None)
    hello_frame = parse_frame(hello_body, expected_sequence=1, binding=binding)
    hello = verify_provider_hello(hello_frame["payload"])
    request = build_service_request(payer, provider_identity=hello["provider_identity"], input_text=input_text, service_id=service_id)
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
    artifacts = {"request": request, "quote": quote, "payment_tx": payment_tx,
                 "payment_authorization": authorization, "service_result": service_result, "receipt": receipt}
    output = verify_purchase_artifacts(artifacts, input_text=input_text, service_id=service_id)
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
        "service_output": output,
        "public_artifacts": artifacts,
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


PILOT_PROFILE = "l28-remote-paid-service-pilot/v0.1"
PILOT_DOMAIN = b"L28-REMOTE-PAID-SERVICE-PILOT-V0.1\x00"
PILOT_PAYMENT_NETWORK = "DISPOSABLE_OFFLINE"
PILOT_SOURCE_FILES = (
    "coin/public_testnet_service_demo.py", "coin/durable_restart_safe_service_demo.py",
    "coin/two_agent_service_transaction_demo.py", "coin/disposable_offline_transfer_demo.py",
    "coin/limited_testnet_service_demo.py", "coin/disposable_testnet_identity.py",
    "coin/tx_validation.py", "coin/ledger.py",
    "coin/uaii_json.py", "coin/__init__.py",
)


def pilot_source_digest() -> str:
    root = Path(__file__).resolve().parents[1]
    inventory = [(name, hashlib.sha256((root / name).read_bytes()).hexdigest()) for name in PILOT_SOURCE_FILES]
    return hashlib.sha256(_pilot_bytes(inventory)).hexdigest()


def _pilot_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")


def _pilot_json(body: bytes) -> dict[str, Any]:
    enforce_body_bound(len(body))
    try:
        value = json.loads(body.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys,
                           parse_constant=lambda _value: (_ for _ in ()).throw(ValueError()))
        from coin.durable_restart_safe_service_demo import _walk_bounded
        _walk_bounded(value, 0, [0])
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise PublicTestnetError("malformed_json") from exc
    if not isinstance(value, dict):
        raise PublicTestnetError("malformed_json")
    return value


def pilot_config(*, session_id: str, provider_host: str, requester_host: str, port: int,
                 created_at: int, route_keys: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Public configuration only. A route declaration is NOT route verification."""
    return validate_pilot_config({
        "profile": PILOT_PROFILE, "session_id": session_id,
        "provider_host": provider_host, "requester_host": requester_host, "port": port,
        "created_at": created_at, "expires_at": created_at + 120,
        "service_id": SUMMARY_SERVICE_ID, "price": PRICE_L28,
        "network_id": NETWORK_ID, "payment_network_id": PILOT_PAYMENT_NETWORK,
        "source_digest": pilot_source_digest(), "route_keys": dict(route_keys or {}),
    })


def validate_pilot_config(value: Any) -> dict[str, Any]:
    fields = ("profile", "session_id", "provider_host", "requester_host", "port", "created_at",
              "expires_at", "service_id", "price", "network_id", "payment_network_id", "source_digest", "route_keys")
    if not isinstance(value, dict) or set(value) != set(fields):
        raise PublicTestnetError("pilot_config_invalid")
    result = {name: value[name] for name in fields}
    session = result["session_id"]
    if not isinstance(session, str) or len(session) != 32 or any(c not in "0123456789abcdef" for c in session):
        raise PublicTestnetError("pilot_session_invalid")
    for name in ("provider_host", "requester_host"):
        try:
            address = ipaddress.IPv4Address(result[name])
        except (ValueError, TypeError, ipaddress.AddressValueError) as exc:
            raise PublicTestnetError("pilot_endpoint_invalid") from exc
        if str(address) != result[name] or not (str(address) == LOOPBACK_HOST or address in ipaddress.IPv4Network("100.64.0.0/10")):
            raise PublicTestnetError("pilot_endpoint_invalid")
    loopback = result["provider_host"] == result["requester_host"] == LOOPBACK_HOST
    keys = result["route_keys"]
    if not loopback:
        if result["provider_host"] == result["requester_host"] or LOOPBACK_HOST in (result["provider_host"], result["requester_host"]):
            raise PublicTestnetError("pilot_endpoint_invalid")
        if not isinstance(keys, dict) or set(keys) != {"provider", "requester"}:
            raise PublicTestnetError("private_route_identity_required")
        if any(not isinstance(k, str) or not k.startswith("nodekey:") or len(k) != 72 or
               any(c not in "0123456789abcdef" for c in k[8:]) for k in keys.values()) or len(set(keys.values())) != 2:
            raise PublicTestnetError("private_route_identity_required")
    elif keys != {}:
        raise PublicTestnetError("pilot_config_invalid")
    if not loopback:
        result["route_keys"] = {role: keys[role] for role in ("provider", "requester")}
    if (type(result["port"]) is not int or not 1024 <= result["port"] <= 65535 or
        type(result["created_at"]) is not int or type(result["expires_at"]) is not int or
        not 0 < result["expires_at"] - result["created_at"] <= 120 or
        result["created_at"] > time.time() + 5 or result["expires_at"] <= time.time()):
        raise PublicTestnetError("pilot_session_expired")
    for name, expected in (("profile", PILOT_PROFILE), ("service_id", SUMMARY_SERVICE_ID),
                           ("network_id", NETWORK_ID), ("payment_network_id", PILOT_PAYMENT_NETWORK),
                           ("source_digest", pilot_source_digest())):
        if result[name] != expected:
            raise PublicTestnetError("pilot_binding_invalid")
    if type(result["price"]) is not int or result["price"] != PRICE_L28:
        raise PublicTestnetError("wrong_amount")
    return result


def verify_pilot_route(config: Mapping[str, Any], role: str) -> None:
    """Verify installed Tailscale's live local and peer device identities, not an ack.

    This read is performed only on an explicitly authorized future private run.
    Operator verification of account/device ownership and topology is still required.
    """
    if config["provider_host"] == config["requester_host"] == LOOPBACK_HOST:
        return
    other = "requester" if role == "provider" else "provider"
    try:
        completed = subprocess.run(["tailscale", "status", "--json"], capture_output=True, timeout=5, check=True)
        if len(completed.stdout) > 1048576:
            raise ValueError()
        status = json.loads(completed.stdout)
        local = status["Self"]
        peers = list(status["Peer"].values())
        matches = [p for p in peers if p.get("PublicKey") == config["route_keys"][other]]
        if (status["BackendState"] != "Running" or local.get("PublicKey") != config["route_keys"][role] or
            config[role + "_host"] not in local.get("TailscaleIPs", []) or len(matches) != 1 or
            matches[0].get("Online") is not True or config[other + "_host"] not in matches[0].get("TailscaleIPs", [])):
            raise ValueError()
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        raise PublicTestnetError("private_route_not_verified") from exc


def _pilot_context(config: Mapping[str, Any]) -> str:
    return hashlib.sha256(PILOT_DOMAIN + _pilot_bytes(config)).hexdigest()


def pilot_envelope(key: Ed25519PrivateKey, config: Mapping[str, Any], role: str, peer: str,
                   method: str, path: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    body = {"context": _pilot_context(config), "role": role, "public_key": _public_key_hex(key),
            "peer": peer, "method": method, "path": path, "payload": dict(payload)}
    return {**body, "signature": _sign_domain(key, PILOT_DOMAIN, body)}


def verify_pilot_envelope(value: Any, config: Mapping[str, Any], role: str, peer: str,
                          method: str, path: str, *, public_key: str | None = None) -> dict[str, Any]:
    validate_pilot_config(dict(config))
    fields = ("context", "role", "public_key", "peer", "method", "path", "payload", "signature")
    if not isinstance(value, dict) or tuple(value) != fields or not isinstance(value["payload"], dict):
        raise PublicTestnetError("pilot_envelope_invalid")
    if (value["context"] != _pilot_context(config) or value["role"] != role or value["peer"] != peer or
        value["method"] != method or value["path"] != path or
        (public_key is not None and value["public_key"] != public_key)):
        raise PublicTestnetError("pilot_peer_or_context_invalid")
    _verify_domain(domain=PILOT_DOMAIN, body={k: value[k] for k in fields[:-1]},
                   public_key_hex=value["public_key"], signature_hex=value["signature"])
    return value["payload"]


class PrivatePilotProvider(PublicProvider):
    """One purchase per context; the existing durable store remains sole payment authority."""
    def __init__(self, config: Mapping[str, Any], state_dir: str | Path) -> None:
        from coin.durable_restart_safe_service_demo import DurableProvider
        self.config = validate_pilot_config(dict(config))
        self.backend = DurableProvider(state_dir, service_id=SUMMARY_SERVICE_ID, context_digest=_pilot_context(self.config))
        self.binding = public_testnet_binding()
        self.service_id = SUMMARY_SERVICE_ID
        self._key = self.backend._key
        self.public_key, self.identity = self.backend.public_key, self.backend.identity
        self.finished = threading.Event()
        self._lock = threading.Lock()
        self.expected = 1
        self.client_key: str | None = None
        self._request = self._quote = None
        self.evidence = None
        self.purchase_evidence = None
        self.deadline = time.monotonic() + min(115, self.config["expires_at"] - time.time())

    def close(self) -> None:
        self.backend.close()
        self._key = None

    def dispatch(self, method: str, path: str, body: bytes | None) -> dict[str, Any]:
        with self._lock:
            validate_pilot_config(self.config)
            if self.finished.is_set() or time.monotonic() >= self.deadline:
                raise PublicTestnetError("pilot_session_expired")
            if method == "GET" and path == DISCOVERY_PATH and self.expected == 1:
                payload = build_service_discovery(self.binding, service_id=self.service_id, private_pilot=True)
                peer = ""
            elif method == "GET" and path == HELLO_PATH and self.expected == 1:
                payload = json.loads(frame_bytes("provider_hello", 1, self.backend.hello(), self.binding))
                self.expected = 2
                peer = ""
            elif method == "POST" and path == SESSION_PATH:
                envelope = _pilot_json(body or b"")
                payload = verify_pilot_envelope(envelope, self.config, "requester", self.public_key, method, path,
                                                public_key=self.client_key)
                candidate_key = envelope["public_key"]
                if set(payload) == {"action", "artifacts"} and payload["action"] == "replay":
                    artifacts = payload["artifacts"]
                    if not isinstance(artifacts, dict) or set(artifacts) != {
                        "request", "quote", "payment_tx", "payment_authorization", "service_result", "receipt"
                    } or not isinstance(artifacts["payment_tx"], dict) or not isinstance(artifacts["payment_tx"].get("id"), str):
                        raise PublicTestnetError("purchase_artifacts_invalid")
                    if artifacts["payment_tx"]["id"] not in self.backend.store.snapshot()["accepted"]:
                        raise PublicTestnetError("unknown_payment")
                    # A payment replay probe must never recompute useful work,
                    # even as a side effect of result verification. The requester
                    # independently verifies result/receipt; this endpoint checks
                    # only the original accepted public payment proof.
                    package = {name: artifacts[name] for name in ("request", "quote", "payment_tx", "payment_authorization")}
                    verify_service_request(package["request"], service_id=self.service_id)
                    verify_payment_intent_binding(request=package["request"], quote=package["quote"],
                        payment_tx=package["payment_tx"], payment_authorization=package["payment_authorization"])
                    if not verify_transfer_signature(package["payment_tx"]):
                        raise PublicTestnetError("payment_signature_invalid")
                    payload = self.backend.handle_payment(package)
                elif payload == {"action": "finish"} and self.evidence is not None:
                    payload = {"finished": True}
                    self.finished.set()
                else:
                    frame = parse_frame(_pilot_bytes(payload), expected_sequence=self.expected, binding=self.binding)
                    if frame["message_type"] == "service_request":
                        request = frame["payload"]
                        if request.get("payer_public_key") != candidate_key:
                            raise PublicTestnetError("pilot_payer_mismatch")
                        if self.backend.store.snapshot()["state_version"] != 0:
                            raise PublicTestnetError("pilot_purchase_already_accepted")
                        quote = self.backend.quote_for(request)
                        self._request, self._quote = request, quote
                        self.client_key = candidate_key
                        self.expected = 4
                        payload = json.loads(frame_bytes("service_quote", 3, quote, self.binding))
                    elif frame["message_type"] == "payment_package" and self._request is not None:
                        if set(frame["payload"]) != {"payment_tx", "payment_authorization"}:
                            raise PublicTestnetError("unexpected_field")
                        result = self.backend.handle_payment({"request": self._request, "quote": self._quote, **frame["payload"]})
                        if not result["ok"]:
                            raise PublicTestnetError(result["error"])
                        self.evidence = result["evidence"]
                        self.purchase_evidence = result["evidence"]
                        self.expected = 0
                        payload = json.loads(frame_bytes("service_result_package", 5,
                            {"service_result": result["service_result"], "receipt": result["receipt"]}, self.binding))
                    else:
                        raise PublicTestnetError("wrong_sequence")
                peer = candidate_key
                if payload.get("error") == "replay":
                    self.evidence = payload["evidence"]
                    self.client_key = candidate_key
            else:
                raise PublicTestnetError("wrong_sequence")
            return pilot_envelope(self._key, self.config, "provider", peer, method, path, payload)


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server: "_Server"

    def log_message(self, _format: str, *_args: Any) -> None:
        return

    def handle(self) -> None:
        remaining = REQUEST_TIMEOUT_SECONDS
        if isinstance(self.server.provider, PrivatePilotProvider):
            remaining = min(remaining, max(0.001, self.server.provider.deadline - time.monotonic()))
        self.request.settimeout(remaining)
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
        if isinstance(self.server.provider, PrivatePilotProvider) and (
            self.headers.get("Transfer-Encoding") is not None or len(self.headers.get_all("Content-Length", [])) != 1
        ):
            raise PublicTestnetError("malformed_http")
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
        if isinstance(self.server.provider, PrivatePilotProvider):
            self._pilot_dispatch("GET")
            return
        if self.path == DISCOVERY_PATH:
            try:
                self._ok(build_service_discovery(self.server.provider.binding, service_id=self.server.provider.service_id))
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
        if isinstance(self.server.provider, PrivatePilotProvider):
            self._pilot_dispatch("POST")
            return
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
        except (TypeError, ValueError, KeyError):
            self._error("malformed_json")

    def _pilot_dispatch(self, method: str) -> None:
        from coin.durable_restart_safe_service_demo import DurableRuntimeError
        try:
            if method == "GET" and (self.headers.get("Transfer-Encoding") is not None or self.headers.get("Content-Length", "0") != "0"):
                raise PublicTestnetError("malformed_http")
            body = self._read_body() if method == "POST" else None
            self._ok(self.server.provider.dispatch(method, self.path, body))
        except (PublicTestnetError, ServiceDemoError, DurableRuntimeError) as exc:
            self._error(exc.code)
        except (TypeError, ValueError, KeyError, RecursionError):
            self._error("malformed_json")
        self.close_connection = True


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


class _PilotServer(_Server):
    """Same HTTP handler, serial bounded requests, exact configured bind/source."""
    # Permit genuine restart on the same exact endpoint after TCP TIME_WAIT.
    # SO_REUSEPORT is not enabled; an existing listener still prevents a bind.
    allow_reuse_address = True
    def __init__(self, provider: PrivatePilotProvider) -> None:
        self.provider = provider
        self.request_count = 0
        self.active_request: socket.socket | None = None
        HTTPServer.__init__(self, (provider.config["provider_host"], provider.config["port"]), _Handler)

    def process_request(self, request: Any, client_address: Any) -> None:
        self.active_request = request
        try:
            HTTPServer.process_request(self, request, client_address)
        finally:
            self.active_request = None

    def verify_request(self, request: Any, client_address: Any) -> bool:
        self.request_count += 1
        return (self.request_count <= 24 and client_address[0] == self.provider.config["requester_host"] and
                time.monotonic() < self.provider.deadline)


def pilot_http_exchange(config: Mapping[str, Any], method: str, path: str, body: bytes | None) -> bytes:
    validate_pilot_config(dict(config))
    remaining = config["expires_at"] - time.time()
    connection = http.client.HTTPConnection(config["provider_host"], config["port"],
        timeout=min(REQUEST_TIMEOUT_SECONDS, remaining), source_address=(config["requester_host"], 0))
    expired = threading.Event()
    transport: list[socket.socket | None] = [None]

    def expire() -> None:
        expired.set()
        if transport[0] is not None:
            try:
                transport[0].shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

    # Socket timeout alone is an inactivity timeout: slow chunks must not reset
    # the request budget. Interrupt the owned socket at this absolute deadline.
    watchdog = threading.Timer(min(REQUEST_TIMEOUT_SECONDS, remaining), expire)
    watchdog.daemon = True
    watchdog.start()
    try:
        connection.connect()
        transport[0] = connection.sock
        if expired.is_set():
            raise PublicTestnetError("pilot_request_timeout")
        if connection.sock.getpeername()[0] != config["provider_host"] or connection.sock.getsockname()[0] != config["requester_host"]:
            raise PublicTestnetError("pilot_endpoint_invalid")
        connection.request(method, path, body=body, headers={"Content-Type": "application/json", "Content-Length": str(len(body or b""))})
        response = connection.getresponse()
        result = response.read(MAX_BODY_BYTES + 1)
        if expired.is_set():
            raise PublicTestnetError("pilot_request_timeout")
        enforce_body_bound(len(result))
        if response.status != 200:
            error = _pilot_json(result).get("error", "request_rejected")
            raise PublicTestnetError(error if isinstance(error, str) else "request_rejected")
        return result
    except (OSError, http.client.HTTPException) as exc:
        raise PublicTestnetError("pilot_request_timeout" if expired.is_set() else "pilot_connection_failed") from exc
    finally:
        watchdog.cancel()
        watchdog.join(timeout=1)
        connection.close()


def run_pilot_requester(config: Mapping[str, Any], input_text: str, *, replay_artifacts: dict[str, Any] | None = None) -> dict[str, Any]:
    config = validate_pilot_config(dict(config))
    verify_pilot_route(config, "requester")
    payer = Ed25519PrivateKey.generate()
    payer_public = _public_key_hex(payer)
    provider_public: str | None = None
    transcript: list[dict[str, Any]] = []

    def exchange(method: str, path: str, body: bytes | None) -> bytes:
        nonlocal provider_public
        request_envelope = None if body is None else pilot_envelope(payer, config, "requester", provider_public or "", method, path, _pilot_json(body))
        message = None if request_envelope is None else _pilot_bytes(request_envelope)
        envelope = _pilot_json(pilot_http_exchange(config, method, path, message))
        payload = verify_pilot_envelope(envelope, config, "provider", "" if method == "GET" else payer_public,
                                        method, path, public_key=provider_public)
        if provider_public is None:
            provider_public = envelope["public_key"]
        if path == HELLO_PATH and payload.get("payload") != {"provider_identity": public_identity(provider_public), "provider_public_key": provider_public}:
            raise PublicTestnetError("pilot_peer_or_context_invalid")
        transcript.append({"request": request_envelope, "response": envelope})
        return _pilot_bytes(payload)

    try:
        if replay_artifacts is None:
            result = run_requester(exchange, input_text, public_testnet_binding(), service_id=SUMMARY_SERVICE_ID,
                                   payer_key=payer, private_pilot=True)
            artifacts = result["public_artifacts"]
        else:
            # Restart keys are fresh; old public signed artifacts are verification
            # data, never authority to re-execute work or re-debit the payer.
            validate_service_discovery(exchange("GET", DISCOVERY_PATH, None), public_testnet_binding(),
                                       service_id=SUMMARY_SERVICE_ID, private_pilot=True)
            artifacts = replay_artifacts
            verify_purchase_artifacts(artifacts, input_text=input_text, service_id=SUMMARY_SERVICE_ID)
            result = {"public_artifacts": artifacts, "restart_replay_only": True}
        replay = _pilot_json(exchange("POST", SESSION_PATH, _pilot_bytes({"action": "replay", "artifacts": artifacts})))
        if replay.get("ok") is not False or replay.get("error") != "replay" or replay["evidence"]["payment_applied"] is not False or replay["evidence"]["service_executed"] is not False:
            raise PublicTestnetError("replay_not_rejected")
        if (replay["evidence"]["requester_balance_after"], replay["evidence"]["provider_balance_after"]) != (72, 28):
            raise PublicTestnetError("payment_binding_invalid")
        finish = _pilot_json(exchange("POST", SESSION_PATH, _pilot_bytes({"action": "finish"})))
        if finish != {"finished": True}:
            raise PublicTestnetError("pilot_finish_failed")
        return {**result, "pilot_profile": PILOT_PROFILE, "session_id": config["session_id"],
                "context_digest": _pilot_context(config), "source_digest": config["source_digest"],
                "public_config": config, "signed_http_transcript": transcript,
                "replay": replay["evidence"], "issued_supply": 0, "mint_height": 0,
                "transport_scope": "LOOPBACK" if config["provider_host"] == LOOPBACK_HOST else "VERIFIED_PRIVATE_ROUTE",
                "physical_remote_verified": False, "production_settlement": False}
    finally:
        payer = None


def run_pilot_provider(config: Mapping[str, Any], state_dir: str | Path) -> dict[str, Any]:
    config = validate_pilot_config(dict(config))
    verify_pilot_route(config, "provider")
    provider = PrivatePilotProvider(config, state_dir)
    server = None
    thread = None
    try:
        server = _PilotServer(provider)
        thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
        thread.start()
        print(json.dumps({"coordination": "pilot_provider_ready", "pid": os.getpid(),
                          "context_digest": _pilot_context(config), "source_digest": pilot_source_digest()}), flush=True)
        if not provider.finished.wait(max(0, provider.deadline - time.monotonic())) or provider.evidence is None:
            raise PublicTestnetError("pilot_session_expired")
        snapshot = provider.backend.store.snapshot()
        public_state = {k: v for k, v in snapshot.items() if k != "restart_generation"}
        return {"coordination": "pilot_provider_evidence", "pid": os.getpid(), "evidence": provider.evidence,
                "purchase_evidence": provider.purchase_evidence,
                "state": public_state, "state_commitment": hashlib.sha256(json.dumps(public_state, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
                "context_digest": _pilot_context(config), "source_digest": pilot_source_digest(),
                "listener_closed": True, "physical_remote_verified": False}
    finally:
        if server is not None:
            if server.active_request is not None:
                try:
                    server.active_request.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
            server.shutdown()
            server.server_close()
        if thread is not None:
            thread.join(timeout=REQUEST_TIMEOUT_SECONDS + 1)
        provider.close()


def start_one_shot_server(port: int = 0, *, service_id: str = SERVICE_ID) -> tuple[_Server, threading.Thread, PublicProvider]:
    provider = PublicProvider(service_id=service_id)
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
    if allow_local_harness and (parsed.scheme != "http" or host != LOOPBACK_HOST or parsed.username or parsed.password):
        raise PublicTestnetError("local_endpoint_invalid")
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
    except (TimeoutError, socket.timeout, http.client.HTTPException) as exc:
        raise PublicTestnetError("request_timeout") from exc
    except OSError as exc:
        raise PublicTestnetError("request_timeout") from exc
    finally:
        connection.close()
    enforce_body_bound(len(payload))
    if response.status != 200:
        raise PublicTestnetError("request_rejected")
    return payload


def run_public_requester(endpoint: str, input_text: str, timeout: float = REQUEST_TIMEOUT_SECONDS, *, service_id: str = SERVICE_ID) -> dict[str, Any]:
    require_public_https_endpoint(endpoint)
    binding = public_testnet_binding()

    def exchange(method: str, path: str, body: bytes | None) -> bytes:
        return http_exchange(endpoint, method, path, body, timeout)

    requester = run_requester(exchange, input_text, binding, service_id=service_id)
    return requester


def execute_local_release_example(input_text: str, *, service_id: str = SERVICE_ID) -> dict[str, Any]:
    """Requester here, provider in a fresh process; real IPv4-loopback HTTP only."""
    if service_id not in SERVICE_IDS:
        raise PublicTestnetError("service_invalid")
    # Leave five seconds within the 120-second invocation for failure cleanup.
    deadline = time.monotonic() + SESSION_DEADLINE_SECONDS - 5
    try:
        process = subprocess.Popen(
            [sys.executable, "-m", "coin.public_testnet_service_demo", "--role", "provider", "--service-id", service_id],
            cwd=str(Path(__file__).resolve().parents[1]), stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
    except OSError as exc:
        raise PublicTestnetError("provider_start_failed") from exc
    expired = threading.Event()

    def expire() -> None:
        expired.set()
        if process.poll() is None:
            try:
                process.terminate()
            except ProcessLookupError:
                pass

    watchdog = threading.Timer(max(0, deadline - time.monotonic()), expire)
    watchdog.daemon = True
    watchdog.start()
    host, port = LOOPBACK_HOST, 0
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ)
            if not selector.select(max(0, deadline - time.monotonic())):
                raise PublicTestnetError("provider_start_timeout")
            # Unbuffered bounded reads: a partial/missing newline cannot bypass
            # the startup deadline by blocking TextIO.readline().
            ready_bytes = bytearray()
            while b"\n" not in ready_bytes:
                chunk = os.read(process.stdout.fileno(), 1)
                if not chunk or len(ready_bytes) >= MAX_BODY_BYTES:
                    raise PublicTestnetError("provider_coordination_invalid")
                ready_bytes.extend(chunk)
                if b"\n" not in ready_bytes and not selector.select(max(0, deadline - time.monotonic())):
                    raise PublicTestnetError("provider_start_timeout")
            ready = json.loads(ready_bytes)
        if not isinstance(ready, dict):
            raise PublicTestnetError("provider_coordination_invalid")
        port = ready.get("port")
        if ready.get("coordination") != "provider_ready" or ready.get("host") != host or type(port) is not int or not 0 < port < 65536:
            raise PublicTestnetError("provider_coordination_invalid")

        def exchange(method: str, path: str, body: bytes | None) -> bytes:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise PublicTestnetError("request_timeout")
            return http_exchange(f"http://{host}:{port}", method, path, body,
                                 min(REQUEST_TIMEOUT_SECONDS, remaining), allow_local_harness=True)

        requester = run_requester(exchange, input_text, public_testnet_binding(), service_id=service_id)
        output, diagnostics = process.communicate(timeout=max(0.01, deadline - time.monotonic()))
        if process.returncode != 0:
            raise PublicTestnetError("provider_failed")
        provider_record = json.loads(output)
        if provider_record.get("coordination") != "provider_evidence":
            raise PublicTestnetError("provider_evidence_incomplete")
        sys.stderr.write(diagnostics)
    except (PublicTestnetError, ServiceDemoError, LimitedTestnetError) as exc:
        if expired.is_set():
            raise PublicTestnetError("invocation_timeout") from exc
        raise
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        raise PublicTestnetError("invocation_timeout" if expired.is_set() else "local_product_failed") from exc
    finally:
        watchdog.cancel()
        watchdog.join(timeout=1)
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2)
        for pipe in (process.stdout, process.stderr):
            if pipe is not None:
                pipe.close()
    if expired.is_set():
        raise PublicTestnetError("invocation_timeout")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.settimeout(0.2)
        if probe.connect_ex((host, port)) == 0:
            raise PublicTestnetError("listener_cleanup_failed")
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
        "service_output": requester["service_output"],
        "public_artifacts": requester["public_artifacts"],
        "requester_pid": os.getpid(),
        "provider_pid": process.pid,
        "provider_exit": process.returncode,
        "listener_closed": True,
        "requester_balance_before": provider_record["requester_balance_before"],
        "requester_balance_after": provider_record["requester_balance_after"],
        "provider_balance_before": provider_record["provider_balance_before"],
        "provider_balance_after": provider_record["provider_balance_after"],
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
        choices=("parent", "provider", "requester", "local-example", "pilot-config", "pilot-runtime-check"),
        default="parent",
    )
    parser.add_argument("--public-endpoint")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--service-id", choices=SERVICE_IDS, default=SERVICE_ID)
    parser.add_argument("--input", default="L28 enables machine payments between autonomous systems.")
    parser.add_argument("--private-pilot", action="store_true")
    parser.add_argument("--pilot-config", type=Path)
    parser.add_argument("--state-dir", type=Path)
    parser.add_argument("--replay-artifacts", type=Path)
    parser.add_argument("--pilot-session")
    parser.add_argument("--provider-host", default=LOOPBACK_HOST)
    parser.add_argument("--requester-host", default=LOOPBACK_HOST)
    parser.add_argument("--provider-node-key")
    parser.add_argument("--requester-node-key")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    try:
        from coin.durable_restart_safe_service_demo import DurableRuntimeError
        assert_identity_flags_unchanged()
        if args.role == "pilot-runtime-check":
            result = {"status": "RUNTIME_CHECK_PASS", "source_digest": pilot_source_digest(), "network_started": False}
            print(json.dumps(result))
            return 0
        if args.role == "pilot-config":
            keys = {} if args.provider_node_key is None and args.requester_node_key is None else {
                "provider": args.provider_node_key, "requester": args.requester_node_key}
            result = pilot_config(session_id=args.pilot_session, provider_host=args.provider_host,
                                  requester_host=args.requester_host, port=args.port, created_at=int(time.time()), route_keys=keys)
            print(_pilot_bytes(result).decode())
            return 0
        if args.private_pilot:
            if args.pilot_config is None or args.role not in {"provider", "requester"} or args.public_endpoint is not None:
                raise PublicTestnetError("pilot_cli_invalid")
            config = validate_pilot_config(_pilot_json(args.pilot_config.read_bytes()))
            if args.role == "provider":
                if args.state_dir is None or args.replay_artifacts is not None:
                    raise PublicTestnetError("pilot_cli_invalid")
                result = run_pilot_provider(config, args.state_dir)
            else:
                if args.state_dir is not None:
                    raise PublicTestnetError("pilot_cli_invalid")
                replay = _pilot_json(args.replay_artifacts.read_bytes()) if args.replay_artifacts else None
                result = run_pilot_requester(config, args.input, replay_artifacts=replay)
            print(_pilot_bytes(result).decode(), flush=True)
            return 0
        if any((args.pilot_config, args.state_dir, args.replay_artifacts, args.pilot_session, args.provider_node_key, args.requester_node_key)):
            raise PublicTestnetError("pilot_cli_invalid")
        if args.role == "provider":
            server, thread, provider = start_one_shot_server(args.port, service_id=args.service_id)
            host, port = server.server_address
            sys.stdout.write(json.dumps({"coordination": "provider_ready", "host": host, "port": port}, sort_keys=True) + "\n")
            sys.stdout.flush()
            try:
                finished = provider.finished.wait(SESSION_DEADLINE_SECONDS)
                evidence = provider.evidence
                network_id = provider.binding["network_id"]
            finally:
                stop_one_shot_server(server, thread)
            if not finished or evidence is None:
                raise PublicTestnetError("request_timeout")
            record = provider_evidence_record(evidence, network_id=network_id, shutdown_complete=True)
            sys.stdout.write(json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n")
            sys.stdout.flush()
            return 0
        if args.role == "local-example":
            result = execute_local_release_example(args.input, service_id=args.service_id)
            sys.stdout.write(
                json.dumps(result, sort_keys=False, separators=(",", ":"), ensure_ascii=False)
                + "\n"
            )
            return 0
        if not args.public_endpoint:
            raise PublicTestnetError(ENDPOINT_BLOCKER)
        require_public_https_endpoint(args.public_endpoint)
        result = run_public_requester(args.public_endpoint, args.input, service_id=args.service_id)
    except (PublicTestnetError, ServiceDemoError, LimitedTestnetError, DurableRuntimeError) as exc:
        if exc.code == ENDPOINT_BLOCKER:
            sys.stderr.write("BLOCKER=PUBLIC_TESTNET_ENDPOINT_UNAVAILABLE\n")
            return 2
        sys.stderr.write(exc.code + "\n")
        return 1
    except (OSError, ValueError, KeyboardInterrupt):
        sys.stderr.write("pilot_io_or_interruption\n")
        return 1
    # Nested artifacts use order-preserving CanonUaii; never sort signed bodies.
    sys.stdout.write(json.dumps(result, sort_keys=False, separators=(",", ":"), ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
