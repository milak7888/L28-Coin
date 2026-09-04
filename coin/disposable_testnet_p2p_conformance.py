# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .disposable_testnet_m2 import (
    DisposableLocalTipAuthority,
    DisposableM2Error,
)
from .disposable_testnet_runtime_boundary import (
    DisposableRuntimeBinding,
    DisposableRuntimeBoundaryError,
    validate_runtime_binding,
)
from .node_role_model import P2PNodeRoleModel


PROFILE = "l28-disposable-testnet-m3-offline-p2p/v0.1"
PROTOCOL_VERSION = "1.0.0"

OFFLINE_CONFORMANCE_MAX_FRAME_BYTES = 4096
PRODUCTION_RUNTIME_LIMIT_DEFINED = False
PRODUCTION_PEER_AUTHENTICATION_DEFINED = False
PRODUCTION_TRUSTED_TIME_DEFINED = False
CONFIRMATION_POLICY_DEFINED = False
REORG_POLICY_DEFINED = False

NETWORK_AUTHORIZED = False
SOCKET_AUTHORIZED = False
LISTEN_AUTHORIZED = False
CONNECT_AUTHORIZED = False
P2P_RUNTIME_AUTHORIZED = False
RPC_AUTHORIZED = False
LEDGER_MUTATION_AUTHORIZED = False
CANONICAL_HEIGHT_OVERRIDE_AUTHORIZED = False
ISSUANCE_AUTHORITY = False
SUPPLY_AUTHORITY = False
SIGNING_AUTHORIZED = False
MINING_AUTHORIZED = False
BROADCAST_AUTHORIZED = False
TESTNET_START_AUTHORIZED = False
SETTLEMENT_AUTHORIZED = False

ALLOWED_MESSAGE_TYPES = frozenset(
    {
        "HELLO",
        "TIP_EVIDENCE",
        "CANDIDATE_EVIDENCE",
    }
)

ENVELOPE_FIELDS = frozenset(
    {
        "protocol_version",
        "network_id",
        "genesis_hash",
        "config_hash",
        "message_type",
        "message_id",
        "peer_identity_evidence",
        "nonce",
        "timestamp",
        "expiry",
        "payload_length",
        "payload_digest",
        "payload",
    }
)

PEER_EVIDENCE_FIELDS = frozenset(
    {
        "kind",
        "peer_id",
    }
)

SAFE_TOKEN_RE = re.compile(r"^[A-Za-z0-9._:-]{1,64}$")
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")

STABLE_CODES = (
    "admitted_offline_evidence",
    "malformed_frame",
    "frame_too_large",
    "duplicate_field",
    "unknown_critical_field",
    "unsupported_protocol",
    "network_id_mismatch",
    "genesis_hash_mismatch",
    "config_hash_mismatch",
    "message_type_unsupported",
    "peer_identity_evidence_invalid",
    "nonce_invalid",
    "timestamp_invalid",
    "expiry_invalid",
    "message_expired",
    "payload_length_mismatch",
    "payload_digest_mismatch",
    "message_id_mismatch",
    "message_replayed",
    "nonce_replayed",
)


class DisposableP2PConformanceError(Exception):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class PeerAdmissionResult:
    ok: bool
    code: str
    disconnect: bool
    message_id: str
    message_type: str
    peer_id: str
    normalized_frame: dict[str, Any] | None
    peer_authenticated: bool = False
    transport_authority: bool = False
    core_override_authority: bool = False
    ledger_mutation_authority: bool = False
    canonical_height_authority: bool = False
    issuance_authority: bool = False
    supply_authority: bool = False
    settlement_authority: bool = False


@dataclass(frozen=True)
class PeerTipAssessment:
    local_height: int
    peer_height: int
    relation: str
    peer_tip_authoritative: bool = False
    local_tip_changed: bool = False
    confirmation_claimed: bool = False
    reorg_decision_made: bool = False


def _canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise DisposableP2PConformanceError(
            "malformed_frame"
        ) from exc


