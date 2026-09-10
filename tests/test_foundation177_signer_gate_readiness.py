# SPDX-License-Identifier: Apache-2.0
import ast
import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from coin.signer_custody_evidence import (
    BLOCKED_BY_UNRESOLVED_CUSTODY_DECISIONS,
    EVIDENCE_COMPLETE,
    UNRESOLVED_DECISIONS,
)
from coin.signer_fault_recovery_evidence import (
    BLOCKED_BY_FAULT_RECOVERY_GAPS,
    FAULT_COMPLETE,
)
from coin.signer_gate_readiness import (
    CUS_DECISION_INVENTORY,
    GATE_BLOCKED,
    GATE_INVALID,
    PROFILE,
    RECORDED_POLICY,
    committed_reassessment_inputs,
    evaluate_cus_decision_readiness,
    reassess_signer_gate,
)
from coin.signer_runtime_hardening_evidence import (
    BLOCKED_BY_RUNTIME_HARDENING_GAPS,
    HARDENING_COMPLETE,
)


ROOT = Path(__file__).resolve().parents[1]
IMPL_PATH = ROOT / "coin/signer_gate_readiness.py"
HARDENING_PATH = ROOT / "coin/signer_runtime_hardening_evidence.py"
FAULT_PATH = ROOT / "coin/signer_fault_recovery_evidence.py"
GATE_PATH = ROOT / "docs/l28_foundation177_signer_gate_completion_v0.1.json"
PROTOCOL_PATH = ROOT / "PROTOCOL.md"
TX_VALIDATION_PATH = ROOT / "coin/tx_validation.py"


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


def test_import_is_inert():
    assert PROFILE == "l28-signer-gate-readiness/v0.1"
    assert set(CUS_DECISION_INVENTORY) == set(UNRESOLVED_DECISIONS)


@pytest.mark.parametrize("decision_id", UNRESOLVED_DECISIONS)
def test_unresolved_cus_decisions_cannot_silently_become_resolved(decision_id):
    result = evaluate_cus_decision_readiness()
    record = result["inventory"][decision_id]
    assert record["decision_id"] == decision_id
    assert record["current_status"] == "UNRESOLVED"
    assert record["current_status"] not in {"RESOLVED", "PASS", "APPROVED"}
    assert record["activation_authority"] is False
    assert record["decision_class"] in {
        "SECURITY_EXPERT_DECISION_REQUIRED",
        "IMPLEMENTATION_EVIDENCE_REQUIRED_FIRST",
    }
    assert record["candidate_options"]
    assert record["required_public_evidence"]
    assert record["required_tests"]
    assert record["known_gaps"]
    assert record["dependencies"]
    claimed = evaluate_cus_decision_readiness(
        {"decision_overrides": {decision_id: "RESOLVED"}}
    )
    assert claimed["result"] == GATE_INVALID
    assert claimed["reason"] == "unresolved_cus_decision_claimed_resolved"
    assert claimed["inventory"][decision_id]["current_status"] == "UNRESOLVED"
    assert claimed["CUSTODY_READINESS"] == "UNRESOLVED"


def test_cus009_remains_implementation_evidence_required_first():
    result = evaluate_cus_decision_readiness()
    assert (
        result["inventory"]["LSOD-CUS-009"]["decision_class"]
        == "IMPLEMENTATION_EVIDENCE_REQUIRED_FIRST"
    )
    for decision_id in UNRESOLVED_DECISIONS:
        if decision_id == "LSOD-CUS-009":
            continue
        assert (
            result["inventory"][decision_id]["decision_class"]
            == "SECURITY_EXPERT_DECISION_REQUIRED"
        )


def test_recorded_policy_does_not_approve_remaining_decisions():
    result = evaluate_cus_decision_readiness()
    assert result["result"] == GATE_BLOCKED
    assert result["recorded_policy"]["LSOD-CUS-002"] == "none"
    assert result["recorded_policy"]["LSOD-CUS-008"] == "backup prohibited"
    assert result["recorded_policy"]["LSOD-CUS-012"] == "A"
    assert result["KEY_GENERATION_PERMITTED"] is False
    assert result["KEY_IMPORT_PERMITTED"] is False
    assert result["BACKUP_PERMITTED"] is False
    assert result["CUSTODY_READINESS"] == "UNRESOLVED"
    assert RECORDED_POLICY["KEY_GENERATION_PERMITTED"] is False


def test_secret_overrides_are_rejected():
    result = evaluate_cus_decision_readiness({"mnemonic": "forbidden"})
    assert result["result"] == GATE_INVALID
    assert result["inventory"]["LSOD-CUS-001"]["current_status"] == "UNRESOLVED"


