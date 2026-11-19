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
import hmac
import http.client
import ipaddress
import json
import os
import re
import secrets
import selectors
import signal
import socket
import ssl
import stat
import subprocess
import sys
import threading
import time
import urllib.parse
from collections.abc import Mapping
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer, ThreadingHTTPServer
from pathlib import Path, PureWindowsPath
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import load_pem_private_key

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
    QUOTE_SIGN_DOMAIN,
    _digest,
    SERVICE_ID,
    SERVICE_IDS,
    SUMMARY_SERVICE_ID,
    DemoError as ServiceDemoError,
    _perform_paid_service,
    _sign_domain,
    _validate_service_input,
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
# Local-only: two proofs and their duplicated signed result/receipt envelopes.
# HTTP frames still use MAX_BODY_BYTES and the same structural limits.
MAX_REPLAY_BUNDLE_BYTES = 3 * MAX_BODY_BYTES
REQUEST_TIMEOUT_SECONDS = 10.0
SESSION_DEADLINE_SECONDS = 120.0
BETA_PROFILE = "l28-public-disposable-beta/v0.1"
BETA_ORIGIN_TOKEN = "X-L28-Origin-Token"
BETA_SESSION = "X-L28-Beta-Session"
BETA_PAYER = "X-L28-Beta-Payer"
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
                            private_pilot: bool = False, beta: bool = False) -> dict[str, Any]:
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
                "one_shot": not beta,
            }
        ],
        "production_authority": False,
    }


def validate_service_discovery(body: bytes, binding: Mapping[str, Any], *, service_id: str = SERVICE_ID,
                               private_pilot: bool = False, beta: bool = False) -> dict[str, Any]:
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
    expected = build_service_discovery(binding, service_id=service_id, private_pilot=private_pilot, beta=beta)
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
                  payer_key: Ed25519PrivateKey | None = None, private_pilot: bool = False,
                  payment_nonce: int = 100, expected_provider_key: str | None = None,
                  beta: bool = False) -> dict[str, Any]:
    discovery_body = exchange("GET", DISCOVERY_PATH, None)
    discovery = validate_service_discovery(discovery_body, binding, service_id=service_id, private_pilot=private_pilot, beta=beta)
    service = discovery["services"][0]
    payer = payer_key if payer_key is not None else Ed25519PrivateKey.generate()
    hello_body = exchange("GET", HELLO_PATH, None)
    hello_frame = parse_frame(hello_body, expected_sequence=1, binding=binding)
    hello = verify_provider_hello(hello_frame["payload"])
    if expected_provider_key is not None and hello["provider_public_key"] != expected_provider_key:
        raise PublicTestnetError("provider_pin_mismatch")
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
        nonce=payment_nonce,
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
PILOT_REUSE_PROFILE = "l28-limited-private-testnet/v0.1"
PILOT_PURCHASE_NONCES = (100, 101)
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


def _pilot_json(body: bytes, *, purchase_bundle: bool = False) -> dict[str, Any]:
    if purchase_bundle:
        if not 0 < len(body) <= MAX_REPLAY_BUNDLE_BYTES:
            raise PublicTestnetError("oversized_body")
    else:
        enforce_body_bound(len(body))
    try:
        value = json.loads(body.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys,
                           parse_constant=lambda _value: (_ for _ in ()).throw(ValueError()))
        from coin.durable_restart_safe_service_demo import _walk_bounded
        if purchase_bundle:
            if (not isinstance(value, dict) or set(value) != {"purchases"}
                or not isinstance(value["purchases"], list) or len(value["purchases"]) != 2):
                raise PublicTestnetError("purchase_artifacts_invalid")
            # Each original receipt bundle gets the same per-message structural
            # budget. The entire local file still shares the existing byte cap.
            for purchase in value["purchases"]:
                _walk_bounded(purchase, 0, [0])
        else:
            _walk_bounded(value, 0, [0])
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise PublicTestnetError("malformed_json") from exc
    if not isinstance(value, dict):
        raise PublicTestnetError("malformed_json")
    return value