def _digest(domain: bytes, value: Any) -> str:
    return hashlib.sha256(
        domain + bytes([0]) + _canonical_bytes(value)
    ).hexdigest()


def _reject_duplicate_pairs(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    result: dict[str, Any] = {}

    for key, value in pairs:
        if key in result:
            raise DisposableP2PConformanceError(
                "duplicate_field"
            )
        result[key] = value

    return result


def _validate_runtime_context(
    binding: DisposableRuntimeBinding,
    tip: DisposableLocalTipAuthority,
) -> None:
    try:
        validate_runtime_binding(binding, tip)
    except DisposableRuntimeBoundaryError as exc:
        raise DisposableP2PConformanceError(
            "runtime_binding_invalid:" + exc.code
        ) from exc


def _validate_peer_identity_evidence(
    value: Any,
) -> str:
    if not isinstance(value, Mapping):
        raise DisposableP2PConformanceError(
            "peer_identity_evidence_invalid"
        )

    if set(value.keys()) != PEER_EVIDENCE_FIELDS:
        raise DisposableP2PConformanceError(
            "peer_identity_evidence_invalid"
        )

    if value["kind"] != "offline_fixture_evidence":
        raise DisposableP2PConformanceError(
            "peer_identity_evidence_invalid"
        )

    peer_id = value["peer_id"]

    if (
        not isinstance(peer_id, str)
        or SAFE_TOKEN_RE.fullmatch(peer_id) is None
    ):
        raise DisposableP2PConformanceError(
            "peer_identity_evidence_invalid"
        )

    return peer_id


def _validate_nonce(value: Any) -> str:
    if (
        not isinstance(value, str)
        or SAFE_TOKEN_RE.fullmatch(value) is None
    ):
        raise DisposableP2PConformanceError(
            "nonce_invalid"
        )

    return value


def _exact_nonnegative_int(
    value: Any,
    code: str,
) -> int:
    if type(value) is not int or value < 0:
        raise DisposableP2PConformanceError(code)

    return value


def _message_projection(
    frame: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        key: frame[key]
        for key in sorted(ENVELOPE_FIELDS)
        if key != "message_id"
    }


def compute_message_id(
    frame: Mapping[str, Any],
) -> str:
    return _digest(
        b"L28-M3-OFFLINE-MESSAGE-ID-V0.1",
        _message_projection(frame),
    )


def nonce_replay_key(
    frame: Mapping[str, Any],
) -> str:
    evidence = frame.get("peer_identity_evidence")
    peer_id = _validate_peer_identity_evidence(
        evidence
    )
    nonce = _validate_nonce(frame.get("nonce"))

    return _digest(
        b"L28-M3-OFFLINE-NONCE-V0.1",
        {
            "peer_id": peer_id,
            "nonce": nonce,
        },
    )


def decode_frame_bytes(
    frame_bytes: Any,
) -> dict[str, Any]:
    if type(frame_bytes) is not bytes:
        raise DisposableP2PConformanceError(
            "malformed_frame"
        )

    if len(frame_bytes) > OFFLINE_CONFORMANCE_MAX_FRAME_BYTES:
        raise DisposableP2PConformanceError(
            "frame_too_large"
        )

    try:
        text = frame_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise DisposableP2PConformanceError(
            "malformed_frame"
        ) from exc

    try:
        decoded = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_pairs,
        )
    except DisposableP2PConformanceError:
        raise
    except (
        json.JSONDecodeError,
        TypeError,
        ValueError,
    ) as exc:
        raise DisposableP2PConformanceError(
            "malformed_frame"
        ) from exc

    if not isinstance(decoded, dict):
        raise DisposableP2PConformanceError(
            "malformed_frame"
        )

    return decoded


def encode_frame_bytes(
    frame: Mapping[str, Any],
) -> bytes:
    encoded = _canonical_bytes(frame)

    if len(encoded) > OFFLINE_CONFORMANCE_MAX_FRAME_BYTES:
        raise DisposableP2PConformanceError(
            "frame_too_large"
        )

    return encoded


