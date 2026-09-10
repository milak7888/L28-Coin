# SPDX-License-Identifier: Apache-2.0
import ast
import hashlib
from copy import deepcopy
from pathlib import Path

import pytest

from coin.signer_runtime_hardening_evidence import (
    AUDIT_PROFILE,
    BLOCKED_BY_RUNTIME_HARDENING_GAPS,
    HARDENING_CATEGORIES,
    HARDENING_COMPLETE,
    HARDENING_INCOMPLETE,
    HARDENING_INVALID,
    PROFILE,
    REQUIRED_REMAINING_GAPS,
    TIME_PROFILE,
    RuntimeHardeningEvidenceError,
    canonical_bytes,
    evaluate_runtime_hardening_evidence,
    evidence_digest,
    load_public_evidence,
)


ROOT = Path(__file__).resolve().parents[1]
IMPL_PATH = ROOT / "coin/signer_runtime_hardening_evidence.py"
HASH_A = hashlib.sha256(b"f177-hardening-audit-ref").hexdigest()
HASH_T = hashlib.sha256(b"f177-hardening-time-ref").hexdigest()


def public_bundle(**overrides):
    bundle = {
        "process_isolation_evidence": {"status": "public_metadata_only"},
        "privilege_boundary_evidence": {"status": "public_metadata_only"},
        "resource_limit_evidence": {"status": "public_metadata_only"},
        "timeout_deadline_evidence": {"status": "public_metadata_only"},
        "crash_containment_evidence": {"status": "public_metadata_only"},
        "restart_policy_evidence": {"status": "public_metadata_only"},
        "concurrency_safety_evidence": {"status": "public_metadata_only"},
        "filesystem_permission_evidence": {"status": "public_metadata_only"},
        "configuration_immutability_evidence": {"status": "public_metadata_only"},
        "dependency_version_provenance": {"status": "public_metadata_only"},
        "audit_integration_evidence": {"profile": AUDIT_PROFILE, "evidence_hash": HASH_A},
        "trusted_time_integration_evidence": {
            "profile": TIME_PROFILE,
            "evidence_hash": HASH_T,
        },
        "non_activation_evidence": {
            "status": "non_activating",
            "signer_invoked": False,
            "runtime_active": False,
            "process_started": False,
            "server_started": False,
            "thread_started": False,
            "socket_opened": False,
        },
        "remaining_gaps": {name: "UNRESOLVED" for name in REQUIRED_REMAINING_GAPS},
    }
    bundle.update(overrides)
    return bundle


def test_import_is_inert():
    assert PROFILE == "l28-signer-runtime-hardening-evidence/v0.1"
    assert HARDENING_COMPLETE == "RUNTIME_HARDENING_EVIDENCE_COMPLETE"


def test_complete_public_bundle_is_blocked_not_resolved():
    bundle = public_bundle()
    original = deepcopy(bundle)
    result = evaluate_runtime_hardening_evidence(bundle)
    assert bundle == original
    assert result["result"] == BLOCKED_BY_RUNTIME_HARDENING_GAPS
    assert result["RUNTIME_HARDENING"] == "UNRESOLVED"
    assert result["F171_SIGNER_ELIGIBILITY_RESULT"] == "BLOCKED"
    assert result["result"] != HARDENING_COMPLETE
    assert result["NOT_INDEPENDENTLY_AUDITED"] is True


def test_canonical_digest_is_stable_and_changes_with_evidence():
    first = public_bundle()
    second = public_bundle()
    assert evidence_digest(first) == evidence_digest(second)
    assert evidence_digest(first) == hashlib.sha256(canonical_bytes(first)).hexdigest()
    second["process_isolation_evidence"] = {"status": "public_metadata_only", "note": "changed"}
    assert evidence_digest(first) != evidence_digest(second)
    result = evaluate_runtime_hardening_evidence(first)
    assert result["evidence_digest"] == evidence_digest(first)


def test_duplicate_json_keys_are_rejected():
    with pytest.raises(RuntimeHardeningEvidenceError, match="duplicate_json_key"):
        load_public_evidence('{"remaining_gaps":{},"remaining_gaps":{}}')


@pytest.mark.parametrize("category", HARDENING_CATEGORIES)
def test_missing_category_fails_closed(category):
    bundle = public_bundle()
    del bundle[category]
    result = evaluate_runtime_hardening_evidence(bundle)
    assert result["result"] == HARDENING_INCOMPLETE


def test_secret_fields_are_rejected_recursively():
    top = evaluate_runtime_hardening_evidence(public_bundle(private_key="forbidden"))
    nested = public_bundle()
    nested["process_isolation_evidence"] = {
        "status": "public_metadata_only",
        "mnemonic": "forbidden",
    }
    nested_result = evaluate_runtime_hardening_evidence(nested)
    locator = public_bundle()
    locator["filesystem_permission_evidence"] = {"key_path": "/tmp/not-inspected"}
    locator_result = evaluate_runtime_hardening_evidence(locator)
    assert top["result"] == HARDENING_INVALID
    assert nested_result["result"] == HARDENING_INVALID
    assert locator_result["result"] == HARDENING_INVALID
    assert top["reason"] == "secret_material_forbidden"


def test_runtime_activation_flags_are_rejected():
    bundle = public_bundle()
    bundle["non_activation_evidence"] = {
        "status": "non_activating",
        "runtime_active": True,
    }
    result = evaluate_runtime_hardening_evidence(bundle)
    assert result["result"] == HARDENING_INVALID
    assert result["reason"] == "runtime_capability_assertion"


def test_remaining_gaps_cannot_be_claimed_resolved():
    bundle = public_bundle()
    bundle["remaining_gaps"] = {name: "UNRESOLVED" for name in REQUIRED_REMAINING_GAPS}
    bundle["remaining_gaps"]["F122-G07"] = "RESOLVED"
    result = evaluate_runtime_hardening_evidence(bundle)
    assert result["result"] == HARDENING_INVALID
    assert result["reason"] == "unresolved_gap_claimed_resolved"
    overclaim = public_bundle(RUNTIME_HARDENING="RESOLVED")
    blocked = evaluate_runtime_hardening_evidence(overclaim)
    assert blocked["result"] == HARDENING_INVALID
    assert blocked["RUNTIME_HARDENING"] == "UNRESOLVED"


def test_missing_gap_fails_closed():
    bundle = public_bundle()
    del bundle["remaining_gaps"]["LSOD-OPS-007"]
    result = evaluate_runtime_hardening_evidence(bundle)
    assert result["result"] == HARDENING_INCOMPLETE


def test_protocol_authority_assertion_fails_closed():
    result = evaluate_runtime_hardening_evidence(
        public_bundle(authority_assertions={"issuance": True})
    )
    assert result["result"] == HARDENING_INVALID
    assert result["reason"] == "protocol_authority_assertion"


def test_non_dict_input_is_invalid():
    result = evaluate_runtime_hardening_evidence(None)
    assert result["result"] == HARDENING_INVALID


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
        "time",
    }.isdisjoint(imports)
    assert "validate_transaction" not in calls
    assert {"sign", "broadcast", "mint", "settle", "connect", "Popen"}.isdisjoint(calls)
    assert "environ" not in source
    assert ".env" not in source
