# SPDX-License-Identifier: Apache-2.0
import json

import pytest

from coin.foundation168_execution_evidence import (
    EvidenceFailure,
    evidence_is_hash_valid,
    finalize_evidence,
    persist_evidence,
    sanitized_exception,
)


def minimal_evidence():
    return {"terminal_state": "EXECUTION_ABORT", "exception_type": "RuntimeError"}


def test_finalize_and_atomic_persistence_are_deterministic(tmp_path):
    first = finalize_evidence(minimal_evidence())
    second = finalize_evidence(minimal_evidence())
    assert first == second
    assert evidence_is_hash_valid(first)
    path = tmp_path / "evidence.json"
    persisted = persist_evidence(path, minimal_evidence())
    assert json.loads(path.read_text(encoding="utf-8")) == persisted
    assert not (tmp_path / "evidence.json.tmp").exists()


@pytest.mark.parametrize(
    "key",
    ("private_key", "seed_phrase", "wallet_path", "rpc_data", "auth_token", "environment"),
)
def test_sensitive_or_authority_material_is_rejected(key):
    evidence = minimal_evidence()
    evidence[key] = "forbidden"
    with pytest.raises(EvidenceFailure, match="SENSITIVE"):
        finalize_evidence(evidence)


def test_invalid_terminal_state_and_tampering_are_rejected():
    with pytest.raises(EvidenceFailure, match="INVALID_TERMINAL_STATE"):
        finalize_evidence({"terminal_state": "RETRY"})
    evidence = finalize_evidence(minimal_evidence())
    evidence["exception_type"] = "Changed"
    assert evidence_is_hash_valid(evidence) is False


def test_exception_representation_never_persists_raw_message_values():
    error_type, representation = sanitized_exception(
        RuntimeError("credential=do-not-persist")
    )
    assert error_type == "RuntimeError"
    assert representation == "RuntimeError(<redacted>)"
    assert "do-not-persist" not in representation
