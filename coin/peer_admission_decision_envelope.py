# SPDX-License-Identifier: Apache-2.0
"""Offline peer admission decision envelope validator (Foundation 43 / F42).

Implements Foundation 42 envelope verification only. Does not open sockets,
start nodes, mine, load wallets, mutate ledgers, or activate a testnet.
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
from .peer_handshake_identity_binding import (
    PROFILE as HANDSHAKE_PROFILE,
    build_peer_identity,
    compute_peer_handshake_challenge_id,
    compute_peer_handshake_response,
)

PROFILE = "l28-peer-admission-decision-envelope/v0.1"
VERIFIER_PROFILE = "l28-peer-admission-decision-envelope-verifier/v0.1"
REPORT_PROFILE = "l28-peer-admission-decision-envelope-report/v0.1"

PROFILE_DOMAIN = (PROFILE + "\x00").encode("utf-8")
REPORT_DOMAIN = (REPORT_PROFILE + "\x00").encode("utf-8")

MAX_ENVELOPE_BYTES = 12288
DEFAULT_LIFETIME = 60
MIN_LIFETIME = 1
MAX_LIFETIME = 3600
DECISION_CANDIDATE = "identity_bound_candidate"

FORBIDDEN_ENVIRONMENTS = frozenset({"MAIN", "CANONICAL", "HISTORICAL", "PRODUCTION"})

ENVELOPE_FIELDS = (
    "envelope_version",
    "environment",
    "network_id",
    "chain_id",
    "protocol_version",
    "genesis_digest",
    "peer_id",
    "peer_public_key",
    "peer_address",
    "handshake_version",
    "handshake_accept_message_id",
    "handshake_accept_report_id",
    "handshake_session_id",
    "challenge",
    "challenge_id",
    "response",
    "challenge_message_id",
    "response_message_id",
    "decision",
    "issued_at_logical",
    "expires_at_logical",
    "nonce",
    "execution_authorized",
    "admission_authorized",
    "envelope_id",
)

SUCCESS_CHECKS = (
    "schema_exact",
    "environment_disposable",
    "network_id_bound",
    "protocol_version_bound",
    "chain_id_bound",
    "genesis_digest_bound",
    "peer_identity_bound",
    "handshake_accept_bound",
    "challenge_response_bound",
    "decision_candidate_only",
    "replay_fresh",
    "execution_authorized_false",
    "admission_authorized_false",
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
    "envelope_version_unsupported",
    "environment_invalid",
    "network_id_invalid",
    "protocol_version_invalid",
    "chain_id_invalid",
    "genesis_digest_invalid",
    "peer_identity_invalid",
    "handshake_binding_invalid",
    "challenge_binding_invalid",
    "decision_invalid",
    "replay_detected",
    "message_stale",
    "message_premature",
    "historical_import_forbidden",
    "execution_authorized_invalid",
    "admission_authorized_invalid",
    "lifecycle_invalid",
    "envelope_id_invalid",
    "internal_error",
)

HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
ADDRESS_RE = re.compile(r"^L28[0-9a-f]{40}$")

ALLOWED_TRANSITIONS = {
    "CREATED": frozenset({"HANDSHAKE_ACCEPTED", "REJECTED", "CLOSED"}),
    "HANDSHAKE_ACCEPTED": frozenset({"ENVELOPE_CANDIDATE", "REJECTED", "CLOSED"}),
    "ENVELOPE_CANDIDATE": frozenset(
        {"ENVELOPE_VERIFIED", "REJECTED", "EXPIRED", "CLOSED"}
    ),
    "ENVELOPE_VERIFIED": frozenset({"CLOSED"}),
    "REJECTED": frozenset({"CLOSED"}),
    "EXPIRED": frozenset({"CLOSED"}),
    "CLOSED": frozenset(),
}


class _DuplicateKey(ValueError):
    pass


class _AdmissionError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class PeerAdmissionDecisionResult:
    ok: bool
    code: str
    decision: str = ""
    network_id: str = ""
    chain_id: str = ""
    genesis_digest: str = ""
    protocol_version: str = ""
    environment: str = ""
    peer_id: str = ""
    handshake_accept_report_id: str = ""
    handshake_accept_message_id: str = ""
    envelope_id: str = ""
    checks: tuple[str, ...] = ()
    detail: str = ""
    execution_authorized: bool = False
    admission_authorized: bool = False
    report_id: str = ""


@dataclass
class PeerAdmissionDecisionSession:
    """Ephemeral offline session state for lifecycle/replay tests (no I/O)."""

    state: str = "CREATED"
    replay_set: set[str] = field(default_factory=set)

    def transition(self, new_state: str) -> None:
        allowed = ALLOWED_TRANSITIONS.get(self.state, frozenset())
        if new_state not in allowed:
            raise _AdmissionError("lifecycle_invalid")
        self.state = new_state

    def record_accepted(self, *, envelope_id: str, nonce: str) -> None:
        self.replay_set.add(envelope_id)
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
    raise _AdmissionError("json_invalid")


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
        raise _AdmissionError("schema_invalid") from exc


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
        if len(payload) > MAX_ENVELOPE_BYTES:
            raise _AdmissionError("input_too_large")
        try:
            return payload.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise _AdmissionError("encoding_invalid") from exc
    if isinstance(payload, str):
        try:
            encoded = payload.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise _AdmissionError("encoding_invalid") from exc
        if len(encoded) > MAX_ENVELOPE_BYTES:
            raise _AdmissionError("input_too_large")
        return payload
    raise _AdmissionError("input_type_invalid")


def _parse(payload: str | bytes) -> dict[str, Any]:
    try:
        value = json.loads(
            _decode(payload),
            object_pairs_hook=_pairs_no_duplicates,
            parse_constant=_reject_constant,
        )
    except _DuplicateKey as exc:
        raise _AdmissionError("duplicate_key") from exc
    except _AdmissionError:
        raise
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise _AdmissionError("json_invalid") from exc
    if not isinstance(value, dict):
        raise _AdmissionError("invalid_top_level")
    return value


def _require_hex64(value: Any, *, code: str) -> str:
    if not isinstance(value, str) or HEX64_RE.fullmatch(value) is None:
        raise _AdmissionError(code)
    return value


def _require_exact_int(value: Any, *, code: str = "schema_invalid") -> int:
    if isinstance(value, bool) or type(value) is not int:
        raise _AdmissionError(code)
    return value


def _report_id(body: Mapping[str, Any]) -> str:
    return hashlib.sha256(REPORT_DOMAIN + _canonical_bytes(dict(body))).hexdigest()


def _failure(code: str) -> PeerAdmissionDecisionResult:
    body = {
        "ok": False,
        "code": code,
        "decision": "",
        "network_id": "",
        "chain_id": "",
        "genesis_digest": "",
        "protocol_version": "",
        "environment": "",
        "peer_id": "",
        "handshake_accept_report_id": "",
        "handshake_accept_message_id": "",
        "envelope_id": "",
        "checks": [],
        "detail": "",
        "execution_authorized": False,
        "admission_authorized": False,
        "verifier_profile": VERIFIER_PROFILE,
    }
    return PeerAdmissionDecisionResult(
        False,
        code,
        detail="",
        execution_authorized=False,
        admission_authorized=False,
        report_id=_report_id(body),
    )


def _success(envelope: Mapping[str, Any]) -> PeerAdmissionDecisionResult:
    body = {
        "ok": True,
        "code": "ok",
        "decision": envelope["decision"],
        "network_id": envelope["network_id"],
        "chain_id": envelope["chain_id"],
        "genesis_digest": envelope["genesis_digest"],
        "protocol_version": envelope["protocol_version"],
        "environment": envelope["environment"],
        "peer_id": envelope["peer_id"],
        "handshake_accept_report_id": envelope["handshake_accept_report_id"],
        "handshake_accept_message_id": envelope["handshake_accept_message_id"],
        "envelope_id": envelope["envelope_id"],
        "checks": list(SUCCESS_CHECKS),
        "detail": "",
        "execution_authorized": False,
        "admission_authorized": False,
        "verifier_profile": VERIFIER_PROFILE,
    }
    return PeerAdmissionDecisionResult(
        True,
        "ok",
        decision=str(envelope["decision"]),
        network_id=str(envelope["network_id"]),
        chain_id=str(envelope["chain_id"]),
        genesis_digest=str(envelope["genesis_digest"]),
        protocol_version=str(envelope["protocol_version"]),
        environment=str(envelope["environment"]),
        peer_id=str(envelope["peer_id"]),
        handshake_accept_report_id=str(envelope["handshake_accept_report_id"]),
        handshake_accept_message_id=str(envelope["handshake_accept_message_id"]),
        envelope_id=str(envelope["envelope_id"]),
        checks=SUCCESS_CHECKS,
        detail="",
        execution_authorized=False,
        admission_authorized=False,
        report_id=_report_id(body),
    )


def compute_peer_admission_envelope_id(envelope_object: Mapping[str, Any]) -> str:
    if not isinstance(envelope_object, Mapping):
        raise TypeError("envelope_object must be a mapping")
    body = {
        key: value
        for key, value in envelope_object.items()
        if key != "envelope_id"
    }
    return hashlib.sha256(
        PROFILE_DOMAIN + b"envelope\x00" + _canonical_bytes(body)
    ).hexdigest()


def _validate_step1_schema(envelope: dict[str, Any]) -> None:
    if tuple(envelope.keys()) != ENVELOPE_FIELDS:
        raise _AdmissionError("schema_invalid")

    string_fields = (
        "envelope_version",
        "environment",
        "network_id",
        "chain_id",
        "protocol_version",
        "genesis_digest",
        "peer_id",
        "peer_public_key",
        "peer_address",
        "handshake_version",
        "handshake_accept_message_id",
        "handshake_accept_report_id",
        "handshake_session_id",
        "challenge",
        "challenge_id",
        "response",
        "challenge_message_id",
        "response_message_id",
        "decision",
        "nonce",
        "envelope_id",
    )
    for name in string_fields:
        if not isinstance(envelope[name], str):
            raise _AdmissionError("schema_invalid")

    if not isinstance(envelope["execution_authorized"], bool):
        raise _AdmissionError("schema_invalid")
    if not isinstance(envelope["admission_authorized"], bool):
        raise _AdmissionError("schema_invalid")

    _require_exact_int(envelope["issued_at_logical"])
    _require_exact_int(envelope["expires_at_logical"])

    # Scope mapping: handshake_version mismatch → schema_invalid in step 1.
    if envelope["handshake_version"] != HANDSHAKE_PROFILE:
        raise _AdmissionError("schema_invalid")


def _validate_envelope(
    envelope: dict[str, Any],
    *,
    expected_genesis_digest: str,
    expected_chain_id: str,
    expected_handshake_accept_report_id: str,
    expected_handshake_accept_message_id: str,
    expected_peer_id: str,
    expected_session_id: str,
    expected_challenge_hex: str,
    expected_challenge_message_id: str,
    expected_response_message_id: str,
    logical_now: int,
    replay_set: AbstractSet[str],
) -> PeerAdmissionDecisionResult:
    # Step 1
    _validate_step1_schema(envelope)

    # Step 2
    if envelope["envelope_version"] != PROFILE:
        raise _AdmissionError("envelope_version_unsupported")

    # Step 3
    if envelope["environment"] in FORBIDDEN_ENVIRONMENTS:
        raise _AdmissionError("historical_import_forbidden")

    # Step 4
    if envelope["environment"] != DISPOSABLE_ENVIRONMENT:
        raise _AdmissionError("environment_invalid")

    # Step 5
    identity = validate_disposable_handshake_identity_binding(
        network_id=envelope["network_id"],
        chain_id=envelope["chain_id"],
        protocol_version=envelope["protocol_version"],
        genesis_digest=envelope["genesis_digest"],
    )
    if not identity.ok:
        raise _AdmissionError(identity.code)

    expected_digest = _require_hex64(
        expected_genesis_digest, code="genesis_digest_invalid"
    )
    expected_chain = _require_hex64(expected_chain_id, code="chain_id_invalid")
    if envelope["genesis_digest"] != expected_digest:
        raise _AdmissionError("genesis_digest_invalid")
    if envelope["chain_id"] != expected_chain:
        raise _AdmissionError("chain_id_invalid")

    # Step 6
    peer_public_key = _require_hex64(
        envelope["peer_public_key"], code="peer_identity_invalid"
    )
    expected_peer = build_peer_identity(peer_public_key)
    if (
        envelope["peer_id"] != expected_peer["peer_id"]
        or envelope["peer_address"] != expected_peer["peer_address"]
        or not ADDRESS_RE.fullmatch(envelope["peer_address"])
    ):
        raise _AdmissionError("peer_identity_invalid")
    expected_peer_id_hex = _require_hex64(
        expected_peer_id, code="peer_identity_invalid"
    )
    if envelope["peer_id"] != expected_peer_id_hex:
        raise _AdmissionError("peer_identity_invalid")

    # Steps 7–8
    accept_report = _require_hex64(
        envelope["handshake_accept_report_id"], code="handshake_binding_invalid"
    )
    accept_message = _require_hex64(
        envelope["handshake_accept_message_id"], code="handshake_binding_invalid"
    )
    session_id = _require_hex64(
        envelope["handshake_session_id"], code="handshake_binding_invalid"
    )
    if accept_report != expected_handshake_accept_report_id:
        raise _AdmissionError("handshake_binding_invalid")
    if accept_message != expected_handshake_accept_message_id:
        raise _AdmissionError("handshake_binding_invalid")
    if session_id != expected_session_id:
        raise _AdmissionError("handshake_binding_invalid")

    # Steps 9–12
    challenge = _require_hex64(envelope["challenge"], code="challenge_binding_invalid")
    if challenge != expected_challenge_hex:
        raise _AdmissionError("challenge_binding_invalid")
    expected_challenge_id = compute_peer_handshake_challenge_id(
        challenge_hex=challenge,
        session_id=session_id,
        genesis_digest=envelope["genesis_digest"],
    )
    if envelope["challenge_id"] != expected_challenge_id:
        raise _AdmissionError("challenge_binding_invalid")
    expected_response = compute_peer_handshake_response(
        challenge_hex=challenge,
        peer_public_key=peer_public_key,
        genesis_digest=envelope["genesis_digest"],
        session_id=session_id,
    )
    if envelope["response"] != expected_response:
        raise _AdmissionError("challenge_binding_invalid")
    challenge_message_id = _require_hex64(
        envelope["challenge_message_id"], code="challenge_binding_invalid"
    )
    response_message_id = _require_hex64(
        envelope["response_message_id"], code="challenge_binding_invalid"
    )
    if challenge_message_id != expected_challenge_message_id:
        raise _AdmissionError("challenge_binding_invalid")
    if response_message_id != expected_response_message_id:
        raise _AdmissionError("challenge_binding_invalid")

    # Step 13
    if envelope["decision"] != DECISION_CANDIDATE:
        raise _AdmissionError("decision_invalid")

    # Step 14
    issued = _require_exact_int(envelope["issued_at_logical"])
    expires = _require_exact_int(envelope["expires_at_logical"])
    if issued < 0 or expires <= issued:
        raise _AdmissionError("schema_invalid")
    lifetime_seconds = expires - issued
    if lifetime_seconds < MIN_LIFETIME or lifetime_seconds > MAX_LIFETIME:
        raise _AdmissionError("schema_invalid")

    # Step 15
    now = _require_exact_int(logical_now)
    if now < issued:
        raise _AdmissionError("message_premature")
    if now > expires:
        raise _AdmissionError("message_stale")
    nonce = _require_hex64(envelope["nonce"], code="schema_invalid")
    envelope_id = _require_hex64(envelope["envelope_id"], code="schema_invalid")
    if envelope_id in replay_set or nonce in replay_set:
        raise _AdmissionError("replay_detected")

    # Step 16 — execution flag before admission flag
    if envelope["execution_authorized"] is not False:
        raise _AdmissionError("execution_authorized_invalid")
    if envelope["admission_authorized"] is not False:
        raise _AdmissionError("admission_authorized_invalid")

    # Step 17
    expected_envelope_id = compute_peer_admission_envelope_id(envelope)
    if envelope_id != expected_envelope_id:
        raise _AdmissionError("envelope_id_invalid")

    return _success(envelope)


def verify_peer_admission_decision_envelope_json(
    payload: str | bytes,
    *,
    expected_genesis_digest: str,
    expected_chain_id: str,
    expected_handshake_accept_report_id: str,
    expected_handshake_accept_message_id: str,
    expected_peer_id: str,
    expected_session_id: str,
    expected_challenge_hex: str,
    expected_challenge_message_id: str,
    expected_response_message_id: str,
    logical_now: int,
    replay_set: AbstractSet[str],
) -> PeerAdmissionDecisionResult:
    try:
        envelope = _parse(payload)
        return _validate_envelope(
            envelope,
            expected_genesis_digest=expected_genesis_digest,
            expected_chain_id=expected_chain_id,
            expected_handshake_accept_report_id=expected_handshake_accept_report_id,
            expected_handshake_accept_message_id=expected_handshake_accept_message_id,
            expected_peer_id=expected_peer_id,
            expected_session_id=expected_session_id,
            expected_challenge_hex=expected_challenge_hex,
            expected_challenge_message_id=expected_challenge_message_id,
            expected_response_message_id=expected_response_message_id,
            logical_now=logical_now,
            replay_set=replay_set,
        )
    except _AdmissionError as exc:
        return _failure(exc.code)
    except Exception:
        return _failure("internal_error")


def build_peer_admission_decision_envelope(
    *,
    chain_id: str,
    genesis_digest: str,
    peer_id: str,
    peer_public_key: str,
    peer_address: str,
    handshake_accept_message_id: str,
    handshake_accept_report_id: str,
    handshake_session_id: str,
    challenge: str,
    challenge_id: str,
    response: str,
    challenge_message_id: str,
    response_message_id: str,
    nonce: str,
    issued_at_logical: int = 0,
    expires_at_logical: int = DEFAULT_LIFETIME,
    decision: str = DECISION_CANDIDATE,
) -> dict[str, Any]:
    draft: dict[str, Any] = {
        "envelope_version": PROFILE,
        "environment": DISPOSABLE_ENVIRONMENT,
        "network_id": NETWORK_ID,
        "chain_id": chain_id,
        "protocol_version": PROTOCOL_VERSION,
        "genesis_digest": genesis_digest,
        "peer_id": peer_id,
        "peer_public_key": peer_public_key,
        "peer_address": peer_address,
        "handshake_version": HANDSHAKE_PROFILE,
        "handshake_accept_message_id": handshake_accept_message_id,
        "handshake_accept_report_id": handshake_accept_report_id,
        "handshake_session_id": handshake_session_id,
        "challenge": challenge,
        "challenge_id": challenge_id,
        "response": response,
        "challenge_message_id": challenge_message_id,
        "response_message_id": response_message_id,
        "decision": decision,
        "issued_at_logical": issued_at_logical,
        "expires_at_logical": expires_at_logical,
        "nonce": nonce,
        "execution_authorized": False,
        "admission_authorized": False,
        "envelope_id": "0" * 64,
    }
    draft["envelope_id"] = compute_peer_admission_envelope_id(draft)
    return draft


def envelope_json_bytes(envelope: Mapping[str, Any]) -> bytes:
    return _json_bytes_preserve_order(envelope)
