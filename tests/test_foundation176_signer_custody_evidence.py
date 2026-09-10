# SPDX-License-Identifier: Apache-2.0
import ast
import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from coin.signer_custody_evidence import (
    AUDIT_PROFILE,
    BLOCKED_BY_UNRESOLVED_CUSTODY_DECISIONS,
    EVIDENCE_COMPLETE,
    EVIDENCE_INCOMPLETE,
    EVIDENCE_INVALID,
    PROFILE,
    TIME_PROFILE,
    UNRESOLVED_DECISIONS,
    CustodyEvidenceError,
    canonical_bytes,
    evaluate_custody_evidence,
    evidence_digest,
    load_public_evidence,
)


ROOT = Path(__file__).resolve().parents[1]
IMPL_PATH = ROOT / "coin/signer_custody_evidence.py"
GATE_PATH = ROOT / "docs/l28_foundation176_custody_evidence_gate_v0.1.json"
HASH_A = hashlib.sha256(b"f176-audit-ref").hexdigest()
HASH_T = hashlib.sha256(b"f176-time-ref").hexdigest()


def reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        assert key not in result, key
        result[key] = value
    return result


def load_json(path):
    return json.loads(
        path.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicate_keys
    )


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def public_bundle(**overrides):
    bundle = {
        "custody_policy": {
            "LSOD-CUS-002": "none",
            "generation_permitted": False,
            "import_permitted": False,
            "LSOD-CUS-008": "backup prohibited",
            "backup_permitted": False,
            "recovery_from_backup_permitted": False,
            "LSOD-CUS-012": "A",
            "custody_evidence_scope": "PUBLIC_NON_SECRET_ONLY",
        },
        "isolation_evidence": {"status": "public_metadata_only", "keys_loaded": False},
        "access_control_evidence": {"status": "public_metadata_only"},
        "lifecycle_evidence": {"status": "public_metadata_only"},
        "revocation_evidence": {"status": "public_metadata_only"},
        "destruction_evidence": {"status": "public_metadata_only"},
        "compromise_response_evidence": {"status": "public_metadata_only"},
        "custody_verification_evidence": {"status": "public_metadata_only"},
        "audit_binding": {"profile": AUDIT_PROFILE, "evidence_hash": HASH_A},
        "trusted_time_binding": {"profile": TIME_PROFILE, "evidence_hash": HASH_T},
        "unresolved_decisions": {name: "UNRESOLVED" for name in UNRESOLVED_DECISIONS},
    }
    bundle.update(overrides)
    return bundle


def test_import_is_inert():
    assert PROFILE == "l28-signer-custody-evidence/v0.1"
    assert EVIDENCE_COMPLETE == "EVIDENCE_COMPLETE"


def test_valid_public_bundle_is_blocked_not_ready():
    bundle = public_bundle()
    original = deepcopy(bundle)
    result = evaluate_custody_evidence(bundle)
    assert bundle == original
    assert result["result"] == BLOCKED_BY_UNRESOLVED_CUSTODY_DECISIONS
    assert result["CUSTODY_READINESS"] == "UNRESOLVED"
    assert result["F171_SIGNER_ELIGIBILITY_RESULT"] == "BLOCKED"
    assert result["result"] != EVIDENCE_COMPLETE


def test_canonical_digest_is_stable_and_changes_with_evidence():
    first = public_bundle()
    second = public_bundle()
    assert evidence_digest(first) == evidence_digest(second)
    assert evidence_digest(first) == hashlib.sha256(canonical_bytes(first)).hexdigest()
    second["isolation_evidence"] = {"status": "public_metadata_only", "note": "changed"}
    assert evidence_digest(first) != evidence_digest(second)
    result = evaluate_custody_evidence(first)
    assert result["evidence_digest"] == evidence_digest(first)


def test_duplicate_json_keys_are_rejected():
    text = '{"custody_policy":{},"custody_policy":{}}'
    with pytest.raises(CustodyEvidenceError, match="duplicate_json_key"):
        load_public_evidence(text)


def test_secret_bearing_top_level_field_is_rejected():
    result = evaluate_custody_evidence(public_bundle(private_key="forbidden"))
    assert result["result"] == EVIDENCE_INVALID
    assert result["reason"] == "secret_material_forbidden"


def test_secret_bearing_nested_field_is_rejected():
    bundle = public_bundle()
    bundle["isolation_evidence"] = {"status": "public_metadata_only", "mnemonic": "forbidden"}
    result = evaluate_custody_evidence(bundle)
    assert result["result"] == EVIDENCE_INVALID
    assert result["reason"] == "secret_material_forbidden"