def build_offline_frame(
    binding: DisposableRuntimeBinding,
    tip: DisposableLocalTipAuthority,
    *,
    message_type: str,
    peer_id: str,
    nonce: str,
    timestamp: int,
    expiry: int,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    _validate_runtime_context(binding, tip)

    if message_type not in ALLOWED_MESSAGE_TYPES:
        raise DisposableP2PConformanceError(
            "message_type_unsupported"
        )

    _validate_peer_identity_evidence(
        {
            "kind": "offline_fixture_evidence",
            "peer_id": peer_id,
        }
    )
    _validate_nonce(nonce)

    timestamp_value = _exact_nonnegative_int(
        timestamp,
        "timestamp_invalid",
    )
    expiry_value = _exact_nonnegative_int(
        expiry,
        "expiry_invalid",
    )

    if expiry_value < timestamp_value:
        raise DisposableP2PConformanceError(
            "expiry_invalid"
        )

    if not isinstance(payload, Mapping):
        raise DisposableP2PConformanceError(
            "malformed_frame"
        )

    payload_dict = dict(payload)
    payload_bytes = _canonical_bytes(payload_dict)

    frame: dict[str, Any] = {
        "protocol_version": PROTOCOL_VERSION,
        "network_id": binding.network_id,
        "genesis_hash": binding.genesis_hash,
        "config_hash": binding.config_hash,
        "message_type": message_type,
        "message_id": "",
        "peer_identity_evidence": {
            "kind": "offline_fixture_evidence",
            "peer_id": peer_id,
        },
        "nonce": nonce,
        "timestamp": timestamp_value,
        "expiry": expiry_value,
        "payload_length": len(payload_bytes),
        "payload_digest": hashlib.sha256(
            payload_bytes
        ).hexdigest(),
        "payload": payload_dict,
    }

    frame["message_id"] = compute_message_id(frame)
    encode_frame_bytes(frame)

    return frame


def _extract_display_fields(
    frame: Any,
) -> tuple[str, str, str]:
    if not isinstance(frame, Mapping):
        return "", "", ""

    message_id = frame.get("message_id")
    message_type = frame.get("message_type")
    evidence = frame.get("peer_identity_evidence")
    peer_id = ""

    if isinstance(evidence, Mapping):
        candidate = evidence.get("peer_id")
        if isinstance(candidate, str):
            peer_id = candidate

    return (
        message_id if isinstance(message_id, str) else "",
        message_type if isinstance(message_type, str) else "",
        peer_id,
    )


def _failure_result(
    code: str,
    frame: Any = None,
) -> PeerAdmissionResult:
    message_id, message_type, peer_id = (
        _extract_display_fields(frame)
    )

    return PeerAdmissionResult(
        ok=False,
        code=code,
        disconnect=True,
        message_id=message_id,
        message_type=message_type,
        peer_id=peer_id,
        normalized_frame=None,
    )


def _validate_frame_or_raise(
    frame: Any,
    binding: DisposableRuntimeBinding,
    *,
    now_ts: Any,
    seen_message_ids: frozenset[str] | set[str],
    seen_nonce_keys: frozenset[str] | set[str],
) -> dict[str, Any]:
    if not isinstance(frame, Mapping):
        raise DisposableP2PConformanceError(
            "malformed_frame"
        )

    keys = set(frame.keys())
    extra = keys - ENVELOPE_FIELDS
    missing = ENVELOPE_FIELDS - keys

    if extra:
        raise DisposableP2PConformanceError(
            "unknown_critical_field"
        )

    if missing:
        raise DisposableP2PConformanceError(
            "malformed_frame"
        )

    if frame["protocol_version"] != PROTOCOL_VERSION:
        raise DisposableP2PConformanceError(
            "unsupported_protocol"
        )

    if frame["network_id"] != binding.network_id:
        raise DisposableP2PConformanceError(
            "network_id_mismatch"
        )

    if frame["genesis_hash"] != binding.genesis_hash:
        raise DisposableP2PConformanceError(
            "genesis_hash_mismatch"
        )

    if frame["config_hash"] != binding.config_hash:
        raise DisposableP2PConformanceError(
            "config_hash_mismatch"
        )

    if frame["message_type"] not in ALLOWED_MESSAGE_TYPES:
        raise DisposableP2PConformanceError(
            "message_type_unsupported"
        )

    peer_id = _validate_peer_identity_evidence(
        frame["peer_identity_evidence"]
    )
    nonce = _validate_nonce(frame["nonce"])

    timestamp = _exact_nonnegative_int(
        frame["timestamp"],
        "timestamp_invalid",
    )
    expiry = _exact_nonnegative_int(
        frame["expiry"],
        "expiry_invalid",
    )
    now_value = _exact_nonnegative_int(
        now_ts,
        "timestamp_invalid",
    )

    if expiry < timestamp:
        raise DisposableP2PConformanceError(
            "expiry_invalid"
        )

    if expiry < now_value:
        raise DisposableP2PConformanceError(
            "message_expired"
        )

    payload = frame["payload"]

    if not isinstance(payload, Mapping):
        raise DisposableP2PConformanceError(
            "malformed_frame"
        )

    payload_dict = dict(payload)
    payload_bytes = _canonical_bytes(payload_dict)

    if (
        type(frame["payload_length"]) is not int
        or frame["payload_length"] != len(payload_bytes)
    ):
        raise DisposableP2PConformanceError(
            "payload_length_mismatch"
        )

    expected_payload_digest = hashlib.sha256(
        payload_bytes
    ).hexdigest()

    if frame["payload_digest"] != expected_payload_digest:
        raise DisposableP2PConformanceError(
            "payload_digest_mismatch"
        )

    message_id = frame["message_id"]

    if (
        not isinstance(message_id, str)
        or HEX64_RE.fullmatch(message_id) is None
        or message_id != compute_message_id(frame)
    ):
        raise DisposableP2PConformanceError(
            "message_id_mismatch"
        )

    if message_id in seen_message_ids:
        raise DisposableP2PConformanceError(
            "message_replayed"
        )

    nonce_key = _digest(
        b"L28-M3-OFFLINE-NONCE-V0.1",
        {
            "peer_id": peer_id,
            "nonce": nonce,
        },
    )

    if nonce_key in seen_nonce_keys:
        raise DisposableP2PConformanceError(
            "nonce_replayed"
        )

    return dict(frame)


def assess_offline_frame(
    frame: Any,
    binding: DisposableRuntimeBinding,
    tip: DisposableLocalTipAuthority,
    *,
    now_ts: Any,
    seen_message_ids: frozenset[str] | set[str] = frozenset(),
    seen_nonce_keys: frozenset[str] | set[str] = frozenset(),
) -> PeerAdmissionResult:
    _validate_runtime_context(binding, tip)

    try:
        normalized = _validate_frame_or_raise(
            frame,
            binding,
            now_ts=now_ts,
            seen_message_ids=seen_message_ids,
            seen_nonce_keys=seen_nonce_keys,
        )
    except DisposableP2PConformanceError as exc:
        return _failure_result(exc.code, frame)

    message_id, message_type, peer_id = (
        _extract_display_fields(normalized)
    )

    return PeerAdmissionResult(
        ok=True,
        code="admitted_offline_evidence",
        disconnect=False,
        message_id=message_id,
        message_type=message_type,
        peer_id=peer_id,
        normalized_frame=normalized,
    )


def assess_frame_bytes(
    frame_bytes: Any,
    binding: DisposableRuntimeBinding,
    tip: DisposableLocalTipAuthority,
    *,
    now_ts: Any,
    seen_message_ids: frozenset[str] | set[str] = frozenset(),
    seen_nonce_keys: frozenset[str] | set[str] = frozenset(),
) -> PeerAdmissionResult:
    _validate_runtime_context(binding, tip)

    try:
        frame = decode_frame_bytes(frame_bytes)
    except DisposableP2PConformanceError as exc:
        return _failure_result(exc.code)

    return assess_offline_frame(
        frame,
        binding,
        tip,
        now_ts=now_ts,
        seen_message_ids=seen_message_ids,
        seen_nonce_keys=seen_nonce_keys,
    )


def evaluate_peer_tip_evidence(
    binding: DisposableRuntimeBinding,
    tip: DisposableLocalTipAuthority,
    *,
    peer_height: Any,
) -> PeerTipAssessment:
    _validate_runtime_context(binding, tip)

    candidate = _exact_nonnegative_int(
        peer_height,
        "peer_height_invalid",
    )

    try:
        local = tip.read_height()
    except DisposableM2Error as exc:
        raise DisposableP2PConformanceError(
            "tip_unavailable"
        ) from exc

    if candidate > local:
        relation = "PEER_AHEAD"
    elif candidate < local:
        relation = "PEER_BEHIND"
    else:
        relation = "EQUAL"

    return PeerTipAssessment(
        local_height=local,
        peer_height=candidate,
        relation=relation,
    )


def plan_single_writer_sync(
    assessment: PeerTipAssessment,
) -> dict[str, Any]:
    if not isinstance(assessment, PeerTipAssessment):
        raise DisposableP2PConformanceError(
            "peer_tip_assessment_required"
        )

    request_start: int | None = None
    request_end: int | None = None

    if assessment.relation == "PEER_AHEAD":
        action = "REQUEST_CANDIDATE_RANGE"
        request_start = assessment.local_height + 1
        request_end = assessment.peer_height
    elif assessment.relation == "PEER_BEHIND":
        action = "IGNORE_PEER_TIP"
    elif assessment.relation == "EQUAL":
        action = "NO_ACTION"
    else:
        raise DisposableP2PConformanceError(
            "peer_tip_relation_invalid"
        )

    return {
        "profile": "l28-m3-single-writer-sync-plan/v0.1",
        "action": action,
        "request_start": request_start,
        "request_end": request_end,
        "plan_only": True,
        "single_writer": "LOCAL_CORE_ONLY",
        "peer_candidate_evidence_only": True,
        "peer_can_mutate_local_tip": False,
        "peer_can_override_canonical_height": False,
        "automatic_apply": False,
        "ledger_mutation_authorized": False,
        "issuance_authority": False,
        "supply_authority": False,
        "validation_override_authority": False,
        "history_override_authority": False,
        "settlement_authority": False,
        "confirmation_policy_defined": False,
        "reorg_policy_defined": False,
    }


def prepare_p2p_conformance_boundary(
    binding: DisposableRuntimeBinding,
    tip: DisposableLocalTipAuthority,
) -> dict[str, Any]:
    _validate_runtime_context(binding, tip)

    p2p = P2PNodeRoleModel()
    configured, result = p2p.transition("CONFIGURED")

    if not result.ok:
        raise DisposableP2PConformanceError(
            "p2p_configuration_failed"
        )

    return {
        "profile": PROFILE,
        "lifecycle_state": configured.state,
        "network_id": binding.network_id,
        "genesis_hash": binding.genesis_hash,
        "config_hash": binding.config_hash,
        "offline_conformance_only": True,
        "production_runtime_limit_defined": False,
        "production_peer_authentication_defined": False,
        "production_trusted_time_defined": False,
        "network_authorized": False,
        "socket_authorized": False,
        "listen_authorized": False,
        "connect_authorized": False,
        "rpc_authorized": False,
        "p2p_runtime_authorized": False,
        "ledger_mutation_authorized": False,
        "canonical_height_override_authorized": False,
        "signing_authorized": False,
        "mining_authorized": False,
        "broadcast_authorized": False,
        "testnet_start_authorized": False,
        "settlement_authorized": False,
    }
