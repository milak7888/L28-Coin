# SPDX-License-Identifier: Apache-2.0
"""Public/non-secret runtime-hardening evidence evaluator.

Importing this module is inert. It never starts a process, server, thread,
or socket, never executes a subprocess, never signs, and never calls
coin.tx_validation.validate_transaction. It never marks RUNTIME_HARDENING
RESOLVED while repository-required F122-G07/G08 and LSOD-OPS gaps remain.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy


PROFILE = "l28-signer-runtime-hardening-evidence/v0.1"
AUDIT_PROFILE = "l28-signer-audit-log/v0.1"
TIME_PROFILE = "l28-signer-trusted-time/v0.1"

HARDENING_COMPLETE = "RUNTIME_HARDENING_EVIDENCE_COMPLETE"
HARDENING_INCOMPLETE = "RUNTIME_HARDENING_EVIDENCE_INCOMPLETE"
HARDENING_INVALID = "RUNTIME_HARDENING_EVIDENCE_INVALID"
BLOCKED_BY_RUNTIME_HARDENING_GAPS = "BLOCKED_BY_RUNTIME_HARDENING_GAPS"

HARDENING_CATEGORIES = (
    "process_isolation_evidence",
    "privilege_boundary_evidence",
    "resource_limit_evidence",
    "timeout_deadline_evidence",
    "crash_containment_evidence",
    "restart_policy_evidence",
    "concurrency_safety_evidence",
    "filesystem_permission_evidence",
    "configuration_immutability_evidence",
    "dependency_version_provenance",
    "audit_integration_evidence",
    "trusted_time_integration_evidence",
    "non_activation_evidence",
)

REQUIRED_REMAINING_GAPS = (
    "F122-G07",
    "F122-G08",
    "LSOD-OPS-003",
    "LSOD-OPS-004",
    "LSOD-OPS-005",
    "LSOD-OPS-006",
    "LSOD-OPS-007",
    "LSOD-OPS-008",
)

HEX64 = 64
RUNTIME_FLAGS = (
    "signer_invoked",
    "signing_attempted",
    "signature_created",
    "wallet_accessed",
    "keys_loaded",
    "runtime_active",
    "process_started",
    "server_started",
    "thread_started",
    "socket_opened",
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
    {"RESOLVED", "APPROVED", "PASS", "COMPLETE", HARDENING_COMPLETE}
)


class RuntimeHardeningEvidenceError(ValueError):
    """Fail-closed runtime-hardening evidence error; does not repair input."""


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
            raise RuntimeHardeningEvidenceError("duplicate_json_key")
        result[key] = value
    return result


def _reject_constant(value):
    raise RuntimeHardeningEvidenceError("schema_invalid")


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


def _result(code, digest, reason):
    return {
        "result": code,
        "reason": reason,
        "evidence_digest": digest,
        "profile": PROFILE,
        "RUNTIME_HARDENING": "UNRESOLVED",
        "F171_SIGNER_ELIGIBILITY_RESULT": "BLOCKED",
        "F177_RUNTIME_HARDENING_EVIDENCE_BOUNDARY": "IMPLEMENTED",
        "KEY_GENERATION_PERMITTED": False,
        "KEY_IMPORT_PERMITTED": False,
        "BACKUP_PERMITTED": False,
        "SIGNER_RUNTIME_ACTIVE": False,
        "SIGNING": False,
        "BROADCAST": False,
        "SETTLEMENT": False,
        "NOT_INDEPENDENTLY_AUDITED": True,
    }


def evaluate_runtime_hardening_evidence(evidence):
    """Evaluate public runtime-hardening metadata. Never mutates caller input."""

    if not isinstance(evidence, dict):
        return _result(HARDENING_INVALID, None, "schema_invalid")
    snapshot = deepcopy(evidence)
    digest = evidence_digest(snapshot)
    if _contains_secret(snapshot):
        return _result(HARDENING_INVALID, digest, "secret_material_forbidden")
    if not _walk_public(snapshot):
        return _result(HARDENING_INVALID, digest, "schema_invalid")

    missing = [name for name in HARDENING_CATEGORIES if name not in snapshot]
    if missing:
        return _result(HARDENING_INCOMPLETE, digest, "required_category_missing")

    for name in HARDENING_CATEGORIES:
        block = snapshot.get(name)
        if not isinstance(block, dict) or not block:
            return _result(HARDENING_INCOMPLETE, digest, "required_category_missing")
        if any(block.get(flag) is True for flag in RUNTIME_FLAGS):
            return _result(HARDENING_INVALID, digest, "runtime_capability_assertion")

    non_activation = snapshot.get("non_activation_evidence")
    for flag in RUNTIME_FLAGS:
        if non_activation.get(flag) is True:
            return _result(HARDENING_INVALID, digest, "runtime_capability_assertion")

    authority = snapshot.get("authority_assertions")
    if isinstance(authority, dict) and any(authority.get(name) for name in PROTECTED_AUTHORITY):
        return _result(HARDENING_INVALID, digest, "protocol_authority_assertion")

    audit = snapshot.get("audit_integration_evidence")
    if audit.get("profile") != AUDIT_PROFILE or not _is_hex64(audit.get("evidence_hash")):
        return _result(HARDENING_INVALID, digest, "malformed_audit_binding")

    time_binding = snapshot.get("trusted_time_integration_evidence")
    if time_binding.get("profile") != TIME_PROFILE or not _is_hex64(
        time_binding.get("evidence_hash")
    ):
        return _result(HARDENING_INVALID, digest, "malformed_trusted_time_binding")

    if snapshot.get("RUNTIME_HARDENING") in CLAIMED_READY:
        return _result(HARDENING_INVALID, digest, "readiness_overclaim")

    remaining = snapshot.get("remaining_gaps")
    if not isinstance(remaining, dict):
        return _result(HARDENING_INCOMPLETE, digest, "required_category_missing")
    for gap in REQUIRED_REMAINING_GAPS:
        if gap not in remaining:
            return _result(HARDENING_INCOMPLETE, digest, "required_hardening_gap_missing")
        status = remaining[gap]
        if status in CLAIMED_READY:
            return _result(HARDENING_INVALID, digest, "unresolved_gap_claimed_resolved")
        if status != "UNRESOLVED":
            return _result(HARDENING_INVALID, digest, "unresolved_gap_claimed_resolved")

    return _result(BLOCKED_BY_RUNTIME_HARDENING_GAPS, digest, "repository_hardening_requirements_unsatisfied")