def test_key_material_locator_is_rejected():
    bundle = public_bundle()
    bundle["lifecycle_evidence"] = {"key_path": "/tmp/not-inspected"}
    result = evaluate_custody_evidence(bundle)
    assert result["result"] == EVIDENCE_INVALID
    assert result["reason"] == "secret_material_forbidden"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("generation_permitted", True),
        ("import_permitted", True),
        ("backup_permitted", True),
        ("recovery_from_backup_permitted", True),
    ],
)
def test_enabled_key_paths_are_rejected(field, value):
    bundle = public_bundle()
    bundle["custody_policy"] = dict(bundle["custody_policy"], **{field: value})
    result = evaluate_custody_evidence(bundle)
    assert result["result"] == EVIDENCE_INVALID
    assert result["reason"] == "contradictory_enabled_key_path"


def test_cus012_scope_outside_a_is_rejected():
    bundle = public_bundle()
    bundle["custody_policy"] = dict(
        bundle["custody_policy"],
        **{"LSOD-CUS-012": "B", "custody_evidence_scope": "SIMULATED"},
    )
    result = evaluate_custody_evidence(bundle)
    assert result["result"] == EVIDENCE_INVALID
    assert result["reason"] == "invalid_cus012_scope"


def test_missing_audit_binding_fails_closed():
    bundle = public_bundle()
    del bundle["audit_binding"]
    result = evaluate_custody_evidence(bundle)
    assert result["result"] == EVIDENCE_INCOMPLETE


def test_missing_trusted_time_binding_fails_closed():
    bundle = public_bundle()
    del bundle["trusted_time_binding"]
    result = evaluate_custody_evidence(bundle)
    assert result["result"] == EVIDENCE_INCOMPLETE


def test_malformed_hashes_are_rejected():
    bundle = public_bundle()
    bundle["audit_binding"] = {"profile": AUDIT_PROFILE, "evidence_hash": "not-a-hash"}
    result = evaluate_custody_evidence(bundle)
    assert result["result"] == EVIDENCE_INVALID
    assert result["reason"] == "malformed_evidence_hash"


def test_unresolved_decisions_cannot_be_claimed_resolved():
    bundle = public_bundle()
    bundle["unresolved_decisions"] = {
        name: "UNRESOLVED" for name in UNRESOLVED_DECISIONS
    }
    bundle["unresolved_decisions"]["LSOD-CUS-001"] = "RESOLVED"
    result = evaluate_custody_evidence(bundle)
    assert result["result"] == EVIDENCE_INVALID
    assert result["reason"] == "unresolved_decision_claimed_resolved"
    complete = public_bundle()
    blocked = evaluate_custody_evidence(complete)
    assert blocked["result"] == BLOCKED_BY_UNRESOLVED_CUSTODY_DECISIONS
    for name in UNRESOLVED_DECISIONS:
        assert complete["unresolved_decisions"][name] == "UNRESOLVED"


def test_non_dict_input_is_invalid():
    result = evaluate_custody_evidence(None)
    assert result["result"] == EVIDENCE_INVALID


def test_malformed_boolean_and_protocol_authority_fail_closed():
    bundle = public_bundle()
    bundle["custody_policy"] = dict(bundle["custody_policy"], generation_permitted=0)
    result = evaluate_custody_evidence(bundle)
    assert result["result"] == EVIDENCE_INVALID
    assert result["reason"] == "malformed_boolean"
    asserted = public_bundle(authority_assertions={"issuance": True})
    result = evaluate_custody_evidence(asserted)
    assert result["result"] == EVIDENCE_INVALID
    assert result["reason"] == "protocol_authority_assertion"


def test_no_validator_signing_wallet_or_network_capability():
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
    }.isdisjoint(imports)
    assert "validate_transaction" not in calls
    assert {"sign", "broadcast", "mint", "settle", "connect"}.isdisjoint(calls)
    assert "environ" not in source
    assert ".env" not in source


def test_gate_json_is_duplicate_free_and_does_not_overclaim():
    gate = load_json(GATE_PATH)
    for binding in gate["source_bindings"].values():
        assert sha256(ROOT / binding["path"]) == binding["sha256"]
    assert gate["F176_PUBLIC_CUSTODY_EVIDENCE_BOUNDARY"] == "IMPLEMENTED"
    assert gate["CUSTODY_READINESS"] == "UNRESOLVED"
    assert gate["F171_SIGNER_ELIGIBILITY_RESULT"] == "BLOCKED"
    assert gate["NOT_INDEPENDENTLY_AUDITED"] is True
    assert gate["secret_material_allowed"] is False
    assert gate["key_operations_allowed"] is False
    assert gate["security_review"] == {
        "PASS": 7,
        "GAP": 0,
        "BLOCKED": 0,
        "COMMIT_READY": True,
    }
    assert gate["current_policy_bindings"]["LSOD-CUS-002"] == "none"
    assert gate["current_policy_bindings"]["LSOD-CUS-008"] == "backup prohibited"
    assert gate["current_policy_bindings"]["LSOD-CUS-012"] == "A"
    assert set(gate["unresolved_custody_decisions"]) == set(UNRESOLVED_DECISIONS)
