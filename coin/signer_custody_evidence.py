# SPDX-License-Identifier: Apache-2.0
"""Public/non-secret custody-evidence evaluator.

Importing this module is inert. It never creates, loads, or simulates keys,
never signs, never accesses wallets, never activates runtime, and never calls
coin.tx_validation.validate_transaction. It never marks CUSTODY_READINESS
RESOLVED.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy


PROFILE = "l28-signer-custody-evidence/v0.1"
AUDIT_PROFILE = "l28-signer-audit-log/v0.1"
TIME_PROFILE = "l28-signer-trusted-time/v0.1"

EVIDENCE_COMPLETE = "EVIDENCE_COMPLETE"
EVIDENCE_INCOMPLETE = "EVIDENCE_INCOMPLETE"
EVIDENCE_INVALID = "EVIDENCE_INVALID"
BLOCKED_BY_UNRESOLVED_CUSTODY_DECISIONS = "BLOCKED_BY_UNRESOLVED_CUSTODY_DECISIONS"

REQUIRED_CATEGORIES = (
    "custody_policy",
    "isolation_evidence",
    "access_control_evidence",
    "lifecycle_evidence",
    "revocation_evidence",
    "destruction_evidence",
    "compromise_response_evidence",
    "custody_verification_evidence",
    "audit_binding",
    "trusted_time_binding",
    "unresolved_decisions",
)

UNRESOLVED_DECISIONS = (
    "LSOD-CUS-001",
    "LSOD-CUS-003",
    "LSOD-CUS-004",
    "LSOD-CUS-005",
    "LSOD-CUS-006",
    "LSOD-CUS-007",
    "LSOD-CUS-009",
    "LSOD-CUS-010",
    "LSOD-CUS-011",
)

REQUIRED_POLICY = {
    "LSOD-CUS-002": "none",
    "generation_permitted": False,
    "import_permitted": False,
    "LSOD-CUS-008": "backup prohibited",
    "backup_permitted": False,
    "recovery_from_backup_permitted": False,
    "LSOD-CUS-012": "A",
    "custody_evidence_scope": "PUBLIC_NON_SECRET_ONLY",
}

HEX64 = 64
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


class CustodyEvidenceError(ValueError):
    """Fail-closed custody-evidence error; does not repair caller input."""


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
            raise CustodyEvidenceError("duplicate_json_key")
        result[key] = value
    return result


def _reject_constant(value):
    raise CustodyEvidenceError("schema_invalid")


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
        "CUSTODY_READINESS": "UNRESOLVED",
        "F171_SIGNER_ELIGIBILITY_RESULT": "BLOCKED",
        "F176_PUBLIC_CUSTODY_EVIDENCE_BOUNDARY": "IMPLEMENTED",
        "KEY_GENERATION_PERMITTED": False,
        "KEY_IMPORT_PERMITTED": False,
        "BACKUP_PERMITTED": False,
        "SIGNER_RUNTIME_ACTIVE": False,
        "SIGNING": False,
        "BROADCAST": False,
        "SETTLEMENT": False,
        "NOT_INDEPENDENTLY_AUDITED": True,
    }


def evaluate_custody_evidence(evidence):
    """Evaluate a public custody-evidence bundle. Never mutates caller input."""

    if not isinstance(evidence, dict):
        return _result(EVIDENCE_INVALID, None, "schema_invalid")
    snapshot = deepcopy(evidence)
    digest = evidence_digest(snapshot)
    if _contains_secret(snapshot):
        return _result(EVIDENCE_INVALID, digest, "secret_material_forbidden")
    if not _walk_public(snapshot):
        return _result(EVIDENCE_INVALID, digest, "schema_invalid")

    missing = [name for name in REQUIRED_CATEGORIES if name not in snapshot]
    if missing:
        return _result(EVIDENCE_INCOMPLETE, digest, "required_category_missing")

    policy = snapshot.get("custody_policy")
    if not isinstance(policy, dict):
        return _result(EVIDENCE_INVALID, digest, "schema_invalid")
    for key, expected in REQUIRED_POLICY.items():
        if key not in policy:
            return _result(EVIDENCE_INCOMPLETE, digest, "missing_required_policy_binding")
        actual = policy[key]
        if key.endswith("_permitted") or key == "recovery_from_backup_permitted":
            if type(actual) is not bool:
                return _result(EVIDENCE_INVALID, digest, "malformed_boolean")
            if actual is True:
                return _result(EVIDENCE_INVALID, digest, "contradictory_enabled_key_path")
            if actual is not expected:
                return _result(EVIDENCE_INVALID, digest, "contradictory_enabled_key_path")
        elif actual != expected:
            if key == "LSOD-CUS-012" or key == "custody_evidence_scope":
                return _result(EVIDENCE_INVALID, digest, "invalid_cus012_scope")
            return _result(EVIDENCE_INVALID, digest, "contradictory_enabled_key_path")

    for name in (
        "isolation_evidence",
        "access_control_evidence",
        "lifecycle_evidence",
        "revocation_evidence",
        "destruction_evidence",
        "compromise_response_evidence",
        "custody_verification_evidence",
    ):
        block = snapshot.get(name)
        if not isinstance(block, dict) or not block:
            return _result(EVIDENCE_INCOMPLETE, digest, "required_category_missing")
        if any(block.get(flag) is True for flag in RUNTIME_FLAGS):
            return _result(EVIDENCE_INVALID, digest, "runtime_capability_assertion")

    authority = snapshot.get("authority_assertions")
    if isinstance(authority, dict) and any(authority.get(name) for name in PROTECTED_AUTHORITY):
        return _result(EVIDENCE_INVALID, digest, "protocol_authority_assertion")

    audit = snapshot.get("audit_binding")
    if not isinstance(audit, dict):
        return _result(EVIDENCE_INCOMPLETE, digest, "missing_audit_binding")
    if audit.get("profile") != AUDIT_PROFILE:
        return _result(EVIDENCE_INVALID, digest, "malformed_audit_binding")
    if not _is_hex64(audit.get("evidence_hash")):
        return _result(EVIDENCE_INVALID, digest, "malformed_evidence_hash")

    time_binding = snapshot.get("trusted_time_binding")
    if not isinstance(time_binding, dict):
        return _result(EVIDENCE_INCOMPLETE, digest, "missing_trusted_time_binding")
    if time_binding.get("profile") != TIME_PROFILE:
        return _result(EVIDENCE_INVALID, digest, "malformed_trusted_time_binding")
    if not _is_hex64(time_binding.get("evidence_hash")):
        return _result(EVIDENCE_INVALID, digest, "malformed_evidence_hash")

    unresolved = snapshot.get("unresolved_decisions")
    if not isinstance(unresolved, dict):
        return _result(EVIDENCE_INCOMPLETE, digest, "required_category_missing")
    for decision in UNRESOLVED_DECISIONS:
        if decision not in unresolved:
            return _result(EVIDENCE_INCOMPLETE, digest, "unresolved_decision_missing")
        status = unresolved[decision]
        if status in {"RESOLVED", "APPROVED", "PASS", EVIDENCE_COMPLETE}:
            return _result(EVIDENCE_INVALID, digest, "unresolved_decision_claimed_resolved")
        if status != "UNRESOLVED":
            return _result(EVIDENCE_INVALID, digest, "unresolved_decision_claimed_resolved")

    return _result(BLOCKED_BY_UNRESOLVED_CUSTODY_DECISIONS, digest, "required_custody_decisions_unresolved")
