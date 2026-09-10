# SPDX-License-Identifier: Apache-2.0
"""Deterministic offline fault/recovery evidence evaluator.

Importing this module is inert. It never starts a signer, wallet, key path,
network, or server. Disposable in-memory state is the only mutation surface.
It never marks FAULT_RECOVERY RESOLVED while repository-required recovery
gaps remain, and never calls coin.tx_validation.validate_transaction.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy


PROFILE = "l28-signer-fault-recovery-evidence/v0.1"
AUDIT_PROFILE = "l28-signer-audit-log/v0.1"
TIME_PROFILE = "l28-signer-trusted-time/v0.1"
GENESIS_PREVIOUS_HASH = hashlib.sha256(b"L28-F177-DISPOSABLE-FAULT-CHAIN-V0.1").hexdigest()

FAULT_COMPLETE = "FAULT_RECOVERY_EVIDENCE_COMPLETE"
FAULT_INCOMPLETE = "FAULT_RECOVERY_EVIDENCE_INCOMPLETE"
FAULT_INVALID = "FAULT_RECOVERY_EVIDENCE_INVALID"
BLOCKED_BY_FAULT_RECOVERY_GAPS = "BLOCKED_BY_FAULT_RECOVERY_GAPS"

FAIL_CLOSED = "FAIL_CLOSED"
COMMITTED_RETAINED = "COMMITTED_STATE_RETAINED"
PREPARED_NOT_COMMITTED = "PREPARED_NOT_COMMITTED"

FAULT_CLASSES = (
    "partial_write",
    "corrupt_evidence",
    "truncated_evidence",
    "stale_evidence",
    "replay",
    "duplicate_request",
    "clock_rollback",
    "audit_chain_corruption",
    "crash_before_commit",
    "crash_after_commit",
    "restart_incomplete_state",
    "concurrent_conflicting_state",
    "revoked_state_reuse",
    "missing_dependency_evidence",
)

REQUIRED_REMAINING_GAPS = (
    "F122-G08",
    "LSOD-STA-012",
    "LSOD-OPS-008",
    "LSOD-OPS-009",
    "LSOD-GAT-004",
)

HEX64 = 64
RUNTIME_FLAGS = (
    "signer_invoked",
    "signing_attempted",
    "signature_created",
    "wallet_accessed",
    "keys_loaded",
    "runtime_active",
    "broadcast_attempted",
    "settlement_finalized",
)
PROTECTED_AUTHORITY = (
    "issuance",
    "supply",
    "height",
    "validation",
    "consensus",
    "history",
    "ledger",
    "settlement",
    "wallet",
    "signing",
    "bitcoin",
)
SECRET_KEYS = frozenset(
    {
        "private_key",
        "privkey",
        "seed",
        "seed_phrase",
        "mnemonic",
        "xprv",
        "secret",
        "password",
        "token",
        "wallet_credential",
        "rpc_user",
        "rpc_password",
        "rpc_cookie",
        "key_material",
        "key_bytes",
        "key_path",
        "keystore_path",
        "wallet_path",
        "hsm_slot",
        "kms_key",
        "pem",
        "der",
    }
)
CLAIMED_READY = frozenset(
    {"RESOLVED", "APPROVED", "PASS", "COMPLETE", FAULT_COMPLETE}
)


class FaultRecoveryEvidenceError(ValueError):
    """Fail-closed fault/recovery evidence error; does not repair input."""


def canonical_bytes(value):
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
        allow_nan=False,
    ).encode("utf-8")


def _reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise FaultRecoveryEvidenceError("duplicate_json_key")
        result[key] = value
    return result


def _reject_constant(value):
    raise FaultRecoveryEvidenceError("schema_invalid")


def load_public_evidence(text):
    return json.loads(
        text, object_pairs_hook=_reject_duplicate_keys, parse_constant=_reject_constant
    )


def evidence_digest(evidence):
    return hashlib.sha256(canonical_bytes(evidence)).hexdigest()


def _is_hex64(value):
    return isinstance(value, str) and len(value) == HEX64 and all(
        char in "0123456789abcdef" for char in value
    )


def _contains_secret(node):
    if isinstance(node, dict):
        for key, value in node.items():
            if isinstance(key, str) and key.lower() in SECRET_KEYS:
                return True
            if _contains_secret(value):
                return True
    elif isinstance(node, (list, tuple)):
        return any(_contains_secret(item) for item in node)
    elif isinstance(node, str) and node.lower() in SECRET_KEYS:
        return True
    return False


def _is_public_scalar(value):
    if isinstance(value, bool):
        return True
    if type(value) is int:
        return True
    return isinstance(value, str) and value != ""


def _walk_public(node):
    if isinstance(node, dict):
        return all(_is_public_scalar(key) and _walk_public(value) for key, value in node.items())
    if isinstance(node, (list, tuple)):
        return all(_walk_public(item) for item in node)
    return _is_public_scalar(node)


def empty_fault_state():
    return {
        "entries": [],
        "high_water_ns": 0,
        "seen_request_ids": [],
        "seen_idempotency_keys": [],
        "revoked_request_ids": [],
        "prepared": None,
        "commit_high_water": 0,
    }


def _entry_hash(entry):
    material = {key: value for key, value in entry.items() if key != "entry_hash"}
    return hashlib.sha256(canonical_bytes(material)).hexdigest()


def verify_fault_state(state):
    if not isinstance(state, dict) or not isinstance(state.get("entries"), list):
        return {"ok": False, "reason": "corrupt_evidence"}
    previous = GENESIS_PREVIOUS_HASH
    high_water = 0
    seen_requests = []
    seen_keys = []
    for index, entry in enumerate(state["entries"]):
        if not isinstance(entry, dict):
            return {"ok": False, "reason": "corrupt_evidence"}
        required = (
            "sequence",
            "request_id",
            "idempotency_key",
            "unix_time_ns",
            "previous_hash",
            "entry_hash",
            "payload",
        )
        if any(name not in entry for name in required):
            return {"ok": False, "reason": "truncated_evidence"}
        if entry.get("sequence") != index + 1:
            return {"ok": False, "reason": "concurrent_conflicting_state"}
        if entry.get("previous_hash") != previous:
            return {"ok": False, "reason": "audit_chain_corruption"}
        if not _is_hex64(entry.get("entry_hash")) or entry.get("entry_hash") != _entry_hash(entry):
            return {"ok": False, "reason": "corrupt_evidence"}
        timestamp = entry.get("unix_time_ns")
        if type(timestamp) is not int or timestamp < high_water:
            return {"ok": False, "reason": "clock_rollback"}
        request_id = entry.get("request_id")
        idempotency_key = entry.get("idempotency_key")
        if request_id in seen_requests:
            return {"ok": False, "reason": "replay"}
        if idempotency_key in seen_keys:
            return {"ok": False, "reason": "duplicate_request"}
        seen_requests.append(request_id)
        seen_keys.append(idempotency_key)
        previous = entry["entry_hash"]
        high_water = timestamp
    return {"ok": True, "reason": "chain_valid"}


def apply_fault_event(state, event):
    """Apply one disposable fault-class event. Never mutates caller state."""

    if not isinstance(state, dict) or not isinstance(event, dict):
        return {"result": FAIL_CLOSED, "reason": "schema_invalid"}, deepcopy(state) if isinstance(state, dict) else empty_fault_state()
    snapshot = deepcopy(state)
    incoming = deepcopy(event)
    if _contains_secret(incoming) or _contains_secret(snapshot):
        return {"result": FAIL_CLOSED, "reason": "secret_material_forbidden"}, snapshot

    fault_class = incoming.get("class")
    if fault_class not in FAULT_CLASSES:
        return {"result": FAIL_CLOSED, "reason": "unknown_fault_class"}, snapshot

    verified = verify_fault_state(snapshot)
    if not verified["ok"] and fault_class not in {
        "corrupt_evidence",
        "truncated_evidence",
        "audit_chain_corruption",
        "stale_evidence",
        "restart_incomplete_state",
    }:
        return {"result": FAIL_CLOSED, "reason": verified["reason"]}, snapshot

    request_id = incoming.get("request_id")
    idempotency_key = incoming.get("idempotency_key")
    timestamp = incoming.get("unix_time_ns")
    payload = incoming.get("payload", "public")

    if fault_class == "missing_dependency_evidence" or incoming.get("dependency_evidence") == "missing":
        return {"result": FAIL_CLOSED, "reason": "missing_dependency_evidence"}, snapshot
    if fault_class == "revoked_state_reuse" or request_id in snapshot.get("revoked_request_ids", []):
        return {"result": FAIL_CLOSED, "reason": "revoked_state_reuse"}, snapshot
    if request_id in snapshot.get("seen_request_ids", []) or fault_class == "replay":
        return {"result": FAIL_CLOSED, "reason": "replay"}, snapshot
    if idempotency_key in snapshot.get("seen_idempotency_keys", []) or fault_class == "duplicate_request":
        return {"result": FAIL_CLOSED, "reason": "duplicate_request"}, snapshot
    if type(timestamp) is not int:
        return {"result": FAIL_CLOSED, "reason": "schema_invalid"}, snapshot
    if timestamp < snapshot.get("high_water_ns", 0) or fault_class == "clock_rollback":
        return {"result": FAIL_CLOSED, "reason": "clock_rollback"}, snapshot

    if fault_class == "stale_evidence":
        return {"result": FAIL_CLOSED, "reason": "stale_evidence"}, snapshot
    if fault_class == "restart_incomplete_state":
        if snapshot.get("prepared") is None:
            snapshot["prepared"] = {"request_id": request_id, "committed": False}
        return {"result": FAIL_CLOSED, "reason": "restart_incomplete_state"}, snapshot
    if fault_class == "crash_before_commit":
        snapshot["prepared"] = {"request_id": request_id, "committed": False}
        return {"result": PREPARED_NOT_COMMITTED, "reason": "crash_before_commit"}, snapshot
    if fault_class == "concurrent_conflicting_state":
        return {"result": FAIL_CLOSED, "reason": "concurrent_conflicting_state"}, snapshot

    previous = (
        snapshot["entries"][-1]["entry_hash"] if snapshot["entries"] else GENESIS_PREVIOUS_HASH
    )
    sequence = incoming.get("sequence_override", len(snapshot["entries"]) + 1)
    entry = {
        "sequence": sequence,
        "request_id": request_id,
        "idempotency_key": idempotency_key,
        "unix_time_ns": timestamp,
        "previous_hash": previous,
        "payload": payload,
    }
    entry["entry_hash"] = _entry_hash(entry)

    if fault_class == "partial_write":
        snapshot["entries"].append({"sequence": sequence, "request_id": request_id})
        return {"result": FAIL_CLOSED, "reason": "partial_write"}, snapshot
    if fault_class == "truncated_evidence":
        snapshot["entries"].append({key: entry[key] for key in ("sequence", "request_id")})
        return {"result": FAIL_CLOSED, "reason": "truncated_evidence"}, snapshot
    if fault_class == "corrupt_evidence":
        entry["entry_hash"] = "0" * HEX64
        snapshot["entries"].append(entry)
        return {"result": FAIL_CLOSED, "reason": "corrupt_evidence"}, snapshot
    if fault_class == "audit_chain_corruption":
        entry["previous_hash"] = "1" * HEX64
        entry["entry_hash"] = _entry_hash(entry)
        snapshot["entries"].append(entry)
        return {"result": FAIL_CLOSED, "reason": "audit_chain_corruption"}, snapshot

    snapshot["entries"].append(entry)
    snapshot["high_water_ns"] = timestamp
    snapshot["seen_request_ids"].append(request_id)
    snapshot["seen_idempotency_keys"].append(idempotency_key)
    snapshot["commit_high_water"] = sequence
    snapshot["prepared"] = None
    if fault_class == "crash_after_commit":
        return {"result": COMMITTED_RETAINED, "reason": "crash_after_commit"}, snapshot
    return {"result": FAIL_CLOSED, "reason": "scenario_not_authorizing"}, snapshot


def _result(code, digest, reason):
    return {
        "result": code,
        "reason": reason,
        "evidence_digest": digest,
        "profile": PROFILE,
        "FAULT_RECOVERY": "UNRESOLVED",
        "F171_SIGNER_ELIGIBILITY_RESULT": "BLOCKED",
        "F177_FAULT_RECOVERY_EVIDENCE_BOUNDARY": "IMPLEMENTED",
        "KEY_GENERATION_PERMITTED": False,
        "KEY_IMPORT_PERMITTED": False,
        "BACKUP_PERMITTED": False,
        "SIGNER_RUNTIME_ACTIVE": False,
        "SIGNING": False,
        "BROADCAST": False,
        "SETTLEMENT": False,
        "NOT_INDEPENDENTLY_AUDITED": True,
    }


def evaluate_fault_recovery_evidence(evidence):
    """Evaluate public fault/recovery metadata. Never mutates caller input."""

    if not isinstance(evidence, dict):
        return _result(FAULT_INVALID, None, "schema_invalid")
    snapshot = deepcopy(evidence)
    digest = evidence_digest(snapshot)
    if _contains_secret(snapshot):
        return _result(FAULT_INVALID, digest, "secret_material_forbidden")
    if not _walk_public(snapshot):
        return _result(FAULT_INVALID, digest, "schema_invalid")

    classes = snapshot.get("fault_classes")
    if not isinstance(classes, dict):
        return _result(FAULT_INCOMPLETE, digest, "required_category_missing")
    for name in FAULT_CLASSES:
        block = classes.get(name)
        if not isinstance(block, dict) or not block:
            return _result(FAULT_INCOMPLETE, digest, "required_category_missing")
        if any(block.get(flag) is True for flag in RUNTIME_FLAGS):
            return _result(FAULT_INVALID, digest, "runtime_capability_assertion")

    authority = snapshot.get("authority_assertions")
    if isinstance(authority, dict) and any(authority.get(name) for name in PROTECTED_AUTHORITY):
        return _result(FAULT_INVALID, digest, "protocol_authority_assertion")

    audit = snapshot.get("audit_binding")
    if not isinstance(audit, dict):
        return _result(FAULT_INCOMPLETE, digest, "missing_audit_binding")
    if audit.get("profile") != AUDIT_PROFILE or not _is_hex64(audit.get("evidence_hash")):
        return _result(FAULT_INVALID, digest, "malformed_audit_binding")

    time_binding = snapshot.get("trusted_time_binding")
    if not isinstance(time_binding, dict):
        return _result(FAULT_INCOMPLETE, digest, "missing_trusted_time_binding")
    if time_binding.get("profile") != TIME_PROFILE or not _is_hex64(
        time_binding.get("evidence_hash")
    ):
        return _result(FAULT_INVALID, digest, "malformed_trusted_time_binding")

    if snapshot.get("FAULT_RECOVERY") in CLAIMED_READY:
        return _result(FAULT_INVALID, digest, "readiness_overclaim")

    remaining = snapshot.get("remaining_gaps")
    if not isinstance(remaining, dict):
        return _result(FAULT_INCOMPLETE, digest, "required_category_missing")
    for gap in REQUIRED_REMAINING_GAPS:
        if gap not in remaining:
            return _result(FAULT_INCOMPLETE, digest, "required_fault_gap_missing")
        status = remaining[gap]
        if status in CLAIMED_READY or status != "UNRESOLVED":
            return _result(FAULT_INVALID, digest, "unresolved_gap_claimed_resolved")

    return _result(BLOCKED_BY_FAULT_RECOVERY_GAPS, digest, "repository_fault_recovery_requirements_unsatisfied")