def test_composite_reassessment_stays_blocked():
    inputs = committed_reassessment_inputs()
    original = deepcopy(inputs)
    result = reassess_signer_gate(inputs)
    assert inputs == original
    assert result["result"] == GATE_BLOCKED
    assert result["F171_SIGNER_ELIGIBILITY_RESULT"] == "BLOCKED"
    assert result["CUSTODY_READINESS"] == "UNRESOLVED"
    assert result["RUNTIME_HARDENING"] == "UNRESOLVED"
    assert result["FAULT_RECOVERY"] == "UNRESOLVED"
    assert result["F172_PRODUCTION_AUDIT_BACKEND"] == "RESOLVED"
    assert result["F173_PRODUCTION_TIME_BACKEND"] == "RESOLVED"
    assert result["F176_PUBLIC_CUSTODY_EVIDENCE_BOUNDARY"] == "IMPLEMENTED"
    assert result["F176_CUSTODY_EVIDENCE_RESULT"] == BLOCKED_BY_UNRESOLVED_CUSTODY_DECISIONS
    assert result["authorization_equals_validation"] is False
    assert result["eligibility_equals_invocation"] is False
    assert result["NOT_INDEPENDENTLY_AUDITED"] is True
    assert "ELIGIBLE" not in result["F171_SIGNER_ELIGIBILITY_RESULT"]


def test_valid_schemas_do_not_become_eligible():
    result = reassess_signer_gate()
    assert result["F171_SIGNER_ELIGIBILITY_RESULT"] == "BLOCKED"
    assert result["result"] != "ELIGIBLE_FOR_FUTURE_SIGNER_AUTHORIZATION_REVIEW"


def test_overclaimed_complete_results_are_invalid_and_still_blocked():
    for field, value, reason in (
        ("f176_custody_evidence_result", EVIDENCE_COMPLETE, "custody_readiness_overclaim"),
        ("f177_runtime_hardening_result", HARDENING_COMPLETE, "runtime_hardening_overclaim"),
        ("f177_fault_recovery_result", FAULT_COMPLETE, "fault_recovery_overclaim"),
    ):
        inputs = committed_reassessment_inputs()
        inputs[field] = value
        result = reassess_signer_gate(inputs)
        assert result["result"] == GATE_INVALID
        assert result["reason"] == reason
        assert result["F171_SIGNER_ELIGIBILITY_RESULT"] == "BLOCKED"


def test_authorization_and_eligibility_boundaries_are_preserved():
    auth = committed_reassessment_inputs()
    auth["authorization_equals_validation"] = True
    elig = committed_reassessment_inputs()
    elig["eligibility_equals_invocation"] = True
    assert reassess_signer_gate(auth)["reason"] == "authorization_equals_validation_forbidden"
    assert reassess_signer_gate(elig)["reason"] == "eligibility_equals_invocation_forbidden"


def test_default_reassessment_digest_is_deterministic():
    first = reassess_signer_gate()
    second = reassess_signer_gate()
    assert first["evidence_digest"] == second["evidence_digest"]


def test_gate_json_is_duplicate_free_and_does_not_overclaim():
    gate = load_json(GATE_PATH)
    for binding in gate["source_bindings"].values():
        assert sha256(ROOT / binding["path"]) == binding["sha256"]
    assert gate["baseline_commit"] == "85116da953505a0d784b9c234ae1e3ae1e615bf0"
    assert gate["CUSTODY_READINESS"] == "UNRESOLVED"
    assert gate["RUNTIME_HARDENING"] == "UNRESOLVED"
    assert gate["FAULT_RECOVERY"] == "UNRESOLVED"
    assert gate["F171_SIGNER_ELIGIBILITY_RESULT"] == "BLOCKED"
    assert gate["F172_PRODUCTION_AUDIT_BACKEND"] == "RESOLVED"
    assert gate["F173_PRODUCTION_TIME_BACKEND"] == "RESOLVED"
    assert gate["F176_PUBLIC_CUSTODY_EVIDENCE_BOUNDARY"] == "IMPLEMENTED"
    assert gate["NOT_INDEPENDENTLY_AUDITED"] is True
    assert gate["KEY_GENERATION_PERMITTED"] is False
    assert gate["KEY_IMPORT_PERMITTED"] is False
    assert gate["BACKUP_PERMITTED"] is False
    assert set(gate["unresolved_custody_decisions"]) == set(UNRESOLVED_DECISIONS)
    assert gate["protected_hashes"]["protocol_sha256"] == sha256(PROTOCOL_PATH)
    assert gate["protected_hashes"]["tx_validation_sha256"] == sha256(TX_VALIDATION_PATH)
    assert gate["security_review"]["BLOCKED"] == 0
    assert "Critical" not in gate.get("unresolved_defects", [])
    assert "High" not in gate.get("unresolved_defects", [])


def test_no_validator_signing_network_or_runtime_capability():
    source = IMPL_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = set()
    from_modules = set()
    calls = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
            from_modules.add(node.module)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                calls.add(node.func.attr)
            elif isinstance(node.func, ast.Name):
                calls.add(node.func.id)
    assert "tx_validation" not in from_modules
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
    assert {"sign", "broadcast", "mint", "settle", "connect", "Popen"}.isdisjoint(calls)
    assert "environ" not in source
    assert ".env" not in source
    assert "evaluate_signer_eligibility" not in calls
    for path in (IMPL_PATH, HARDENING_PATH, FAULT_PATH):
        text = path.read_text(encoding="utf-8")
        assert "validate_transaction" not in text or "never calls" in text
