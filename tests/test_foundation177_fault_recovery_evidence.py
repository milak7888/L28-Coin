# SPDX-License-Identifier: Apache-2.0
import ast
import hashlib
from copy import deepcopy
from pathlib import Path

import pytest

from coin.signer_fault_recovery_evidence import (
    AUDIT_PROFILE,
    BLOCKED_BY_FAULT_RECOVERY_GAPS,
    COMMITTED_RETAINED,
    FAIL_CLOSED,
    FAULT_CLASSES,
    FAULT_COMPLETE,
    FAULT_INCOMPLETE,
    FAULT_INVALID,
    PREPARED_NOT_COMMITTED,
    PROFILE,
    REQUIRED_REMAINING_GAPS,
    TIME_PROFILE,
    FaultRecoveryEvidenceError,
    apply_fault_event,
    canonical_bytes,
    empty_fault_state,
    evaluate_fault_recovery_evidence,
    evidence_digest,
    load_public_evidence,
    verify_fault_state,
)


ROOT = Path(__file__).resolve().parents[1]
IMPL_PATH = ROOT / "coin/signer_fault_recovery_evidence.py"
HASH_A = hashlib.sha256(b"f177-fault-audit-ref").hexdigest()
HASH_T = hashlib.sha256(b"f177-fault-time-ref").hexdigest()


def public_bundle(**overrides):
    bundle = {
        "fault_classes": {
            name: {"status": "public_metadata_only"} for name in FAULT_CLASSES
        },
        "audit_binding": {"profile": AUDIT_PROFILE, "evidence_hash": HASH_A},
        "trusted_time_binding": {"profile": TIME_PROFILE, "evidence_hash": HASH_T},
        "remaining_gaps": {name: "UNRESOLVED" for name in REQUIRED_REMAINING_GAPS},
    }
    bundle.update(overrides)
    return bundle


def commit_event(request_id, key, timestamp, fault_class="crash_after_commit"):
    return {
        "class": fault_class,
        "request_id": request_id,
        "idempotency_key": key,
        "unix_time_ns": timestamp,
        "payload": "public",
        "dependency_evidence": "present",
    }


def test_import_is_inert():
    assert PROFILE == "l28-signer-fault-recovery-evidence/v0.1"
    assert FAULT_COMPLETE == "FAULT_RECOVERY_EVIDENCE_COMPLETE"
    assert empty_fault_state()["entries"] == []


def test_complete_public_bundle_is_blocked_not_resolved():
    bundle = public_bundle()
    original = deepcopy(bundle)
    result = evaluate_fault_recovery_evidence(bundle)
    assert bundle == original
    assert result["result"] == BLOCKED_BY_FAULT_RECOVERY_GAPS
    assert result["FAULT_RECOVERY"] == "UNRESOLVED"
    assert result["F171_SIGNER_ELIGIBILITY_RESULT"] == "BLOCKED"
    assert result["result"] != FAULT_COMPLETE
    assert result["NOT_INDEPENDENTLY_AUDITED"] is True


def test_canonical_digest_is_stable_and_input_not_mutated():
    first = public_bundle()
    second = public_bundle()
    assert evidence_digest(first) == evidence_digest(second)
    assert evidence_digest(first) == hashlib.sha256(canonical_bytes(first)).hexdigest()
    result = evaluate_fault_recovery_evidence(first)
    assert first == second
    assert result["evidence_digest"] == evidence_digest(first)


def test_duplicate_json_keys_are_rejected():
    with pytest.raises(FaultRecoveryEvidenceError, match="duplicate_json_key"):
        load_public_evidence('{"fault_classes":{},"fault_classes":{}}')


def test_missing_fault_class_fails_closed():
    bundle = public_bundle()
    del bundle["fault_classes"]["replay"]
    result = evaluate_fault_recovery_evidence(bundle)
    assert result["result"] == FAULT_INCOMPLETE


def test_secret_fields_are_rejected_recursively():
    top = evaluate_fault_recovery_evidence(public_bundle(seed="forbidden"))
    nested = public_bundle()
    nested["fault_classes"]["replay"] = {"status": "public_metadata_only", "xprv": "x"}
    nested_result = evaluate_fault_recovery_evidence(nested)
    assert top["result"] == FAULT_INVALID
    assert nested_result["result"] == FAULT_INVALID
    assert top["reason"] == "secret_material_forbidden"


def test_remaining_gaps_cannot_be_claimed_resolved():
    bundle = public_bundle()
    bundle["remaining_gaps"]["LSOD-GAT-004"] = "PASS"
    result = evaluate_fault_recovery_evidence(bundle)
    assert result["result"] == FAULT_INVALID
    overclaim = evaluate_fault_recovery_evidence(public_bundle(FAULT_RECOVERY="RESOLVED"))
    assert overclaim["result"] == FAULT_INVALID
    assert overclaim["FAULT_RECOVERY"] == "UNRESOLVED"


