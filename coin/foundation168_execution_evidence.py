# SPDX-License-Identifier: Apache-2.0
"""Deterministic structured evidence construction and persistence for F168."""

import hashlib
import json
from pathlib import Path


TERMINAL_STATES = (
    "SUCCESS",
    "EXECUTION_ABORT",
    "CLEANUP_FAILURE",
    "TERMINALIZATION_FAILURE",
)
FORBIDDEN_KEY_FRAGMENTS = (
    "secret", "credential", "private_key", "seed", "mnemonic", "xprv",
    "wallet", "rpc", "token", "infrastructure", "environment", "env",
)


class EvidenceFailure(ValueError):
    pass


def sanitized_exception(error):
    """Return type plus an allowlisted internal code, never a raw error message."""

    if error is None:
        return None, None
    error_type = type(error).__name__
    code = getattr(error, "code", None)
    if (
        isinstance(code, str)
        and 0 < len(code) <= 160
        and all(character.isalnum() or character in "_:-" for character in code)
    ):
        return error_type, error_type + "(" + repr(code) + ")"
    return error_type, error_type + "(<redacted>)"


def _reject_sensitive_keys(value):
    if isinstance(value, dict):
        for key, item in value.items():
            normalized = str(key).lower()
            if any(fragment in normalized for fragment in FORBIDDEN_KEY_FRAGMENTS):
                raise EvidenceFailure("FORBIDDEN_SENSITIVE_EVIDENCE_KEY")
            _reject_sensitive_keys(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _reject_sensitive_keys(item)


def evidence_fingerprint(evidence):
    unsigned = dict(evidence)
    unsigned.pop("evidence_sha256", None)
    encoded = json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()


def finalize_evidence(evidence):
    if not isinstance(evidence, dict):
        raise EvidenceFailure("EVIDENCE_MAPPING_REQUIRED")
    _reject_sensitive_keys(evidence)
    terminal = evidence.get("terminal_state")
    if terminal not in TERMINAL_STATES:
        raise EvidenceFailure("INVALID_TERMINAL_STATE")
    result = dict(evidence)
    result["evidence_sha256"] = evidence_fingerprint(result)
    return result


def persist_evidence(path, evidence):
    """Persist finalized evidence atomically; called only after future execution."""

    finalized = finalize_evidence(evidence)
    target = Path(path)
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(
        json.dumps(finalized, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    temporary.replace(target)
    return finalized


def evidence_is_hash_valid(evidence):
    return (
        isinstance(evidence, dict)
        and isinstance(evidence.get("evidence_sha256"), str)
        and evidence["evidence_sha256"] == evidence_fingerprint(evidence)
    )
