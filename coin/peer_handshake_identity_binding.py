# SPDX-License-Identifier: Apache-2.0
"""Offline peer-handshake identity-binding validator (Foundation 41 / F40 M2).

Implements Foundation 40 handshake message verification only. Does not open
sockets, start nodes, mine, load wallets, mutate ledgers, or activate a testnet.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import AbstractSet, Any, Mapping

from .disposable_network_identity_genesis_binding import (
    ENVIRONMENT as DISPOSABLE_ENVIRONMENT,
    NETWORK_ID,
    PROTOCOL_VERSION,
    validate_disposable_handshake_identity_binding,
)

PROFILE = "l28-peer-handshake-identity-binding/v0.1"
VERIFIER_PROFILE = "l28-peer-handshake-identity-binding-verifier/v0.1"
REPORT_PROFILE = "l28-peer-handshake-identity-binding-report/v0.1"

PROFILE_DOMAIN = (PROFILE + "\x00").encode("utf-8")
REPORT_DOMAIN = (REPORT_PROFILE + "\x00").encode("utf-8")

MAX_HANDSHAKE_BYTES = 8192
CHALLENGE_BYTE_LEN = 32
DEFAULT_LIFETIME = 60
MIN_LIFETIME = 1
MAX_LIFETIME = 3600

MESSAGE_HELLO = "handshake_hello"
MESSAGE_CHALLENGE = "handshake_challenge"
MESSAGE_RESPONSE = "handshake_response"
MESSAGE_ACCEPT = "handshake_accept"
MESSAGE_REJECT = "handshake_reject"
MESSAGE_TYPES = frozenset(
    {
        MESSAGE_HELLO,
        MESSAGE_CHALLENGE,
        MESSAGE_RESPONSE,
        MESSAGE_ACCEPT,
        MESSAGE_REJECT,
    }
)

HEADER_FIELDS = (
    "handshake_version",
    "message_type",
    "environment",
    "network_id",
    "chain_id",
    "protocol_version",
    "genesis_digest",
    "message_id",
    "session_id",
    "peer",
    "nonce",
    "issued_at_logical",
    "expires_at_logical",
    "execution_authorized",
)

PEER_FIELDS = ("peer_id", "peer_public_key", "peer_address")

TYPE_TAIL_FIELDS = {
    MESSAGE_HELLO: ("supported_handshake_versions", "capabilities"),
    MESSAGE_CHALLENGE: ("challenge", "challenge_id", "hello_message_id"),
    MESSAGE_RESPONSE: ("challenge_id", "response", "challenge_message_id"),
    MESSAGE_ACCEPT: ("accepted_peer_id", "response_message_id", "binding_checks"),
    MESSAGE_REJECT: ("rejected_message_id", "reject_code", "detail"),
}

SUCCESS_CHECKS = (
    "schema_exact",
    "environment_disposable",
    "network_id_bound",
    "protocol_version_bound",
    "chain_id_bound",
    "genesis_digest_bound",
    "peer_identity_valid",
    "challenge_response_bound",
    "replay_fresh",
    "execution_authorized_false",
)

STABLE_CODES = (
    "ok",
    "input_type_invalid",
    "input_too_large",
    "encoding_invalid",
    "json_invalid",
    "duplicate_key",
    "invalid_top_level",
    "schema_invalid",
    "handshake_version_unsupported",
    "message_type_invalid",
    "environment_invalid",
    "network_id_invalid",
    "protocol_version_invalid",
    "chain_id_invalid",
    "genesis_digest_invalid",
    "peer_identity_invalid",
    "challenge_invalid",
    "response_invalid",
    "binding_mismatch",
    "replay_detected",
    "message_stale",
    "message_premature",
    "historical_import_forbidden",
    "execution_authorized_invalid",
    "lifecycle_invalid",
    "internal_error",
)

HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
ADDRESS_RE = re.compile(r"^L28[0-9a-f]{40}$")

ALLOWED_TRANSITIONS = {
    "CREATED": frozenset({"HELLO_SENT", "HELLO_RECEIVED", "CLOSED"}),
    "HELLO_SENT": frozenset({"CHALLENGED", "REJECTED", "EXPIRED", "CLOSED"}),
    "HELLO_RECEIVED": frozenset({"CHALLENGED", "REJECTED", "EXPIRED", "CLOSED"}),
    "CHALLENGED": frozenset({"RESPONDED", "REJECTED", "EXPIRED", "CLOSED"}),
    "RESPONDED": frozenset({"ACCEPTED", "REJECTED", "EXPIRED", "CLOSED"}),
    "ACCEPTED": frozenset({"CLOSED"}),
    "REJECTED": frozenset({"CLOSED"}),
    "EXPIRED": frozenset({"CLOSED"}),
    "CLOSED": frozenset(),
}


class _DuplicateKey(ValueError):
    pass


class _HandshakeError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class PeerHandshakeResult:
    ok: bool
    code: str
    message_type: str = ""
    network_id: str = ""
    chain_id: str = ""
    genesis_digest: str = ""
    protocol_version: str = ""
    session_id: str = ""
    message_id: str = ""
    checks: tuple[str, ...] = ()
    execution_authorized: bool = False
    report_id: str = ""


@dataclass
class PeerHandshakeSession:
    """Ephemeral offline session state for lifecycle/replay tests (no I/O)."""

    state: str = "CREATED"
    replay_set: set[str] = field(default_factory=set)

    def transition(self, new_state: str) -> None:
        allowed = ALLOWED_TRANSITIONS.get(self.state, frozenset())
        if new_state not in allowed:
            raise _HandshakeError("lifecycle_invalid")
        self.state = new_state

    def record_accepted(self, *, message_id: str, nonce: str) -> None:
        self.replay_set.add(message_id)
        self.replay_set.add(nonce)

    def clear(self) -> None:
        self.replay_set.clear()
        self.state = "CLOSED"


def _pairs_no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKey(key)
        result[key] = value
    return result


def _reject_constant(_: str) -> None:
    raise _HandshakeError("json_invalid")


def _canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise _HandshakeError("schema_invalid") from exc


def _json_bytes_preserve_order(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=False,
    ).encode("utf-8")


def _decode(payload: str | bytes) -> str:
    if isinstance(payload, bytes):
        if len(payload) > MAX_HANDSHAKE_BYTES:
            raise _HandshakeError("input_too_large")
        try:
            return payload.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise _HandshakeError("encoding_invalid") from exc
    if isinstance(payload, str):
        try:
            encoded = payload.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise _HandshakeError("encoding_invalid") from exc
        if len(encoded) > MAX_HANDSHAKE_BYTES:
            raise _HandshakeError("input_too_large")
        return payload
    raise _HandshakeError("input_type_invalid")


def _parse(payload: str | bytes) -> dict[str, Any]:
    try:
        value = json.loads(
            _decode(payload),
            object_pairs_hook=_pairs_no_duplicates,
            parse_constant=_reject_constant,
        )
    except _DuplicateKey as exc:
        raise _HandshakeError("duplicate_key") from exc
    except _HandshakeError:
        raise
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise _HandshakeError("json_invalid") from exc
    if not isinstance(value, dict):
        raise _HandshakeError("invalid_top_level")
    return value


def _require_hex64(value: Any, *, code: str) -> str:
    if not isinstance(value, str) or HEX64_RE.fullmatch(value) is None:
        raise _HandshakeError(code)
    return value


def _require_exact_int(value: Any, *, code: str = "schema_invalid") -> int:
    if isinstance(value, bool) or type(value) is not int:
        raise _HandshakeError(code)
    return value


def _report_id(body: Mapping[str, Any]) -> str:
    return hashlib.sha256(REPORT_DOMAIN + _canonical_bytes(dict(body))).hexdigest()


def _failure(code: str, *, message_type: str = "") -> PeerHandshakeResult:
    body = {
        "ok": False,
        "code": code,
        "handshake_version": PROFILE,
        "message_type": message_type,
        "network_id": "",
        "chain_id": "",
        "protocol_version": "",
        "genesis_digest": "",
        "session_id": "",
        "message_id": "",
        "checks": [],
        "execution_authorized": False,
    }
    return PeerHandshakeResult(
        False,
        code,
        message_type=message_type,
        execution_authorized=False,
        report_id=_report_id(body),
    )


def compute_peer_handshake_message_id(message_object: Mapping[str, Any]) -> str:
    if not isinstance(message_object, Mapping):
        raise TypeError("message_object must be a mapping")
    body = {key: value for key, value in message_object.items() if key != "message_id"}
    return hashlib.sha256(
        PROFILE_DOMAIN + b"message\x00" + _canonical_bytes(body)
    ).hexdigest()


def compute_peer_handshake_challenge_id(
    *, challenge_hex: str, session_id: str, genesis_digest: str
) -> str:
    challenge_bytes = bytes.fromhex(challenge_hex)
    if len(challenge_bytes) != CHALLENGE_BYTE_LEN:
        raise ValueError("challenge must decode to 32 bytes")
    return hashlib.sha256(
        PROFILE_DOMAIN
        + b"challenge\x00"
        + challenge_bytes
        + b"\x00"
        + session_id.encode("utf-8")
        + b"\x00"
        + genesis_digest.encode("utf-8")
    ).hexdigest()


def compute_peer_handshake_response(
    *,
    challenge_hex: str,
    peer_public_key: str,
    genesis_digest: str,
    session_id: str,
) -> str:
    challenge_bytes = bytes.fromhex(challenge_hex)
    if len(challenge_bytes) != CHALLENGE_BYTE_LEN:
        raise ValueError("challenge must decode to 32 bytes")
    return hashlib.sha256(
        PROFILE_DOMAIN
        + b"response\x00"
        + challenge_bytes
        + b"\x00"
        + peer_public_key.encode("utf-8")
        + b"\x00"
        + genesis_digest.encode("utf-8")
        + b"\x00"
        + session_id.encode("utf-8")
    ).hexdigest()


def compute_vector_challenge_hex(*, session_id: str, genesis_digest: str) -> str:
    digest = hashlib.sha256(
        PROFILE_DOMAIN
        + b"vector-challenge\x00"
        + session_id.encode("utf-8")
        + b"\x00"
        + genesis_digest.encode("utf-8")
    ).digest()
    return digest[:CHALLENGE_BYTE_LEN].hex()


def compute_peer_id(peer_public_key: str) -> str:
    return hashlib.sha256(
        PROFILE_DOMAIN + peer_public_key.encode("utf-8")
    ).hexdigest()


def compute_peer_address(peer_public_key: str) -> str:
    raw = bytes.fromhex(peer_public_key)
    if len(raw) != 32:
        raise ValueError("peer_public_key must be 32 bytes")
    return "L28" + hashlib.sha256(raw).hexdigest()[:40]


def build_peer_identity(peer_public_key: str) -> dict[str, str]:
    _require_hex64(peer_public_key, code="peer_identity_invalid")
    return {
        "peer_id": compute_peer_id(peer_public_key),
        "peer_public_key": peer_public_key,
        "peer_address": compute_peer_address(peer_public_key),
    }


def _fields_for_type(message_type: str) -> tuple[str, ...]:
    return HEADER_FIELDS + TYPE_TAIL_FIELDS[message_type]


def _validate_peer(peer: Any) -> dict[str, str]:
    if not isinstance(peer, dict) or tuple(peer.keys()) != PEER_FIELDS:
        raise _HandshakeError("schema_invalid")
    public_key = _require_hex64(peer["peer_public_key"], code="peer_identity_invalid")
    expected = build_peer_identity(public_key)
    if peer["peer_id"] != expected["peer_id"] or peer["peer_address"] != expected[
        "peer_address"
    ]:
        raise _HandshakeError("peer_identity_invalid")
    if not ADDRESS_RE.fullmatch(peer["peer_address"]):
        raise _HandshakeError("peer_identity_invalid")
    return expected


def _validate_common_header(
    message: dict[str, Any],
    *,
    expected_genesis_digest: str,
    expected_chain_id: str,
    logical_now: int,
    replay_set: AbstractSet[str],
) -> None:
    message_type = message.get("message_type")
    if not isinstance(message_type, str) or message_type not in MESSAGE_TYPES:
        if isinstance(message_type, str) and message_type:
            raise _HandshakeError("message_type_invalid")
        raise _HandshakeError("schema_invalid")
    if tuple(message.keys()) != _fields_for_type(message_type):
        raise _HandshakeError("schema_invalid")
    if message["handshake_version"] != PROFILE:
        raise _HandshakeError("handshake_version_unsupported")

    if not isinstance(message["environment"], str):
        raise _HandshakeError("schema_invalid")
    if message["environment"] in {"MAIN", "CANONICAL", "HISTORICAL", "PRODUCTION"}:
        raise _HandshakeError("historical_import_forbidden")
    if message["environment"] != DISPOSABLE_ENVIRONMENT:
        raise _HandshakeError("environment_invalid")

    for name in ("network_id", "chain_id", "protocol_version", "genesis_digest"):
        if not isinstance(message[name], str):
            raise _HandshakeError("schema_invalid")

    identity = validate_disposable_handshake_identity_binding(
        network_id=message["network_id"],
        chain_id=message["chain_id"],
        protocol_version=message["protocol_version"],
        genesis_digest=message["genesis_digest"],
    )
    if not identity.ok:
        raise _HandshakeError(identity.code)

    expected_digest = _require_hex64(
        expected_genesis_digest, code="genesis_digest_invalid"
    )
    expected_chain = _require_hex64(expected_chain_id, code="chain_id_invalid")
    if message["genesis_digest"] != expected_digest:
        raise _HandshakeError("genesis_digest_invalid")
    if message["chain_id"] != expected_chain:
        raise _HandshakeError("chain_id_invalid")

    _require_hex64(message["message_id"], code="schema_invalid")
    _require_hex64(message["session_id"], code="schema_invalid")
    _require_hex64(message["nonce"], code="schema_invalid")
    _validate_peer(message["peer"])

    issued = _require_exact_int(message["issued_at_logical"])
    expires = _require_exact_int(message["expires_at_logical"])
    if issued < 0 or expires <= issued:
        raise _HandshakeError("schema_invalid")
    lifetime = expires - issued
    if lifetime < MIN_LIFETIME or lifetime > MAX_LIFETIME:
        raise _HandshakeError("schema_invalid")

    now = _require_exact_int(logical_now)
    if now < issued:
        raise _HandshakeError("message_premature")
    if now > expires:
        raise _HandshakeError("message_stale")

    if message["execution_authorized"] is not False:
        raise _HandshakeError("execution_authorized_invalid")

    expected_message_id = compute_peer_handshake_message_id(message)
    if message["message_id"] != expected_message_id:
        raise _HandshakeError("binding_mismatch")

    if message["message_id"] in replay_set or message["nonce"] in replay_set:
        raise _HandshakeError("replay_detected")


def _validate_hello_tail(message: dict[str, Any]) -> None:
    versions = message["supported_handshake_versions"]
    capabilities = message["capabilities"]
    if not isinstance(versions, list) or versions != [PROFILE]:
        raise _HandshakeError("handshake_version_unsupported")
    if not isinstance(capabilities, list) or capabilities != ["identity_binding"]:
        raise _HandshakeError("schema_invalid")
    if not all(isinstance(item, str) for item in versions + capabilities):
        raise _HandshakeError("schema_invalid")


def _validate_challenge_tail(
    message: dict[str, Any], *, expected_hello_message_id: str | None
) -> None:
    challenge = _require_hex64(message["challenge"], code="challenge_invalid")
    try:
        raw = bytes.fromhex(challenge)
    except ValueError as exc:
        raise _HandshakeError("challenge_invalid") from exc
    if len(raw) != CHALLENGE_BYTE_LEN:
        raise _HandshakeError("challenge_invalid")
    expected_id = compute_peer_handshake_challenge_id(
        challenge_hex=challenge,
        session_id=message["session_id"],
        genesis_digest=message["genesis_digest"],
    )
    if message["challenge_id"] != expected_id:
        raise _HandshakeError("challenge_invalid")
    hello_id = _require_hex64(message["hello_message_id"], code="schema_invalid")
    if expected_hello_message_id is not None and hello_id != expected_hello_message_id:
        raise _HandshakeError("binding_mismatch")


def _validate_response_tail(
    message: dict[str, Any], *, expected_challenge: Mapping[str, Any] | None
) -> None:
    challenge_id = _require_hex64(message["challenge_id"], code="schema_invalid")
    response = _require_hex64(message["response"], code="response_invalid")
    challenge_message_id = _require_hex64(
        message["challenge_message_id"], code="schema_invalid"
    )
    if expected_challenge is None:
        return
    if challenge_id != expected_challenge.get("challenge_id"):
        raise _HandshakeError("binding_mismatch")
    if challenge_message_id != expected_challenge.get("message_id"):
        raise _HandshakeError("binding_mismatch")
    if message["session_id"] != expected_challenge.get("session_id"):
        raise _HandshakeError("binding_mismatch")
    expected_response = compute_peer_handshake_response(
        challenge_hex=str(expected_challenge["challenge"]),
        peer_public_key=str(message["peer"]["peer_public_key"]),
        genesis_digest=message["genesis_digest"],
        session_id=message["session_id"],
    )
    if response != expected_response:
        raise _HandshakeError("response_invalid")


def _validate_accept_tail(
    message: dict[str, Any],
    *,
    expected_response_message_id: str | None,
    expected_peer_id: str | None,
) -> None:
    accepted_peer_id = _require_hex64(message["accepted_peer_id"], code="schema_invalid")
    response_message_id = _require_hex64(
        message["response_message_id"], code="schema_invalid"
    )
    checks = message["binding_checks"]
    if not isinstance(checks, list) or [str(item) for item in checks] != list(
        SUCCESS_CHECKS
    ):
        raise _HandshakeError("binding_mismatch")
    if expected_peer_id is not None and accepted_peer_id != expected_peer_id:
        raise _HandshakeError("binding_mismatch")
    if (
        expected_response_message_id is not None
        and response_message_id != expected_response_message_id
    ):
        raise _HandshakeError("binding_mismatch")
    if accepted_peer_id != message["peer"]["peer_id"]:
        raise _HandshakeError("binding_mismatch")


def _validate_reject_tail(message: dict[str, Any]) -> None:
    _require_hex64(message["rejected_message_id"], code="schema_invalid")
    reject_code = message["reject_code"]
    if not isinstance(reject_code, str) or reject_code not in STABLE_CODES or reject_code == "ok":
        raise _HandshakeError("schema_invalid")
    if message["detail"] != "":
        raise _HandshakeError("schema_invalid")


def _success(message: dict[str, Any], *, checks: tuple[str, ...]) -> PeerHandshakeResult:
    body = {
        "ok": True,
        "code": "ok",
        "handshake_version": PROFILE,
        "message_type": message["message_type"],
        "network_id": message["network_id"],
        "chain_id": message["chain_id"],
        "protocol_version": message["protocol_version"],
        "genesis_digest": message["genesis_digest"],
        "session_id": message["session_id"],
        "message_id": message["message_id"],
        "checks": list(checks),
        "execution_authorized": False,
    }
    return PeerHandshakeResult(
        True,
        "ok",
        message["message_type"],
        message["network_id"],
        message["chain_id"],
        message["genesis_digest"],
        message["protocol_version"],
        message["session_id"],
        message["message_id"],
        checks,
        False,
        _report_id(body),
    )


def verify_peer_handshake_message_json(
    payload: str | bytes,
    *,
    expected_genesis_digest: str,
    expected_chain_id: str,
    logical_now: int,
    replay_set: AbstractSet[str],
    expected_hello_message_id: str | None = None,
    expected_challenge: Mapping[str, Any] | None = None,
    expected_response_message_id: str | None = None,
    expected_peer_id: str | None = None,
) -> PeerHandshakeResult:
    try:
        message = _parse(payload)
        # Peek type early for better failure labeling when schema fails later.
        message_type = message.get("message_type")
        if not isinstance(message_type, str):
            message_type = ""
        _validate_common_header(
            message,
            expected_genesis_digest=expected_genesis_digest,
            expected_chain_id=expected_chain_id,
            logical_now=logical_now,
            replay_set=replay_set,
        )
        message_type = message["message_type"]
        if message_type == MESSAGE_HELLO:
            _validate_hello_tail(message)
            return _success(message, checks=())
        if message_type == MESSAGE_CHALLENGE:
            _validate_challenge_tail(
                message, expected_hello_message_id=expected_hello_message_id
            )
            return _success(message, checks=())
        if message_type == MESSAGE_RESPONSE:
            _validate_response_tail(message, expected_challenge=expected_challenge)
            return _success(message, checks=())
        if message_type == MESSAGE_ACCEPT:
            _validate_accept_tail(
                message,
                expected_response_message_id=expected_response_message_id,
                expected_peer_id=expected_peer_id,
            )
            return _success(message, checks=SUCCESS_CHECKS)
        if message_type == MESSAGE_REJECT:
            _validate_reject_tail(message)
            return _success(message, checks=())
        raise _HandshakeError("message_type_invalid")
    except _HandshakeError as exc:
        return _failure(exc.code)
    except Exception:
        return _failure("internal_error")


def verify_peer_handshake_hello_json(
    payload: str | bytes,
    *,
    expected_genesis_digest: str,
    expected_chain_id: str,
    logical_now: int,
    replay_set: AbstractSet[str],
) -> PeerHandshakeResult:
    result = verify_peer_handshake_message_json(
        payload,
        expected_genesis_digest=expected_genesis_digest,
        expected_chain_id=expected_chain_id,
        logical_now=logical_now,
        replay_set=replay_set,
    )
    if result.ok and result.message_type != MESSAGE_HELLO:
        return _failure("message_type_invalid", message_type=result.message_type)
    return result


def verify_peer_handshake_challenge_json(
    payload: str | bytes,
    *,
    expected_genesis_digest: str,
    expected_chain_id: str,
    logical_now: int,
    replay_set: AbstractSet[str],
    expected_hello_message_id: str,
) -> PeerHandshakeResult:
    result = verify_peer_handshake_message_json(
        payload,
        expected_genesis_digest=expected_genesis_digest,
        expected_chain_id=expected_chain_id,
        logical_now=logical_now,
        replay_set=replay_set,
        expected_hello_message_id=expected_hello_message_id,
    )
    if result.ok and result.message_type != MESSAGE_CHALLENGE:
        return _failure("message_type_invalid", message_type=result.message_type)
    return result


def verify_peer_handshake_response_json(
    payload: str | bytes,
    *,
    expected_genesis_digest: str,
    expected_chain_id: str,
    logical_now: int,
    replay_set: AbstractSet[str],
    expected_challenge: Mapping[str, Any],
) -> PeerHandshakeResult:
    result = verify_peer_handshake_message_json(
        payload,
        expected_genesis_digest=expected_genesis_digest,
        expected_chain_id=expected_chain_id,
        logical_now=logical_now,
        replay_set=replay_set,
        expected_challenge=expected_challenge,
    )
    if result.ok and result.message_type != MESSAGE_RESPONSE:
        return _failure("message_type_invalid", message_type=result.message_type)
    return result


def verify_peer_handshake_accept_json(
    payload: str | bytes,
    *,
    expected_genesis_digest: str,
    expected_chain_id: str,
    logical_now: int,
    replay_set: AbstractSet[str],
    expected_response_message_id: str,
    expected_peer_id: str,
) -> PeerHandshakeResult:
    result = verify_peer_handshake_message_json(
        payload,
        expected_genesis_digest=expected_genesis_digest,
        expected_chain_id=expected_chain_id,
        logical_now=logical_now,
        replay_set=replay_set,
        expected_response_message_id=expected_response_message_id,
        expected_peer_id=expected_peer_id,
    )
    if result.ok and result.message_type != MESSAGE_ACCEPT:
        return _failure("message_type_invalid", message_type=result.message_type)
    return result


def _attach_message_id(message: dict[str, Any]) -> dict[str, Any]:
    value = dict(message)
    value["message_id"] = compute_peer_handshake_message_id(value)
    return value


def build_handshake_hello(
    *,
    chain_id: str,
    genesis_digest: str,
    session_id: str,
    peer: Mapping[str, str],
    nonce: str,
    issued_at_logical: int = 0,
    expires_at_logical: int = DEFAULT_LIFETIME,
) -> dict[str, Any]:
    draft = {
        "handshake_version": PROFILE,
        "message_type": MESSAGE_HELLO,
        "environment": DISPOSABLE_ENVIRONMENT,
        "network_id": NETWORK_ID,
        "chain_id": chain_id,
        "protocol_version": PROTOCOL_VERSION,
        "genesis_digest": genesis_digest,
        "message_id": "0" * 64,
        "session_id": session_id,
        "peer": dict(peer),
        "nonce": nonce,
        "issued_at_logical": issued_at_logical,
        "expires_at_logical": expires_at_logical,
        "execution_authorized": False,
        "supported_handshake_versions": [PROFILE],
        "capabilities": ["identity_binding"],
    }
    return _attach_message_id(draft)


def build_handshake_challenge(
    *,
    chain_id: str,
    genesis_digest: str,
    session_id: str,
    peer: Mapping[str, str],
    nonce: str,
    hello_message_id: str,
    issued_at_logical: int = 0,
    expires_at_logical: int = DEFAULT_LIFETIME,
) -> dict[str, Any]:
    challenge = compute_vector_challenge_hex(
        session_id=session_id, genesis_digest=genesis_digest
    )
    challenge_id = compute_peer_handshake_challenge_id(
        challenge_hex=challenge,
        session_id=session_id,
        genesis_digest=genesis_digest,
    )
    draft = {
        "handshake_version": PROFILE,
        "message_type": MESSAGE_CHALLENGE,
        "environment": DISPOSABLE_ENVIRONMENT,
        "network_id": NETWORK_ID,
        "chain_id": chain_id,
        "protocol_version": PROTOCOL_VERSION,
        "genesis_digest": genesis_digest,
        "message_id": "0" * 64,
        "session_id": session_id,
        "peer": dict(peer),
        "nonce": nonce,
        "issued_at_logical": issued_at_logical,
        "expires_at_logical": expires_at_logical,
        "execution_authorized": False,
        "challenge": challenge,
        "challenge_id": challenge_id,
        "hello_message_id": hello_message_id,
    }
    return _attach_message_id(draft)


def build_handshake_response(
    *,
    chain_id: str,
    genesis_digest: str,
    session_id: str,
    peer: Mapping[str, str],
    nonce: str,
    challenge: Mapping[str, Any],
    issued_at_logical: int = 0,
    expires_at_logical: int = DEFAULT_LIFETIME,
) -> dict[str, Any]:
    response = compute_peer_handshake_response(
        challenge_hex=str(challenge["challenge"]),
        peer_public_key=str(peer["peer_public_key"]),
        genesis_digest=genesis_digest,
        session_id=session_id,
    )
    draft = {
        "handshake_version": PROFILE,
        "message_type": MESSAGE_RESPONSE,
        "environment": DISPOSABLE_ENVIRONMENT,
        "network_id": NETWORK_ID,
        "chain_id": chain_id,
        "protocol_version": PROTOCOL_VERSION,
        "genesis_digest": genesis_digest,
        "message_id": "0" * 64,
        "session_id": session_id,
        "peer": dict(peer),
        "nonce": nonce,
        "issued_at_logical": issued_at_logical,
        "expires_at_logical": expires_at_logical,
        "execution_authorized": False,
        "challenge_id": challenge["challenge_id"],
        "response": response,
        "challenge_message_id": challenge["message_id"],
    }
    return _attach_message_id(draft)


def build_handshake_accept(
    *,
    chain_id: str,
    genesis_digest: str,
    session_id: str,
    peer: Mapping[str, str],
    nonce: str,
    response_message_id: str,
    issued_at_logical: int = 0,
    expires_at_logical: int = DEFAULT_LIFETIME,
) -> dict[str, Any]:
    draft = {
        "handshake_version": PROFILE,
        "message_type": MESSAGE_ACCEPT,
        "environment": DISPOSABLE_ENVIRONMENT,
        "network_id": NETWORK_ID,
        "chain_id": chain_id,
        "protocol_version": PROTOCOL_VERSION,
        "genesis_digest": genesis_digest,
        "message_id": "0" * 64,
        "session_id": session_id,
        "peer": dict(peer),
        "nonce": nonce,
        "issued_at_logical": issued_at_logical,
        "expires_at_logical": expires_at_logical,
        "execution_authorized": False,
        "accepted_peer_id": peer["peer_id"],
        "response_message_id": response_message_id,
        "binding_checks": list(SUCCESS_CHECKS),
    }
    return _attach_message_id(draft)


def handshake_json_bytes(message: Mapping[str, Any]) -> bytes:
    return _json_bytes_preserve_order(message)