def test_partial_write_and_truncated_state_fail_closed():
    state = empty_fault_state()
    original = deepcopy(state)
    partial, after_partial = apply_fault_event(state, commit_event("r1", "k1", 10, "partial_write"))
    assert state == original
    assert partial["result"] == FAIL_CLOSED
    assert verify_fault_state(after_partial)["reason"] == "truncated_evidence"
    truncated, after_trunc = apply_fault_event(empty_fault_state(), commit_event("r2", "k2", 11, "truncated_evidence"))
    assert truncated["reason"] == "truncated_evidence"
    assert verify_fault_state(after_trunc)["ok"] is False


def test_corrupt_and_audit_chain_corruption_fail_closed():
    corrupt, after_corrupt = apply_fault_event(
        empty_fault_state(), commit_event("r3", "k3", 12, "corrupt_evidence")
    )
    assert corrupt["result"] == FAIL_CLOSED
    assert verify_fault_state(after_corrupt)["reason"] == "corrupt_evidence"
    broken, after_broken = apply_fault_event(
        empty_fault_state(), commit_event("r4", "k4", 13, "audit_chain_corruption")
    )
    assert broken["reason"] == "audit_chain_corruption"
    assert verify_fault_state(after_broken)["reason"] == "audit_chain_corruption"


def test_stale_replay_duplicate_and_clock_rollback_fail_closed():
    committed, state = apply_fault_event(empty_fault_state(), commit_event("r5", "k5", 100))
    assert committed["result"] == COMMITTED_RETAINED
    assert verify_fault_state(state)["ok"] is True
    stale, _ = apply_fault_event(state, commit_event("r6", "k6", 101, "stale_evidence"))
    replay, _ = apply_fault_event(state, commit_event("r5", "k7", 102, "replay"))
    duplicate, _ = apply_fault_event(state, commit_event("r7", "k5", 103, "duplicate_request"))
    rollback, _ = apply_fault_event(state, commit_event("r8", "k8", 50))
    explicit_rollback, _ = apply_fault_event(
        state, commit_event("r9", "k9", 200, "clock_rollback")
    )
    assert stale["reason"] == "stale_evidence"
    assert replay["reason"] == "replay"
    assert duplicate["reason"] == "duplicate_request"
    assert rollback["reason"] == "clock_rollback"
    assert explicit_rollback["reason"] == "clock_rollback"
    for outcome in (stale, replay, duplicate, rollback, explicit_rollback):
        assert outcome["result"] == FAIL_CLOSED


def test_crash_boundaries_are_deterministic():
    before, prepared = apply_fault_event(
        empty_fault_state(), commit_event("r10", "k10", 20, "crash_before_commit")
    )
    assert before["result"] == PREPARED_NOT_COMMITTED
    assert prepared["prepared"]["committed"] is False
    assert prepared["entries"] == []
    after, retained = apply_fault_event(
        empty_fault_state(), commit_event("r11", "k11", 21, "crash_after_commit")
    )
    assert after["result"] == COMMITTED_RETAINED
    assert verify_fault_state(retained)["ok"] is True
    assert retained["commit_high_water"] == 1
    restart, incomplete = apply_fault_event(
        prepared, commit_event("r12", "k12", 22, "restart_incomplete_state")
    )
    assert restart["result"] == FAIL_CLOSED
    assert restart["reason"] == "restart_incomplete_state"
    assert incomplete["prepared"]["committed"] is False


def test_concurrent_revoked_and_missing_dependency_fail_closed():
    concurrent, _ = apply_fault_event(
        empty_fault_state(), commit_event("r13", "k13", 30, "concurrent_conflicting_state")
    )
    seeded = empty_fault_state()
    seeded["revoked_request_ids"] = ["r-revoked"]
    revoked, _ = apply_fault_event(seeded, commit_event("r-revoked", "k14", 31, "revoked_state_reuse"))
    missing, _ = apply_fault_event(
        empty_fault_state(), commit_event("r15", "k15", 32, "missing_dependency_evidence")
    )
    assert concurrent["reason"] == "concurrent_conflicting_state"
    assert revoked["reason"] == "revoked_state_reuse"
    assert missing["reason"] == "missing_dependency_evidence"


def test_fault_event_does_not_mutate_caller_state():
    state = empty_fault_state()
    original = deepcopy(state)
    event = commit_event("r16", "k16", 40)
    event_original = deepcopy(event)
    apply_fault_event(state, event)
    assert state == original
    assert event == event_original


def test_no_validator_signing_network_or_runtime_capability():
    source = IMPL_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = set()
    calls = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                calls.add(node.func.attr)
            elif isinstance(node.func, ast.Name):
                calls.add(node.func.id)
    assert "coin" not in imports
    assert {
        "socket",
        "subprocess",
        "multiprocessing",
        "threading",
        "requests",
        "urllib",
        "http",
        "asyncio",
        "os",
        "tempfile",
    }.isdisjoint(imports)
    assert "validate_transaction" not in calls
    assert {"sign", "broadcast", "mint", "settle", "connect", "Popen"}.isdisjoint(calls)
    assert "environ" not in source
    assert ".env" not in source