def pilot_config(*, session_id: str, provider_host: str, requester_host: str, port: int,
                 created_at: int, route_keys: Mapping[str, str] | None = None,
                 two_purchases: bool = False) -> dict[str, Any]:
    """Public configuration only. A route declaration is NOT route verification."""
    return validate_pilot_config({
        "profile": PILOT_REUSE_PROFILE if two_purchases else PILOT_PROFILE, "session_id": session_id,
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
    if result["profile"] not in (PILOT_PROFILE, PILOT_REUSE_PROFILE):
        raise PublicTestnetError("pilot_binding_invalid")
    for name, expected in (("service_id", SUMMARY_SERVICE_ID),
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


def _pilot_indexed_payload(payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    index = payload.get("purchase_index")
    message = payload.get("message")
    if set(payload) != {"purchase_index", "message"} or type(index) is not int or index not in (1, 2) or not isinstance(message, dict):
        raise PublicTestnetError("pilot_purchase_index_invalid")
    return index, message


class PrivatePilotProvider(PublicProvider):
    """Bounded purchases; the existing durable store remains sole payment authority."""
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
        self.two_purchases = self.config["profile"] == PILOT_REUSE_PROFILE
        self.purchases: list[dict[str, Any]] = []
        self.replayed_indices: set[int] = set()
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
                index = 1
                if self.two_purchases:
                    index, payload = _pilot_indexed_payload(payload)
                replay_field = "proof" if self.two_purchases else "artifacts"
                if set(payload) == {"action", replay_field} and payload["action"] == "replay":
                    artifacts = payload[replay_field]
                    proof_fields = {"request", "quote", "payment_tx", "payment_authorization"}
                    fields = proof_fields if self.two_purchases else proof_fields | {"service_result", "receipt"}
                    if not isinstance(artifacts, dict) or set(artifacts) != fields or not isinstance(
                        artifacts["payment_tx"], dict
                    ) or not isinstance(artifacts["payment_tx"].get("id"), str):
                        raise PublicTestnetError("purchase_artifacts_invalid")
                    snapshot = self.backend.store.snapshot()
                    record = snapshot["accepted"].get(artifacts["payment_tx"]["id"])
                    if record is None:
                        raise PublicTestnetError("unknown_payment")
                    if self.two_purchases and (
                        snapshot["state_version"] != 2 or record["state_version"] != index
                        or not record["service_executed"] or not record["receipt_id"]
                        or artifacts["payment_tx"].get("nonce") != PILOT_PURCHASE_NONCES[index - 1]
                        or index in self.replayed_indices
                    ):
                        raise PublicTestnetError("pilot_purchase_index_invalid")
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
                    if self.two_purchases:
                        if payload.get("error") != "replay":
                            raise PublicTestnetError("replay_not_rejected")
                        payload["receipt_id"] = record["receipt_id"]
                        self.replayed_indices.add(index)
                elif payload == {"action": "finish"} and self.evidence is not None:
                    if self.two_purchases and (index != 2 or self.replayed_indices != {1, 2}):
                        raise PublicTestnetError("pilot_purchases_incomplete")
                    payload = {"finished": True}
                    self.finished.set()
                else:
                    if self.two_purchases and (
                        self.backend.store.reopened or index != len(self.purchases) + 1
                        or self.backend.store.snapshot()["state_version"] != index - 1
                    ):
                        raise PublicTestnetError("pilot_purchase_index_invalid")
                    frame = parse_frame(_pilot_bytes(payload), expected_sequence=self.expected, binding=self.binding)
                    if frame["message_type"] == "service_request":
                        request = frame["payload"]
                        if request.get("payer_public_key") != candidate_key:
                            raise PublicTestnetError("pilot_payer_mismatch")
                        if not self.two_purchases and self.backend.store.snapshot()["state_version"] != 0:
                            raise PublicTestnetError("pilot_purchase_already_accepted")
                        if self.two_purchases and index == 2 and request.get("input") == self._request["input"]:
                            raise PublicTestnetError("pilot_distinct_inputs_required")
                        quote = self.backend.quote_for(request)
                        self._request, self._quote = request, quote
                        self.client_key = candidate_key
                        self.expected = 4
                        payload = json.loads(frame_bytes("service_quote", 3, quote, self.binding))
                    elif frame["message_type"] == "payment_package" and self._request is not None:
                        if set(frame["payload"]) != {"payment_tx", "payment_authorization"}:
                            raise PublicTestnetError("unexpected_field")
                        if self.two_purchases and frame["payload"]["payment_tx"]["nonce"] != PILOT_PURCHASE_NONCES[index - 1]:
                            raise PublicTestnetError("pilot_purchase_nonce_invalid")
                        result = self.backend.handle_payment({"request": self._request, "quote": self._quote, **frame["payload"]})
                        if not result["ok"]:
                            raise PublicTestnetError(result["error"])
                        self.evidence = result["evidence"]
                        self.purchase_evidence = result["evidence"]
                        if self.two_purchases:
                            self.purchases.append(result["evidence"])
                        self.expected = 1 if self.two_purchases and index == 1 else 0
                        payload = json.loads(frame_bytes("service_result_package", 5,
                            {"service_result": result["service_result"], "receipt": result["receipt"]}, self.binding))
                    else:
                        raise PublicTestnetError("wrong_sequence")
                peer = candidate_key
                if payload.get("error") == "replay":
                    self.evidence = payload["evidence"]
                    self.client_key = candidate_key
                if self.two_purchases:
                    payload = {"purchase_index": index, "message": payload}
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
            if isinstance(self.server, _DeveloperServer):
                self.server.request_guard.check()
            response = self.server.provider.handle_frame(body)
            self._ok(response)
            if self.server.provider.finished.is_set() and not isinstance(self.server, _DeveloperServer):
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


def _verify_reuse_purchase(config: Mapping[str, Any], purchase: Any, index: int, input_text: str) -> dict[str, Any]:
    if not isinstance(purchase, dict) or set(purchase) != {"artifacts", "delivery"}:
        raise PublicTestnetError("purchase_artifacts_invalid")
    artifacts = purchase["artifacts"]
    verify_purchase_artifacts(artifacts, input_text=input_text, service_id=SUMMARY_SERVICE_ID)
    signed = verify_pilot_envelope(
        purchase["delivery"], config, "provider", artifacts["request"]["payer_public_key"],
        "POST", SESSION_PATH, public_key=artifacts["quote"]["provider_public_key"],
    )
    delivered_index, message = _pilot_indexed_payload(signed)
    frame = parse_frame(_pilot_bytes(message), expected_sequence=5, binding=public_testnet_binding())
    if (delivered_index != index or artifacts["payment_tx"]["nonce"] != PILOT_PURCHASE_NONCES[index - 1]
        or frame["message_type"] != "service_result_package"
        or frame["payload"] != {k: artifacts[k] for k in ("service_result", "receipt")}):
        raise PublicTestnetError("purchase_artifacts_invalid")
    return artifacts


def run_pilot_requester(config: Mapping[str, Any], input_text: str, *, replay_artifacts: dict[str, Any] | None = None,
                        second_input: str | None = None) -> dict[str, Any]:
    config = validate_pilot_config(dict(config))
    two_purchases = config["profile"] == PILOT_REUSE_PROFILE
    if two_purchases:
        _validate_service_input(input_text, SUMMARY_SERVICE_ID)
        _validate_service_input(second_input, SUMMARY_SERVICE_ID)
        if input_text == second_input:
            raise PublicTestnetError("pilot_distinct_inputs_required")
    elif second_input is not None:
        raise PublicTestnetError("pilot_cli_invalid")
    verify_pilot_route(config, "requester")
    payer = Ed25519PrivateKey.generate()
    payer_public = _public_key_hex(payer)
    provider_public: str | None = None
    transcript: list[dict[str, Any]] = []
    index = 1

    def exchange(method: str, path: str, body: bytes | None) -> bytes:
        nonlocal provider_public
        request_envelope = None
        if body is not None:
            request = _pilot_json(body)
            if two_purchases:
                request = {"purchase_index": index, "message": request}
            request_envelope = pilot_envelope(payer, config, "requester", provider_public or "", method, path, request)
        message = None if request_envelope is None else _pilot_bytes(request_envelope)
        envelope = _pilot_json(pilot_http_exchange(config, method, path, message))
        payload = verify_pilot_envelope(envelope, config, "provider", "" if method == "GET" else payer_public,
                                        method, path, public_key=provider_public)
        if provider_public is None:
            provider_public = envelope["public_key"]
        if path == HELLO_PATH and payload.get("payload") != {"provider_identity": public_identity(provider_public), "provider_public_key": provider_public}:
            raise PublicTestnetError("pilot_peer_or_context_invalid")
        if two_purchases and method == "POST":
            response_index, payload = _pilot_indexed_payload(payload)
            if response_index != index:
                raise PublicTestnetError("pilot_purchase_index_invalid")
        transcript.append({"request": request_envelope, "response": envelope})
        return _pilot_bytes(payload)

    try:
        if two_purchases:
            inputs = (input_text, second_input)
            if replay_artifacts is None:
                purchases = []
                for index, text in enumerate(inputs, 1):
                    purchase = run_requester(exchange, text, public_testnet_binding(), service_id=SUMMARY_SERVICE_ID,
                                             payer_key=payer, private_pilot=True, payment_nonce=PILOT_PURCHASE_NONCES[index - 1])
                    purchases.append({"artifacts": purchase["public_artifacts"], "delivery": transcript[-1]["response"]})
            else:
                purchases = replay_artifacts.get("purchases")
                if set(replay_artifacts) != {"purchases"} or not isinstance(purchases, list) or len(purchases) != 2:
                    raise PublicTestnetError("purchase_artifacts_invalid")
            verified = [_verify_reuse_purchase(config, purchase, i, text)
                        for i, (purchase, text) in enumerate(zip(purchases, inputs), 1)]
            if replay_artifacts is not None:
                validate_service_discovery(exchange("GET", DISCOVERY_PATH, None), public_testnet_binding(),
                                           service_id=SUMMARY_SERVICE_ID, private_pilot=True)
            result = {"public_artifacts": {"purchases": purchases}, "restart_replay_only": replay_artifacts is not None}
        elif replay_artifacts is None:
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
        replays = []
        for index, artifacts in enumerate(verified if two_purchases else [artifacts], 1):
            proof = {k: artifacts[k] for k in ("request", "quote", "payment_tx", "payment_authorization")}
            replay = _pilot_json(exchange("POST", SESSION_PATH, _pilot_bytes(
                {"action": "replay", "proof": proof} if two_purchases else {"action": "replay", "artifacts": artifacts}
            )))
            evidence = replay["evidence"]
            if (replay.get("ok") is not False or replay.get("error") != "replay"
                or evidence["payment_applied"] is not False or evidence["service_executed"] is not False
                or evidence["payment_tx_id"] != artifacts["payment_tx"]["id"]):
                raise PublicTestnetError("replay_not_rejected")
            if ((evidence["requester_balance_after"], evidence["provider_balance_after"]) != ((44, 56) if two_purchases else (72, 28))
                or (two_purchases and replay.get("receipt_id") != artifacts["receipt"]["receipt_id"])):
                raise PublicTestnetError("payment_binding_invalid")
            replays.append(evidence)
        finish = _pilot_json(exchange("POST", SESSION_PATH, _pilot_bytes({"action": "finish"})))
        if finish != {"finished": True}:
            raise PublicTestnetError("pilot_finish_failed")
        if two_purchases:
            result["replays"] = replays
        return {**result, "pilot_profile": config["profile"], "session_id": config["session_id"],
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
                **({"purchases": provider.purchases} if provider.two_purchases else {}),
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


class _DeveloperSocketDeadline:
    """Interrupt the underlying TCP connection even after TLS takes its fd."""

    def __init__(self, transport: socket.socket, deadline: float) -> None:
        self.deadline = deadline
        self.interrupt = transport.dup()
        self.timer = threading.Timer(max(0, deadline - time.monotonic()), self._expire)
        self.timer.daemon = True
        self.timer.start()

    def _expire(self) -> None:
        try:
            self.interrupt.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass

    def check(self) -> None:
        if time.monotonic() >= self.deadline:
            raise PublicTestnetError("developer_deadline_expired")

    def close(self) -> None:
        self.timer.cancel()
        self.timer.join()
        self.interrupt.close()


class _DeveloperServer(_Server):
    request_count = 0
    deadline = float('inf')

    def process_request(self, request: Any, client_address: Any) -> None:
        self.request_count += 1
        guard = _DeveloperSocketDeadline(
            request, min(self.deadline, time.monotonic() + REQUEST_TIMEOUT_SECONDS))
        self.request_guard = guard
        try:
            guard.check()
            HTTPServer.process_request(self, request, client_address)
        finally:
            guard.close()


class DeveloperProvider(PublicProvider):
    """Existing wire protocol backed by the existing durable disposable store."""

    def __init__(self, state_dir: Path) -> None:
        from coin.durable_restart_safe_service_demo import DurableProvider

        state_dir.mkdir(mode=0o700)
        super().__init__(service_id=SUMMARY_SERVICE_ID)
        self.backend = DurableProvider(state_dir, service_id=SUMMARY_SERVICE_ID)
        self._key = self.backend._key
        self.public_key, self.identity = self.backend.public_key, self.backend.identity

    def close(self) -> None:
        self.backend.close()
        super().close()

    def _settle(self, package: Mapping[str, Any]) -> dict[str, Any]:
        from coin.durable_restart_safe_service_demo import DurableRuntimeError

        if self._request is None or self._quote is None or set(package) != {"payment_tx", "payment_authorization"}:
            raise PublicTestnetError("unexpected_field")
        # Consume before entering the durable payment path, even on interruption.
        self.expected = 0
        try:
            result = self.backend.handle_payment({"request": self._request, "quote": self._quote, **package})
        except DurableRuntimeError as exc:
            raise PublicTestnetError(exc.code) from exc
        if not result["ok"]:
            raise PublicTestnetError(result["error"])
        self.evidence = result["evidence"]
        reply = json.loads(frame_bytes("service_result_package", 5,
            {"service_result": result["service_result"], "receipt": result["receipt"]}, self.binding))
        self.finished.set()
        return reply


def load_beta_config(path: Path) -> tuple[str, dict[str, tuple[str, str]], str]:
    with path.open("rb") as stream:
        raw = stream.read(4097)
    if len(raw) > 4096:
        raise PublicTestnetError("beta_config_invalid")
    value = json.loads(raw, object_pairs_hook=_reject_duplicate_keys)
    if (not isinstance(value, dict) or set(value) != {"profile", "provider_public_key", "clients"}
            or value["profile"] != BETA_PROFILE or not _lan_pin(value["provider_public_key"])
            or not isinstance(value["clients"], list) or len(value["clients"]) != 2):
        raise PublicTestnetError("beta_config_invalid")
    clients = {}
    payers = {value["provider_public_key"]}
    for client in value["clients"]:
        if (not isinstance(client, dict) or set(client) != {"source_ipv4", "client_sha256", "payer_public_key"}
                or not _lan_pin(client["client_sha256"]) or not _lan_pin(client["payer_public_key"])
                or not isinstance(client["source_ipv4"], str)):
            raise PublicTestnetError("beta_config_invalid")
        source = str(ipaddress.IPv4Address(client["source_ipv4"]))
        fingerprint, payer = client["client_sha256"], client["payer_public_key"]
        if fingerprint in clients or payer in payers:
            raise PublicTestnetError("beta_config_invalid")
        clients[fingerprint] = (source, payer)
        payers.add(payer)
    digest = hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return value["provider_public_key"], clients, digest


def _windows_beta_credential_location(path: PureWindowsPath) -> tuple[str, str]:
    if (not path.is_absolute() or not re.fullmatch(r"[A-Za-z]:", path.drive)
            or len(path.parts) < 2):
        raise PublicTestnetError("beta_credential_not_private")
    parts = path.parts[1:]
    if any(PureWindowsPath(part).is_reserved() or part.endswith((" ", "."))
           or any(character in part for character in (":", "\0")) for part in parts):
        raise PublicTestnetError("beta_credential_not_private")
    return path.anchor, "\\".join(parts)


def _windows_api(dll, name, result, *args):
    function = getattr(dll, name)
    function.argtypes = args
    function.restype = result
    return function


def _require_windows_beta_owner(file_handle, kernel, security):
    import ctypes as c
    from ctypes import wintypes as w

    class Acl(c.Structure):
        _fields_ = [("revision", w.BYTE), ("reserved", w.BYTE), ("size", w.WORD),
                    ("ace_count", w.WORD), ("reserved2", w.WORD)]

    class AceHeader(c.Structure):
        _fields_ = [("type", w.BYTE), ("flags", w.BYTE), ("size", w.WORD)]

    close = _windows_api(kernel, "CloseHandle", w.BOOL, w.HANDLE)
    current_process = _windows_api(kernel, "GetCurrentProcess", w.HANDLE)
    open_token = _windows_api(security, "OpenProcessToken", w.BOOL, w.HANDLE, w.DWORD, c.POINTER(w.HANDLE))
    get_token = _windows_api(security, "GetTokenInformation", w.BOOL, w.HANDLE, c.c_int,
                             w.LPVOID, w.DWORD, c.POINTER(w.DWORD))
    get_security = _windows_api(security, "GetSecurityInfo", w.DWORD, w.HANDLE, c.c_int, w.DWORD,
                                c.POINTER(w.LPVOID), w.LPVOID, c.POINTER(w.LPVOID),
                                w.LPVOID, c.POINTER(w.LPVOID))
    valid_acl = _windows_api(security, "IsValidAcl", w.BOOL, w.LPVOID)
    equal_sid = _windows_api(security, "EqualSid", w.BOOL, w.LPVOID, w.LPVOID)
    sid_length = _windows_api(security, "GetLengthSid", w.DWORD, w.LPVOID)
    get_ace = _windows_api(security, "GetAce", w.BOOL, w.LPVOID, w.DWORD, c.POINTER(w.LPVOID))
    free = _windows_api(kernel, "LocalFree", w.LPVOID, w.LPVOID)

    token = w.HANDLE()
    if not open_token(current_process(), 0x0008, c.byref(token)):  # TOKEN_QUERY
        raise c.WinError(c.get_last_error())
    owner, dacl, descriptor = w.LPVOID(), w.LPVOID(), w.LPVOID()
    try:
        size = w.DWORD()
        get_token(token, 1, None, 0, c.byref(size))  # TokenUser
        if not size.value:
            raise c.WinError(c.get_last_error())
        token_user = c.create_string_buffer(size.value)
        if not get_token(token, 1, token_user, size, c.byref(size)):
            raise c.WinError(c.get_last_error())
        # TOKEN_USER starts with SID_AND_ATTRIBUTES, whose first member is PSID.
        user_sid = c.cast(token_user, c.POINTER(w.LPVOID)).contents
        error = get_security(file_handle, 1, 0x0005, c.byref(owner), None, c.byref(dacl),
                             None, c.byref(descriptor))  # SE_FILE_OBJECT, OWNER | DACL
        if error:
            raise c.WinError(error)
        if not owner or not equal_sid(owner, user_sid) or not dacl or not valid_acl(dacl):
            raise PublicTestnetError("beta_credential_not_private")
        acl = c.cast(dacl, c.POINTER(Acl)).contents
        if not acl.ace_count:
            raise PublicTestnetError("beta_credential_not_private")
        user_sid_size = sid_length(user_sid)
        for index in range(acl.ace_count):
            ace = w.LPVOID()
            if not get_ace(dacl, index, c.byref(ace)):
                raise c.WinError(c.get_last_error())
            header = c.cast(ace, c.POINTER(AceHeader)).contents
            # Reject conditional/object ACEs. A plain allow ACE has a fixed
            # header and access mask followed by its trustee SID.
            if header.type == 1:  # ACCESS_DENIED_ACE_TYPE
                continue
            sid_offset = c.sizeof(AceHeader) + c.sizeof(w.DWORD)
            if (header.type != 0 or header.size != sid_offset + user_sid_size
                    or c.string_at(ace.value + sid_offset, user_sid_size) != c.string_at(user_sid, user_sid_size)):
                raise PublicTestnetError("beta_credential_not_private")
    finally:
        if descriptor:
            free(descriptor)
        close(token)


def _read_windows_beta_credential(path: Path, limit: int) -> bytes:
    import ctypes as c
    from ctypes import wintypes as w

    class UnicodeString(c.Structure):
        _fields_ = [("length", w.USHORT), ("maximum_length", w.USHORT), ("buffer", w.LPWSTR)]

    class ObjectAttributes(c.Structure):
        _fields_ = [("length", w.ULONG), ("root_directory", w.HANDLE),
                    ("object_name", c.POINTER(UnicodeString)), ("attributes", w.ULONG),
                    ("security_descriptor", w.LPVOID), ("security_qos", w.LPVOID)]

    class IoStatusBlock(c.Structure):
        # The first field is a union of NTSTATUS and a pointer.
        _fields_ = [("status_or_pointer", w.LPVOID), ("information", c.c_size_t)]

    root, relative = _windows_beta_credential_location(path.absolute())
    path_bytes = relative.encode("utf-16-le")
    if len(path_bytes) > 65532:
        raise PublicTestnetError("beta_credential_not_private")
    kernel = c.WinDLL("kernel32", use_last_error=True)
    security = c.WinDLL("advapi32", use_last_error=True)
    ntdll = c.WinDLL("ntdll", use_last_error=True)
    close = _windows_api(kernel, "CloseHandle", w.BOOL, w.HANDLE)
    drive_type = _windows_api(kernel, "GetDriveTypeW", w.UINT, w.LPCWSTR)
    create = _windows_api(kernel, "CreateFileW", w.HANDLE, w.LPCWSTR, w.DWORD, w.DWORD,
                          w.LPVOID, w.DWORD, w.DWORD, w.HANDLE)
    final_path = _windows_api(kernel, "GetFinalPathNameByHandleW", w.DWORD, w.HANDLE,
                              w.LPWSTR, w.DWORD, w.DWORD)
    volume_info = _windows_api(kernel, "GetVolumeInformationByHandleW", w.BOOL, w.HANDLE,
                               w.LPWSTR, w.DWORD, w.LPVOID, w.LPVOID, c.POINTER(w.DWORD),
                               w.LPWSTR, w.DWORD)
    attribute_info = _windows_api(kernel, "GetFileInformationByHandleEx", w.BOOL, w.HANDLE,
                                  c.c_int, w.LPVOID, w.DWORD)
    kind = _windows_api(kernel, "GetFileType", w.DWORD, w.HANDLE)
    read = _windows_api(kernel, "ReadFile", w.BOOL, w.HANDLE, w.LPVOID, w.DWORD,
                        c.POINTER(w.DWORD), w.LPVOID)
    open_relative = _windows_api(ntdll, "NtOpenFile", c.c_long, c.POINTER(w.HANDLE), w.ULONG,
                                 c.POINTER(ObjectAttributes), c.POINTER(IoStatusBlock), w.ULONG, w.ULONG)
    dos_error = _windows_api(ntdll, "RtlNtStatusToDosError", w.ULONG, c.c_long)

    # Anchor the native relative open at a real local volume root, not a DOS
    # device alias or a substituted directory. Require persistent ACL support.
    if drive_type(root) != 3:  # DRIVE_FIXED
        raise PublicTestnetError("beta_credential_not_private")
    extended_root = "\\\\?\\" + root
    root_handle = create(extended_root, 0x00A0, 7, None, 3, 0x02200000, None)
    if root_handle == c.c_void_p(-1).value:
        raise c.WinError(c.get_last_error())
    try:
        resolved = c.create_unicode_buffer(128)
        volume_flags = w.DWORD()
        length = final_path(root_handle, resolved, len(resolved), 2)  # VOLUME_NAME_NT
        if (not 0 < length < len(resolved)
                or not re.fullmatch(r"\\Device\\HarddiskVolume[0-9]+\\?", resolved.value, re.IGNORECASE)
                or not volume_info(root_handle, None, 0, None, None, c.byref(volume_flags), None, 0)
                or not volume_flags.value & 0x0008):  # FILE_PERSISTENT_ACLS
            raise PublicTestnetError("beta_credential_not_private")
        file_path = c.create_unicode_buffer(relative)
        name = UnicodeString(len(path_bytes), c.sizeof(file_path), c.cast(file_path, w.LPWSTR))
        # OBJ_CASE_INSENSITIVE | OBJ_DONT_REPARSE rejects reparses in the whole
        # relative path. There is no path-based check followed by a second open.
        attributes = ObjectAttributes(c.sizeof(ObjectAttributes), root_handle, c.pointer(name), 0x1040, None, None)
        handle, status_block = w.HANDLE(), IoStatusBlock()
        # SYNCHRONIZE | READ_CONTROL | FILE_READ_ATTRIBUTES | FILE_READ_DATA.
        # FILE_SHARE_READ, FILE_NON_DIRECTORY_FILE | FILE_SYNCHRONOUS_IO_NONALERT.
        status = open_relative(c.byref(handle), 0x00120081, c.byref(attributes), c.byref(status_block), 1, 0x60)
        if status:
            if (status & 0xffffffff) == 0xc000050b:  # STATUS_REPARSE_POINT_ENCOUNTERED
                raise PublicTestnetError("beta_credential_not_private")
            raise c.WinError(dos_error(status))
        try:
            tag_info = (w.DWORD * 2)()
            if (kind(handle) != 1 or not attribute_info(handle, 9, tag_info, c.sizeof(tag_info))
                    or tag_info[0] & 0x410):  # FILE_TYPE_DISK, FileAttributeTagInfo, REPARSE_POINT | DIRECTORY
                raise PublicTestnetError("beta_credential_not_private")
            _require_windows_beta_owner(handle, kernel, security)
            buffer = c.create_string_buffer(limit + 1)
            count = w.DWORD()
            if not read(handle, buffer, len(buffer), c.byref(count), None):
                error = c.get_last_error()
                if error == 38:  # ERROR_HANDLE_EOF
                    return b""
                raise c.WinError(error)
            if count.value > limit:
                raise PublicTestnetError("beta_credential_invalid")
            return buffer.raw[:count.value]
        finally:
            close(handle)
    finally:
        close(root_handle)


def _read_beta_credential(path: Path, limit: int) -> bytes:
    if os.name == "nt":
        return _read_windows_beta_credential(path, limit)
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o600 or info.st_uid != os.getuid():
            raise PublicTestnetError("beta_credential_not_private")
        value = stream.read(limit + 1)
        if len(value) > limit:
            raise PublicTestnetError("beta_credential_invalid")
        return value


def read_beta_credential(path: Path) -> bytes:
    value = _read_beta_credential(path, 32)
    if len(value) != 32:
        raise PublicTestnetError("beta_credential_invalid")
    return value


def load_beta_disposable_key(path: Path) -> Ed25519PrivateKey:
    pem = _read_beta_credential(path, 256)
    if not re.fullmatch(rb"-----BEGIN PRIVATE KEY-----\n[A-Za-z0-9+/=\n]+-----END PRIVATE KEY-----\n", pem):
        raise PublicTestnetError("beta_credential_invalid")
    key = load_pem_private_key(pem, password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise PublicTestnetError("beta_credential_invalid")
    return key


@contextmanager
def _beta_clean_run(marker: Path):
    parent = marker.parent
    info = parent.stat()
    if (not marker.is_absolute() or not stat.S_ISDIR(info.st_mode)
            or stat.S_IMODE(info.st_mode) != 0o700 or info.st_uid != os.getuid()):
        raise PublicTestnetError("beta_runtime_directory_not_private")
    fd = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    os.close(fd)
    parent_fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(parent_fd)
        yield
        marker.unlink()
        os.fsync(parent_fd)
    finally:
        os.close(parent_fd)


@contextmanager
def _beta_stop_signal():
    stop = threading.Event()

    def request_stop(_signal, _frame):
        stop.set()

    previous = {sig: signal.signal(sig, request_stop) for sig in (signal.SIGTERM, signal.SIGINT)}
    try:
        yield stop
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)


class _BetaProvider(DeveloperProvider):
    def __init__(self, state_dir, key, payer_keys, digest, *, initialize):
        from coin.durable_restart_safe_service_demo import DurableProvider

        PublicProvider.__init__(self, service_id=SUMMARY_SERVICE_ID)
        self.payers = {public_identity(payer) for payer in payer_keys}
        provider = public_identity(_public_key_hex(key))
        balances = {payer: 100 for payer in self.payers}
        balances[provider] = 0
        self.backend = DurableProvider(state_dir, service_id=SUMMARY_SERVICE_ID,
            context_digest=digest, beta_balances=balances, beta_key=key, beta_initialize=initialize)
        self._key = key
        self.public_key, self.identity = self.backend.public_key, self.backend.identity
        self.token = None
        self.payer = None
        self.cutoff = 0.0

    def open_session(self, token, payer):
        if self.backend.fatal or payer not in self.payers or token == self.token:
            raise PublicTestnetError("beta_session_rejected")
        self.token, self.payer = token, payer
        self.cutoff = time.monotonic() + 105
        self.finished.clear()
        self.expected = 1
        self._request = self._quote = None
        return self.hello_frame()

    def _quote_for(self, request):
        verified = verify_service_request(request, service_id=self.service_id)
        if verified["payer_identity"] != self.payer or verified["provider_identity"] != self.identity:
            raise PublicTestnetError("beta_payer_mismatch")
        if self.backend.store.snapshot()["balances"][self.payer] < PRICE_L28:
            raise PublicTestnetError("beta_balance_exhausted")
        quote = build_service_quote(self._key, request=request)
        # The signed quote binds the payment authorization to this attempt.
        body = {k: v for k, v in quote.items() if k not in ("signature", "quote_id")}
        body["nonce"] = self.token
        quote = {**body, "quote_id": _digest(body),
                 "signature": _sign_domain(self._key, QUOTE_SIGN_DOMAIN, body)}
        self._request, self._quote = request, quote
        self.expected = 4
        return json.loads(frame_bytes("service_quote", 3, quote, self.binding))


class _BetaProviderHandler(_Handler):
    def _authorized(self):
        token = self.headers.get_all(BETA_ORIGIN_TOKEN, [])
        return (self.headers.get_all("Host", []) == ["localhost"] and len(token) == 1
                and token[0].isascii() and hmac.compare_digest(token[0], self.server.origin_token))

    def _dispatch(self, method):
        try:
            if not self._authorized():
                raise PublicTestnetError("beta_origin_denied")
            provider = self.server.provider
            self.server.request_guard.check()
            if method == "GET" and self.path == DISCOVERY_PATH:
                self._ok(build_service_discovery(provider.binding, service_id=SUMMARY_SERVICE_ID, beta=True))
                return
            token = self.headers.get_all(BETA_SESSION, [])
            payer = self.headers.get_all(BETA_PAYER, [])
            if len(token) != 1 or not _lan_pin(token[0]) or len(payer) != 1 or not _lan_pin(payer[0]):
                raise PublicTestnetError("beta_session_rejected")
            payer_identity = public_identity(payer[0])
            if method == "GET" and self.path == HELLO_PATH:
                response = provider.open_session(token[0], payer_identity)
            elif method == "POST" and self.path == SESSION_PATH:
                if (token[0] != provider.token or payer_identity != provider.payer
                        or time.monotonic() >= provider.cutoff):
                    raise PublicTestnetError("beta_session_rejected")
                if self.headers.get_all("Transfer-Encoding") or len(self.headers.get_all("Content-Length", [])) != 1:
                    raise PublicTestnetError("malformed_http")
                body = self._read_body()
                self.server.request_guard.check()
                response = provider.handle_frame(body)
            else:
                raise PublicTestnetError("path_not_found")
            self._ok(response)
        except (PublicTestnetError, ServiceDemoError, LimitedTestnetError) as exc:
            self._error(exc.code)
        except (TypeError, ValueError, KeyError, RecursionError):
            self._error("malformed_json")

    def do_GET(self):
        self._dispatch("GET")

    def do_POST(self):
        self._dispatch("POST")


class _BetaProviderServer(_DeveloperServer):
    allow_reuse_address = True

    def __init__(self, provider, port, origin_token):
        self.provider, self.origin_token = provider, origin_token
        HTTPServer.__init__(self, (LOOPBACK_HOST, port), _BetaProviderHandler)


def _run_beta_provider(args):
    if (args.state_dir is None or not args.state_dir.is_absolute() or
            not all((args.beta_config, args.beta_provider_key, args.beta_origin_token))):
        raise PublicTestnetError("beta_provider_configuration_required")
    pin, clients, digest = load_beta_config(args.beta_config)
    key = load_beta_disposable_key(args.beta_provider_key)
    if not hmac.compare_digest(_public_key_hex(key), pin):
        raise PublicTestnetError("beta_provider_pin_mismatch")
    origin = read_beta_credential(args.beta_origin_token).hex()
    marker = args.state_dir.with_name(args.state_dir.name + ".running")
    with _beta_stop_signal() as stop, _beta_clean_run(marker):
        if args.beta_init and args.state_dir.exists():
            raise PublicTestnetError("beta_state_already_exists")
        provider = _BetaProvider(args.state_dir, key, {payer for _, payer in clients.values()},
                                 digest, initialize=args.beta_init)
        try:
            if args.beta_init:
                print(json.dumps({"coordination": "beta_initialized", "provider_public_key": pin}), flush=True)
                return
            with _BetaProviderServer(provider, args.port, origin) as server:
                server.timeout = 0.1
                print(json.dumps({"coordination": "beta_provider_ready", "port": server.server_port,
                                  "provider_public_key": pin}), flush=True)
                while not stop.is_set() and not provider.backend.fatal:
                    server.handle_request()
                snapshot = provider.backend.store.snapshot()
                if provider.backend.fatal or any(not item["service_executed"] for item in snapshot["accepted"].values()):
                    raise PublicTestnetError("beta_reconciliation_required")
        finally:
            provider.close()


_DEVELOPER_RESOLVER = (
    "import json,socket,sys; "
    "print(json.dumps(sorted({r[4][0] for r in socket.getaddrinfo("
    "sys.argv[1],int(sys.argv[2]),socket.AF_INET,socket.SOCK_STREAM)})))"
)


def _developer_resolve(host: str, port: int, deadline: float) -> set[str]:
    if time.monotonic() >= deadline:
        raise PublicTestnetError("developer_deadline_expired")
    try:
        return {str(ipaddress.IPv4Address(host))}
    except ipaddress.AddressValueError:
        pass
    with subprocess.Popen([sys.executable, "-I", "-B", "-c", _DEVELOPER_RESOLVER, host, str(port)],
                          stdout=subprocess.PIPE, stderr=subprocess.DEVNULL) as resolver:
        try:
            raw, _ = resolver.communicate(timeout=max(0, deadline - time.monotonic()))
        except subprocess.TimeoutExpired as exc:
            resolver.kill()
            resolver.communicate()
            raise PublicTestnetError("developer_deadline_expired") from exc
        if time.monotonic() >= deadline:
            raise PublicTestnetError("developer_deadline_expired")
        if resolver.returncode != 0:
            raise PublicTestnetError("developer_route_invalid")
        return {str(ipaddress.IPv4Address(ip)) for ip in json.loads(raw)}


def purchase_developer_summary(endpoint: str, input_text: str, *, expected_provider_key: str,
                               tls_context: ssl.SSLContext, loopback_test: bool = False,
                               approved_private_origin: str | None = None,
                               beta_payer: Ed25519PrivateKey | None = None) -> dict[str, Any]:
    parsed = urllib.parse.urlsplit(endpoint)
    host = parsed.hostname
    if (parsed.scheme != "https" or not host or parsed.username or parsed.password
            or parsed.path not in ("", "/") or parsed.query or parsed.fragment
            or tls_context.verify_mode != ssl.CERT_REQUIRED or not tls_context.check_hostname
            or not _lan_pin(expected_provider_key)):
        raise PublicTestnetError("developer_endpoint_or_trust_invalid")
    if beta_payer is not None and approved_private_origin is not None:
        raise PublicTestnetError("beta_private_origin_unsupported")
    if loopback_test and host != (LOOPBACK_HOST if beta_payer is None else "localhost"):
        raise PublicTestnetError("developer_loopback_required")
    private_ip = "100.66.229.15"
    if approved_private_origin is not None:
        # The configured origin supplies the operator-approved DNS name and port.
        # Never substitute the numeric socket address for the TLS server name.
        labels = host.split(".")
        dns_name = len(host) <= 253 and len(labels) >= 2 and any(c.isalpha() for c in labels[-1])
        dns_name = dns_name and all(
            0 < len(label) <= 63 and label[0] != "-" and label[-1] != "-"
            and all(c in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in label)
            for label in labels
        )
        if loopback_test or endpoint.rstrip("/") != approved_private_origin.rstrip("/") or not dns_name:
            raise PublicTestnetError("developer_private_origin_invalid")
    deadline = time.monotonic() + SESSION_DEADLINE_SECONDS

    def exchange(method: str, path: str, body: bytes | None) -> bytes:
        request_deadline = min(deadline, time.monotonic() + REQUEST_TIMEOUT_SECONDS)
        port = parsed.port or 443
        ips = _developer_resolve(host, port, request_deadline)
        if approved_private_origin is not None:
            allowed = ips == {private_ip}
        elif loopback_test:
            allowed = ips == {LOOPBACK_HOST}
        else:
            allowed = bool(ips) and all(ipaddress.IPv4Address(ip).is_global for ip in ips)
        if not allowed:
            raise PublicTestnetError("developer_route_invalid")
        conn = http.client.HTTPSConnection(host, port, context=tls_context)
        guard = None

        def connect(_address: Any, _timeout: Any, _source: Any) -> socket.socket:
            nonlocal guard
            remaining = request_deadline - time.monotonic()
            if remaining <= 0:
                raise PublicTestnetError("developer_deadline_expired")
            transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                guard = _DeveloperSocketDeadline(transport, request_deadline)
                transport.settimeout(remaining)
                transport.connect((min(ips), port))
                guard.check()
                return transport
            except BaseException:
                transport.close()
                raise

        conn._create_connection = connect
        try:
            conn.request(method, path, body=body, headers={"Content-Type": "application/json"})
            reply = conn.getresponse()
            payload = reply.read(MAX_BODY_BYTES + 1)
            guard.check()
            enforce_body_bound(len(payload))
            if reply.status != 200:
                if (beta_payer is not None and reply.status == 400
                        and payload == b'{"error":"beta_balance_exhausted","ok":false}'):
                    raise PublicTestnetError("beta_balance_exhausted")
                raise PublicTestnetError("request_rejected")
            return payload
        except (OSError, http.client.HTTPException) as exc:
            if guard is not None:
                guard.check()
            raise PublicTestnetError("developer_transport_failed_stop") from exc
        finally:
            conn.close()
            if guard is not None:
                guard.close()

    return run_requester(exchange, input_text, public_testnet_binding(), service_id=SUMMARY_SERVICE_ID,
                         expected_provider_key=expected_provider_key, payer_key=beta_payer,
                         payment_nonce=secrets.randbits(53) if beta_payer is not None else 100,
                         beta=beta_payer is not None)


def _lan_pin(pin: str) -> bool:
    return isinstance(pin, str) and len(pin) == 64 and all(c in "0123456789abcdef" for c in pin)


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
        choices=("parent", "provider", "requester", "local-example", "pilot-config", "pilot-runtime-check", "developer-provider", "beta-provider"),
        default="parent",
    )
    parser.add_argument("--public-endpoint")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--service-id", choices=SERVICE_IDS, default=SERVICE_ID)
    parser.add_argument("--input", default="L28 enables machine payments between autonomous systems.")
    parser.add_argument("--private-pilot", action="store_true")
    parser.add_argument("--two-purchases", action="store_true", help="Generate a two-purchase pilot configuration")
    parser.add_argument("--second-input", help="Second distinct input for the two-purchase requester")
    parser.add_argument("--pilot-config", type=Path)
    parser.add_argument("--state-dir", type=Path)
    parser.add_argument("--beta-config", type=Path)
    parser.add_argument("--beta-provider-key", type=Path)
    parser.add_argument("--beta-origin-token", type=Path)
    parser.add_argument("--beta-init", action="store_true")
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
        if (args.two_purchases and args.role != "pilot-config") or (
            args.second_input is not None and not (args.private_pilot and args.role == "requester")
        ):
            raise PublicTestnetError("pilot_cli_invalid")
        if args.role == "beta-provider":
            if any((args.private_pilot, args.pilot_config, args.pilot_session, args.replay_artifacts,
                    args.public_endpoint, args.provider_node_key, args.requester_node_key)):
                raise PublicTestnetError("beta_provider_configuration_invalid")
            _run_beta_provider(args)
            return 0
        if any((args.beta_config, args.beta_provider_key, args.beta_origin_token, args.beta_init)):
            raise PublicTestnetError("beta_options_require_beta_provider")
        if args.role == "pilot-runtime-check":
            result = {"status": "RUNTIME_CHECK_PASS", "source_digest": pilot_source_digest(), "network_started": False}
            print(json.dumps(result))
            return 0
        if args.role == "pilot-config":
            keys = {} if args.provider_node_key is None and args.requester_node_key is None else {
                "provider": args.provider_node_key, "requester": args.requester_node_key}
            result = pilot_config(session_id=args.pilot_session, provider_host=args.provider_host,
                                  requester_host=args.requester_host, port=args.port, created_at=int(time.time()),
                                  route_keys=keys, two_purchases=args.two_purchases)
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
                replay = None
                if args.replay_artifacts:
                    bundle = config["profile"] == PILOT_REUSE_PROFILE
                    limit = MAX_REPLAY_BUNDLE_BYTES if bundle else MAX_BODY_BYTES
                    with args.replay_artifacts.open("rb") as artifacts_file:
                        replay = _pilot_json(artifacts_file.read(limit + 1), purchase_bundle=bundle)
                result = run_pilot_requester(config, args.input, replay_artifacts=replay, second_input=args.second_input)
            print(_pilot_bytes(result).decode(), flush=True)
            return 0
        if args.role == "developer-provider":
            if args.state_dir is None or not args.state_dir.is_absolute():
                raise PublicTestnetError("developer_state_dir_required")
            provider = DeveloperProvider(args.state_dir)
            try:
                with _DeveloperServer(provider, args.port) as server:
                    server.timeout = 0.25
                    deadline = server.deadline = time.monotonic() + SESSION_DEADLINE_SECONDS - 5
                    print(json.dumps({"coordination": "developer_ready", "port": server.server_port,
                                      "provider_public_key": provider.public_key}), flush=True)
                    while server.request_count < 12 and not provider.finished.is_set() and time.monotonic() < deadline:
                        # Serve serially so completion cannot race the response.
                        server.handle_request()
                    if provider.evidence is None:
                        raise PublicTestnetError("developer_incomplete_preserve_store")
                print(json.dumps({"coordination": "developer_evidence", "evidence": provider.evidence,
                                  "listener_closed": True}), flush=True)
            finally:
                provider.close()
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
