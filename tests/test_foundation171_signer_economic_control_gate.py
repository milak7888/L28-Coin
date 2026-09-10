# SPDX-License-Identifier: Apache-2.0
import ast
import hashlib
import importlib.util
import json
from copy import deepcopy
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "tests/foundation171_signer_economic_control_gate.py"
GATE_PATH = ROOT / "docs/l28_foundation171_signer_economic_control_gate_v0.1.json"
REVIEW_PATH = ROOT / "docs/foundation171_signer_economic_control_gate_v0.1.md"
F170_MODEL_PATH = ROOT / "tests/foundation170_forward_path_decision.py"


def load_model():
    spec = importlib.util.spec_from_file_location("f171_gate", MODEL_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


model = load_model()


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


def code_of(result):
    return result["F171_SIGNER_ELIGIBILITY_RESULT"]


def assert_non_activating(result):
    assert result["F170_OPERATOR_SELECTION"] == "OPTION_B"
    assert result["F171_SIGNER_RUNTIME_ACTIVE"] is False
    assert result["F171_SIGNING"] is False
    assert result["F171_BROADCAST"] is False
    assert result["F171_SETTLEMENT"] is False
    assert result["F171_PROTOCOL_AUTHORITY"] is False
    assert result["canonical_validator"] == "coin.tx_validation.validate_transaction"
    assert result["eligibility_equals_validation"] is False
    assert result["authorization_equals_validation"] is False
    assert result["signer_invoked"] is False


def complete_test_local_evidence(**overrides):
    evidence = {
        "F170_OPERATOR_SELECTION": model.OPTION_B,
        "production_time_backend": "TEST_LOCAL_EVIDENCE_CONTRACT_ONLY",
        "production_audit_backend": "TEST_LOCAL_EVIDENCE_CONTRACT_ONLY",
        "caller_identity_evidence": {
            "caller_id": "caller-fixture-public-001",
            "authentication_status": "verified",
            "scope_request_id": "req-001",
            "public_evidence_only": True,
        },
        "operator_authorization_evidence": {
            "operator_id": "operator-fixture-public-001",
            "authentication_status": "verified",
            "decision": "approved",
            "request_id": "req-001",
            "intent_id": "intent-001",
            "scope_matches": True,
        },
        "authorization_evidence": {
            "authorization_status": "allowed",
            "intent_id": "intent-001",
            "request_id": "req-001",
        },
        "economic_policy": {
            "policy_status": "active",
            "authentication_status": "verified",
            "asset_id": "L28",
            "per_transaction_limit": 100,
            "cumulative_limit": 250,
            "approval_threshold": 1,
            "authorized_approver_ids": ["approver-public-001"],
            "protocol_override_allowed": False,
            "unlimited_spend_allowed": False,
        },
        "approvals": [
            {
                "approver_id": "approver-public-001",
                "authentication_status": "verified",
                "decision": "approved",
                "request_id": "req-001",
                "intent_id": "intent-001",
            }
        ],
        "replay_evidence": {
            "available": True,
            "request_id": "req-001",
            "intent_id": "intent-001",
            "idempotency_key": "idem-001",
            "status": "fresh",
            "atomic_transition_status": "ready",
        },
        "time_evidence": {
            "source": model.TRUSTED_TIME_SOURCE,
            "authentication_status": "verified",
            "evaluation_time": 1700000100,
            "system_clock_read": False,
            "network_clock_read": False,
        },
        "audit_evidence": {
            "available": True,
            "evidence_profile": model.AUDIT_PROFILE,
            "public_evidence_only": True,
            "audit_id": "audit-001",
        },
        "proposed_transaction": {
            "sender": "agent-payer-public-001",
            "receiver": "agent-payee-public-001",
            "amount": 50,
            "type": "transfer",
            "coinbase": False,
        },
        "custody_readiness_evidence": {"status": "resolved", "keys_loaded": False},
        "runtime_hardening_evidence": {"status": "resolved"},
        "fault_recovery_evidence": {"status": "resolved"},
        "prior_accept_state": model.empty_accept_state(),
        "protected_economics": {
            "hard_cap_l28": 28000000,
            "emission_ceiling_l28": 11130000,
            "historically_mined_l28": 2824584,
            "treasury_locked_l28": 500000,
            "circulating_snapshot_l28": 2324584,
            "halving_interval": 210000,
            "reward_schedule": [28, 14, 7, 3, 1, 0],
            "historical_mined_through_entry": 100877,
            "next_canonical_height_after_bootstrap": 100878,
            "issuance_mechanism": "coinbase_only",
            "canonical_height_authority": "consensus_derived",
        },
        "authority_assertions": {name: False for name in model.PROTECTED_AUTHORITY},
        "non_execution": {name: False for name in model.NON_EXECUTION_FLAGS},
    }
    evidence.update(overrides)
    return evidence


def evaluate(evidence):
    original = deepcopy(evidence)
    result, next_state = model.evaluate_signer_eligibility(evidence)
    assert evidence == original
    assert_non_activating(result)
    return result, next_state


def test_committed_state_records_option_b_and_blocks_eligibility():
    result = model.committed_gate_result()
    assert_non_activating(result)
    assert code_of(result) == model.BLOCKED
    assert result["reason"] == "production_time_backend_unresolved"
    committed = model.committed_evidence()
    assert committed["F170_OPERATOR_SELECTION"] == "OPTION_B"
    assert committed["production_time_backend"] == "UNRESOLVED"
    assert committed["production_audit_backend"] == "UNRESOLVED"
    assert committed["custody_readiness_evidence"]["keys_loaded"] is False


def test_complete_test_local_bundle_is_eligible_for_future_review_only():
    result, next_state = evaluate(complete_test_local_evidence())
    assert code_of(result) == model.ELIGIBLE
    assert result["reason"] == "signer_eligible_public_projection"
    assert next_state == {
        "request_ids": ("req-001",),
        "idempotency_keys": ("idem-001",),
        "authorized_total": 50,
    }


@pytest.mark.parametrize(
    ("override", "code", "reason"),
    [
        (
            {"caller_identity_evidence": None},
            model.NOT_ELIGIBLE,
            "identity_evidence_unavailable",
        ),
        (
            {
                "caller_identity_evidence": {
                    "caller_id": "unknown-caller",
                    "authentication_status": "unknown",
                }
            },
            model.NOT_ELIGIBLE,
            "identity_evidence_unauthenticated",
        ),
        ({"approvals": None}, model.NOT_ELIGIBLE, "approval_policy_unavailable"),
        ({"approvals": []}, model.NOT_ELIGIBLE, "approval_policy_unavailable"),
        (
            {
                "economic_policy": {
                    "policy_status": "active",
                    "authentication_status": "verified",
                    "asset_id": "L28",
                    "per_transaction_limit": "unlimited",
                    "cumulative_limit": 250,
                    "approval_threshold": 1,
                    "authorized_approver_ids": ["approver-public-001"],
                    "protocol_override_allowed": False,
                    "unlimited_spend_allowed": False,
                }
            },
            model.NOT_ELIGIBLE,
            "schema_invalid",
        ),
        (
            {
                "replay_evidence": {
                    "available": True,
                    "request_id": "req-001",
                    "intent_id": "intent-001",
                    "idempotency_key": "idem-001",
                    "status": "replayed",
                    "atomic_transition_status": "ready",
                }
            },
            model.NOT_ELIGIBLE,
            "replay_detected",
        ),
        ({"prior_accept_state": None}, model.NOT_ELIGIBLE, "replay_state_unavailable"),
        ({"time_evidence": None}, model.NOT_ELIGIBLE, "evaluation_time_unavailable"),
        (
            {
                "time_evidence": {
                    "source": "system_clock",
                    "authentication_status": "verified",
                    "evaluation_time": 1700000100,
                    "system_clock_read": True,
                    "network_clock_read": False,
                }
            },
            model.NOT_ELIGIBLE,
            "evaluation_time_unavailable",
        ),
        ({"audit_evidence": None}, model.NOT_ELIGIBLE, "audit_lineage_invalid"),
        (
            {"custody_readiness_evidence": {"status": "unresolved", "keys_loaded": False}},
            model.BLOCKED,
            "custody_readiness_unresolved",
        ),
        (
            {"runtime_hardening_evidence": {"status": "unresolved"}},
            model.BLOCKED,
            "runtime_hardening_unresolved",
        ),
        (
            {"fault_recovery_evidence": {"status": "unresolved"}},
            model.BLOCKED,
            "fault_recovery_unresolved",
        ),
    ],
)
def test_required_evidence_failures_are_fail_closed(override, code, reason):
    result, _state = evaluate(complete_test_local_evidence(**override))
    assert code_of(result) == code
    assert result["reason"] == reason


def test_duplicate_request_cannot_become_eligible_twice():
    first, next_state = evaluate(complete_test_local_evidence())
    assert code_of(first) == model.ELIGIBLE
    replayed, unchanged = evaluate(
        complete_test_local_evidence(prior_accept_state=next_state)
    )
    assert code_of(replayed) == model.NOT_ELIGIBLE
    assert replayed["reason"] == "replay_detected"
    assert unchanged == next_state


def test_duplicate_idempotency_key_is_rejected():
    prior = {
        "request_ids": ("req-other",),
        "idempotency_keys": ("idem-001",),
        "authorized_total": 10,
    }
    result, next_state = evaluate(complete_test_local_evidence(prior_accept_state=prior))
    assert code_of(result) == model.NOT_ELIGIBLE
    assert result["reason"] == "replay_detected"
    assert next_state == prior


def test_cumulative_spend_violation_is_rejected_without_recording():
    prior = {
        "request_ids": ("req-prior",),
        "idempotency_keys": ("idem-prior",),
        "authorized_total": 220,
    }
    result, next_state = evaluate(complete_test_local_evidence(prior_accept_state=prior))
    assert code_of(result) == model.NOT_ELIGIBLE
    assert result["reason"] == "cumulative_limit_exceeded"
    assert next_state == prior


def test_gate_never_mints_signs_broadcasts_settles_or_bypasses_validator():
    source = MODEL_PATH.read_text(encoding="utf-8")
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
    assert "socket" not in imports
    assert "subprocess" not in imports
    assert "validate_transaction" not in calls
    assert "sign" not in calls
    assert "broadcast" not in calls
    assert "mint" not in calls
    assert "settle" not in calls
    result, _state = evaluate(complete_test_local_evidence())
    assert result["canonical_validator"] == "coin.tx_validation.validate_transaction"
    assert "validate_transaction(" not in source
    assert "mint(" not in source


def test_protocol_override_and_execution_claims_cannot_become_eligible():
    mutated = complete_test_local_evidence()
    mutated["protected_economics"]["hard_cap_l28"] = 28000001
    result, _state = evaluate(mutated)
    assert code_of(result) == model.NOT_ELIGIBLE
    assert result["reason"] == "protocol_override_forbidden"

    override = complete_test_local_evidence(
        authority_assertions={
            **{name: False for name in model.PROTECTED_AUTHORITY},
            "issuance_override_allowed": True,
        }
    )
    result, _state = evaluate(override)
    assert code_of(result) == model.NOT_ELIGIBLE

    execution = complete_test_local_evidence(
        non_execution={
            **{name: False for name in model.NON_EXECUTION_FLAGS},
            "signing_attempted": True,
        }
    )
    result, _state = evaluate(execution)
    assert code_of(result) == model.NOT_ELIGIBLE
    assert result["reason"] == "execution_forbidden"


def test_secret_material_and_loaded_keys_fail_closed():
    result, _state = evaluate(complete_test_local_evidence(private_key="forbidden"))
    assert code_of(result) == model.NOT_ELIGIBLE
    assert result["reason"] == "secret_material_forbidden"
    result, _state = evaluate(
        complete_test_local_evidence(
            custody_readiness_evidence={"status": "resolved", "keys_loaded": True}
        )
    )
    assert code_of(result) == model.NOT_ELIGIBLE
    assert result["reason"] == "secret_material_forbidden"


def test_option_a_or_pending_selection_cannot_open_the_gate():
    result, _state = evaluate(
        complete_test_local_evidence(F170_OPERATOR_SELECTION="OPTION_A")
    )
    assert code_of(result) == model.BLOCKED
    result, _state = evaluate(
        complete_test_local_evidence(F170_OPERATOR_SELECTION="PENDING_OPERATOR_SELECTION")
    )
    assert code_of(result) == model.BLOCKED


def test_gate_is_duplicate_free_hash_bound_and_records_option_b():
    gate = load_json(GATE_PATH)
    for binding in gate["source_bindings"].values():
        assert sha256(ROOT / binding["path"]) == binding["sha256"]
    assert gate["decision_state"]["F170_OPERATOR_SELECTION"] == "OPTION_B"
    assert gate["decision_state"]["F171_SIGNER_ELIGIBILITY_RESULT"] == model.BLOCKED
    assert gate["decision_state"]["F171_SIGNER_RUNTIME_ACTIVE"] is False
    assert gate["decision_state"]["F171_SIGNING"] is False
    assert gate["decision_state"]["F171_BROADCAST"] is False
    assert gate["decision_state"]["F171_SETTLEMENT"] is False
    assert gate["decision_state"]["F171_PROTOCOL_AUTHORITY"] is False
    assert gate["protected_hashes"]["protocol_sha256"] == sha256(ROOT / "PROTOCOL.md")
    assert gate["protected_hashes"]["tx_validation_sha256"] == sha256(
        ROOT / "coin/tx_validation.py"
    )


def test_security_rules_protocol_validator_and_authority_remain_protected():
    gate = load_json(GATE_PATH)
    rules = gate["security_rules"]
    assert rules["protocol_version"] == "1.0.0"
    assert rules["protocol_frozen"] is True
    assert rules["coinbase_only_issuance"] is True
    assert rules["canonical_validator"] == "coin.tx_validation.validate_transaction"
    assert rules["immutable_economics_and_history"] is True
    assert rules["bitcoin_role"] == "EXTERNAL_EVIDENCE_ONLY"
    assert rules["signer_activation_allowed"] is False
    assert rules["signing_allowed"] is False
    assert rules["broadcast_allowed"] is False
    assert rules["settlement_allowed"] is False
    assert not any(gate["protected_authority"].values())
    economics = gate["protected_economics"]
    assert economics == {
        "hard_cap_l28": 28000000,
        "emission_ceiling_l28": 11130000,
        "historically_mined_l28": 2824584,
        "treasury_locked_l28": 500000,
        "circulating_snapshot_l28": 2324584,
        "halving_interval": 210000,
        "reward_schedule": [28, 14, 7, 3, 1, 0],
        "historical_mined_through_entry": 100877,
        "next_canonical_height_after_bootstrap": 100878,
    }


def test_new_python_files_have_no_runtime_capability():
    forbidden_imports = {
        "multiprocessing",
        "socket",
        "subprocess",
        "threading",
        "asyncio",
        "concurrent",
        "selectors",
        "requests",
        "urllib",
        "http",
        "coin",
    }
    forbidden_calls = {
        "start",
        "spawn",
        "fork",
        "connect",
        "bind",
        "listen",
        "accept",
        "send",
        "recv",
        "terminate",
        "kill",
        "sign",
        "broadcast",
        "mint",
        "settle",
        "validate_transaction",
    }
    for path in (MODEL_PATH, Path(__file__), F170_MODEL_PATH):
        tree = ast.parse(path.read_text(encoding="utf-8"))
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
        assert forbidden_imports.isdisjoint(imports), path
        assert forbidden_calls.isdisjoint(calls), path


def test_security_review_and_exact_candidate_scope():
    gate = load_json(GATE_PATH)
    assert gate["candidate_scope"] == [
        "docs/foundation171_signer_economic_control_gate_v0.1.md",
        "docs/l28_foundation171_signer_economic_control_gate_v0.1.json",
        "tests/foundation171_signer_economic_control_gate.py",
        "tests/test_foundation171_signer_economic_control_gate.py",
    ]
    assert gate["security_review"] == {
        "PASS": 5,
        "GAP": 0,
        "BLOCKED": 0,
        "COMMIT_READY": True,
    }
    review = REVIEW_PATH.read_text(encoding="utf-8")
    assert "PASS 5 / GAP 0 / BLOCKED 0" in review
    assert "F170_OPERATOR_SELECTION=OPTION_B" in review
    assert "F171_SIGNER_ELIGIBILITY_RESULT=BLOCKED" in review
    assert "F171_SIGNER_RUNTIME_ACTIVE=false" in review
